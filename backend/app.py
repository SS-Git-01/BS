from flask import Flask, request, jsonify, send_from_directory, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from PIL import Image, ExifTags, ImageOps, ImageEnhance
from sqlalchemy.dialects.mysql import JSON
import jwt
import datetime
import os
import re
import math
import threading
import requests
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
from ai_classify import analyze_image, get_image_embedding, get_text_embedding
from llm_search import extract_search_params

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

image_tags = db.Table('image_tags',
    db.Column('image_id', db.Integer, db.ForeignKey('images.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(64), unique=True, nullable=False)

class ImageModel(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    upload_time = db.Column(db.DateTime, default=datetime.datetime.now)
    device = db.Column(db.String(100))
    capture_date = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    ai_tags = db.Column(JSON)
    clip_embedding = db.Column(JSON)
    tags = db.relationship('Tag', secondary=image_tags, backref=db.backref('images', lazy='dynamic'))

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) > 1:
                token = parts[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def _convert_to_degrees(value):
    try:
        def force_float(v):
            try:
                f = float(v)
                return 0.0 if math.isnan(f) else f
            except:
                pass
            s = str(v).strip()
            if '/' in s:
                parts = s.split('/')
                if len(parts) == 2 and float(parts[1]) != 0:
                    return float(parts[0]) / float(parts[1])
            nums = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", s)
            if len(nums) >= 2 and float(nums[1]) != 0:
                return float(nums[0]) / float(nums[1])
            if len(nums) == 1:
                return float(nums[0])
            return 0.0
        d = force_float(value[0])
        m = force_float(value[1])
        s = force_float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return 0.0

def transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def transform_lon(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def wgs84_to_gcj02(lat, lon):
    """
    将 GPS 原始坐标 (WGS-84) 转换为 高德/腾讯 地图坐标 (GCJ-02)
    否则在国内会有几百米的偏移
    """
    a = 6378245.0
    ee = 0.00669342162296594323
    
    if lon < 72.004 or lon > 137.8347 or lat < 0.8293 or lat > 55.8271:
        return lat, lon # 不在国内，直接返回
        
    dLat = transform_lat(lon - 105.0, lat - 35.0)
    dLon = transform_lon(lon - 105.0, lat - 35.0)
    radLat = lat / 180.0 * math.pi
    magic = math.sin(radLat)
    magic = 1 - ee * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * math.pi)
    dLon = (dLon * 180.0) / (a / sqrtMagic * math.cos(radLat) * math.pi)
    mgLat = lat + dLat
    mgLon = lon + dLon
    return mgLat, mgLon

AMAP_KEY = 'da3e4171bbbee5c2d2d88c127dbad75d' 

def get_address_from_coords(lat, lon):
    try:
        if not AMAP_KEY or AMAP_KEY == '你的高德Web服务Key填在这里':
            print("Error: Amap Key not configured.")
            return None

        g_lat, g_lon = wgs84_to_gcj02(lat, lon)
        
        location_str = f"{g_lon:.6f},{g_lat:.6f}"
        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            'key': AMAP_KEY,
            'location': location_str,
            'extensions': 'base', 
            'radius': 1000,
            'roadlevel': 0
        }
        
        resp = requests.get(url, params=params, timeout=3)
        data = resp.json()
    
        if data.get('status') == '1' and data.get('regeocode'):
            address = data['regeocode']['formatted_address']
            return address
        else:
            print(f"Amap Error: {data.get('info')}")
            return None
            
    except Exception as e:
        print(f"Geocoding Error: {e}")
        return None
    
def get_image_exif(file_path):
    exif_data = {"device": "Unknown", "date": None, "location": "Unknown", "raw_gps": None}
    try:
        img = Image.open(file_path)
        raw_exif = img._getexif()
        if not raw_exif:
            return exif_data
        gps_info = {}
        make, model = "", ""
        for tag, value in raw_exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "Make": make = str(value).strip()
            if decoded == "Model": model = str(value).strip()
            if decoded == "DateTimeOriginal":
                try:
                    exif_data["date"] = datetime.datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                except:
                    pass
            if decoded == "GPSInfo":
                gps_info = value
        if model:
            exif_data["device"] = model if make and make in model else f"{make} {model}" if make else model
        if gps_info:
            try:
                lat_raw, lat_ref = gps_info.get(2), gps_info.get(1)
                lon_raw, lon_ref = gps_info.get(4), gps_info.get(3)
                if lat_raw and lon_raw:
                    lat = _convert_to_degrees(lat_raw)
                    lon = _convert_to_degrees(lon_raw)
                    if lat_ref:
                        ref = str(lat_ref).upper() if not isinstance(lat_ref, bytes) else lat_ref.decode().upper()
                        if 'S' in ref: lat = -lat
                    if lon_ref:
                        ref = str(lon_ref).upper() if not isinstance(lon_ref, bytes) else lon_ref.decode().upper()
                        if 'W' in ref: lon = -lon
                    if abs(lat) > 0.001 or abs(lon) > 0.001:
                        exif_data["location"] = f"{lat:.4f}, {lon:.4f}"
                        exif_data["raw_gps"] = (lat, lon)
            except Exception:
                pass
    except Exception:
        pass
    return exif_data

def process_image_ai(app_obj, image_id):
    with app_obj.app_context():
        try:
            image = ImageModel.query.get(image_id)
            if not image:
                print(f"Image {image_id} not found in background task.")
                return
            
            print(f"Starting AI analysis for {image.filename}...")
            ai_tags = analyze_image(image.file_path)
            clip_embedding = get_image_embedding(image.file_path)
            
            image.ai_tags = ai_tags
            image.clip_embedding = clip_embedding
            db.session.commit()
            print(f"AI analysis finished for {image.filename}")
        except Exception as e:
            db.session.rollback()
            print(f"AI Task Error: {e}")

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username, email, password = data.get('username'), data.get('email'), data.get('password')
    if not username or not email or not password:
        return jsonify({"message": "Missing information"}), 400
    if len(password) < 6:
        return jsonify({"message": "Password too short"}), 400
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"message": "User already exists"}), 400
    new_user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username, password = data.get('username'), data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({"token": token, "user_id": user.id, "username": user.username}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/upload', methods=['POST'])
@token_required
def upload_image(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S_")
        unique_filename = timestamp + filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(save_path)
        
        exif = get_image_exif(save_path)
        
        final_loc = exif['location']
        if exif.get('raw_gps'):
            lat, lon = exif['raw_gps']
            addr = get_address_from_coords(lat, lon)
            if addr: final_loc = addr
            
        capture_date = exif['date'] if exif['date'] else datetime.datetime.now()

        img = Image.open(save_path)
        try:
            img = ImageOps.exif_transpose(img)
        except:
            pass
            
        img_w, img_h = img.size
        
        img.save(save_path, quality=95)
        
        img.thumbnail((300, 300))
        thumb_filename = "thumb_" + unique_filename
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename))
        
        new_image = ImageModel(
            user_id=current_user.id,
            filename=unique_filename,
            file_path=save_path,
            thumbnail_path=thumb_filename,
            file_size=os.path.getsize(save_path),
            device=exif['device'],
            capture_date=capture_date,
            location=final_loc,
            width=img_w,
            height=img_h,
            ai_tags=[],
            clip_embedding=[]
        )
        db.session.add(new_image)
        db.session.commit()
        
        thread = threading.Thread(target=process_image_ai, args=(app, new_image.id))
        thread.start()
        
        return jsonify({
            'message': 'Upload successful',
            'id': new_image.id,  
            'filename': unique_filename,
            'thumbnail': thumb_filename,
            'device': exif['device'],
            'location': final_loc,
            'resolution': f"{img_w}x{img_h}"
        }), 201
    except Exception as e:
        print(f"Upload Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Upload failed: {str(e)}'}), 500

@app.route('/api/images', methods=['GET'])
@token_required
def get_user_images(current_user):
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    def format_list(items, has_next):
        return jsonify({
            'items': [{
                'id': img.id,
                'filename': img.filename,
                'thumbnail': img.thumbnail_path,
                'device': img.device,
                'capture_date': img.capture_date.strftime('%Y-%m-%d %H:%M:%S') if img.capture_date else None,
                'location': img.location,
                'tags': [t.tag_name for t in img.tags],
                'ai_tags': img.ai_tags or [],
                'resolution': f"{img.width}x{img.height}" if img.width else "未知"
            } for img in items],
            'has_next': has_next
        })
    
    if not query:
        pagination = ImageModel.query.filter_by(user_id=current_user.id)\
            .order_by(ImageModel.capture_date.desc())\
            .paginate(page=page, per_page=limit, error_out=False)
        return format_list(pagination.items, pagination.has_next)

    llm_params = extract_search_params(query)
    search_keywords = llm_params.get('keywords', [query])
    start_date = llm_params.get('start_date')
    end_date = llm_params.get('end_date')

    sql_query = ImageModel.query.filter_by(user_id=current_user.id)

    if start_date:
        try:
            s_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            sql_query = sql_query.filter(ImageModel.capture_date >= s_date)
        except:
            pass

    if end_date:
        try:
            e_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            e_date = e_date + datetime.timedelta(days=1)
            sql_query = sql_query.filter(ImageModel.capture_date < e_date)
        except:
            pass

    images = sql_query.all()
    text_vector = get_text_embedding(query)
    scored_images = []
    
    for img in images:
        score = 0

        if img.tags:
            for t in img.tags:
                for kw in search_keywords:
                    if kw.lower() == t.tag_name.lower():
                        score += 3.0 # 高分
                        print(f"DEBUG: {img.filename} hit USER TAG: {kw} (+3.0)")
                        break 

        if img.ai_tags:
            for t in img.ai_tags:
                label = t.get('label', '').lower()
                for kw in search_keywords:
                    if kw.lower() in label:
                        score += 1.5 # 中等分
                        print(f"DEBUG: {img.filename} hit AI TAG: {kw} in '{label}' (+1.5)")
                        break

        location_lower = (img.location or "").lower()
        filename_lower = img.filename.lower()
        for kw in search_keywords:
            hit = False
            if kw.lower() in location_lower:
                score += 0.5
                print(f"DEBUG: {img.filename} hit LOCATION: {kw} (+0.5)")
                hit = True
            
            if not hit and kw.lower() in filename_lower:
                score += 0.5 # 低分
                print(f"DEBUG: {img.filename} hit FILENAME: {kw} (+0.5)")
        
        clip_score = 0
        if text_vector and img.clip_embedding:
            dot_product = sum(a * b for a, b in zip(text_vector, img.clip_embedding))
            clip_score = dot_product
            score += clip_score * 2.0
     
        if score > 0.8:
            scored_images.append((score, img))
            
    scored_images.sort(key=lambda x: x[0], reverse=True)
    
    start = (page - 1) * limit
    end = start + limit
    sliced_result = [img for score, img in scored_images[start:end]]
    has_next = len(scored_images) > end
    
    return format_list(sliced_result, has_next)

@app.route('/api/images/<int:image_id>', methods=['GET'])
@token_required
def get_image_detail(current_user, image_id):
    img = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not img:
        return jsonify({'message': 'Image not found'}), 404
        
    return jsonify({
        'id': img.id,
        'filename': img.filename,
        'thumbnail': img.thumbnail_path,
        'device': img.device,
        'capture_date': img.capture_date.strftime('%Y-%m-%d %H:%M:%S') if img.capture_date else None,
        'location': img.location,
        'tags': [t.tag_name for t in img.tags],
        'ai_tags': img.ai_tags or [], # 返回 AI 标签
        'resolution': f"{img.width}x{img.height}" if img.width else "未知"
    })

@app.route('/api/tags', methods=['POST'])
@token_required
def add_tag(current_user):
    data = request.json
    image_id, tag_name = data.get('image_id'), data.get('tag_name')
    image = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image: return jsonify({'message': 'Image not found'}), 404
    tag = Tag.query.filter_by(tag_name=tag_name).first()
    if not tag:
        tag = Tag(tag_name=tag_name)
        db.session.add(tag)
    if tag not in image.tags:
        image.tags.append(tag)
        db.session.commit()
    return jsonify({'message': 'Tag added'}), 200

@app.route('/api/tags', methods=['DELETE'])
@token_required
def delete_tag(current_user):
    data = request.json
    image_id, tag_name = data.get('image_id'), data.get('tag_name')
    
    image = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image: 
        return jsonify({'message': 'Image not found'}), 404
        
    tag = Tag.query.filter_by(tag_name=tag_name).first()
    if tag and tag in image.tags:
        image.tags.remove(tag)
        db.session.commit()
        return jsonify({'message': 'Tag removed'}), 200
    
    return jsonify({'message': 'Tag not associated'}), 400

@app.route('/api/images/<int:image_id>/edit', methods=['PUT'])
@token_required
def edit_image(current_user, image_id):
    image = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image: return jsonify({'message': 'Image not found'}), 404
    
    data = request.json
    crop_data = data.get('crop')
    rotate = data.get('rotate', 0)
    brightness = data.get('brightness', 1.0)
    contrast = data.get('contrast', 1.0)

    try:
        img = Image.open(image.file_path)
        
        if rotate != 0:
            img = img.rotate(-rotate, expand=True)

        if crop_data:
            real_w, real_h = img.size
            x = max(0, int(crop_data['x']))
            y = max(0, int(crop_data['y']))
            w = int(crop_data['width'])
            h = int(crop_data['height'])
            if x + w > real_w: w = real_w - x
            if y + h > real_h: h = real_h - y
            if w > 0 and h > 0:
                img = img.crop((x, y, x + w, y + h))

        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)

        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)

        img.save(image.file_path, quality=95)

        image.width, image.height = img.size
        image.file_size = os.path.getsize(image.file_path)

        img.thumbnail((300, 300))
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], image.thumbnail_path))
        
        db.session.commit()

        return jsonify({
            'message': 'Image edited successfully',
            'resolution': f"{image.width}x{image.height}"
        }), 200

    except Exception as e:
        print(f"Edit Error: {e}")
        return jsonify({'message': 'Failed to process image'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/images/<int:image_id>', methods=['DELETE'])
@token_required
def delete_image(current_user, image_id):
    image = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image: return jsonify({'message': 'Image not found'}), 404
    try:
        if os.path.exists(image.file_path): os.remove(image.file_path)
        if image.thumbnail_path:
            tp = os.path.join(app.config['UPLOAD_FOLDER'], image.thumbnail_path)
            if os.path.exists(tp): os.remove(tp)
    except Exception: pass
    db.session.delete(image)
    db.session.commit()
    return jsonify({'message': 'Delete successful'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)