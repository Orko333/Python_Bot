import sqlite3
from contextlib import closing

DB_PATH = 'botdata.sqlite3'

# --- Ініціалізація БД ---
def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            first_name TEXT,
            username TEXT,
            phone_number TEXT,
            type_label TEXT,
            order_type TEXT,
            topic TEXT,
            subject TEXT,
            deadline TEXT,
            volume TEXT,
            requirements TEXT,
            file_id TEXT,
            price INTEGER,
            status TEXT,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            text TEXT,
            stars INTEGER,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS support_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            admin_id INTEGER,
            message TEXT,
            direction TEXT,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            referred_id INTEGER,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            discount_type TEXT,
            discount_value INTEGER,
            usage_limit INTEGER,
            used_count INTEGER DEFAULT 0,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS promocode_usages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            used_at TEXT
        )''')
        conn.commit()

# --- Функції для роботи з orders ---
def add_order(order: dict):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO orders (user_id, first_name, username, phone_number, type_label, order_type, topic, subject, deadline, volume, requirements, file_id, price, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))''',
            (
                order.get('user_id'), order.get('first_name'), order.get('username'), order.get('phone_number'),
                order.get('type_label'), order.get('order_type'), order.get('topic'), order.get('subject'),
                order.get('deadline'), order.get('volume'), order.get('requirements'), order.get('file_id'),
                order.get('price'), order.get('status', 'нове')
            )
        )
        conn.commit()
        return c.lastrowid

def get_orders(user_id=None, status=None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        q = 'SELECT * FROM orders WHERE 1=1'
        params = []
        if user_id:
            q += ' AND user_id=?'
            params.append(user_id)
        if status:
            q += ' AND status=?'
            params.append(status)
        c.execute(q, params)
        return c.fetchall()

def get_order_by_num(num):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY id ASC')
        orders = c.fetchall()
        if num < 1 or num > len(orders):
            return None
        return orders[num - 1]

def find_orders(query):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        q = '''SELECT * FROM orders WHERE \
            user_id LIKE ? OR \
            username LIKE ? OR \
            topic LIKE ?'''
        like = f'%{query}%'
        c.execute(q, (like, like, like))
        return c.fetchall()

def update_order_status(num, new_status):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM orders ORDER BY id ASC')
        ids = [row[0] for row in c.fetchall()]
        if num < 1 or num > len(ids):
            return False, None
        order_id = ids[num - 1]
        c.execute('UPDATE orders SET status=? WHERE id=?', (new_status, order_id))
        conn.commit()
        return True, order_id

# --- Функції для роботи з feedbacks ---
def add_feedback(feedback: dict):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO feedbacks (user_id, username, text, stars, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))''',
            (feedback.get('user_id'), feedback.get('username'), feedback.get('text'), feedback.get('stars'))
        )
        conn.commit()
        return c.lastrowid

def get_feedbacks():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM feedbacks ORDER BY created_at DESC')
        return c.fetchall()

# --- Функції для роботи з support_logs ---
def add_support_log(log: dict):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO support_logs (user_id, admin_id, message, direction, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))''',
            (log.get('user_id'), log.get('admin_id'), log.get('message'), log.get('direction'))
        )
        conn.commit()
        return c.lastrowid

def get_support_logs(user_id=None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        q = 'SELECT * FROM support_logs WHERE 1=1'
        params = []
        if user_id:
            q += ' AND user_id=?'
            params.append(user_id)
        c.execute(q, params)
        return c.fetchall()

# --- Реферали ---
def add_referral(user_id, referred_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO referrals (user_id, referred_id, created_at) VALUES (?, ?, datetime("now"))', (user_id, referred_id))
        conn.commit()

def get_referrals(user_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM referrals WHERE user_id=?', (user_id,))
        return c.fetchall()

# --- Промокоди ---
def add_promocode(code, discount_type, discount_value, usage_limit):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO promocodes (code, discount_type, discount_value, usage_limit, created_at) VALUES (?, ?, ?, ?, datetime("now"))', (code, discount_type, discount_value, usage_limit))
        conn.commit()

def get_promocode(code):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM promocodes WHERE code=?', (code,))
        return c.fetchone()

def use_promocode(user_id, code):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO promocode_usages (user_id, code, used_at) VALUES (?, ?, datetime("now"))', (user_id, code))
        c.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE code=?', (code,))
        conn.commit()

def get_promocode_usages(code):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM promocode_usages WHERE code=?', (code,))
        return c.fetchall()

# --- Викликати при старті бота ---
if __name__ == '__main__':
    init_db() 