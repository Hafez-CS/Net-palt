# models.py
import sqlite3
import bcrypt
import os

DB_FILE = "chat_app.db"
ADMIN_USERNAME = "admin"
# پسورد پیش‌فرض ادمین را اینجا تعیین کنید
ADMIN_PASSWORD = "admin_password" 

def hash_password(password):
    """Generates a secure hash for a given password."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')

def check_password_hash(password, password_hash):
    """Checks a plain password against a stored hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def get_db_connection():
    """Returns a new database connection."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Initializes the database and creates the users table if it doesn't exist."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL 
            )
        ''')
        
        # Add initial admin user if not exists
        if not get_user_by_username(ADMIN_USERNAME, conn):
            admin_hash = hash_password(ADMIN_PASSWORD)
            add_user_db(ADMIN_USERNAME, admin_hash, "admin", conn)
            print(f"[DB] Default admin user '{ADMIN_USERNAME}' created with password '{ADMIN_PASSWORD}'.")
            
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] Initialization failed: {e}")
    finally:
        if conn:
            conn.close()


def add_user_db(username, password_hash, role, conn=None):
    """Adds a new user to the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                    (username, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"[DB ERROR] User {username} already exists.")
        return False
    except Exception as e:
        print(f"[DB ERROR] Add user failed: {e}")
        return False
    finally:
        if close_conn:
            conn.close()

def get_user_by_username(username, conn=None):
    """Fetches user data by username: (username, password_hash, role)"""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT username, password_hash, role FROM users WHERE username = ?", (username,))
        return cur.fetchone()
    except Exception as e:
        print(f"[DB ERROR] Fetch user failed: {e}")
        return None
    finally:
        if close_conn:
            conn.close()

def get_all_users_db(conn=None):
    """Fetches all usernames from the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users") 
        return [row[0] for row in cur.fetchall()] 
    except Exception as e:
        print(f"[DB ERROR] Fetch all users failed: {e}")
        return []
    finally:
        if close_conn:
            conn.close()

def remove_user_db(username, conn=None):
    """Removes a user from the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return cur.rowcount > 0 
    except Exception as e:
        print(f"[DB ERROR] Remove user failed: {e}")
        return False
    finally:
        if close_conn:
            conn.close()