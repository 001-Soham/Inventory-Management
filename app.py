from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = "maverix_secret"

# SQLite DB (Render compatible)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    quantity = db.Column(db.Integer)
    user_id = db.Column(db.Integer)

# ================= ROUTES =================

@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ================= AUTH =================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User exists"})
    
    user = User(username=data["username"], password=data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Registered"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"], password=data["password"]).first()
    
    if not user:
        return jsonify({"error": "Invalid credentials"})
    
    session["user"] = user.username
    session["user_id"] = user.id
    return jsonify({"message": "Logged in"})

@app.route("/api/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= INVENTORY =================

@app.route("/api/items", methods=["GET"])
def get_items():
    if "user_id" not in session:
        return jsonify([])
    
    items = Item.query.filter_by(user_id=session["user_id"]).all()
    return jsonify([{"id": i.id, "name": i.name, "quantity": i.quantity} for i in items])

@app.route("/api/items", methods=["POST"])
def add_item():
    data = request.json
    item = Item(name=data["name"], quantity=data["quantity"], user_id=session["user_id"])
    db.session.add(item)
    db.session.commit()
    return jsonify({"message": "Added"})

@app.route("/api/items/<int:id>", methods=["DELETE"])
def delete_item(id):
    item = Item.query.get(id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return jsonify({"message": "Deleted"})

# ================= INIT =================

if __name__ == "__main__":
    if not os.path.exists("instance"):
        os.makedirs("instance")
    with app.app_context():
        db.create_all()
    app.run(debug=True)
