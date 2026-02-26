import sqlite3

def low_stock_items():
    conn = sqlite3.connect("inventory.db")
    cur = conn.cursor()
    cur.execute("SELECT item_name FROM inventory WHERE quantity < 5")
    items = [i[0] for i in cur.fetchall()]
    conn.close()
    return items