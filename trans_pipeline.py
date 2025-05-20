from transformers import AutoModelForImageClassification, AutoImageProcessor
from PIL import Image
import torch
from transformers import pipeline
from os import listdir
from os.path import isfile, join
from settings import TRANS_MODELS

from loguru import logger



#hsrp model load

reg_image_processor = AutoImageProcessor.from_pretrained(TRANS_MODELS.REG_CLS_MODEL_DIR)
reg_model = AutoModelForImageClassification.from_pretrained(TRANS_MODELS.REG_CLS_MODEL_DIR)

reg_pipe = pipeline("image-classification", 
                model=reg_model,
                feature_extractor=reg_image_processor,device=0)  

#vin model load

vin_image_processor = AutoImageProcessor.from_pretrained(TRANS_MODELS.VIN_CLS_MODEL_DIR)
vin_model = AutoModelForImageClassification.from_pretrained(TRANS_MODELS.VIN_CLS_MODEL_DIR)

vin_pipe = pipeline("image-classification", 
                model=vin_model,
                feature_extractor=vin_image_processor,device=0)  


@logger.catch
def predict_image(img_type,img_file_path):
    try:
        if img_type == 'reg':
            result=reg_pipe(img_file_path)
            max_score_dict = max(result, key=lambda x: x['score'])
            pred_result=max_score_dict['label']
            pred_score=max_score_dict['score']
            errors='none'
        elif img_type=='vin':
            result=vin_pipe(img_file_path)
            max_score_dict = max(result, key=lambda x: x['score'])
            pred_result=max_score_dict['label']
            pred_score=max_score_dict['score']
            errors='none'
    except Exception as e:
        errors=e
        logger.error(e)
        pred_result='none'
        pred_score='none'

    return pred_result,pred_score,errors


