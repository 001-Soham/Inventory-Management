from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import os
from ai import low_stock_items

app = Flask(__name__, template_folder="templates")
app.secret_key = "inventory_secret"

# ---------------- DATABASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ---------------- INIT DATABASE ----------------
def init_db():

    conn = db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # SHOP PROFILE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shop_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT,
        owner_name TEXT,
        staff_count INTEGER,
        legal_doc TEXT
    )
    """)

    # INVENTORY WITH PRICE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE,
        quantity INTEGER NOT NULL,
        price REAL DEFAULT 0
    )
    """)

    # TRANSACTIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        action TEXT,
        quantity INTEGER,
        person TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        conn = db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username,password) VALUES (?,?)",
                (username,password)
            )
            conn.commit()
        except:
            conn.close()
            return "Username already exists"

        conn.close()

        return redirect('/')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username,password)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/dashboard')

        return "Invalid Login"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/')

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM inventory")
    items = cur.fetchall()

    cur.execute("SELECT * FROM transactions ORDER BY time DESC")
    transactions = cur.fetchall()

    cur.execute("SELECT * FROM shop_profile LIMIT 1")
    profile = cur.fetchone()

    alerts = low_stock_items()

    conn.close()

    return render_template(
        "index.html",
        items=items,
        transactions=transactions,
        alerts=alerts,
        profile=profile
    )

# ---------------- UPDATE PROFILE ----------------
@app.route('/update-profile', methods=['POST'])
def update_profile():

    if 'user' not in session:
        return redirect('/')

    shop = request.form['shop_name']
    owner = request.form['owner_name']
    staff = request.form['staff_count']
    doc = request.form['legal_doc']

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM shop_profile")

    if cur.fetchone() is None:

        cur.execute("""
        INSERT INTO shop_profile
        (shop_name, owner_name, staff_count, legal_doc)
        VALUES (?, ?, ?, ?)
        """,(shop,owner,staff,doc))

    else:

        cur.execute("""
        UPDATE shop_profile
        SET shop_name=?, owner_name=?, staff_count=?, legal_doc=?
        WHERE id=1
        """,(shop,owner,staff,doc))

    conn.commit()
    conn.close()

    return redirect('/dashboard')

# ---------------- RECEIVE / ISSUE ----------------
@app.route('/transact', methods=['POST'])
def transact():

    if 'user' not in session:
        return redirect('/')

    name = request.form['name']
    qty = int(request.form['quantity'])
    action = request.form['action']
    person = request.form['person']
    price = request.form.get('price',0)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT quantity FROM inventory WHERE item_name=?", (name,))
    row = cur.fetchone()

    if row is None:

        if action == "issue":
            return "Item does not exist"

        cur.execute(
            "INSERT INTO inventory (item_name,quantity,price) VALUES (?,?,?)",
            (name,qty,price)
        )

    else:

        current_qty = row[0]

        if action == "issue":

            if qty > current_qty:
                return "Not enough stock"

            new_qty = current_qty - qty

        else:
            new_qty = current_qty + qty

        cur.execute(
            "UPDATE inventory SET quantity=? WHERE item_name=?",
            (new_qty,name)
        )

    cur.execute(
        """
        INSERT INTO transactions
        (item_name,action,quantity,person,time)
        VALUES (?,?,?,?,?)
        """,
        (name,action,qty,person,now)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')

# ---------------- DELETE TRANSACTIONS ----------------
@app.route('/delete-transactions', methods=['POST'])
def delete_transactions():

    ids = request.form.getlist('delete_ids')

    conn = db()
    cur = conn.cursor()

    cur.executemany(
        "DELETE FROM transactions WHERE id=?",
        [(i,) for i in ids]
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():

    session.pop('user',None)

    return redirect('/')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
