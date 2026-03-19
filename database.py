import sqlite3

DB_NAME = "pulse.db"

# ---------------- CONNECTION ----------------
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# ---------------- CREATE TABLES ----------------
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # -------- USERS TABLE --------
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

    # -------- DONATIONS TABLE --------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            cause TEXT,
            operator TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # -------- OPERATORS TABLE --------
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

    # -------- EXPENSES TABLE --------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            description TEXT,
            date DATE
        )
    """)

    conn.commit()
    conn.close()