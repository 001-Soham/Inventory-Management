from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
from ai import low_stock_items

app = Flask(__name__)

# ---------------- DB CONNECTION ----------------
def db():
    return sqlite3.connect("inventory.db")


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
    capacity = request.form.get('capacity')  # only for first receive

    if qty <= 0:
        return "❌ Quantity must be greater than zero."

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT quantity, total_capacity FROM inventory WHERE item_name = ?",
        (name,)
    )
    row = cur.fetchone()

    now = datetime.now()

    # 🔹 ITEM DOES NOT EXIST
    if row is None:
        if action == "issue":
            return "❌ Cannot issue item that does not exist."

        if capacity is None:
            return "❌ Max storage capacity required."

        capacity = int(capacity)

        if qty > capacity:
            return "❌ Quantity exceeds max storage capacity."

        cur.execute(
            """
            INSERT INTO inventory (item_name, quantity, total_capacity, remaining_capacity)
            VALUES (?, ?, ?, ?)
            """,
            (name, qty, capacity, capacity - qty)
        )

        cur.execute(
            "INSERT INTO transactions VALUES (NULL, ?, ?, ?, ?, ?)",
            (name, action, qty, person, now)
        )

        conn.commit()
        conn.close()
        return redirect('/')

    # 🔹 ITEM EXISTS
    current_qty, total_capacity = row

    if action == "receive":
        if current_qty + qty > total_capacity:
            return "❌ Cannot exceed max storage capacity."

        new_qty = current_qty + qty

    else:  # issue
        if qty > current_qty:
            return "❌ Not enough stock to issue."

        new_qty = current_qty - qty

    remaining = total_capacity - new_qty  # 🔥 ALWAYS NON-NEGATIVE

    cur.execute(
        """
        UPDATE inventory
        SET quantity = ?, remaining_capacity = ?
        WHERE item_name = ?
        """,
        (new_qty, remaining, name)
    )

    cur.execute(
        "INSERT INTO transactions VALUES (NULL, ?, ?, ?, ?, ?)",
        (name, action, qty, person, now)
    )

    conn.commit()
    conn.close()
    return redirect('/')


# ---------------- RUN APP (LAST LINE ONLY) ----------------
if __name__ == "__main__":
    app.run(debug=True)