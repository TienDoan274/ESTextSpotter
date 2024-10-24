import os, sys
import torch
import numpy as np

from models.ests import build_ests
from util.slconfig import SLConfig
from util.visualizer import COCOVisualizer
from util import box_ops
from PIL import Image
import datasets.transforms as T

import pickle

dictionary = "aàáạảãâầấậẩẫăằắặẳẵAÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪeèéẹẻẽêềếệểễEÈÉẸẺẼÊỀẾỆỂỄoòóọỏõôồốộổỗơờớợởỡOÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠiìíịỉĩIÌÍỊỈĨuùúụủũưừứựửữƯỪỨỰỬỮUÙÚỤỦŨyỳýỵỷỹYỲÝỴỶỸ"

def make_groups():
    groups = []
    i = 0
    while i < len(dictionary) - 5:
        group = [c for c in dictionary[i : i + 6]]
        i += 6
        groups.append(group)
    return groups


groups = make_groups()

TONES = ["", "ˋ", "ˊ", "﹒", "ˀ", "˜"]
SOURCES = ["ă", "â", "Ă", "Â", "ê", "Ê", "ô", "ơ", "Ô", "Ơ", "ư", "Ư", "Đ", "đ"]
TARGETS = ["aˇ", "aˆ", "Aˇ", "Aˆ", "eˆ", "Eˆ", "oˆ", "o˒", "Oˆ", "O˒", "u˒", "U˒", "D-", "d‑"]


def correct_tone_position(word):
    word = word[:-1]
    if len(word) < 2:
        pass
    first_ord_char = ""
    second_order_char = ""
    for char in word:
        for group in groups:
            if char in group:
                second_order_char = first_ord_char
                first_ord_char = group[0]
    if word[-1] == first_ord_char and second_order_char != "":
        pair_chars = ["qu", "Qu", "qU", "QU", "gi", "Gi", "gI", "GI"]
        for pair in pair_chars:
            if pair in word and second_order_char in ["u", "U", "i", "I"]:
                return first_ord_char
        return second_order_char
    return first_ord_char


def decoder(recognition):
    for char in TARGETS:
        recognition = recognition.replace(char, SOURCES[TARGETS.index(char)])
    if len(recognition) < 1:
        return recognition
    if recognition[-1] in TONES:
        if len(recognition) < 2:
            return recognition
        replace_char = correct_tone_position(recognition)
        tone = recognition[-1]
        recognition = recognition[:-1]
        for group in groups:
            if replace_char in group:
                recognition = recognition.replace(replace_char, group[TONES.index(tone)])
    return recognition

CTLABELS = [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~', 'ˋ', 'ˊ', '﹒', 'ˀ', '˜', 'ˇ', 'ˆ', '˒', '‑']
def _decode_recognition(rec):
    word = ''
    rec = rec.tolist()
    for c in rec:
        if c>104:
            continue
        word += CTLABELS[c]
    word = decoder(word)
    return word

def build_model_main(args):
    # we use register to maintain models from catdet6 on.
    from models.registry import MODULE_BUILD_FUNCS
    assert args.modelname in MODULE_BUILD_FUNCS._module_dict
    build_func = MODULE_BUILD_FUNCS.get(args.modelname)
    args.device = 'cuda'
    model, criterion, postprocessors = build_func(args)
    return model, criterion, postprocessors

model_config_path = "config/ESTS/ESTS_5scale_vintext_finetune.py" # change the path of the model config file
model_checkpoint_path = "/kaggle/input/vintext_textspotteres/pytorch/default/1/vintext_checkpoint.pth" # change the path of the model checkpoint

args = SLConfig.fromfile(model_config_path) 
model, criterion, postprocessors = build_model_main(args)
checkpoint = torch.load(model_checkpoint_path, map_location='cuda')
model.load_state_dict(checkpoint['model'])
model.eval()
model.cuda()
transform = T.Compose([
    # T.RandomResize([800],max_size=1024),
    T.ToTensor(),
    T.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])]
)
image_dir = '/kaggle/input/dsc-images/public-test-images/dev-images/a57db320eb6d1f8eb5e95f9ff039de40cad75447a49bea4ce60866cea93dd624.jpg'
# dir = os.listdir(image_dir)
def extract_number(file_name):
    return int(file_name.split('.')[0].rstrip('_'))
from tqdm import tqdm
texts = {}
# for image_path in tqdm(dir):
#     image_text = []
#     img_path = os.path.join(image_dir, image_path)
    
    
image = Image.open(image_dir).convert('RGB')
image, _ = transform(image,None)
output = model(image[None].cuda())
output = postprocessors['bbox'](output, torch.Tensor([[1.0, 1.0]]))[0]
rec = [_decode_recognition(i) for i in output['rec']]
thershold = 0.3 # set a thershold
scores = output['scores']
select_mask = scores > thershold
recs = []
for i,r in zip(select_mask,rec):
    if i:
        recs.append(r)
print(image_dir,recs)
if (recs):
    texts[image_dir]=(' ' .join(recs))
torch.save(texts,'/kaggle/working/texts2000.pt')