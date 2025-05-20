
import cv2
import os
from loguru import logger
 #verify image format and size #1:Image size should less than 1 MB #2:Image format should be either .jpg or .jpeg
def verifyfile(image_file_path):
  image_size_threshold=1024 #in KB
  array_img=cv2.imread(image_file_path)
  image_file_sizeKB=round(os.path.getsize(image_file_path)/1024)
  image_status=0 if array_img is None else 1
  if os.path.exists(image_file_path):
    file_exist='true'
    if image_status == int(1) and image_file_sizeKB < image_size_threshold:
      imagesize_imgstatus='pass'
    else:
      imagesize_imgstatus='fail'
      logger.error('Error occured during image verification:Either image is corrupted or size>1024KB')
  else:
    file_exist='false'
    logger.error('Error occured during image verification:Image file not exist in the specified directory')
  return file_exist,imagesize_imgstatus






