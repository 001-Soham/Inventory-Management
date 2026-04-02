from datetime import datetime
import os

from flask import Flask, jsonify, redirect, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, inspect, or_, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_change_this")

if not os.path.exists("instance"):
    os.makedirs("instance")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:////tmp/database.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=True)  # legacy plain-text column
    password_hash = db.Column(db.String(255), nullable=False)


class Product(db.Model):
    __table_args__ = (UniqueConstraint("user_id", "sku", name="uq_user_sku"),)

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(120), nullable=False, default="General")
    supplier = db.Column(db.String(200), nullable=False, default="Unknown")
    unit_price = db.Column(db.Float, nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable=False, index=True)


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    movement_type = db.Column(db.String(20), nullable=False)  # in/out/adjust
    quantity = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def initialize_db():
    db.create_all()

    inspector = inspect(db.engine)
    columns = {col["name"] for col in inspector.get_columns("user")}
    if "password_hash" not in columns:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN password_hash VARCHAR(255)'))
        db.session.execute(text('UPDATE "user" SET password_hash = password WHERE password_hash IS NULL'))
        db.session.commit()

    if "password" not in columns:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN password VARCHAR(100)'))
        db.session.commit()


with app.app_context():
    initialize_db()


def current_user_id():
    return session.get("user_id")


def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.route("/")
def home():
    if current_user_id():
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
    if not current_user_id():
        return redirect("/login")
    return render_template("dashboard.html", active_tab="dashboard")


@app.route("/inventory")
def inventory_page():
    if not current_user_id():
        return redirect("/login")
    return render_template("inventory.html", active_tab="inventory")


@app.route("/issue")
def issue_page():
    if not current_user_id():
        return redirect("/login")
    return render_template("issue.html", active_tab="issue")


@app.route("/receive")
def receive_page():
    if not current_user_id():
        return redirect("/login")
    return render_template("receive.html", active_tab="receive")


@app.route("/logs")
def logs_page():
    if not current_user_id():
        return redirect("/login")
    return render_template("logs.html", active_tab="logs")


@app.route("/profile")
def profile_page():
    if not current_user_id():
        return redirect("/login")
    return render_template("profile.html", active_tab="profile")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or len(password) < 6:
        return jsonify({"error": "Username required and password must be at least 6 chars"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists"}), 409

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Registered successfully"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()
    is_valid_hash = bool(user and user.password_hash and check_password_hash(user.password_hash, password))
    is_legacy_plain = bool(user and user.password and user.password == password)

    if not user or (not is_valid_hash and not is_legacy_plain):
        return jsonify({"error": "Invalid credentials"}), 401

    if is_legacy_plain and not user.password_hash:
        user.password_hash = generate_password_hash(password)
        db.session.commit()

    session["user"] = user.username
    session["user_id"] = user.id
    return jsonify({"message": "Login success"})


@app.route("/api/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/api/dashboard-summary")
def dashboard_summary():
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    products = Product.query.filter_by(user_id=user_id).all()
    total_products = len(products)
    total_units = sum(p.quantity for p in products)
    inventory_value = round(sum(p.quantity * p.unit_price for p in products), 2)
    low_stock = sum(1 for p in products if p.quantity <= p.reorder_level)

    recent_movements = (
        StockMovement.query.filter_by(user_id=user_id)
        .order_by(StockMovement.created_at.desc())
        .limit(8)
        .all()
    )
    products_map = {p.id: p.name for p in Product.query.filter_by(user_id=user_id).all()}

    return jsonify(
        {
            "metrics": {
                "total_products": total_products,
                "total_units": total_units,
                "inventory_value": inventory_value,
                "low_stock": low_stock,
            },
            "recent_movements": [
                {
                    "id": m.id,
                    "product_id": m.product_id,
                    "product_name": products_map.get(m.product_id, "Deleted product"),
                    "movement_type": m.movement_type,
                    "quantity": m.quantity,
                    "note": m.note,
                    "created_at": m.created_at.isoformat(),
                }
                for m in recent_movements
            ],
        }
    )


@app.route("/api/products", methods=["GET"])
def get_products():
    user_id = current_user_id()
    if not user_id:
        return jsonify([])

    query = Product.query.filter_by(user_id=user_id)
    search = (request.args.get("query") or "").strip()
    category = (request.args.get("category") or "").strip()
    status = (request.args.get("status") or "").strip()

    if search:
        like_q = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(like_q), Product.sku.ilike(like_q), Product.supplier.ilike(like_q)))
    if category:
        query = query.filter(Product.category == category)

    products = query.order_by(Product.created_at.desc()).all()

    if status == "low":
        products = [p for p in products if p.quantity <= p.reorder_level]

    return jsonify(
        [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "supplier": p.supplier,
                "unit_price": p.unit_price,
                "quantity": p.quantity,
                "reorder_level": p.reorder_level,
                "is_low_stock": p.quantity <= p.reorder_level,
                "inventory_value": round(p.quantity * p.unit_price, 2),
            }
            for p in products
        ]
    )


@app.route("/api/products", methods=["POST"])
def create_product():
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    sku = (data.get("sku") or "").strip()

    if not name or not sku:
        return jsonify({"error": "Name and SKU are required"}), 400

    existing = Product.query.filter_by(user_id=user_id, sku=sku).first()
    if existing:
        return jsonify({"error": "SKU already exists"}), 409

    product = Product(
        sku=sku,
        name=name,
        category=(data.get("category") or "General").strip() or "General",
        supplier=(data.get("supplier") or "Unknown").strip() or "Unknown",
        unit_price=max(0, parse_float(data.get("unit_price"), 0)),
        quantity=max(0, parse_int(data.get("quantity"), 0)),
        reorder_level=max(0, parse_int(data.get("reorder_level"), 5)),
        user_id=user_id,
    )
    db.session.add(product)
    db.session.flush()

    if product.quantity > 0:
        db.session.add(
            StockMovement(
                product_id=product.id,
                user_id=user_id,
                movement_type="in",
                quantity=product.quantity,
                note="Opening stock",
            )
        )

    db.session.commit()
    return jsonify({"message": "Product created", "id": product.id})


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json() or {}
    next_sku = (data.get("sku") or product.sku).strip()
    if next_sku != product.sku:
        duplicate = Product.query.filter_by(user_id=user_id, sku=next_sku).first()
        if duplicate:
            return jsonify({"error": "SKU already exists"}), 409

    product.name = (data.get("name") or product.name).strip()
    product.sku = next_sku
    product.category = (data.get("category") or product.category).strip()
    product.supplier = (data.get("supplier") or product.supplier).strip()
    product.unit_price = max(0, parse_float(data.get("unit_price"), product.unit_price))
    product.reorder_level = max(0, parse_int(data.get("reorder_level"), product.reorder_level))

    db.session.commit()
    return jsonify({"message": "Product updated"})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    StockMovement.query.filter_by(product_id=product_id, user_id=user_id).delete()
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})


@app.route("/api/products/<int:product_id>/movement", methods=["POST"])
def add_movement(product_id):
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json() or {}
    movement_type = data.get("movement_type")
    qty = max(0, parse_int(data.get("quantity"), 0))
    note = (data.get("note") or "").strip()

    if movement_type not in {"in", "out", "adjust"} or qty <= 0:
        return jsonify({"error": "Invalid movement data"}), 400

    if movement_type == "out":
        if product.quantity < qty:
            return jsonify({"error": "Not enough stock"}), 400
        product.quantity -= qty
    elif movement_type == "in":
        product.quantity += qty
    else:  # adjust
        product.quantity = qty

    db.session.add(
        StockMovement(
            product_id=product.id,
            user_id=user_id,
            movement_type=movement_type,
            quantity=qty,
            note=note,
        )
    )
    db.session.commit()
    return jsonify({"message": "Movement recorded", "quantity": product.quantity})


@app.route("/api/products/<int:product_id>/movements", methods=["GET"])
def get_movements(product_id):
    user_id = current_user_id()
    if not user_id:
        return jsonify([])

    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    movements = (
        StockMovement.query.filter_by(product_id=product_id, user_id=user_id)
        .order_by(StockMovement.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify(
        [
            {
                "id": m.id,
                "movement_type": m.movement_type,
                "quantity": m.quantity,
                "note": m.note,
                "created_at": m.created_at.isoformat(),
            }
            for m in movements
        ]
    )


@app.route("/api/logs", methods=["GET"])
def get_logs():
    user_id = current_user_id()
    if not user_id:
        return jsonify([])

    movement_type = (request.args.get("type") or "").strip()
    limit = min(max(parse_int(request.args.get("limit"), 100), 1), 500)
    query = StockMovement.query.filter_by(user_id=user_id)
    if movement_type in {"in", "out", "adjust"}:
        query = query.filter_by(movement_type=movement_type)

    logs = query.order_by(StockMovement.created_at.desc()).limit(limit).all()
    products_map = {p.id: p for p in Product.query.filter_by(user_id=user_id).all()}
    return jsonify(
        [
            {
                "id": log.id,
                "movement_type": log.movement_type,
                "quantity": log.quantity,
                "note": log.note,
                "created_at": log.created_at.isoformat(),
                "product_id": log.product_id,
                "product_name": products_map.get(log.product_id).name if products_map.get(log.product_id) else "Deleted product",
                "sku": products_map.get(log.product_id).sku if products_map.get(log.product_id) else "-",
            }
            for log in logs
        ]
    )


@app.route("/api/profile", methods=["GET", "PUT"])
def profile_api():
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if request.method == "GET":
        products_count = Product.query.filter_by(user_id=user_id).count()
        movements_count = StockMovement.query.filter_by(user_id=user_id).count()
        return jsonify(
            {
                "username": user.username,
                "products_count": products_count,
                "movements_count": movements_count,
            }
        )

    data = request.get_json() or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 chars"}), 400

    valid_hash = bool(user.password_hash and check_password_hash(user.password_hash, current_password))
    valid_legacy = bool(user.password and user.password == current_password)
    if not valid_hash and not valid_legacy:
        return jsonify({"error": "Current password is incorrect"}), 400

    user.password_hash = generate_password_hash(new_password)
    user.password = None
    db.session.commit()
    return jsonify({"message": "Password updated"})


if __name__ == "__main__":
    app.run(debug=True)
