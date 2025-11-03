# models.py
import sqlite3
import bcrypt
import os
import time

current_dir = os.getcwd()

# Join the CWD with the file name
DB_FILE = os.path.join(current_dir, 'chat_app.db')

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

        # --- 8 messages
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_user_id INTEGER NOT NULL,
                recipient_user_id INTEGER, -- NULL for public/broadcast messages
                text TEXT NOT NULL,
                sent_at INTEGER NOT NULL,
                is_group_message BOOLEAN NOT NULL DEFAULT 0,
                
                FOREIGN KEY (sender_user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_user_id) REFERENCES users (user_id) ON DELETE SET NULL
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


def get_user_id_by_username(username, conn=None):
    """Fetches user ID by username."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"[DB ERROR] Fetch user ID failed: {e}")
        return None
    finally:
        if close_conn:
            conn.close()


def add_message_db(sender_username, recipient_username, text, is_group=False, conn=None):
    """Logs a new message (public or private) to the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        
        # Get user IDs
        sender_id = get_user_id_by_username(sender_username, conn)
        recipient_id = get_user_id_by_username(recipient_username, conn) if recipient_username else None
        
        if sender_id is None:
            print(f"[DB ERROR] Sender '{sender_username}' not found.")
            return False

        # If it's a private message, ensure recipient is valid (unless public)
        if recipient_username and recipient_id is None:
             print(f"[DB ERROR] Recipient '{recipient_username}' not found.")
             return False

        current_time = int(time.time()) # time.time() is used for INTEGER timestamps
        
        cur.execute("""
            INSERT INTO messages (sender_user_id, recipient_user_id, text, sent_at, is_group_message)
            VALUES (?, ?, ?, ?, ?)
        """, (sender_id, recipient_id, text, current_time, 1 if is_group else 0))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] Add message failed: {e}")
        return False
    finally:
        if close_conn:
            conn.close()

# models.py (Add this function)

def get_historical_messages_db(user1_username, user2_username, conn=None):
    """
    Fetches all private messages exchanged between two specific users, 
    ordered by time.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    try:
        cur = conn.cursor()
        
        # Get user IDs for the two usernames
        user1_id = get_user_id_by_username(user1_username, conn)
        user2_id = get_user_id_by_username(user2_username, conn)
        
        if user1_id is None or user2_id is None:
            print("[DB ERROR] One or both users not found for message history.")
            return []

        # SQL query to select messages where:
        # 1. Sender is user1 AND Recipient is user2
        # OR
        # 2. Sender is user2 AND Recipient is user1
        # The result is ordered by sent_at time.
        cur.execute(f"""
            SELECT T1.username AS sender, T3.username AS recipient, T2.text, T2.sent_at 
            FROM messages T2
            JOIN users T1 ON T2.sender_user_id = T1.user_id
            JOIN users T3 ON T2.recipient_user_id = T3.user_id
            WHERE (
                (T2.sender_user_id = ? AND T2.recipient_user_id = ?) OR
                (T2.sender_user_id = ? AND T2.recipient_user_id = ?)
            )
            AND T2.is_group_message = 0 
            ORDER BY T2.sent_at ASC
        """, (user1_id, user2_id, user2_id, user1_id))
        
        # Fetch results and format them
        messages = []
        for row in cur.fetchall():
            messages.append({
                "sender": row[0],
                "recipient": row[1],
                "text": row[2],
                "sent_at": row[3] # Unix timestamp
            })
            
        return messages
    
    except Exception as e:
        print(f"[DB ERROR] Fetch historical messages failed: {e}")
        return []
    finally:
        if close_conn:
            conn.close()

def add_group_db(group_name, conn=None):
    """Adds a new group to the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO groups (name) VALUES (?)", (group_name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"[DB ERROR] Group '{group_name}' already exists.")
        return None
    except Exception as e:
        print(f"[DB ERROR] Add group failed: {e}")
        return False
    finally:
        if close_conn:
            conn.close()

def get_all_groups_db(conn=None):
    """Fetches the names of all groups from the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        # فقط نام گروه‌ها را انتخاب می‌کنیم
        cur.execute("SELECT name FROM groups") 
        # نتایج را به صورت یک لیست از رشته‌ها برمی‌گردانیم
        return [row[0] for row in cur.fetchall()] 
    except Exception as e:
        print(f"[DB ERROR] Fetch all groups failed: {e}")
        return []
    finally:
        if close_conn:
            conn.close()

def get_group_id_by_name(group_name, conn=None):
    """Fetches group ID by group name."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT group_id FROM groups WHERE name = ?", (group_name,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"[DB ERROR] Fetch group ID failed: {e}")
        return None
    finally:
        if close_conn:
            conn.close()

            
def add_user_to_group_db(username, group_name, conn=None):
    """Adds a user to a specific group."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        
        # 1. Get IDs
        user_id = get_user_id_by_username(username, conn)
        group_id = get_group_id_by_name(group_name, conn)
        
        if user_id is None:
            print(f"[DB ERROR] User '{username}' not found.")
            return False
        if group_id is None:
            print(f"[DB ERROR] Group '{group_name}' not found.")
            return False
            
        # 2. Add to junction table
        cur.execute("""
            INSERT INTO group_members (group_id, user_id) 
            VALUES (?, ?)
        """, (group_id, user_id))
        
        conn.commit()
        print(f"[DB] User '{username}' added to group '{group_name}'.")
        return True
    except sqlite3.IntegrityError:
        print(f"[DB ERROR] User '{username}' is already a member of group '{group_name}'.")
        return False
    except Exception as e:
        print(f"[DB ERROR] Add user to group failed: {e}")
        return False
    finally:
        if close_conn:
            conn.close()

def remove_user_from_group_db(username, group_name, conn=None):
    """Removes a user from a specific group."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cur = conn.cursor()
        
        # 1. Get IDs (از توابعی که قبلاً تعریف شدند استفاده می‌کنیم)
        user_id = get_user_id_by_username(username, conn)
        group_id = get_group_id_by_name(group_name, conn)
        
        if user_id is None:
            print(f"[DB ERROR] User '{username}' not found.")
            return False
        if group_id is None:
            print(f"[DB ERROR] Group '{group_name}' not found.")
            return False
            
        # 2. Delete from junction table
        cur.execute("""
            DELETE FROM group_members 
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        
        row_count = cur.rowcount
        conn.commit()
        
        if row_count > 0:
            print(f"[DB] User '{username}' removed from group '{group_name}'.")
            return True
        else:
            print(f"[DB] User '{username}' was not a member of group '{group_name}' or already removed.")
            return False
            
    except Exception as e:
        print(f"[DB ERROR] Remove user from group failed: {e}")
        return False
    finally:
        if close_conn:
            conn.close()

def get_group_members_db(group_name, conn=None):
    """
    Fetches the usernames of all members in a specific group 
    by joining the 'users', 'groups', and 'group_members' tables.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    try:
        cur = conn.cursor()
        
        # SQL query to join the three tables and filter by group name
        cur.execute("""
            SELECT T1.username 
            FROM users T1
            JOIN group_members T2 ON T1.user_id = T2.user_id
            JOIN groups T3 ON T2.group_id = T3.group_id
            WHERE T3.name = ?
            ORDER BY T1.username ASC
        """, (group_name,))
        
        # Fetch results and return them as a list of usernames
        members = [row[0] for row in cur.fetchall()]
        
        if not members:
            # بررسی می‌کنیم که آیا اصلاً گروهی با این نام وجود دارد یا خیر
            if get_group_id_by_name(group_name, conn) is None:
                print(f"[DB INFO] Group '{group_name}' not found.")
            else:
                print(f"[DB INFO] Group '{group_name}' found, but has no members.")
        
        return members
    
    except Exception as e:
        print(f"[DB ERROR] Fetch group members failed: {e}")
        return []
    finally:
        if close_conn:
            conn.close()