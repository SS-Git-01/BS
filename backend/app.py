from flask import Flask, request, jsonify, send_from_directory
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
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
from ai_classify import analyze_image, get_image_embedding, get_text_embedding

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
UPLOAD_FOLDER = '/app/uploads'
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

def get_address_from_coords(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'format': 'json',
            'lat': lat,
            'lon': lon,
            'zoom': 18,
            'addressdetails': 1,
            'accept-language': 'zh-CN'
        }
        full_url = f"{url}?{urlencode(params)}"
        req = Request(full_url, headers={'User-Agent': 'MyStudentProject/1.0'})
        with urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            address = data.get('address', {})
            country = address.get('country', '')
            province = address.get('state', '')
            city = address.get('city', '') or \
                   address.get('municipality', '') or \
                   address.get('prefecture', '') or \
                   address.get('state_district', '') or \
                   address.get('region', '') or \
                   address.get('administrative', '')
            district = address.get('district', '') or \
                       address.get('county', '') or \
                       address.get('city_district', '')
            town = address.get('town', '') or \
                   address.get('suburb', '') or \
                   address.get('street', '') or \
                   address.get('village', '') or \
                   address.get('subdistrict', '')
            parts = []
            if country: parts.append(country)
            if province: parts.append(province)
            if city and city not in parts:
                parts.append(city)
            if district and district not in parts:
                parts.append(district)
            if town and town not in parts:
                parts.append(town)
            return " ".join(parts)
    except Exception:
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
        
        # 1. 先保存原始文件
        file.save(save_path)
        
        # 2. 关键：先提取 Exif 信息（因为后续的 save 会清除 Exif）
        exif = get_image_exif(save_path)
        
        final_loc = exif['location']
        if exif.get('raw_gps'):
            lat, lon = exif['raw_gps']
            addr = get_address_from_coords(lat, lon)
            if addr: final_loc = addr
            
        capture_date = exif['date'] if exif['date'] else datetime.datetime.now()

        # 3. 图片处理：旋转矫正 + 获取分辨率
        img = Image.open(save_path)
        try:
            # 根据 Exif 旋转图片
            img = ImageOps.exif_transpose(img)
        except:
            pass
            
        # 获取旋转后的真实宽高
        img_w, img_h = img.size
        
        # 覆盖保存矫正后的图片
        img.save(save_path, quality=95)
        
        # 4. 生成缩略图
        img.thumbnail((300, 300))
        thumb_filename = "thumb_" + unique_filename
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename))
        
        ai_tags = []
        try:
            ai_tags = analyze_image(save_path)
        except:
            pass
            
        clip_embedding = []
        try:
            clip_embedding = get_image_embedding(save_path)
        except:
            pass

        # 6. 存入数据库
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
            ai_tags=ai_tags,
            clip_embedding=clip_embedding
        )
        db.session.add(new_image)
        db.session.commit()
        
        return jsonify({
            'message': 'Upload successful',
            'filename': unique_filename,
            'thumbnail': thumb_filename,
            'device': exif['device'],
            'location': final_loc,
            'resolution': f"{img_w}x{img_h}"
        }), 201
    except Exception as e:
        print(f"Upload Error: {e}")
        return jsonify({'message': 'Upload failed'}), 500

@app.route('/api/images', methods=['GET'])
@token_required
def get_user_images(current_user):
    query = request.args.get('q', '').strip()
    images = ImageModel.query.filter_by(user_id=current_user.id).order_by(ImageModel.capture_date.desc()).all()
    
    # 辅助函数：格式化图片数据
    def format_image(img, score=None):
        data = {
            'id': img.id,
            'filename': img.filename,
            'thumbnail': img.thumbnail_path,
            'device': img.device,
            'capture_date': img.capture_date.strftime('%Y-%m-%d %H:%M:%S') if img.capture_date else None,
            'location': img.location,
            'tags': [t.tag_name for t in img.tags],
            'ai_tags': img.ai_tags,
            'resolution': f"{img.width}x{img.height}" if img.width else "未知"
        }
        if score:
            data['debug_score'] = f"{score:.3f}"
        return data
    
    if not query:
        return jsonify([format_image(img) for img in images]), 200

    print(f"DEBUG: Searching for '{query}'...", flush=True)
    text_vector = get_text_embedding(query)
    
    scored_images = []
    
    for img in images:
        score = 0
        basic_match = False
        
        if query.lower() in (img.location or "").lower(): basic_match = True
        if query.lower() in img.filename.lower(): basic_match = True
        if img.ai_tags:
            for t in img.ai_tags:
                if query.lower() in t.get('label', '').lower(): basic_match = True
        
        if img.tags:
            for t in img.tags:
                if query.lower() in t.tag_name.lower(): 
                    basic_match = True
                    score += 0.8  
                    print(f"DEBUG: '{img.filename}' Hit User Tag '{t.tag_name}'", flush=True)

        if basic_match:
            score += 0.5
            print(f"DEBUG: '{img.filename}' Hit Basic Match (+0.5)", flush=True)
            
        clip_score = 0
        if text_vector and img.clip_embedding:
            dot_product = sum(a * b for a, b in zip(text_vector, img.clip_embedding))
            clip_score = dot_product
            score += clip_score
        
        if clip_score > 0.05 or basic_match:
            print(f"DEBUG: '{img.filename}' CLIP Score: {clip_score:.4f} | Total: {score:.4f}", flush=True)

        if score > 0.38:  
            scored_images.append((score, img))
            
    scored_images.sort(key=lambda x: x[0], reverse=True)
    
    output = [format_image(img, score) for score, img in scored_images]
    print(f"DEBUG: Found {len(output)} results.", flush=True)
    return jsonify(output), 200

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

        # 更新数据库中的宽高
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