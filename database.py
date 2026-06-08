import sqlite3
from datetime import datetime, date, timedelta

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_premium BOOLEAN DEFAULT 0,
                premium_until DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                response_text TEXT,
                provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                date DATE,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        self.conn.commit()
        def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def set_premium(self, user_id, days=30):
        premium_until = date.today() + timedelta(days=days)
        self.cursor.execute('''
            UPDATE users SET is_premium = 1, premium_until = ?
            WHERE user_id = ?
        ''', (premium_until, user_id))
        self.conn.commit()
    
    def is_premium(self, user_id):
        user = self.get_user(user_id)
        if user and user[3]:
            return True
        return False
    
    def get_daily_usage(self, user_id):
        today = date.today()
        self.cursor.execute('''
            SELECT message_count FROM daily_usage
            WHERE user_id = ? AND date = ?
        ''', (user_id, today))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def increment_usage(self, user_id):
        today = date.today()
        self.cursor.execute('''
            INSERT INTO daily_usage (user_id, date, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT (user_id, date)
            DO UPDATE SET message_count = daily_usage.message_count + 1
        ''', (user_id, today))
        self.conn.commit()
    
    def can_send_message(self, user_id, daily_limit=10):
        if self.is_premium(user_id):
            return True
        usage = self.get_daily_usage(user_id)
        return usage < daily_limit
    
    def get_remaining_messages(self, user_id, daily_limit=10):
        if self.is_premium(user_id):
            return float('inf')
        usage = self.get_daily_usage(user_id)
        return max(0, daily_limit - usage)
    
    def save_message(self, user_id, message_text, response_text, provider):        self.cursor.execute('''
            INSERT INTO messages (user_id, message_text, response_text, provider)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message_text, response_text, provider))
        self.conn.commit()
    
    def get_total_users(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]

db = Database()
