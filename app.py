from flask import Flask, request, jsonify, render_template, session
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from datetime import datetime
import sqlite3
import os
import hashlib
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-change-this'
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)

# Database file
DB_FILE = 'inventory.db'

# Predefined items
PREDEFINED_ITEMS = [
    "Laptop Dell Inspiron", "Mouse Logitech Wireless", "Keyboard Mechanical",
    "Monitor 24 inch", "Hard Drive 1TB", "RAM 16GB DDR4", "SSD 512GB NVMe",
    "Printer HP LaserJet", "Router Cisco", "Switch Network 24 Port",
    "UPS 1000VA", "Webcam HD", "Headphones Noise Cancelling",
    "Mobile Phone Stand", "Cable HDMI 2m"
]

def init_db():
    """Initialize database and create tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inventory items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            unit_price REAL DEFAULT 0.0
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('receive', 'issue')),
            unit_price REAL,
            total_amount REAL,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        )
    ''')
    
    # Add predefined items if they don't exist
    for item_name in PREDEFINED_ITEMS:
        cursor.execute('SELECT id FROM inventory_items WHERE name = ?', (item_name,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO inventory_items (name) VALUES (?)', (item_name,))
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Username already exists'}), 400
        
        # Insert new user
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                      (username, password))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'User registered successfully'})
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = data['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', 
                      (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            access_token = create_access_token(identity=user['id'])
            return jsonify({
                'access_token': access_token,
                'user_id': user['id'],
                'username': user['username']
            })
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/api/predefined_items')
@jwt_required()
def get_predefined_items():
    conn = get_db_connection()
    items = conn.execute('SELECT id, name, quantity FROM inventory_items ORDER BY name').fetchall()
    conn.close()
    
    return jsonify([dict(item) for item in items])

@app.route('/api/receive', methods=['POST'])
@jwt_required()
def receive_item():
    data = request.get_json()
    item_id = data['item_id']
    quantity = data['quantity']
    unit_price = data.get('unit_price', 0)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item exists
    cursor.execute('SELECT id, name, quantity FROM inventory_items WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return jsonify({'error': 'Item not found'}), 404
    
    # Update inventory
    new_quantity = item['quantity'] + quantity
    cursor.execute('''
        UPDATE inventory_items 
        SET quantity = ? 
        WHERE id = ?
    ''', (new_quantity, item_id))
    
    # Add transaction
    cursor.execute('''
        INSERT INTO transactions (item_id, item_name, quantity, type, unit_price, total_amount, user_id)
        VALUES (?, ?, ?, 'receive', ?, ?, ?)
    ''', (item_id, item['name'], quantity, unit_price, quantity * unit_price, get_jwt_identity()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Item received successfully',
        'current_quantity': new_quantity,
        'transaction': {
            'item_name': item['name'],
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item exists and has enough quantity
    cursor.execute('SELECT id, name, quantity FROM inventory_items WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return jsonify({'error': 'Item not found'}), 404
    
    if item['quantity'] < quantity:
        conn.close()
        return jsonify({'error': 'Insufficient quantity'}), 400
    
    # Update inventory
    new_quantity = item['quantity'] - quantity
    cursor.execute('''
        UPDATE inventory_items 
        SET quantity = ? 
        WHERE id = ?
    ''', (new_quantity, item_id))
    
    # Add transaction
    cursor.execute('''
        INSERT INTO transactions (item_id, item_name, quantity, type, user_id)
        VALUES (?, ?, ?, 'issue', ?)
    ''', (item_id, item['name'], quantity, get_jwt_identity()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Item issued successfully',
        'current_quantity': new_quantity,
        'transaction': {
            'item_name': item['name'],
            'quantity': quantity,
            'type': 'issue'
        }
    })

@app.route('/api/transactions')
@jwt_required()
def get_transactions():
    conn = get_db_connection()
    transactions = conn.execute('''
        SELECT id, item_name, quantity, type, unit_price, total_amount, date 
        FROM transactions 
        ORDER BY date DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    
    result = []
    for t in transactions:
        result.append({
            'id': t['id'],
            'item_name': t['item_name'],
            'quantity': t['quantity'],
            'type': t['type'],
            'unit_price': t['unit_price'] or 0,
            'total_amount': t['total_amount'] or 0,
            'date': t['date']
        })
    
    return jsonify(result)

@app.route('/dashboard')
@jwt_required()
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
