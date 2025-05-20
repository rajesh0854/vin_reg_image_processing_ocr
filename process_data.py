
import base64
import os
from imagecheck import verifyfile
from settings import PROCESS_UTIL,DBCONN,AZURE_STORAGE
from vinmodel.vin_det_yolov7 import vinimgprocess
import mysql.connector
from mysql.connector import Error
import logging
import cv2
from azure.storage.blob import BlobServiceClient
from trans import predictor
import json
from settings import PROCESS_UTIL
from datetime import datetime
from reg_ocr_process import plate_det_fn, text_det_fn, parseq_ocr_fn
from dotenv import load_dotenv
load_dotenv()



logging.basicConfig(filename=PROCESS_UTIL.LOGGING_DIR+'aimodels.log', level=logging.INFO, format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

temp_img_save_dir=os.getenv('TMP_IMG_SVAE_DIR')

store_reqfile=PROCESS_UTIL.STORE_REQ_ID
hsrp_image_save=PROCESS_UTIL.SAVE_HSRP_IMG_DIR
vin_image_save=PROCESS_UTIL.SAVE_VIN_IMG_DIR
logging_dir=PROCESS_UTIL.LOGGING_DIR
storage_account_key=AZURE_STORAGE.STORAGE_ACCOUNT_KEY
storage_account_name=AZURE_STORAGE.STORAGE_ACCOUNT_NAME
connection_string=AZURE_STORAGE.CONNECTION_STRING
hsrp_container_name=AZURE_STORAGE.HSRP_CONTAINER_NAME
vin_container_name=AZURE_STORAGE.VIN_CONTAINER_NAME
vin_predictor=PROCESS_UTIL.VIN_PRED_MODEL
hsrp_predictor=PROCESS_UTIL.HSRP_PRED_MODEL


def decodebase64string(encodestring,temp_img_name):
    try:
        #Decode base64 string and save image
        image_64_decode = base64.b64decode(encodestring)

    except ValueError:
        logging.error('invalid base64 string')
        return 'false'
    else:
        image_result = open(temp_img_save_dir+temp_img_name, 'wb')
        image_result.write(image_64_decode)
        image_result.close()

        stat1,stat2=verifyfile(temp_img_save_dir+temp_img_name)
        imagestatus='true' if stat1=='true' and stat2 == 'pass' else 'false'
        logging.info(f'image file verification process completed: {imagestatus}')
    return imagestatus


def get_data(json_content, request_id):
    date_time_stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_img_name = f"{request_id}_{date_time_stamp}.jpg"

    # Parse core input values
    base64_string = json_content.get('image')
    check_type = json_content.get('check_type')
    user_id = json_content.get('user_id')
    dealer_id = json_content.get('dealer_id')
    
    name_to_save_img=f"{request_id}_{dealer_id}_{user_id}_{date_time_stamp}.jpg"
    
    # Optional key check
    save_img = json_content.get('save_img', 'true').lower()
    save_data = json_content.get('save_data', 'true').lower()
    
    # Decode image
    if decodebase64string(base64_string,temp_img_name) != 'true':
        logging.error('Image is corrupted, invalid format or too large.')
        return {'result': ['fail', 'invalid image']}
    

    if check_type == 'reg':
        predict_func = reg_process(temp_img_name)
    elif check_type == 'vin':
        predict_func,vinprediction = vinimagepredict(temp_img_name,request_id)
    else:
        logging.error(f"Invalid check_type: {check_type}")
        return {'result': ['fail', 'invalid check_type']}
    
    saved_location = save_image(str(check_type), name_to_save_img, predict_func['image_accuracy'], predict_func['image_type'], temp_img_name) if save_img == 'true' else 'no_save'
    final_json_response = generate_response(json_content, predict_func, str(check_type), saved_location, name_to_save_img, request_id)
    logging.info('Final JSON response generated.')
    
    # Delete the temporary image file
    if os.path.isfile(temp_img_save_dir+temp_img_name):
        os.remove(temp_img_save_dir+temp_img_name)
    
    dbstatus = store_predict_results(json_content, final_json_response) if save_data == 'true' else 'no_save'
    if dbstatus == 'success':
        logging.info('Prediction results stored in database.')
        return final_json_response
    elif dbstatus == 'no_save':
        logging.info('Prediction results not stored in database.')
        #final_json_response['result'] = ['pass']
        return final_json_response
    else:
        logging.error(f"Failed to store results in database. Status: {dbstatus}")
        final_json_response['result'] = ['fail', 'database connection failed']
        return final_json_response
        
    


def create_prediction_results(image_type, result, image_accuracy, read_value, data_accuracy):
    return {
        "image_type": image_type,
        "result": result,
        "image_accuracy": image_accuracy,
        "read_value": read_value,
        "data_accuracy": data_accuracy
    }

def reg_process(temp_img_name):
    prediction, accuracy = predictor(temp_img_save_dir + temp_img_name, 'reg')
    print(prediction, accuracy)
    # Early return if the result is not 'real'
    if prediction != 'real':
        return create_prediction_results(prediction, "['fail','fake image']", accuracy, "null", 0)

    test_image = temp_img_save_dir + temp_img_name
    cv2_array = cv2.imread(test_image)
    
    # Process plate detection
    cropped_det_plate, err = plate_det_fn(cv2_array)
    if err:
        logging.error(f"Error in plate detection: {err}")
        return create_prediction_results(prediction, "['fail','incorrect reg value']", accuracy, "null", 0)

    # Process text detection
    all_text_crops, err = text_det_fn(cropped_det_plate)
    if err:
        logging.error(f"Error in text detection: {err}")
        return create_prediction_results(prediction, "['fail','incorrect reg value']", accuracy, "null", 0)

    # Process OCR
    output, all_text, err = parseq_ocr_fn(all_text_crops)
    if err:
        logging.error(f"Error in OCR process: {err}")
        return create_prediction_results(prediction, "['fail','incorrect reg value']", accuracy, "null", 0)

    # Success case
    logging.info('ROI detection and OCR process completed for reg')
    
    if len(output) <= 8 or len(output) >= 12:
        return create_prediction_results(prediction, ["fail", "incorrect reg value"], accuracy, "null", 0)
    else:
        return create_prediction_results(prediction, ["pass"], accuracy, output, 0.9)


##vin image prediction
def vinimagepredict(temp_img_name,request_id):
    vinprediction,resultacc=predictor(temp_img_save_dir+temp_img_name,'vin')
    if vinprediction == 'real':
        vin_res=vinocr_process(temp_img_name,request_id)
        j_result={
        'image_type':vinprediction,
        'image_accuracy':resultacc,
        'read_value':vin_res['read_value'],
        'data_accuracy':vin_res['data_accuracy'],
        'result':vin_res['result']
        }

    else:
        j_result={
        'image_type':vinprediction,
        'image_accuracy':resultacc,
        "read_value":'null',
        'data_accuracy':0,
        'result':['fail','fake image']
        }

    logging.info('vin image prediction process completed')
    return j_result,vinprediction #check_result=(real/fake/bw/color)



##if check_type is vin
def vinocr_process(temp_img_name,request_id):
    vinreadvalue,vinreadacc=vinimgprocess(temp_img_save_dir+temp_img_name,request_id)
    vinreadvalue=vinreadvalue.upper()
    vinreadvalue=vinreadvalue.replace(vinreadvalue[0:3],'MBL')
    firstfiveletters=vinreadvalue[0:5]
    fivelettersverify='true' if firstfiveletters == 'MBLJA' or firstfiveletters == 'MBLHA' else 'false'
    if len(vinreadvalue) == 17 and fivelettersverify == 'true':
        finalvintext={'read_value':vinreadvalue,
                      'result':['pass']
                      }
    else:
        logging.info(f'recognised {len(vinreadvalue)} characters.true characters count is 17')
        finalvintext={'read_value':vinreadvalue,
                      'result':['fail','incorrect vin detection']
                      }

    prediction_results={
    'read_value':finalvintext['read_value'],
    'data_accuracy':vinreadacc,
    'result':finalvintext['result']
    }
    return prediction_results



def uploadToBlobStorage(container_name, file_path, filename):
    try:
        # Initialize blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)

        # Upload the file
        with open(file_path, "rb") as data:
            # Upload the blob and check if the upload is successful
            upload_result = blob_client.upload_blob(data, overwrite=True)  # overwrite=True ensures the file gets replaced if it already exists
            logging.info(f"Uploaded {filename}. Blob upload result: {upload_result}")

        # Construct the image URL
        img_url = f"https://{storage_account_name}.blob.core.windows.net/{container_name}/{filename}"

    except Exception as ex:
        # Log the error with detailed message
        logging.error(f"Failed to upload image to container: {container_name}. Error: {str(ex)}")
        img_url = ""

    return img_url



def save_image(image_type, filename, accuracy, image_pred,temp_img_name):
    # Validate inputs
    if image_pred not in ['real', 'replay', 'color', 'bw']:
        logging.error(f"Invalid image_pred value: {image_pred}")
        return "null"

    # Define container and Redis key
    if image_type == 'vin':
        container_name = vin_container_name
        folder_prefix = 'vin'
    elif image_type == 'reg':
        container_name = hsrp_container_name
        folder_prefix = 'hsrp'
    else:
        logging.error(f"Invalid image_type: {image_type}")
        return "null"

    # Determine confidence level
    confidence_level = 'high' if accuracy >= 0.9 else 'low'

    # Compose blob path
    blob_path = f"{confidence_level}_{folder_prefix}/{image_pred}/{filename}"

    # Upload and return URL
    return uploadToBlobStorage(
        container_name=container_name,
        file_path=temp_img_save_dir + temp_img_name,
        filename=blob_path,
    )


def save_reg(filename, accuracy, image_pred,temp_img_name):
    return save_image('hsrp', filename, accuracy, image_pred,temp_img_name)

def save_vin(filename, accuracy, image_pred,temp_img_name):
    return save_image('vin', filename, accuracy, image_pred,temp_img_name)



def save_images(filename,imgtype,accuracy,image_pred,temp_img_name):
    if imgtype == 'reg':
        save_loc=save_reg(filename,accuracy,image_pred,temp_img_name)
    else:
        save_loc=save_vin(filename,accuracy,image_pred,temp_img_name)
    return save_loc



def generate_response(json_contents, vin_reg_res, check_type, img_location, rename_img_name, request_id):
    return {
        "check_type": check_type,
        "dealer_id": json_contents.get("dealer_id"),
        "user_id": json_contents.get("user_id"),
        "request_id": request_id,
        "image_name": rename_img_name,
        "image_location": img_location,
        "image_type": vin_reg_res.get("image_type"),
        "image_accuracy": round(vin_reg_res.get("image_accuracy", 0), 2),
        "read_value": vin_reg_res.get("read_value"),
        "data_accuracy": vin_reg_res.get("data_accuracy"),
        "result": vin_reg_res.get("result"),
    }



#store results in database
def store_predict_results(requestjson,responsejson):

    client=requestjson['client']
    vechile=requestjson['vehicle']
    chk_type=requestjson['check_type']
    usrid=requestjson['user_id']
    dlrid=requestjson['dealer_id']
    znid=requestjson['zone_id']
    req=responsejson['request_id']
    res=responsejson['result']
    imgacc=responsejson['image_accuracy']
    readval=responsejson['read_value']
    datacc=responsejson['data_accuracy']
    imgname=responsejson['image_name']
    img_type=responsejson['image_type']
    image_location=responsejson['image_location']


    #imgloc=responsejson['image_location']

    SQL=f"""INSERT INTO {DBCONN.TBL}(created_date,client,vechile,check_type,user_id,dealer_id,zone_id,request_id,result,image_accuracy,read_value,data_accuracy,image_name,image_location)
            VALUES (now(),'{client}','{vechile}','{chk_type}','{usrid}','{dlrid}','{znid}','{req}','{img_type}',{imgacc},'{readval}',{datacc},'{imgname}','{image_location}');
          """
    try:
      connection = mysql.connector.connect(host=DBCONN.HOST,
                                         database=DBCONN.DB,
                                         user=DBCONN.USER,
                                         password=DBCONN.PASSWORD,
                                         port=DBCONN.PORT)
    except mysql.connector.Error as error:
      logging.error(f'database connection failed.error:{error}')
      logging.info(f'query:{SQL}')
      dbstatus='failure'

    else:
      cursor = connection.cursor()
      cursor.execute(SQL)
      connection.commit()
      cursor.close()
      connection.close()
      logging.info('mysql connection closed!')
      dbstatus='success'
    return dbstatus




'''
pip install azure-storage-blob azure-identity
'''
