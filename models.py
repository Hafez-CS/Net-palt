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
        
        # --- 1. users Table ---
        # user_id INTEGER PRIMARY KEY AUTOINCREMENT is the standard
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, 
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )""")
        # --- 2. groups Table ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")

        # --- 3. group_members Table (Junction Table: Many-to-Many Users <-> Groups) ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups (group_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )""")
        
        # --- 4. files Table ---
        # Renamed uploader to uploader_user_id and ensured it's an INTEGER Foreign Key
        cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploader_user_id INTEGER NOT NULL,
            filesize INTEGER,
            saved_name TEXT UNIQUE NOT NULL,
            uploaded_at INTEGER NOT NULL,
            FOREIGN KEY (uploader_user_id) REFERENCES users (user_id) ON DELETE RESTRICT
        )""")

        # --- 5. user_files Table (Junction Table: Many-to-Many Users <-> Files) ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_files (
            file_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (file_id, user_id),
            FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )""")
        
        # --- 6. tasks Table ---
        # Renamed columns to snake_case and fixed data types to INTEGER for user IDs
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,      
            from_user_id INTEGER,                
            title TEXT NOT NULL,
            body TEXT,
            attached_file_id INTEGER,
            created_at INTEGER NOT NULL,
            
            FOREIGN KEY (owner_user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (from_user_id) REFERENCES users (user_id) ON DELETE SET NULL, 
            FOREIGN KEY (attached_file_id) REFERENCES files (file_id) ON DELETE SET NULL
        )""")

        # --- 7. user_tasks Table (Junction Table: Many-to-Many Users <-> Tasks) ---
        # This table allows a task to be assigned to multiple users or a user to be assigned multiple tasks
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (task_id, user_id),
            FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )""")
            
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