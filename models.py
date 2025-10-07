import sqlite3

DB_FILE = "chat_app.db"


def init_db():
    # 1. Connect to the database
    conn = sqlite3.connect(DB_FILE)
    
    # 2. Enable foreign key constraint checking (essential for them to work in SQLite)
    conn.execute("PRAGMA foreign_keys = ON;") 
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
    
    # 8. Commit and Close
    conn.commit()
    conn.close()
    print("Database initialized with all tables and Foreign Keys.")
# Example usage (optional, for testing):

def add_user_db(username: str, password_hash: str, role: str = "user"):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                    (username, password_hash, role))
        conn.commit()
        print(f"User '{username}' added successfully.")
    except sqlite3.IntegrityError as e:
        print(f"Error adding user '{username}':", e)
    finally:
        conn.close()

        
if __name__ == '__main__':

        
    init_db()
    print(f"Database '{DB_FILE}' initialized successfully with all tables and Foreign Keys.")
    
    # Quick check of tables created
    conn = sqlite3.connect(DB_FILE)
    table_list = conn.execute("SELECT name,* FROM sqlite_master WHERE type='table';").fetchall()
    print("Tables created:", [t[0] for t in table_list])
    conn.close()