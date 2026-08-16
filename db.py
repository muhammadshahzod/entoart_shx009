import sqlite3

DB_NAME = "etnoart.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Hunarmandlar jadvali
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artisans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    
    # Mahsulotlar jadvali
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            market_price REAL,
            description TEXT,
            artisan_id INTEGER,
            image_url TEXT,
            FOREIGN KEY (artisan_id) REFERENCES artisans (id)
        )
    """)
    
    # Sharhlar jadvali
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            user_name TEXT,
            rating INTEGER,
            comment TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)
    
    # Buyurtmalar jadvali
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            phone TEXT,
            address TEXT,
            product_id INTEGER,
            amount REAL,
            status TEXT,
            payment_method TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)
    
    # Agar bazada birorta ham hunarmand bo'lmasa, avtomatik Tursunov Temurbekni qo'shamiz
    artisan_count = conn.execute("SELECT COUNT(*) FROM artisans").fetchone()[0]
    if artisan_count == 0:
        conn.execute("INSERT INTO artisans (name) VALUES (?)", ("Tursunov Temurbek",))
    
    conn.commit()
    conn.close()

def get_all_products(category=None, search=None):
    conn = get_db_connection()
    query = "SELECT products.*, artisans.name as artisan_name FROM products LEFT JOIN artisans ON products.artisan_id = artisans.id WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
        
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    products = conn.execute(query, params).fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return product

def get_all_artisans():
    conn = get_db_connection()
    artisans = conn.execute("SELECT * FROM artisans").fetchall()
    conn.close()
    return artisans