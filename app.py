from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
from ai import low_stock_items

app = Flask(__name__, template_folder="templates")

# ---------------- DB CONNECTION ----------------
def init_db():
    conn = sqlite3.connect("inventory.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE,
        quantity INTEGER NOT NULL
    )
    """)

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


@app.route('/delete-transactions', methods=['POST'])
def delete_transactions():
    ids = request.form.getlist('delete_ids')

    if not ids:
        return redirect('/')

    conn = db()
    cur = conn.cursor()

    cur.executemany(
        "DELETE FROM transactions WHERE id = ?",
        [(i,) for i in ids]
    )

    conn.commit()
    conn.close()
    return redirect('/')

# ---------------- HOME / DASHBOARD ----------------
@app.route('/')
def index():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM inventory")
    items = cur.fetchall()

    cur.execute("SELECT * FROM transactions ORDER BY time DESC")
    transactions = cur.fetchall()

    alerts = low_stock_items()

    conn.close()

    return render_template(
        "index.html",
        items=items,
        transactions=transactions,
        alerts=alerts
    )

# ---------------- ADD NEW ITEM ----------------
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    cap = int(request.form['capacity'])

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO inventory VALUES (NULL, ?, ?, 0, ?)",
        (name, cap, cap)
    )
    conn.commit()
    conn.close()
    return redirect('/')


# ---------------- RECEIVE / ISSUE ITEM ----------------
@app.route('/transact', methods=['POST'])
def transact():
    name = request.form['name']
    qty = int(request.form['quantity'])
    action = request.form['action']
    person = request.form['person']
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if qty <= 0:
        return "❌ Quantity must be greater than zero."

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT quantity FROM inventory WHERE item_name = ?",
        (name,)
    )
    row = cur.fetchone()

    # 🔹 ITEM DOES NOT EXIST
    if row is None:
        if action == "issue":
            return "❌ Cannot issue item that does not exist."

        # auto-create on receive
        cur.execute(
            "INSERT INTO inventory (item_name, quantity) VALUES (?, ?)",
            (name, qty)
        )
    else:
        current_qty = row[0]

        if action == "issue":
            if qty > current_qty:
                return "❌ Not enough stock."
            new_qty = current_qty - qty
        else:
            new_qty = current_qty + qty

        cur.execute(
            "UPDATE inventory SET quantity = ? WHERE item_name = ?",
            (new_qty, name)
        )

    # 🔹 SAVE TRANSACTION
    cur.execute(
        "INSERT INTO transactions VALUES (NULL, ?, ?, ?, ?, ?)",
        (name, action, qty, person, now)
    )

    conn.commit()
    conn.close()
    return redirect('/')


# ---------------- RUN APP (LAST LINE ONLY) ----------------
if __name__ == "__main__":

    app.run(host="0.0.0.0", port=10000)



