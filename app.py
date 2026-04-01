from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# -------- DATABASE INIT --------
def init_db():
    conn = sqlite3.connect("inventory.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            item TEXT PRIMARY KEY,
            qty INTEGER
        )
    """)
    conn.close()

init_db()

# -------- ROUTES --------

@app.route("/")
def home():
    return render_template("base.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/receive")
def receive():
    return render_template("receive.html")

@app.route("/issue")
def issue():
    return render_template("issue.html")

@app.route("/stock")
def stock():
    conn = sqlite3.connect("inventory.db")
    data = conn.execute("SELECT * FROM stock").fetchall()
    conn.close()
    return render_template("stock.html", items=data)

# -------- ADD ITEM --------
@app.route("/add", methods=["POST"])
def add():
    item = request.form["item"]
    qty = int(request.form["qty"])

    conn = sqlite3.connect("inventory.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM stock WHERE item=?", (item,))
    existing = cur.fetchone()

    if existing:
        cur.execute("UPDATE stock SET qty = qty + ? WHERE item=?", (qty, item))
    else:
        cur.execute("INSERT INTO stock VALUES (?,?)", (item, qty))

    conn.commit()
    conn.close()

    return redirect("/")

# -------- ISSUE ITEM --------
@app.route("/issue_item", methods=["POST"])
def issue_item():
    item = request.form["item"]
    qty = int(request.form["qty"])

    conn = sqlite3.connect("inventory.db")
    cur = conn.cursor()

    cur.execute("UPDATE stock SET qty = qty - ? WHERE item=?", (qty, item))

    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
