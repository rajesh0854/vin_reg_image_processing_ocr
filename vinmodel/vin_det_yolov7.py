import os
import sys
import re
from pathlib import Path
import cv2
import torch
import numpy as np
import torch.backends.cudnn as cudnn
from PIL import Image
from paddleocr import PaddleOCR
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

sys.path.insert(1, '/datadisk/CODE_MAIN/vinmodel')

from models.experimental import attempt_load
from utils.general import check_img_size, non_max_suppression, scale_coords
from utils.torch_utils import select_device, time_synchronized

# Settings file
from settings import YOLOv7_CONFIG_VIN, PADDLEOCR_CONFIG

# Constants from settings
WEIGHT_FILE = YOLOv7_CONFIG_VIN.WEIGHT_FILE
CROPPED_IMAGE_DIR = YOLOv7_CONFIG_VIN.CROP_IMG_SAVE_DIR
DET_MODEL_DIR = PADDLEOCR_CONFIG.DET_MODEL
REC_MODEL_DIR = PADDLEOCR_CONFIG.REC_MODEL
CLS_MODEL_DIR = PADDLEOCR_CONFIG.CLS_MODEL
TMP_DIR = os.getenv('TMP_IMG_SVAE_DIR')

# Initialize model globally to avoid reloading for each request
def initialize_model():
    """Initialize YOLOv7 model once to improve performance"""
    opt = {
        "weights": WEIGHT_FILE,
        "img-size": 640,
        "conf-thres": 0.25,
        "iou-thres": 0.45,
        "device": '0',
        "classes": None  # Filter by class, if needed
    }
    
    device = select_device(opt['device'])
    half = device.type != 'cpu'
    model = attempt_load(opt['weights'], map_location=device)
    stride = int(model.stride.max())
    imgsz = check_img_size(opt['img-size'], s=stride)
    
    if half:
        model.half()
        
    # Warmup the model
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))
        
    return model, device, half, imgsz, stride, opt

# Initialize the model and device globally
model, device, half, imgsz, stride, opt = initialize_model()

# Initialize OCR engine globally
ocr = PaddleOCR(
    det_model_dir=DET_MODEL_DIR,
    rec_model_dir=REC_MODEL_DIR,
    cls_model_dir=CLS_MODEL_DIR,
    ocr_version='PP-OCRv3',
    use_angle_cls=True,
    lang='en',
    cls_thresh=0.8,
    rec_char_type='en',
    det_algorithm='DB',
    det_db_thres=0.3,
    det_db_box_thresh=0.4,
    det_db_unclip_ratio=1.7,
    det_limit_side_len=960,
    rec_algorithm='SVTR_LCNet',
    rec_image_shape='3, 48, 320',
    rec_image_height=48,
    warmup=True,
    box_thresh=0.5,
    text_thresh=0.01,
    use_gpu=True,
    show_log=False
)

@logger.catch
def letterbox(img, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleFill=False, scaleup=True, stride=32):
    """Resize and pad image while meeting stride-multiple constraints"""
    shape = img.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better test mAP)
        r = min(r, 1.0)

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
    elif scaleFill:  # stretch
        dw, dh = 0.0, 0.0
        new_unpad = (new_shape[1], new_shape[0])
        ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # width, height ratios

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
    return img, ratio, (dw, dh)

@logger.catch
def det_engine(source_image_path, request_id):
    """Detect VIN regions in image using YOLOv7"""
    try:
        with torch.no_grad():
            names = model.module.names if hasattr(model, 'module') else model.names
            colors = [[np.random.randint(0, 255) for _ in range(3)] for _ in names]
            
            # Read image
            img0 = cv2.imread(source_image_path)
            if img0 is None:
                logger.error(f"Failed to read image: {source_image_path}")
                return 'fail', 'fail'
                
            img = letterbox(img0, imgsz, stride=stride)[0]
            img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
            img = np.ascontiguousarray(img)
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Inference
            t1 = time_synchronized()
            pred = model(img, augment=False)[0]

            # Apply NMS
            classes = None
            if opt['classes']:
                classes = []
                for class_name in opt['classes']:
                    classes.append(opt['classes'].index(class_name))

            pred = non_max_suppression(pred, opt['conf-thres'], opt['iou-thres'], classes=classes, agnostic=False)
            t2 = time_synchronized()
            
            c1, c2, c3, c4 = 0, 0, 0, 0
            bbox_det_result = 'fail'
            
            for i, det in enumerate(pred):
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], img0.shape).round()
                    
                    # Get the first detection (assuming the highest confidence)
                    for *xyxy, conf, cls in reversed(det):
                        c1, c2, c3, c4 = (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]))
                        bbox_det_result = 'pass'
                        break
                    
                    if bbox_det_result == 'pass':
                        break

        # Save detected boundary box using bbox coordinates
        crop_image_save_result = 'fail'
        if c1 + c2 + c3 + c4 != 0:
            try:
                img_x = Image.open(source_image_path)
                box = (c1, c2, c3, c4)
                img_y = img_x.crop(box)
                
                # Save the cropped image
                output_path = os.path.join(TMP_DIR, f"{request_id}vinimageroi.jpg")
                try:
                    img_y.save(output_path)
                except OSError:
                    logger.info('PNG image detected. Converting to RGB')
                    rgb_image = img_y.convert('RGB')
                    rgb_image.save(output_path)
                
                logger.info(f'Saved ROI image to {output_path}')
                crop_image_save_result = 'pass'
            except Exception as e:
                logger.error(f"Error saving cropped image: {str(e)}")
                crop_image_save_result = 'fail'
        else:
            logger.info('No ROI detected, cannot save cropped image')

        return bbox_det_result, crop_image_save_result
    
    except Exception as e:
        logger.error(f"Error in detection engine: {str(e)}")
        return 'fail', 'fail'

@logger.catch
def ocr_engine(img_path):
    """Process image with PaddleOCR to extract text"""
    try:
        result_t = ocr.ocr(img_path, cls=True)
        
        if not result_t or not result_t[0]:
            logger.info('No OCR results found')
            return 'null', 0
            
        txts = [line[1][0] for line in result_t[0]]
        scores = [line[1][1] for line in result_t[0]]
        
        if len(txts) >= 1:
            vin_text = re.sub('[^A-Za-z0-9]+', '', ''.join(txts))
            vin_acc = round(sum(scores) / len(scores), 2)
        else:
            vin_text = 'null'
            vin_acc = 0
            logger.info(f'No characters detected by OCR engine. Length of text: {len(txts)}')

        return vin_text, vin_acc
    except Exception as e:
        logger.error(f"Error in OCR engine: {str(e)}")
        return 'null', 0

@logger.catch
def get_ocr(req_id, img_arry, roi_type):
    """Get OCR results from image array with potential image enhancements"""
    try:
        # First, create inverted image and run OCR
        inverted_image = cv2.bitwise_not(img_arry)
        inverted_path = os.path.join(TMP_DIR, f"{req_id}invert_roi_image.jpg")
        cv2.imwrite(inverted_path, inverted_image)
        
        txt, score = ocr_engine(inverted_path)
        logger.info(f'Initial VIN text: {txt}, confidence: {score}')
        
        text_one = txt if txt else 'MBL'
        acc_one = score
        
        # If OCR result is too short, try with resized image (only for ROI crops)
        if len(text_one) < 5 and roi_type == 'half':
            try:
                resized_path = os.path.join(TMP_DIR, f"{req_id}rs_invert_roi_image.jpg")
                resized_image = cv2.resize(inverted_image, (320, 48))
                inverted_image_q = cv2.bitwise_not(resized_image)
                cv2.imwrite(resized_path, inverted_image_q)
                
                txt, score = ocr_engine(resized_path)
                logger.info(f'VIN text after resize: {txt}, confidence: {score}')
                
                text_two = txt if txt else 'MBL'
                acc_two = score
                
                # Choose the better result
                if len(text_two) > len(text_one):
                    final_text = text_two
                    final_acc = acc_two
                else:
                    final_text = text_one
                    final_acc = acc_one
            except Exception as e:
                logger.error(f"Error in resizing: {str(e)}")
                final_text = text_one
                final_acc = acc_one
        else:
            final_text = text_one
            final_acc = acc_one
            
        return final_text, final_acc
    except Exception as e:
        logger.error(f"Error in OCR processing: {str(e)}")
        return 'null', 0

@logger.catch
def vinimgprocess(imagefile, req_id):
    """Main function to process VIN images and extract text"""
    try:
        # Create grayscale image before sending to ROI detector YOLOv7 model
        read_img = cv2.imread(imagefile)
        if read_img is None:
            logger.error(f"Failed to read input image: {imagefile}")
            return 'null', 0
            
        gray_image = cv2.cvtColor(read_img, cv2.COLOR_BGR2GRAY)
        gray_path = os.path.join(TMP_DIR, f"{req_id}greyscaleimage.jpg")
        cv2.imwrite(gray_path, gray_image)
        
        # Detect ROI using YOLOv7 model
        roidetstatus, cropsavestatus = det_engine(gray_path, req_id)
        
        if roidetstatus == 'pass' and cropsavestatus == 'pass':
            logger.info('ROI detected for VIN image. Using cropped image for OCR')
            roi_path = os.path.join(TMP_DIR, f"{req_id}vinimageroi.jpg")
            roimagearray = cv2.imread(roi_path)
            
            if roimagearray is None:
                logger.error(f"Failed to read ROI image: {roi_path}")
                # Fall back to using the full image
                vin_text, vin_acc = get_ocr(req_id, gray_image, 'full')
            else:
                # Process based on image orientation
                if roimagearray.shape[1] > roimagearray.shape[0]:  # Horizontal image
                    vin_text, vin_acc = get_ocr(req_id, roimagearray, 'half')
                else:  # Vertical image, rotate 90 degrees counter-clockwise
                    imagerotate = cv2.rotate(roimagearray, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    vin_text, vin_acc = get_ocr(req_id, imagerotate, 'half')
                    logger.info('ROI image rotated counter-clockwise')
        else:
            logger.info('No ROI detected. Using complete image for OCR process')
            # Process based on original image orientation
            if gray_image.shape[1] > gray_image.shape[0]:  # Horizontal image
                vin_text, vin_acc = get_ocr(req_id, gray_image, 'full')
            else:  # Vertical image, rotate 90 degrees counter-clockwise
                fulimagerotate = cv2.rotate(gray_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                logger.info('Original image rotated counter-clockwise')
                vin_text, vin_acc = get_ocr(req_id, fulimagerotate, 'full')

        # Clean up temporary files
        cleanup_temp_files(req_id)
            
        return vin_text, vin_acc
    
    except Exception as e:
        logger.error(f"Error in VIN image processing: {str(e)}")
        cleanup_temp_files(req_id)
        return 'null', 0

def cleanup_temp_files(req_id):
    """Clean up temporary files created during processing"""
    temp_files = [
        f"{req_id}greyscaleimage.jpg",
        f"{req_id}vinimageroi.jpg",
        f"{req_id}invert_roi_image.jpg",
        f"{req_id}rs_invert_roi_image.jpg"
    ]
    
    for filename in temp_files:
        file_path = os.path.join(TMP_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing temp file {file_path}: {str(e)}")

