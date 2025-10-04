# server.py
# Chat server with SQLite auth, roles, groups, tasks, files
# Dependencies: bcrypt (pip install bcrypt)

import socket, threading, json, os, sqlite3, bcrypt, time, traceback
from typing import Optional

DB_FILE = "server_data.db"
FILES_DIR = "server_files"
os.makedirs(FILES_DIR, exist_ok=True)

# -------------------------
# DB helpers
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_members (
        group_id INTEGER,
        username TEXT,
        PRIMARY KEY (group_id, username)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        to_user TEXT,
        from_user TEXT,
        title TEXT,
        body TEXT,
        created_at INTEGER
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        uploader TEXT,
        filesize INTEGER,
        saved_name TEXT,
        uploaded_at INTEGER
    )""")
    conn.commit()
    conn.close()

def add_user_db(username, password, role="user"):
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users(username, password_hash, role) VALUES(?,?,?)",
                (username, pw_hash, role))
    conn.commit(); conn.close()

def remove_user_db(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username=?", (username,))
    cur.execute("DELETE FROM group_members WHERE username=?", (username,))
    cur.execute("DELETE FROM tasks WHERE to_user=?", (username,))
    conn.commit(); conn.close()

def verify_user_db(username, password) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT password_hash, role FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    pw_hash, role = row
    if bcrypt.checkpw(password.encode('utf-8'), pw_hash.encode('utf-8')):
        return role
    return None

def list_users_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users")
    rows = cur.fetchall(); conn.close()
    return [{"username":r[0],"role":r[1]} for r in rows]

def create_group_db(name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO groups(name) VALUES(?)", (name,))
        conn.commit()
    except:
        pass
    conn.close()

def list_groups_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM groups")
    rows = cur.fetchall(); conn.close()
    return [{"id":r[0],"name":r[1]} for r in rows]

def add_user_to_group_db(group_id, username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO group_members(group_id, username) VALUES(?,?)", (group_id, username))
        conn.commit()
    except:
        pass
    conn.close()

def get_group_members_db(group_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT username FROM group_members WHERE group_id=?", (group_id,))
    rows = cur.fetchall(); conn.close()
    return [r[0] for r in rows]

def add_task_db(to_user, from_user, title, body):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks(to_user, from_user, title, body, created_at) VALUES(?,?,?,?,?)",
                (to_user, from_user, title, body, int(time.time())))
    conn.commit(); conn.close()

def list_tasks_for_user(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id,from_user,title,body,created_at FROM tasks WHERE to_user=? ORDER BY created_at DESC", (username,))
    rows = cur.fetchall(); conn.close()
    return [{"id":r[0],"from":r[1],"title":r[2],"body":r[3],"created_at":r[4]} for r in rows]

def add_file_db(filename, uploader, filesize, saved_name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO files(filename,uploader,filesize,saved_name,uploaded_at) VALUES(?,?,?,?,?)",
                (filename, uploader, filesize, saved_name, int(time.time())))
    conn.commit(); conn.close()

def list_files_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT filename,filesize,uploader,saved_name FROM files ORDER BY uploaded_at DESC")
    rows = cur.fetchall(); conn.close()
    return [{"filename":r[0],"filesize":r[1],"uploader":r[2],"saved_name":r[3]} for r in rows]

# -------------------------
# Networking helpers (same protocol)
# -------------------------
def send_control(sock, data: dict):
    j = json.dumps(data).encode('utf-8')
    header = f"{len(j):010d}".encode('utf-8')
    sock.sendall(header + j)

def recv_all(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf.extend(chunk)
    return bytes(buf)

def recv_control(sock):
    header = recv_all(sock, 10)
    length = int(header.decode('utf-8'))
    j = recv_all(sock, length)
    return json.loads(j.decode('utf-8'))

# -------------------------
# ChatServer
# -------------------------
class ChatServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host; self.port = port
        self.clients = {}    # username -> sock
        self.lock = threading.Lock()
        self.running = False
        init_db()

    def start_background(self):
        t = threading.Thread(target=self.start, daemon=True)
        t.start()

    def start(self):
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(50)
        self.running = True
        try:
            while self.running:
                client_sock, addr = srv.accept()
                print("[SERVER] Connection from", addr)
                threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True).start()
        except Exception as e:
            print("[SERVER] Main loop error:", e)
        finally:
            srv.close()

    def broadcast(self, data, exclude=None):
        dead = []
        with self.lock:
            for user, sock in list(self.clients.items()):
                if sock == exclude: continue
                try:
                    send_control(sock, data)
                except:
                    dead.append(user)
        for u in dead:
            with self.lock:
                sock = self.clients.get(u)
                if sock:
                    self.remove_client(sock)

    def remove_client(self, sock):
        username = None
        with self.lock:
            for u,s in list(self.clients.items()):
                if s == sock:
                    username = u; break
            if username:
                del self.clients[username]
        if username:
            self.broadcast({"type":"USER_LEFT","username":username})
            print(f"[SERVER] {username} disconnected")
        try:
            sock.close()
        except:
            pass

    # -------------------------
    # Admin operations (DB-backed)
    # -------------------------
    def add_user(self, username, password, role="user"):
        add_user_db(username,password,role)

    def remove_user(self, username):
        remove_user_db(username)
        # also if connected, kick
        with self.lock:
            sock = self.clients.get(username)
        if sock:
            try: sock.close()
            except: pass
            self.remove_client(sock)

    def list_clients(self):
        with self.lock:
            res = []
            for username, sock in self.clients.items():
                try: addr = sock.getpeername()
                except: addr = ("?","?")
                res.append({"username":username,"addr":addr})
            return res

    def kick_by_username(self, username: str):
        sock = None
        with self.lock:
            sock = self.clients.get(username)
        if sock:
            try: send_control(sock, {"type":"ERROR","message":"You were kicked by admin"}); sock.close()
            except: pass
            self.remove_client(sock)
            print(f"[SERVER] Kicked {username}")

    def create_group(self, name):
        create_group_db(name)

    def list_groups(self):
        return list_groups_db()

    def add_user_to_group(self, group_id, username):
        add_user_to_group_db(group_id, username)

    def send_task(self, to_user, from_user, title, body):
        add_task_db(to_user, from_user, title, body)
        # if user online, push a notification
        with self.lock:
            sock = self.clients.get(to_user)
        if sock:
            try:
                send_control(sock, {"type":"TASK_NOTICE","from":from_user,"title":title,"body":body})
            except:
                pass

    def list_files(self):
        return list_files_db()

    # -------------------------
    # handle client
    # -------------------------
    def send_file_list(self, sock):
        files = list_files_db()
        send_control(sock, {"type":"FILE_LIST","files":files})

    def handle_client(self, sock):
        username = None
        try:
            hello = recv_control(sock)
            if hello.get("type") != "HELLO":
                send_control(sock, {"type":"ERROR","message":"Must send HELLO first"})
                sock.close(); return

            uname = hello.get("username")
            password = hello.get("password","")
            role = verify_user_db(uname, password)
            if not role:
                send_control(sock, {"type":"ERROR","message":"Invalid credentials"})
                sock.close(); return

            # accept
            username = uname
            with self.lock:
                if username in self.clients:
                    send_control(sock, {"type":"ERROR","message":"Already connected"})
                    sock.close(); return
                self.clients[username] = sock

            # send initial lists: users, groups, files, tasks
            send_control(sock, {"type":"WELCOME","username":username,"role":role})
            self.broadcast({"type":"USER_JOIN","username":username}, exclude=sock)
            self.send_file_list(sock)
            # send groups
            send_control(sock, {"type":"GROUP_LIST","groups":list_groups_db()})
            # send tasks for user
            tasks = list_tasks_for_user(username)
            send_control(sock, {"type":"TASK_LIST","tasks":tasks})

            print(f"[SERVER] {username} connected with role {role}")

            # main loop
            while True:
                msg = recv_control(sock)
                t = msg.get("type")
                if t == "MSG":
                    text = msg.get("text","")
                    self.broadcast({"type":"MSG","username":username,"text":text})
                elif t == "PRIVATE":
                    to = msg.get("to")
                    text = msg.get("text","")
                    with self.lock:
                        s = self.clients.get(to)
                    if s:
                        send_control(s, {"type":"PRIVATE","from":username,"text":text})
                elif t == "FILE_META":
                    filename = msg.get("filename")
                    filesize = int(msg.get("filesize",0))
                    # save with unique name to avoid conflicts
                    saved = f"{int(time.time())}_{username}_{filename}"
                    path = os.path.join(FILES_DIR, saved)
                    with open(path, "wb") as f:
                        remaining = filesize
                        while remaining>0:
                            chunk = sock.recv(min(4096, remaining))
                            if not chunk: break
                            f.write(chunk); remaining -= len(chunk)
                    add_file_db(filename, username, filesize, saved)
                    # broadcast new file list
                    self.broadcast({"type":"FILE_NOTICE","username":username,"filename":filename})
                    self.broadcast({"type":"FILE_LIST","files":list_files_db()})
                elif t == "GET_FILE":
                    filename = msg.get("filename")
                    # find saved_name from DB
                    files = list_files_db()
                    saved_name = None
                    for fi in files:
                        if fi["filename"] == filename:
                            saved_name = fi["saved_name"]; break
                    if not saved_name:
                        send_control(sock, {"type":"ERROR","message":"File not found"})
                        continue
                    path = os.path.join(FILES_DIR, saved_name)
                    if not os.path.exists(path):
                        send_control(sock, {"type":"ERROR","message":"File missing on server"})
                        continue
                    filesize = os.path.getsize(path)
                    send_control(sock, {"type":"FILE_SEND","filename":filename,"filesize":filesize})
                    with open(path,"rb") as f:
                        while chunk := f.read(4096):
                            sock.sendall(chunk)
                elif t == "GET_GROUP_MESSAGES":
                    # placeholder - groups message history not stored in DB in this first iteration
                    send_control(sock, {"type":"ERROR","message":"Group history not implemented yet"})
                elif t == "JOIN_GROUP":
                    gid = msg.get("group_id")
                    add_user_to_group_db(gid, username)
                elif t == "TASK_ADD":
                    to = msg.get("to"); title = msg.get("title"); body = msg.get("body")
                    self.send_task(to, username, title, body)
                elif t == "QUIT":
                    self.remove_client(sock); break
        except Exception as e:
            print("[SERVER] Error in client handler:", e)
            traceback.print_exc()
        finally:
            if username:
                self.remove_client(sock)

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # create a default admin if none
    init_db()
    users = list_users_db()
    if not any(u["username"]=="admin" for u in users):
        print("[SERVER] creating default admin/admin")
        add_user_db("admin","admin","admin")

    srv = ChatServer(host="0.0.0.0", port=5000)
    srv.start_background()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("shutting down")
