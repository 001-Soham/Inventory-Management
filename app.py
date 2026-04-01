from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-change-this'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)

# Predefined items
PREDEFINED_ITEMS = [
    "Laptop Dell Inspiron",
    "Mouse Logitech Wireless",
    "Keyboard Mechanical",
    "Monitor 24 inch",
    "Hard Drive 1TB",
    "RAM 16GB DDR4",
    "SSD 512GB NVMe",
    "Printer HP LaserJet",
    "Router Cisco",
    "Switch Network 24 Port",
    "UPS 1000VA",
    "Webcam HD",
    "Headphones Noise Cancelling",
    "Mobile Phone Stand",
    "Cable HDMI 2m"
]

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'receive' or 'issue'
    unit_price = db.Column(db.Float)
    total_amount = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Initialize database
with app.app_context():
    db.create_all()
    
    # Add predefined items if not exist
    for item_name in PREDEFINED_ITEMS:
        if not InventoryItem.query.filter_by(name=item_name).first():
            item = InventoryItem(name=item_name)
            db.session.add(item)
    db.session.commit()

# Routes
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'message': 'User registered successfully'})
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        
        if user and bcrypt.check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'access_token': access_token,
                'user_id': user.id,
                'username': user.username
            })
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/api/predefined_items')
@jwt_required()
def get_predefined_items():
    items = InventoryItem.query.all()
    return jsonify([{'id': item.id, 'name': item.name, 'quantity': item.quantity} for item in items])

@app.route('/api/receive', methods=['POST'])
@jwt_required()
def receive_item():
    data = request.get_json()
    item_id = data['item_id']
    quantity = data['quantity']
    unit_price = data.get('unit_price', 0)
    
    item = InventoryItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    item.quantity += quantity
    
    transaction = Transaction(
        item_id=item.id,
        item_name=item.name,
        quantity=quantity,
        type='receive',
        unit_price=unit_price,
        total_amount=quantity * unit_price,
        user_id=get_jwt_identity()
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Item received successfully',
        'current_quantity': item.quantity,
        'transaction': {
            'item_name': item.name,
            'quantity': quantity,
            'type': 'receive'
        }
    })

@app.route('/api/issue', methods=['POST'])
@jwt_required()
def issue_item():
    data = request.get_json()
    item_id = data['item_id']
    quantity = data['quantity']
    
    item = InventoryItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    if item.quantity < quantity:
        return jsonify({'error': 'Insufficient quantity'}), 400
    
    item.quantity -= quantity
    
    transaction = Transaction(
        item_id=item.id,
        item_name=item.name,
        quantity=quantity,
        type='issue',
        user_id=get_jwt_identity()
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Item issued successfully',
        'current_quantity': item.quantity,
        'transaction': {
            'item_name': item.name,
            'quantity': quantity,
            'type': 'issue'
        }
    })

@app.route('/api/transactions')
@jwt_required()
def get_transactions():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    return jsonify([{
        'id': t.id,
        'item_name': t.item_name,
        'quantity': t.quantity,
        'type': t.type,
        'unit_price': t.unit_price,
        'total_amount': t.total_amount,
        'date': t.date.strftime('%Y-%m-%d %H:%M:%S')
    } for t in transactions])

@app.route('/dashboard')
@jwt_required()
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
