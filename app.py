from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'simple-session-key-2024')
app.config['SESSION_TYPE'] = 'filesystem'

bcrypt = Bcrypt(app)
CORS(app)

DB_PATH = 'inventory.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

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
        date TEXT NOT NULL,
        username TEXT
    )''')
    
    default_items = ["Laptop", "Mouse", "Keyboard", "Monitor", "Hard Drive", "RAM", "SSD", "Printer", "Router", "UPS"]
    for item in default_items:
        conn.execute('INSERT OR IGNORE INTO items (name) VALUES (?)', (item,))
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username', '').strip()
    password = bcrypt.generate_password_hash(request.json['password']).decode('utf-8')
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        return jsonify({'message': 'Registered successfully!'})
    except:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', '').strip()
    password = request.json['password']
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and bcrypt.check_password_hash(user['password'], password):
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'message': 'Login successful!', 'username': username})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/api/items')
def get_items():
    if not session.get('logged_in'):
        return jsonify({'error': 'Please login first'}), 401
    
    conn = get_db()
    items = conn.execute('SELECT * FROM items ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(item) for item in items])

@app.route('/api/receive', methods=['POST'])
def receive():
    if not session.get('logged_in'):
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    item_name = data.get('item', '').strip()
    qty = int(data.get('quantity', 0))
    
    if not item_name or qty <= 0:
        return jsonify({'error': 'Invalid data'}), 400
    
    conn = get_db()
    conn.execute('UPDATE items SET quantity = quantity + ? WHERE name = ?', (qty, item_name))
    conn.execute('INSERT INTO transactions (item_name, quantity, type, date, username) VALUES (?, ?, "RECEIVE", ?, ?)', 
                (item_name, qty, datetime.now().isoformat(), session['username']))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Received {qty} {item_name} ✅'})

@app.route('/api/issue', methods=['POST'])
def issue():
    if not session.get('logged_in'):
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.json
    item_name = data.get('item', '').strip()
    qty = int(data.get('quantity', 0))
    
    if not item_name or qty <= 0:
        return jsonify({'error': 'Invalid data'}), 400
    
    conn = get_db()
    item = conn.execute('SELECT quantity FROM items WHERE name = ?', (item_name,)).fetchone()
    
    if not item or item['quantity'] < qty:
        conn.close()
        return jsonify({'error': f'Not enough stock (Available: {item["quantity"] if item else 0})'}), 400
    
    conn.execute('UPDATE items SET quantity = quantity - ? WHERE name = ?', (qty, item_name))
    conn.execute('INSERT INTO transactions (item_name, quantity, type, date, username) VALUES (?, ?, "ISSUE", ?, ?)', 
                (item_name, qty, datetime.now().isoformat(), session['username']))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Issued {qty} {item_name} ✅'})

@app.route('/api/history')
def history():
    if not session.get('logged_in'):
        return jsonify({'error': 'Please login first'}), 401
    
    conn = get_db()
    trans = conn.execute('SELECT * FROM transactions ORDER BY date DESC LIMIT 50').fetchall()
    conn.close()
    return jsonify([dict(t) for t in trans])

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
