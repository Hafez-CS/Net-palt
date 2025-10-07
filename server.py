import socket
import threading
import json
import os
import models
# =========================
# Utility functions for JSON protocol
# =========================
def send_control(sock, data: dict):
    """Send a JSON control message with fixed header length"""
    j = json.dumps(data).encode('utf-8')
    header = f"{len(j):010d}".encode('utf-8')
    sock.sendall(header + j)

def recv_all(sock, n):
    """Receive exactly n bytes"""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf.extend(chunk)
    return bytes(buf)

def recv_control(sock):
    """Receive a JSON control message"""
    header = recv_all(sock, 10)
    length = int(header.decode('utf-8'))
    j = recv_all(sock, length)
    return json.loads(j.decode('utf-8'))


# =========================
# Chat Server
# =========================
class ChatServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.clients = {}  # تغییر: username -> sock
        self.lock = threading.Lock()
        self.files_dir = "server_files"
        os.makedirs(self.files_dir, exist_ok=True)
        self.running = False

        models.init_db()
    def start(self):
        print(f"[SERVER] Starting on {self.host}:{self.port}")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)

        self.running = True
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
            except OSError:
                break
            print(f"[SERVER] New connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def broadcast(self, data, exclude=None):
        """Send control message to all clients"""
        with self.lock:
            for client_sock in list(self.clients.values()):
                if client_sock == exclude:
                    continue
                try:
                    send_control(client_sock, data)
                except:
                    for username, sock in list(self.clients.items()):
                        if sock == client_sock:
                            self.remove_client(sock)
                            break

    def remove_client(self, sock):
        """Helper to remove client safely without recursion issues"""
        with self.lock:
            username = None
            for u, s in self.clients.items():
                if s == sock:
                    username = u
                    break
            
            if username:
                del self.clients[username]
        if username:
            self.broadcast({"type": "USER_LEFT", "username": username})
            print(f"[SERVER] {username} disconnected")
        try:
            sock.close()
        except:
            pass

    def disconnect(self, sock):
        """Wrapper for compatibility"""
        self.remove_client(sock)

    # =========================
    # متدهای اضافه برای GUI و مدیریت
    # =========================
    def start_background(self):
        """Run server in background thread"""
        t = threading.Thread(target=self.start, daemon=True)
        t.start()

    def list_clients(self):
        """Return list of connected clients info"""
        with self.lock:
            result = []
            for username, sock in self.clients.items():
                try:
                    addr = sock.getpeername()
                except:
                    addr = "?"
                result.append({
                    "username": username,
                    "addr": addr
                })
            return result
    
    def kick_by_username(self, username: str):

        sock = None
        # فقط پیدا کردن کلاینت بدون lock
        with self.lock:
            sock = self.clients.get(username)

        if sock:
            try:
                sock.close()
            except Exception:
                pass
            # حذف از لیست با remove_client (خودش lock می‌گیره)
            self.remove_client(sock)
            print(f"[SERVER] Kicked user {username}")

    def add_user(self, username, password, role="user"):
        models.add_user_db(username,password,role)

    def broadcast_admin(self, text):
        """Broadcast admin message to all clients"""
        self.broadcast({"type": "MSG", "username": "[ADMIN]", "text": text})

    def safe_shutdown(self):
        """Shutdown server gracefully"""
        self.running = False
        with self.lock:
            for sock in list(self.clients.values()):
                self.remove_client(sock)
        print("[SERVER] Shutdown complete")

    # =========================
    # فایل‌ها و پیام‌های کلاینت
    # =========================
    def send_file_list(self, sock):
        """Send the list of available files to one client"""
        files = []
        for f in os.listdir(self.files_dir):
            path = os.path.join(self.files_dir, f)
            if os.path.isfile(path):
                size = os.path.getsize(path)
                files.append({"filename": f, "filesize": size})
        send_control(sock, {"type": "FILE_LIST", "files": files})

    def handle_client(self, sock):
        try:
            hello = recv_control(sock)
            if hello["type"] != "HELLO":
                send_control(sock, {"type": "ERROR", "message": "Must start with HELLO"})
                sock.close()
                return

            username = hello.get("username", "Guest")
            with self.lock:
                if username in self.clients:
                    send_control(sock, {"type": "ERROR", "message": "Username already taken"})
                    sock.close()
                    return
                self.clients[username] = sock

            self.broadcast({"type": "USER_JOIN", "username": username}, exclude=sock)
            self.send_file_list(sock)
            print(f"[SERVER] {username} joined")

            while True:
                msg = recv_control(sock)

                if msg["type"] == "MSG":
                    self.broadcast({"type": "MSG", "username": username, "text": msg["text"]})

                elif msg["type"] == "FILE_META":
                    filename = msg["filename"]
                    filesize = int(msg["filesize"])
                    path = os.path.join(self.files_dir, filename)

                    with open(path, "wb") as f:
                        remaining = filesize
                        while remaining > 0:
                            chunk = sock.recv(min(4096, remaining))
                            if not chunk:
                                break
                            f.write(chunk)
                            remaining -= len(chunk)

                    print(f"[SERVER] {username} uploaded {filename} ({filesize} bytes)")

                    self.broadcast({"type": "FILE_NOTICE", "username": username, "filename": filename})
                    self.broadcast({"type": "FILE_LIST", "files": [
                        {"filename": f, "filesize": os.path.getsize(os.path.join(self.files_dir, f))}
                        for f in os.listdir(self.files_dir)
                        if os.path.isfile(os.path.join(self.files_dir, f))
                    ]})

                elif msg["type"] == "GET_FILE":
                    filename = msg["filename"]
                    path = os.path.join(self.files_dir, filename)
                    if not os.path.exists(path):
                        send_control(sock, {"type": "ERROR", "message": "File not found"})
                        continue

                    filesize = os.path.getsize(path)
                    send_control(sock, {"type": "FILE_SEND", "filename": filename, "filesize": filesize})

                    with open(path, "rb") as f:
                        while chunk := f.read(4096):
                            sock.sendall(chunk)

                    print(f"[SERVER] Sent {filename} to {username}")

                elif msg["type"] == "QUIT":
                    self.remove_client(sock)
                    break
        except Exception as e:
            print("[SERVER] Error:", e)
        finally:
            self.remove_client(sock)


# =========================
# Run Server
# =========================
if __name__ == "__main__":
    srv = ChatServer(host="0.0.0.0", port=5000)
    srv.start_background()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        srv.safe_shutdown()