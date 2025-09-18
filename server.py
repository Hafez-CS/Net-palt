import socket
import threading
import json
import os

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
        self.clients = {}  # sock -> username
        self.lock = threading.Lock()
        self.files_dir = "server_files"
        os.makedirs(self.files_dir, exist_ok=True)

    def start(self):
        print(f"[SERVER] Starting on {self.host}:{self.port}")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)

        while True:
            client_socket, addr = server_socket.accept()
            print(f"[SERVER] New connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def broadcast(self, data, exclude=None):
        """Send control message to all clients"""
        with self.lock:
            for client in list(self.clients.keys()):
                if client == exclude:
                    continue
                try:
                    send_control(client, data)
                except:
                    self.disconnect(client)

    def disconnect(self, sock):
        """Remove a client cleanly"""
        with self.lock:
            username = self.clients.pop(sock, None)
        if username:
            self.broadcast({"type": "USER_LEFT", "username": username})
            print(f"[SERVER] {username} disconnected")
        try:
            sock.close()
        except:
            pass

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
                self.clients[sock] = username

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

                    # Receive file data
                    with open(path, "wb") as f:
                        remaining = filesize
                        while remaining > 0:
                            chunk = sock.recv(min(4096, remaining))
                            if not chunk:
                                break
                            f.write(chunk)
                            remaining -= len(chunk)

                    print(f"[SERVER] {username} uploaded {filename} ({filesize} bytes)")

                    # Notify all users about new file
                    self.broadcast({"type": "FILE_NOTICE", "username": username, "filename": filename})
                    # Send updated file list
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
                    self.disconnect(sock)
                    break
        except Exception as e:
            print("[SERVER] Error:", e)
        finally:
            self.disconnect(sock)


# =========================
# Run Server
# =========================
if __name__ == "__main__":
    ChatServer(host="0.0.0.0", port=5000).start()
