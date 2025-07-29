import sqlite3
from contextlib import closing
import json
from datetime import datetime, timedelta
import random

DB_PATH = 'botdata.sqlite3'

def get_db_connection():
    """Створює з'єднання з базою даних з таймаутом."""
    return sqlite3.connect(DB_PATH, timeout=10)

# --- Ініціалізація БД ---
def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Оновлена таблиця замовлень з підтримкою кількох файлів
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
            files TEXT,  -- JSON array of file_ids
            price INTEGER,
            status TEXT DEFAULT 'draft',
            created_at TEXT,
            updated_at TEXT,
            confirmed_at TEXT,
            manager_id INTEGER,
            notes TEXT
        )''')
        
        # Таблиця для файлів замовлень
        c.execute('''CREATE TABLE IF NOT EXISTS order_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            file_id TEXT,
            file_name TEXT,
            file_type TEXT,
            uploaded_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )''')
        
        # Таблиця для історії статусів
        c.execute('''CREATE TABLE IF NOT EXISTS order_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            status TEXT,
            changed_by INTEGER,
            changed_at TEXT,
            notes TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id)
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
        
        # Оновлена таблиця промокодів з часовими обмеженнями
        c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            discount_type TEXT,
            discount_value INTEGER,
            usage_limit INTEGER,
            used_count INTEGER DEFAULT 0,
            created_at TEXT,
            expires_at TEXT,
            is_personal BOOLEAN DEFAULT 0,
            personal_user_id INTEGER,
            min_order_amount INTEGER DEFAULT 0
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS promocode_usages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            order_id INTEGER,
            used_at TEXT,
            discount_amount INTEGER
        )''')
        
        # Таблиця для реферальних бонусів
        c.execute('''CREATE TABLE IF NOT EXISTS referral_bonuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            referred_user_id INTEGER,
            order_id INTEGER,
            bonus_amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            paid_at TEXT
        )''')
        
        # Таблиця для нагадувань
        c.execute('''CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_id INTEGER,
            reminder_type TEXT,
            scheduled_at TEXT,
            sent_at TEXT,
            message TEXT
        )''')
        
        # Таблиця для спам захисту
        c.execute('''CREATE TABLE IF NOT EXISTS spam_protection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            created_at TEXT
        )''')
        
        # Таблиця для бекапів
        c.execute('''CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_file TEXT,
            created_at TEXT,
            size_bytes INTEGER
        )''')
        
        # Таблиця для зберігання всіх переписок
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            direction TEXT, -- 'user' або 'bot'
            text TEXT,
            message_type TEXT,
            created_at TEXT
        )''')
        
        conn.commit()

# --- Функції для роботи з замовленнями ---
def add_order(user_id, first_name, username, phone_number, type_label, order_type, 
              topic, subject, deadline, volume, requirements, price, files=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        # Генеруємо унікальний випадковий id (5-значне число)
        while True:
            rand_id = random.randint(10000, 99999)
            c.execute('SELECT 1 FROM orders WHERE id = ?', (rand_id,))
            if not c.fetchone():
                break
        # Конвертуємо файли в JSON
        files_json = json.dumps(files or [])
        c.execute('''INSERT INTO orders 
                    (id, user_id, first_name, username, phone_number, type_label, order_type,
                     topic, subject, deadline, volume, requirements, files, price, 
                     status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)''',
                 (rand_id, user_id, first_name, username, phone_number, type_label, order_type,
                  topic, subject, deadline, volume, requirements, files_json, price, now, now))
        order_id = rand_id
        # Додаємо файли окремо
        if files:
            for file_id in files:
                c.execute('''INSERT INTO order_files (order_id, file_id, uploaded_at)
                            VALUES (?, ?, ?)''', (order_id, file_id, now))
        # Додаємо запис в історію статусів
        c.execute('''INSERT INTO order_status_history (order_id, status, changed_at)
                    VALUES (?, 'draft', ?)''', (order_id, now))
        conn.commit()
        return order_id

def update_order(order_id, **kwargs):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        # Оновлюємо основні поля
        update_fields = []
        values = []
        for key, value in kwargs.items():
            if key != 'files' and key != 'status':
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if update_fields:
            update_fields.append("updated_at = ?")
            values.append(now)
            values.append(order_id)
            
            query = f"UPDATE orders SET {', '.join(update_fields)} WHERE id = ?"
            c.execute(query, values)
        
        # Оновлюємо файли якщо потрібно
        if 'files' in kwargs:
            files = kwargs['files']
            files_json = json.dumps(files or [])
            c.execute("UPDATE orders SET files = ? WHERE id = ?", (files_json, order_id))
            
            # Видаляємо старі файли
            c.execute("DELETE FROM order_files WHERE order_id = ?", (order_id,))
            
            # Додаємо нові файли
            if files:
                for file_id in files:
                    c.execute('''INSERT INTO order_files (order_id, file_id, uploaded_at)
                                VALUES (?, ?, ?)''', (order_id, file_id, now))
        
        # Оновлюємо статус якщо потрібно
        if 'status' in kwargs:
            new_status = kwargs['status']
            c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
            c.execute('''INSERT INTO order_status_history (order_id, status, changed_at)
                        VALUES (?, ?, ?)''', (order_id, new_status, now))
        
        conn.commit()

def get_order_by_id(order_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT * FROM orders WHERE id = ?''', (order_id,))
        order = c.fetchone()
        
        if order:
            # Отримуємо файли
            c.execute('''SELECT file_id, file_name, file_type FROM order_files 
                        WHERE order_id = ?''', (order_id,))
            files = c.fetchall()
            
            # Отримуємо історію статусів
            c.execute('''SELECT status, changed_at, notes FROM order_status_history 
                        WHERE order_id = ? ORDER BY changed_at DESC''', (order_id,))
            status_history = c.fetchall()
            
            return {
                'order': order,
                'files': files,
                'status_history': status_history
            }
        return None

def get_orders(user_id=None, status=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        
        query = "SELECT * FROM orders"
        params = []
        
        if user_id:
            query += " WHERE user_id = ?"
            params.append(user_id)
            
            if status:
                query += " AND status = ?"
                params.append(status)
        elif status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        c.execute(query, params)
        return c.fetchall()

# --- Функції для промокодів ---
def add_promocode(code, discount_type, discount_value, usage_limit, 
                 expires_at=None, is_personal=False, personal_user_id=None, min_order_amount=0):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''INSERT INTO promocodes 
                    (code, discount_type, discount_value, usage_limit, created_at, 
                     expires_at, is_personal, personal_user_id, min_order_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (code, discount_type, discount_value, usage_limit, now,
                  expires_at, is_personal, personal_user_id, min_order_amount))
        conn.commit()

def get_promocode(code):
    with get_db_connection() as conn:
        c = conn.cursor()
        # Явно вказуємо всі колонки, щоб уникнути помилок з `*`
        c.execute('''SELECT 
                        code, discount_type, discount_value, usage_limit, 
                        used_count, created_at, expires_at, is_personal, 
                        personal_user_id, min_order_amount 
                     FROM promocodes WHERE code = ?''', (code,))
        return c.fetchone()

def is_promocode_valid(promocode, user_id, order_amount):
    if not promocode:
        return False, "Промокод не знайдено (повернуто None)"
    if not isinstance(promocode, (tuple, list)):
        return False, f"Промокод має неправильний тип: {type(promocode)}"
    if len(promocode) < 10:
        return False, f"Промокод має {len(promocode)} полів замість 10. Зміст: {promocode}"

    # 0:code, 1:type, 2:value, 3:limit, 4:used, 5:created, 6:expires, 7:is_personal, 8:personal_id, 9:min_amount
    
    expires_at_str = promocode[6]
    if expires_at_str and datetime.fromisoformat(expires_at_str.split('.')[0]) < datetime.now():
        return False, "Термін дії промокоду закінчився"

    usage_limit = promocode[3]
    used_count = promocode[4]
    if usage_limit is not None and used_count >= usage_limit:
        return False, "Ліміт використання промокоду вичерпано"

    is_personal = promocode[7] == 1
    personal_user_id = promocode[8]
    if is_personal and personal_user_id != user_id:
        return False, "Цей промокод призначений для іншого користувача"

    min_order_amount = promocode[9]
    if order_amount < min_order_amount:
        return False, f"Мінімальна сума замовлення для цього промокоду: {min_order_amount} грн"
        
    return True, "Промокод дійсний"

def use_promocode(code, user_id, order_id, order_amount):
    promocode = get_promocode(code)
    if not promocode:
        return 0

    # Розрахунок знижки
    discount = 0
    if promocode[1] == 'percent':
        discount = int(order_amount * promocode[2] / 100)
    elif promocode[1] == 'fixed':
        discount = int(promocode[2])

    # Оновлюємо used_count
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?', (code,))
        c.execute('INSERT INTO promocode_usages (code, user_id, order_id, discount_amount, used_at) VALUES (?, ?, ?, ?, ?)',
                  (code, user_id, order_id, discount, datetime.now().isoformat()))
        conn.commit()

    return discount

# --- Функції для реферальної системи ---
def add_referral(user_id, referred_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        # Перевіряємо чи не існує вже
        c.execute('''SELECT id FROM referrals 
                    WHERE user_id = ? AND referred_id = ?''', (user_id, referred_id))
        if not c.fetchone():
            c.execute('''INSERT INTO referrals (user_id, referred_id, created_at)
                        VALUES (?, ?, ?)''', (user_id, referred_id, now))
            conn.commit()

def get_referrals(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT referred_id, created_at FROM referrals 
                    WHERE user_id = ?''', (user_id,))
        return c.fetchall()

def add_referral_bonus(user_id, referred_user_id, order_id, bonus_amount):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''INSERT INTO referral_bonuses 
                    (user_id, referred_user_id, order_id, bonus_amount, created_at)
                    VALUES (?, ?, ?, ?, ?)''',
                 (user_id, referred_user_id, order_id, bonus_amount, now))
        conn.commit()

# --- Функції для нагадувань ---
def add_reminder(user_id, order_id, reminder_type, scheduled_at, message):
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''INSERT INTO reminders 
                    (user_id, order_id, reminder_type, scheduled_at, message)
                    VALUES (?, ?, ?, ?, ?)''',
                 (user_id, order_id, reminder_type, scheduled_at, message))
        conn.commit()

def get_pending_reminders():
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''SELECT * FROM reminders 
                    WHERE scheduled_at <= ? AND sent_at IS NULL''', (now,))
        return c.fetchall()

def mark_reminder_sent(reminder_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''UPDATE reminders SET sent_at = ? WHERE id = ?''', (now, reminder_id))
        conn.commit()

# --- Функції для спам захисту ---
def check_spam_protection(user_id, action_type, limit=5, window_minutes=5):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now()
        window_start = (now - timedelta(minutes=window_minutes)).isoformat()
        
        # Видаляємо старі записи
        c.execute('''DELETE FROM spam_protection 
                    WHERE created_at < ?''', (window_start,))
        
        # Перевіряємо кількість дій
        c.execute('''SELECT COUNT(*) FROM spam_protection 
                    WHERE user_id = ? AND action_type = ? AND created_at >= ?''',
                 (user_id, action_type, window_start))
        
        count = c.fetchone()[0]
        
        if count >= limit:
            return False
        
        # Додаємо нову дію
        c.execute('''INSERT INTO spam_protection (user_id, action_type, created_at)
                    VALUES (?, ?, ?)''', (user_id, action_type, now.isoformat()))
        
        conn.commit()
        return True

# --- Функції для бекапів ---
def create_backup():
    import shutil
    import os
    
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/backup_{timestamp}.sqlite3"
    
    shutil.copy2(DB_PATH, backup_file)
    
    # Записуємо інформацію про бекап
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO backups (backup_file, created_at, size_bytes)
                    VALUES (?, ?, ?)''',
                 (backup_file, datetime.now().isoformat(), os.path.getsize(backup_file)))
        conn.commit()
    
    return backup_file

# --- Інші функції ---
def update_order_status(order_id, status, manager_id=None, notes=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''UPDATE orders SET status = ? WHERE id = ?''', (status, order_id))
        c.execute('''INSERT INTO order_status_history 
                    (order_id, status, changed_by, changed_at, notes)
                    VALUES (?, ?, ?, ?, ?)''',
                 (order_id, status, manager_id, now, notes))
        conn.commit()

def find_orders(query):
    with get_db_connection() as conn:
        c = conn.cursor()
        search_term = f"%{query}%"
        c.execute('''SELECT * FROM orders 
                    WHERE topic LIKE ? OR subject LIKE ? OR requirements LIKE ?
                    ORDER BY created_at DESC''', (search_term, search_term, search_term))
        return c.fetchall()

def get_order_by_num(order_num):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT * FROM orders WHERE id = ?''', (order_num,))
        return c.fetchone()

def get_promocode_usages(code):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT * FROM promocode_usages WHERE code = ?''', (code,))
        return c.fetchall() 

# --- Функції для роботи з відгуками ---
def add_feedback(feedback: dict):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO feedbacks (user_id, username, text, stars, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))''',
                 (feedback.get('user_id'), feedback.get('username'), feedback.get('text'), feedback.get('stars')))
        conn.commit()
        return c.lastrowid

def get_feedbacks():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM feedbacks ORDER BY created_at DESC')
        return c.fetchall()

# --- Функції для роботи з support_logs ---
def add_support_log(log: dict):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO support_logs (user_id, admin_id, message, direction, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))''',
                 (log.get('user_id'), log.get('admin_id'), log.get('message'), log.get('direction')))
        conn.commit()
        return c.lastrowid

def get_support_logs(user_id=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        query = "SELECT * FROM support_logs"
        params = []
        
        if user_id:
            query += " WHERE user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY created_at DESC"
        c.execute(query, params)
        return c.fetchall()

# --- Функції для роботи з промокодами (старі версії для сумісності) ---
def add_promocode_old(code, discount_type, discount_value, usage_limit):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO promocodes (code, discount_type, discount_value, usage_limit, created_at) VALUES (?, ?, ?, ?, datetime("now"))', (code, discount_type, discount_value, usage_limit))
        conn.commit()

def use_promocode_old(user_id, code):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO promocode_usages (user_id, code, used_at) VALUES (?, ?, datetime("now"))', (user_id, code))
        c.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE code=?', (code,))
        conn.commit()

# --- Функції для роботи з замовленнями (старі версії для сумісності) ---
def add_order_old(order: dict):
    with get_db_connection() as conn:
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

def update_order_status_old(order_id, new_status):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('UPDATE orders SET status=? WHERE id=?', (new_status, order_id))
        conn.commit()
        # Check if the update was successful
        return c.rowcount > 0

def get_order_by_num_old(num):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY id ASC')
        orders = c.fetchall()
        if num < 1 or num > len(orders):
            return None
        return orders[num - 1]

def find_orders_old(query):
    with get_db_connection() as conn:
        c = conn.cursor()
        search_term = f"%{query}%"
        c.execute('''SELECT * FROM orders 
                    WHERE topic LIKE ? OR subject LIKE ? OR requirements LIKE ?
                    ORDER BY created_at DESC''', (search_term, search_term, search_term))
        return c.fetchall()

def log_message(user_id, username, direction, text, chat_id=None, message_type='text'):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO messages (user_id, username, direction, text, chat_id, message_type, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''',
                  (user_id, username, direction, text, chat_id, message_type))
        conn.commit()


# --- Викликати при старті бота ---
if __name__ == '__main__':
    init_db() 