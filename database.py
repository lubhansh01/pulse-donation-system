import sqlite3

DB_PATH = "data/database.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE,
        name TEXT,
        phone TEXT UNIQUE,
        village TEXT,
        age INTEGER
    )
    """)

    # DONATIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        cause TEXT,
        operator TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # EXPENSES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        description TEXT,
        date DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # OPERATORS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        age INTEGER,
        email TEXT,
        password TEXT,
        is_active INTEGER DEFAULT 1
    )
   """)

    conn.commit()
    conn.close()