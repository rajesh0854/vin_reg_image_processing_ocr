import cv2
import numpy as np
from ultralytics import YOLO
import os
import torch
import re
import torch
from PIL import Image
from torchvision import transforms
#pip install git+https://github.com/baudm/parseq.git
#pip install pytorch_lightning
#pip install nltk
#pip install timm


device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Load the trained YOLOv8 OBB model
plate_det_model = YOLO('reg_ocr_process_weights/plate_det_obb.pt')
text_det_model = YOLO('reg_ocr_process_weights/text_det_yolov11m.pt')

parseq_ocr_model=torch.load('reg_ocr_process_weights/parseq_ocr_model.pt',map_location=device)

# Define image preprocessing
transform = transforms.Compose([
    transforms.Resize((32, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5]),
])


def box_center(box):
    box_height = box[3] - box[1]
    return box[1] + box_height/2

def order_points(pts):
    # Order points: top-left, top-right, bottom-right, bottom-left
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    rect[0] = pts[np.argmin(s)]      # Top-left
    rect[2] = pts[np.argmax(s)]      # Bottom-right
    rect[1] = pts[np.argmin(diff)]   # Top-right
    rect[3] = pts[np.argmax(diff)]   # Bottom-left
    return rect


def plate_det_fn(cv2_array):
    cropped_det_plate = None  
    err = None
    try:
        results = plate_det_model.predict(source=cv2_array, device=device, conf=0.75, verbose=False)

        
        # Early check: are there any detections?
        if not results or not hasattr(results[0], 'obb') or results[0].obb is None:
            return None, 'No plate detected'

        obb = results[0].obb  # Get oriented bounding box from first result
        boxes = obb.xyxyxyxy.cpu().numpy()

        if boxes.size == 0:
            return None, 'No plate box detected'  # No detected boxes

        for box in boxes:
            box = box.reshape((4, 2))
            ordered_box = order_points(box)
            width = int(np.linalg.norm(ordered_box[0] - ordered_box[1]))
            height = int(np.linalg.norm(ordered_box[1] - ordered_box[2]))

            dst_pts = np.array([[0, 0],
                                [width - 1, 0],
                                [width - 1, height - 1],
                                [0, height - 1]], dtype="float32")

            M = cv2.getPerspectiveTransform(ordered_box, dst_pts)
            cropped_det_plate = cv2.warpPerspective(cv2_array, M, (width, height))
            break  # Process only the first valid detection

    except Exception as e:
        cropped_det_plate = None
        err = e

    return cropped_det_plate, err


def text_det_fn(cropped_det_plate):
    all_text_crops = None
    err = None
    try:
        results = text_det_model(source=cropped_det_plate, device=device, conf=0.75, verbose=False)


        # Ensure results is a list or iterable and not empty
        if not results or len(results) == 0:
            return None, 'No text detected'

        result = results[0]

        # Ensure boxes exist and are not None
        if not hasattr(result, 'boxes') or result.boxes is None or result.boxes.xyxy is None:
            return None, 'No text box detected'

        boxes = result.boxes.xyxy.cpu().numpy()
        if boxes.size == 0:
            return None, 'No text box detected'

        sorted_boxes = sorted(boxes, key=box_center)
        all_text_crops = []

        for i, box in enumerate(sorted_boxes):
            x1, y1, x2, y2 = map(int, box)
            text_crop = cropped_det_plate[y1:y2, x1:x2]

            # Optional: get class name
            if hasattr(result.boxes, 'cls') and result.boxes.cls is not None:
                cls_id = int(result.boxes.cls[i].cpu())
                class_name = text_det_model.names[cls_id]
            else:
                class_name = None

            all_text_crops.append(text_crop)

    except Exception as e:
        return None, err

    return all_text_crops, err



def parseq_ocr_fn(all_text_crops):
    final_output = None
    all_text = []
    err = None

    try:
        # Early exit if no text crops
        if not all_text_crops:
            return None, None, None

        for text_crop in all_text_crops:
            pil_image = Image.fromarray(text_crop)
            img = transform(pil_image).unsqueeze(0).to(device)

            with torch.no_grad():
                pred = parseq_ocr_model(img)
                probabilities = torch.nn.functional.softmax(pred, dim=-1)
                confidence, _ = torch.max(probabilities, dim=-1)

                decoded_text = parseq_ocr_model.tokenizer.decode(pred)[0]
                #text = decoded_text.strip()
                text = decoded_text[0].strip()

                if not text:
                    continue

                all_text.append(text)

        if not all_text:
            return None, None, None

        # Join all predictions into one string
        output = ''.join(all_text)
        final_output = output.replace(' ', '')

        # Optional: replace 'O' at position 2 with '0'
        if len(final_output) > 2 and final_output[2] == 'O':
            final_output = final_output[:2] + '0' + final_output[3:]

    except Exception as e:
        final_output = None
        all_text = None
        err = e

    return final_output, all_text, err



