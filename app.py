from flask import Flask, request, jsonify, render_template
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-2024')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'super-jwt-secret-2024')

bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)

DB_PATH = 'inventory.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Create tables
def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        quantity INTEGER DEFAULT 0
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        type TEXT NOT NULL,
        date TEXT NOT NULL
    )''')
    
    # Add default items
    default_items = [
        "Laptop", "Mouse", "Keyboard", "Monitor", "Hard Drive", 
        "RAM", "SSD", "Printer", "Router", "UPS"
    ]
    
    for item in default_items:
        conn.execute('INSERT OR IGNORE INTO items (name) VALUES (?)', (item,))
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        return jsonify({'message': 'Registered successfully'})
    except:
        return jsonify({'error': 'Username exists'}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (data['username'],)).fetchone()
    conn.close()
    
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        token = create_access_token(identity=user['id'])
        return jsonify({'token': token, 'username': data['username']})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/items')
@jwt_required()
def get_items():
    conn = get_db()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return jsonify([dict(item) for item in items])

@app.route('/api/receive', methods=['POST'])
@jwt_required()
def receive():
    data = request.json
    item_name = data['item']
    qty = int(data['quantity'])
    
    conn = get_db()
    conn.execute('UPDATE items SET quantity = quantity + ? WHERE name = ?', (qty, item_name))
    conn.execute('INSERT INTO transactions (item_name, quantity, type, date) VALUES (?, ?, "RECEIVE", ?)', 
                (item_name, qty, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Received {qty} {item_name}'})

@app.route('/api/issue', methods=['POST'])
@jwt_required()
def issue():
    data = request.json
    item_name = data['item']
    qty = int(data['quantity'])
    
    conn = get_db()
    item = conn.execute('SELECT quantity FROM items WHERE name = ?', (item_name,)).fetchone()
    
    if item['quantity'] < qty:
        conn.close()
        return jsonify({'error': 'Insufficient stock'}), 400
    
    conn.execute('UPDATE items SET quantity = quantity - ? WHERE name = ?', (qty, item_name))
    conn.execute('INSERT INTO transactions (item_name, quantity, type, date) VALUES (?, ?, "ISSUE", ?)', 
                (item_name, qty, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Issued {qty} {item_name}'})

@app.route('/api/history')
@jwt_required()
def history():
    conn = get_db()
    trans = conn.execute('SELECT * FROM transactions ORDER BY date DESC LIMIT 50').fetchall()
    conn.close()
    return jsonify([dict(t) for t in trans])

@app.route('/dashboard')
@jwt_required()
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
