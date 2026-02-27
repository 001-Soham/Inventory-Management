import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")

def low_stock_items():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT item_name FROM inventory WHERE quantity < 5")
    items = [i[0] for i in cur.fetchall()]

    conn.close()
    return items
