from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from PIL import Image, ExifTags
import jwt
import datetime
import os
import re

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

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class ImageModel(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    upload_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    device = db.Column(db.String(100))
    capture_date = db.Column(db.DateTime)
    location = db.Column(db.String(255))

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
                return float(v)
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
    except Exception as e:
        return 0.0

def get_image_exif(file_path):
    exif_data = {"device": "Unknown", "date": None, "location": "Unknown"}
    try:
        img = Image.open(file_path)
        raw_exif = img._getexif()
        if not raw_exif:
            return exif_data

        gps_info = {}
        make = ""
        model = ""

        for tag, value in raw_exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            
            if decoded == "Make":
                make = str(value).strip()
            if decoded == "Model":
                model = str(value).strip()
            
            if decoded == "DateTimeOriginal":
                try:
                    exif_data["date"] = datetime.datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                except:
                    pass
            if decoded == "GPSInfo":
                gps_info = value

        if model:
            if make and make in model:
                exif_data["device"] = model
            else:
                exif_data["device"] = f"{make} {model}" if make else model

        if gps_info:
            try:
                lat_raw = gps_info.get(2)
                lat_ref = gps_info.get(1)
                lon_raw = gps_info.get(4)
                lon_ref = gps_info.get(3)

                if lat_raw and lon_raw:
                    lat = _convert_to_degrees(lat_raw)
                    lon = _convert_to_degrees(lon_raw)

                    if lat_ref == 'S': lat = -lat
                    if lon_ref == 'W': lon = -lon
                    
                    exif_data["location"] = f"{lat:.4f}, {lon:.4f}"
            except Exception:
                pass
    except Exception:
        pass
    return exif_data

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"message": "信息不完整"}), 400
    if len(password) < 6:
        return jsonify({"message": "密码长度需大于6位"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"message": "用户名或邮箱已存在"}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "注册成功"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({"token": token, "user_id": user.id, "username": user.username}), 200
    
    return jsonify({"message": "用户名或密码错误"}), 401

@app.route('/api/upload', methods=['POST'])
@token_required
def upload_image(current_user):
    if 'file' not in request.files:
        return jsonify({'message': '没有文件部分'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': '未选择文件'}), 400
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S_")
        unique_filename = timestamp + filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(save_path)
        
        exif = get_image_exif(save_path)
        
        capture_date = exif['date'] if exif['date'] else datetime.datetime.utcnow()
        file_size = os.path.getsize(save_path)

        new_image = ImageModel(
            user_id=current_user.id,
            filename=unique_filename,
            file_path=save_path,
            file_size=file_size,
            device=exif['device'],
            capture_date=capture_date,
            location=exif['location']
        )
        db.session.add(new_image)
        db.session.commit()
        
        return jsonify({'message': '上传成功！', 'filename': unique_filename, 'device': exif['device']}), 201

@app.route('/api/images', methods=['GET'])
@token_required
def get_user_images(current_user):
    images = ImageModel.query.filter_by(user_id=current_user.id).order_by(ImageModel.capture_date.desc()).all()
    output = []
    for img in images:
        output.append({
            'id': img.id,
            'filename': img.filename,
            'device': img.device,
            'capture_date': img.capture_date,
            'location': img.location,
            'file_size': img.file_size
        })
    return jsonify(output), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/images/<int:image_id>', methods=['DELETE'])
@token_required
def delete_image(current_user, image_id):
    image = ImageModel.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image:
        return jsonify({'message': '图片不存在或无权删除'}), 404
    try:
        if os.path.exists(image.file_path):
            os.remove(image.file_path)
    except Exception:
        pass
    db.session.delete(image)
    db.session.commit()
    return jsonify({'message': '删除成功'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)