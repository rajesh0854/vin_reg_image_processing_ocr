## Load dict model

import torchvision
from torchvision.transforms import ToTensor
from transformers import ViTModel
from transformers.modeling_outputs import SequenceClassifierOutput
import torch.nn as nn
import torch.nn.functional as F
from transformers import ViTFeatureExtractor
import torch.nn as nn
import torch
import torch.utils.data as data
from torch.autograd import Variable
import numpy as np
from os import listdir
from os.path import isfile, join
from PIL import Image
import torchvision.transforms.functional as TF
import os
from dotenv import load_dotenv
load_dotenv()

VIN_MODEL = os.getenv('VIN_IMG_CLASSIFIER_MODEL')
HSRP_MODE = os.getenv('HSRP_IMG_CLASSIFIER_MODEL')

class ViTForImageClassification(nn.Module):
    def __init__(self, num_labels=4):
        super(ViTForImageClassification, self).__init__()
        self.vit = ViTModel.from_pretrained('google/vit-base-patch16-224-in21k')
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.vit.config.hidden_size, num_labels)
        self.num_labels = num_labels

    def forward(self, pixel_values, labels):
        outputs = self.vit(pixel_values=pixel_values)
        output = self.dropout(outputs.last_hidden_state[:,0])
        logits = self.classifier(output)

        loss = None
        if labels is not None:
          loss_fct = nn.CrossEntropyLoss()
          loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
        if loss is not None:
          return logits, loss.item()
        else:
          return logits, None

model_v=ViTForImageClassification()
model_h=ViTForImageClassification()

model_v.load_state_dict(torch.load(VIN_MODEL))
model_h.load_state_dict(torch.load(HSRP_MODE))
print('loaded vin and hsrp image classifier models')

feature_extractor = ViTFeatureExtractor.from_pretrained('google/vit-base-patch16-224-in21k')


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') 
if torch.cuda.is_available():
    model_v.cuda() 
    model_h.cuda()

def predictor(img,chk_type):
  classes=['bw','color','real','replay']

  image = Image.open(img)
  x = TF.to_tensor(image)
  inputs = x.permute(1, 2, 0)
  # Save original Input
  originalInput = inputs
  for index, array in enumerate(inputs):
    inputs[index] = np.squeeze(array)
  inputs = torch.tensor(np.stack(feature_extractor(inputs)['pixel_values'], axis=0))
  inputs = inputs.to(device)
  target=torch.tensor([0])
  target = target.to(device)
  # Generate prediction
  if chk_type == 'vin':
    prediction, loss = model_v(inputs,target)
  else:
    prediction, loss = model_h(inputs,target)
  x = prediction.detach().cpu().numpy()
  X=[]
  for idx, pred_prob in enumerate(x):
      for i in pred_prob:
          X.append(i)
  index_val=(X.index(max(X)))
  res=classes[index_val]
  acc=float(0.9)
  return res,acc
