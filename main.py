import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth
from functools import wraps

from db import init_db, get_db_connection, get_all_products, get_product_by_id, get_all_artisans

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY", "etnoart_secure_secret_key_2026")

UPLOAD_DIR = "static/uploads"

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

ADMIN_EMAILS = ["temurbektursunov059@gmail.com",
                "muhammadshahzod09@gmail.com"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('google_login'))
        if session['user']['email'] not in ADMIN_EMAILS:
            return "Sizda admin panelga kirish huquqi yo'q.", 403
        return f(*args, **kwargs)
    return decorated_function

with app.app_context():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    init_db()

@app.route("/")
def index():
    cat = request.args.get("cat")
    search = request.args.get("search")
    sort = request.args.get("sort")

    products = get_all_products(category=cat, search=search)

    if sort == "price_asc":
        products = sorted(products, key=lambda x: x["price"])
    elif sort == "price_desc":
        products = sorted(products, key=lambda x: x["price"], reverse=True)
    elif sort == "newest":
        products = sorted(products, key=lambda x: x["id"], reverse=True)

    artisans = get_all_artisans()
    return render_template("index.html",
                           products=products,
                           artisans=artisans,
                           selected_category=cat,
                           search_query=search,
                           selected_sort=sort)

@app.route("/login/google")
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/authorize/google")
def google_authorize():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if user_info:
            session['user'] = {
                'name': user_info.get('name'),
                'email': user_info.get('email'),
                'picture': user_info.get('picture')
            }
    except Exception as e:
        print(f"Auth error: {e}")
    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_product_by_id(product_id)
    if not product:
        abort(404)

    conn = get_db_connection()
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,)).fetchall()
    artisan = None
    if product.get("artisan_id"):
        artisan = conn.execute("SELECT * FROM artisans WHERE id = ?", (product["artisan_id"],)).fetchone()
    conn.close()

    return render_template("product_detail.html", product=product, reviews=reviews, artisan=artisan)

@app.route("/product/<int:product_id>/review", methods=["POST"])
def add_review(product_id):
    user_name = request.form.get("user_name", "").strip()
    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()

    if not user_name or not comment:
        product = get_product_by_id(product_id)
        if not product:
            abort(404)
        conn = get_db_connection()
        reviews = conn.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,)).fetchall()
        artisan = None
        if product.get("artisan_id"):
            artisan = conn.execute("SELECT * FROM artisans WHERE id = ?", (product["artisan_id"],)).fetchone()
        conn.close()
        return render_template("product_detail.html", product=product, reviews=reviews,
                               artisan=artisan, error="Iltimos, ism va izohni to'ldiring")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO reviews (product_id, user_name, rating, comment) VALUES (?, ?, ?, ?)",
        (product_id, user_name, rating, comment)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("product_detail", product_id=product_id))

@app.route("/admin")
@login_required
def admin_panel():
    conn = get_db_connection()
    products = conn.execute("""
        SELECT products.*, artisans.name as artisan_name
        FROM products
        LEFT JOIN artisans ON products.artisan_id = artisans.id
    """).fetchall()
    artisans = conn.execute("SELECT * FROM artisans").fetchall()
    orders = conn.execute("SELECT * FROM orders").fetchall()

    total_products = len(products)
    total_orders = len(orders)
    total_revenue = sum([o["amount"] for o in orders if o["amount"]])

    conn.close()
    return render_template("admin.html",
                           products=products,
                           artisans=artisans,
                           orders=orders,
                           total_products=total_products,
                           total_orders=total_orders,
                           total_revenue=total_revenue)

@app.route("/admin/add-product-page")
@login_required
def add_product_page():
    conn = get_db_connection()
    artisans = conn.execute("SELECT * FROM artisans").fetchall()
    conn.close()
    return render_template("add_product.html", artisans=artisans)

@app.route("/admin/orders")
@login_required
def admin_orders():
    conn = get_db_connection()
    orders = conn.execute("""
        SELECT orders.*, products.title as product_title
        FROM orders
        LEFT JOIN products ON orders.product_id = products.id
        ORDER BY orders.id DESC
    """).fetchall()

    total_revenue = sum([o["amount"] for o in orders if o["amount"]])
    new_orders_count = sum([1 for o in orders if o["status"] == "Yangi"])

    conn.close()
    return render_template("admin_orders.html",
                           orders=orders,
                           total_revenue=total_revenue,
                           new_orders_count=new_orders_count)

@app.route("/admin/update-order-status/<int:order_id>", methods=["POST"])
@login_required
def update_order_status(order_id):
    new_status = request.form.get("status")
    conn = get_db_connection()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_orders"))

@app.route("/admin/add-product", methods=["POST"])
@login_required
def add_product():
    title = request.form.get("title")
    category = request.form.get("category")
    price = float(request.form.get("price", 0))
    market_price = request.form.get("market_price")
    market_price = float(market_price) if market_price else None
    description = request.form.get("description")
    artisan_id = int(request.form.get("artisan_id", 1))

    image = request.files.get("image")
    image_url = ""
    if image and image.filename:
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_DIR, filename)
        image.save(image_path)
        image_url = f"/static/uploads/{filename}"

    conn = get_db_connection()
    conn.execute(
        """INSERT INTO products (title, category, price, market_price, description, artisan_id, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (title, category, price, market_price, description, artisan_id, image_url)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete-product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_panel"))

@app.route("/api/create-order", methods=["POST"])
def create_order():
    data = request.get_json() or request.form

    user_name = data.get("user_name")
    phone = data.get("phone")
    address = data.get("address")
    payment_method = data.get("payment_method")

    cart_items = data.get("cart_items")
    amount = float(data.get("amount", 0))
    product_id = int(data.get("product_id", 0))

    conn = get_db_connection()

    if cart_items and isinstance(cart_items, list) and len(cart_items) > 0:
        main_product_id = cart_items[0].get("id", product_id)

        calc_amount = sum([float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items])
        if calc_amount > 0:
            amount = calc_amount

        items_summary = ", ".join([f"{i.get('title')} (x{i.get('quantity', 1)})" for i in cart_items])

        conn.execute(
            """INSERT INTO orders (user_name, phone, address, product_id, amount, status, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_name, phone, f"{address} | Buyurtmalar: {items_summary}", main_product_id, amount, "Yangi", payment_method)
        )
    else:
        conn.execute(
            """INSERT INTO orders (user_name, phone, address, product_id, amount, status, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_name, phone, address, product_id, amount, "Yangi", payment_method)
        )

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Buyurtma muvaffaqiyatli qabul qilindi!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    # shakhzod's version 5xx