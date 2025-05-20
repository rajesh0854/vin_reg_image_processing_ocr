from flask import Flask, request, jsonify
from flask_caching import Cache
import os
import json
import uuid
import time
import redis
from loguru import logger
from dotenv import load_dotenv
load_dotenv()
from flask_cors import CORS

# Import project modules
from process_data import get_data
from settings import FLASK_CONN, PROCESS_UTIL, REDIS_DB

# Logging Setup
logger.remove()
logger.add("logs/app_server.log", format="{time} {level} {message}",
           diagnose=False, backtrace=False, level="INFO", rotation="1024 MB")

# Redis Setup
redis_db = redis.Redis(host=REDIS_DB.IP, port=REDIS_DB.PORT, db=REDIS_DB.DB)

# App Configuration
app = Flask(__name__, template_folder=FLASK_CONN.TEMPLATE_FOLDER)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['TEMPLATES_AUTO_RELOAD'] = FLASK_CONN.TEMPLATE_AUTO_RELOAD
app.jinja_env.auto_reload = FLASK_CONN.AUTO_RELOAD
cache = Cache(app)
CORS(app)

TEMP_DIR = PROCESS_UTIL.TMP_DIR

# Utility Function: Generate Unique Request ID
def generate_request_id():
    unique_id = str(uuid.uuid4())
    counter = redis_db.incr('request_counter')
    request_id = f"req_{unique_id}_{counter}"
    redis_db.set('vinreg', json.dumps({'requestid': unique_id}))
    return request_id

# Health Check Routes
@app.route("/ping")
def ping():
    return "API connected successfully!"

# Main API Endpoint
@app.route("/vin_reg_check", methods=['POST'])
def vin_reg_check():
    request_id = generate_request_id()
    start_time = time.time()

    json_contents = request.get_json(force=True)
    check_type = json_contents.get('check_type')
    user_id = json_contents.get('user_id')

    logger.info(f"Request ID: {request_id}, Check Type: {check_type}")

    if check_type not in ['reg', 'vin']:
        logger.error(f"Invalid check_type. User ID: {user_id}, Check Type: {check_type}")
        result_json = {'result': ['fail', 'invalid value for check_type']}
    else:
        result_json = get_data(json_contents, request_id)
        image_path = os.path.join(TEMP_DIR, f"{request_id}decoded.jpg")
        if os.path.isfile(image_path):
            os.remove(image_path)
        #image_path = os.path.join(TEMP_DIR, f"{request_id+'.jpg'}")


    duration = round(time.time() - start_time, 3)
    logger.info(f"Request processed in {duration} seconds.")
    logger.info("------------ End of Process ------------")
    
    print(result_json)

    return jsonify(result_json)

# Entry Point
if __name__ == '__main__':
    try:
        app.run(debug=FLASK_CONN.DEBUG, host=FLASK_CONN.HOST, port=FLASK_CONN.PORT, threaded=True)
    except Exception as e:
        logger.critical(f"Flask server failed to start: {e}")







# from flask import Flask,render_template, request,jsonify
# from flask_caching import Cache
# from werkzeug.utils import secure_filename
# from werkzeug.datastructures import  FileStorage
# import os
# import json
# from process_data import get_data
# import time
# from datetime import datetime
# import uuid
# #Settings file
# from settings import FLASK_CONN,PROCESS_UTIL,REDIS_DB
# import redis
# from redis.commands.json.path import Path

# from loguru import logger
# import sys
# logger.remove(0)
# logger.add("logs/app_server.log", format="{time} {level} {message}",diagnose=False,backtrace=False,level='INFO',rotation="1024 MB")
# #logger.add("logs/app_server.log", rotation="1024 MB") 


# #redis db to store temporary data
# redis_db = redis.Redis(host=REDIS_DB.IP, port=REDIS_DB.PORT, db=REDIS_DB.DB)

# TEMP_DIR=PROCESS_UTIL.TMP_DIR

# def generate_requestID():
#     unique_id = str(uuid.uuid4())
#     counter = int(redis_db.incr('request_counter'))
#     requestid = f"req_{unique_id}_{counter}"
#     st = redis_db.set('vinreg', json.dumps({'requestid': unique_id}))
#     return requestid

# config={'CACHE_TYPE': 'SimpleCache'} 


# app = Flask(__name__,template_folder=FLASK_CONN.TEMPLATE_FOLDER)
# app.config.from_mapping(config)
# cache = Cache(app)
# #app.logger.setLevel(logger.INFO)



# @app.route("/test")
# def hello_world():
#     app.logger.info('Hello World')
#     return "Hello World!"

# @app.route("/ping") 
# def image_url():
#     return('Working..!')

# @app.route("/vin_reg_check",methods=['POST','GET'])
# def vin_reg_check():
#     new_req_id=generate_requestID()
#     start_time = time.time()
#     if request.method=='POST':
#         json_contents=request.get_json()
#         logger.info(f"request id generated : {new_req_id}, checktype: {json_contents['check_type']}")
#         #json_contents=json.loads(json_contents)
#         if json_contents['check_type'] not in ['reg','vin']:
#             result_json={'result':['fail','invalid value for check_type']}
#             user_id=json_contents['user_id']
#             chktype_val=json_contents['check_type']
#             logger.error(f'inavlid value for check_type detected. user id : {user_id},check type value : {chktype_val}')
#         else:
#             result_json=get_data(json_contents,new_req_id)
#             if os.path.isfile(TEMP_DIR+new_req_id+'decoded.jpg'):
#                 os.remove(TEMP_DIR+new_req_id+'decoded.jpg')
#     else:
#         logger.info('request method not allowed.')
#     end_time = time.time()
#     tot_time=(end_time-start_time).__round__(3)
#     logger.info(f"request processed in:{tot_time} seconds")    
#     logger.info('------------------end of process------------------')
#     return jsonify(result_json)



# if __name__ == '__main__':
#     int()
#     app.jinja_env.auto_reload = FLASK_CONN.AUTO_RELOAD
#     app.config['TEMPLATES_AUTO_RELOAD'] = FLASK_CONN.TEMPLATE_AUTO_RELOAD
#     app.run(debug=FLASK_CONN.DEBUG, host=FLASK_CONN.HOST, port=FLASK_CONN.PORT,threaded=True)
#     logger.critical("Flask server is down")

