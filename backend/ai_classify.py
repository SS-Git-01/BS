import os
import sys

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
from torchvision import models, transforms
from PIL import Image
import json
from urllib.request import urlopen
from transformers import (
    ChineseCLIPModel, 
    BertTokenizer, 
    ChineseCLIPImageProcessor,
    ChineseCLIPProcessor
)

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

resnet_model = None
clip_model = None
clip_tokenizer = None
clip_image_processor = None
clip_processor = None
imagenet_labels = []

LABELS_URL = "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"
LOCAL_LABEL_FILE = os.path.join(os.path.dirname(__file__), 'imagenet_labels.json')

def load_labels():
    global imagenet_labels
    if os.path.exists(LOCAL_LABEL_FILE):
        try:
            with open(LOCAL_LABEL_FILE, 'r') as f:
                imagenet_labels = json.load(f)
            return
        except:
            pass
    try:
        with urlopen(LABELS_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            imagenet_labels = data
            with open(LOCAL_LABEL_FILE, 'w') as f:
                json.dump(data, f)
    except Exception:
        imagenet_labels = [f"Class {i}" for i in range(1000)]

load_labels()

try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_resnet = os.path.join(base_dir, 'models', 'resnet50-19c8e357.pth')
    
    resnet_model = models.resnet50(weights=None)
    if os.path.exists(local_resnet):
        print(f"--> Found local ResNet: {local_resnet}", file=sys.stderr)
        state_dict = torch.load(local_resnet, weights_only=False)
        resnet_model.load_state_dict(state_dict)
        print("--> ResNet loaded successfully!", file=sys.stderr)
    else:
        print("--> Local ResNet not found, downloading...", file=sys.stderr)
        resnet_model = models.resnet50(weights='DEFAULT')
    resnet_model.eval()
    
    print("--> Starting to load Chinese-CLIP components...", file=sys.stderr)
    clip_local_path = os.path.join(base_dir, 'models', 'chinese-clip')
    
    if os.path.exists(clip_local_path) and os.path.exists(os.path.join(clip_local_path, 'pytorch_model.bin')):
        print(f"--> Found local Chinese-CLIP at: {clip_local_path}", file=sys.stderr)
        model_name_or_path = clip_local_path
    else:
        print("--> Local Chinese-CLIP not found! Trying to download...", file=sys.stderr)
        model_name_or_path = "OFA-Sys/chinese-clip-vit-base-patch16"
    
    try:
        clip_model = ChineseCLIPModel.from_pretrained(model_name_or_path)
        clip_tokenizer = BertTokenizer.from_pretrained(model_name_or_path)
        clip_image_processor = ChineseCLIPImageProcessor.from_pretrained(model_name_or_path)
        clip_processor = ChineseCLIPProcessor(image_processor=clip_image_processor, tokenizer=clip_tokenizer)
        print("--> Chinese-CLIP loaded successfully!", file=sys.stderr)
    except Exception as e:
        print(f"--> Error loading components: {e}", file=sys.stderr)
        raise e
    
    if torch.cuda.is_available():
        resnet_model.to('cuda')
        clip_model.to('cuda')
        
    print("=== All AI Models Ready ===", file=sys.stderr)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Model Load Failed: {e}", file=sys.stderr)

def analyze_image(image_path):
    if resnet_model is None: return []
    try:
        input_image = Image.open(image_path).convert('RGB')
        input_tensor = preprocess(input_image)
        input_batch = input_tensor.unsqueeze(0)
        if torch.cuda.is_available(): input_batch = input_batch.to('cuda')
        with torch.no_grad(): output = resnet_model(input_batch)
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        top3_prob, top3_catid = torch.topk(probabilities, 3)
        results = []
        for i in range(top3_prob.size(0)):
            class_id = top3_catid[i].item()
            score = top3_prob[i].item()
            label_name = imagenet_labels[class_id] if class_id < len(imagenet_labels) else f"Class {class_id}"
            if score > 0.05:
                results.append({"id": class_id, "label": label_name, "score": f"{score:.2f}"})
        return results
    except Exception as e:
        print(f"Error in analyze_image: {e}", file=sys.stderr)
        return []

def get_image_embedding(image_path):
    if clip_model is None or clip_processor is None: return None
    try:
        image = Image.open(image_path).convert('RGB')
        inputs = clip_processor(images=image, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
        with torch.no_grad():
            outputs = clip_model.get_image_features(**inputs)
        feature = outputs[0] / outputs[0].norm(dim=-1, keepdim=True)
        return feature.cpu().tolist()
    except Exception as e:
        print(f"Error in get_image_embedding: {e}", file=sys.stderr)
        return None

def get_text_embedding(text):
    if clip_model is None or clip_tokenizer is None: return None
    try:
        inputs = clip_tokenizer(
            text=[text], 
            return_tensors="pt", 
            padding='max_length', 
            truncation=True, 
            max_length=52
        )
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
        with torch.no_grad():
            text_outputs = clip_model.text_model(**inputs)
            pooled_output = getattr(text_outputs, "pooler_output", None)
            if pooled_output is None:
                last_hidden_state = text_outputs[0]
                pooled_output = last_hidden_state[:, 0, :]
            text_features = clip_model.text_projection(pooled_output)
        feature = text_features / text_features.norm(dim=-1, keepdim=True)
        return feature.cpu().tolist()[0]
    except Exception as e:
        print(f"Error in get_text_embedding: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None