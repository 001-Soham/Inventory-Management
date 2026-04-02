from flask import Flask, render_template, request, jsonify, session, redirect
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

bcrypt = Bcrypt(app)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        quantity INTEGER
    )
    """)

    items = ["Laptop","Mouse","Keyboard","Monitor","SSD","RAM"]

    for item in items:
        cur.execute(
            "INSERT INTO items (name, quantity) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (item, 10)
        )

    conn.commit()
    conn.close()

init_db()

# ---------- ROUTES ----------
@app.route('/')
def home():
    if "user" in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login_page():
    return render_template("login.html", title="Login")

@app.route('/register')
def register_page():
    return render_template("register.html", title="Register")

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect('/login')
    return render_template("dashboard.html", title="Dashboard")

# ---------- AUTH ----------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = bcrypt.generate_password_hash(data['password']).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registered"})
    except:
        return jsonify({"message": "User exists"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user[2], password):
        session['user'] = username
        return jsonify({"message": "Login success"})

    return jsonify({"message": "Invalid"}), 401

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- INVENTORY ----------
@app.route('/api/items')
def get_items():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, quantity FROM items")
    data = [{"name": r[0], "quantity": r[1]} for r in cur.fetchall()]
    conn.close()
    return jsonify(data)

@app.route('/api/update', methods=['POST'])
def update():
    data = request.json
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE items SET quantity = quantity + %s WHERE name=%s",
        (data['change'], data['name'])
    )

    conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})

if __name__ == "__main__":
    app.run()
