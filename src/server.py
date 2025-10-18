# server.py
import socket
import threading
import json
import os
import models 
import time

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
        self.clients = {}  # {username: sock}
        self.lock = threading.Lock()
        self.files_dir = "server_files"
        os.makedirs(self.files_dir, exist_ok=True)
        self.running = False
        self.server_socket = None
        self.server_thread = None

        #setuping the database!
        models.init_db()


        self.available_files = self._get_file_list_from_dir() 

    def _get_file_list_from_dir(self):
        files = []
        for filename in os.listdir(self.files_dir):
            filepath = os.path.join(self.files_dir, filename)
            if os.path.isfile(filepath):
                files.append({"filename": filename, "filesize": os.path.getsize(filepath)})
        return files
    
    #users that are online!
    def get_all_users_with_status(self):
        all_db_users = models.get_all_users_db() 
        users_with_status = []
        
        with self.lock:
            online_set = set(self.clients.keys()) 
            
            for username in all_db_users:
                is_online = username in online_set
                users_with_status.append({"username": username, "is_online": is_online})
        
        return users_with_status

    # server.py (تابع kick_by_username)

    def kick_by_username(self, username_to_kick):
        with self.lock:
            client_socket = self.clients.get(username_to_kick)
            
            if client_socket:
                kicked_successfully = False
                try:
                    # 1. ارسال پیام کیک
                    send_control(client_socket, {"type": "KICKED", "message": "You have been kicked by the admin."})
                    
                    # 2. قطع سوکت و بستن آن
                    time.sleep(0.1) # یک مکث کوتاه برای اطمینان از ارسال پیام
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
                    kicked_successfully = True

                except Exception as e:
                    # اگر در فرآیند ارسال پیام یا بستن سوکت خطا رخ دهد
                    print(f"[SERVER ERROR] Error during socket closure for {username_to_kick}: {e}")
                    
                finally:
                    # 3. حذف از لیست سرور (مهمترین قسمت برای رفع فریز)
                    if username_to_kick in self.clients:
                        del self.clients[username_to_kick]
                        self.broadcast_message(f"[{username_to_kick} was kicked by admin]", "SERVER")
                        print(f"[SERVER] Removed client {username_to_kick} from list.")
                        return True
        return False
        
    def send_private(self, msg, recipient):
        #check if the user is online
        users_with_status = self.get_all_users_with_status()
        for user in users_with_status:
            if user["username"] == recipient:
                if user["is_online"]:
                    print(f"{msg} --> {recipient}")
                    return
        print(f"the user {recipient} is offline!")  


    def broadcast_admin(self, message):
        self.broadcast_message(message, "ADMIN")

    def broadcast_message(self, message, sender):
        """ارسال پیام به تمام کلاینت‌های متصل، شامل ادمین."""
        msg = {"type": "MSG", "username": sender, "text": message}
        j = json.dumps(msg).encode('utf-8')
        header = f"{len(j):010d}".encode('utf-8')
        
        with self.lock:
            for username, client_socket in list(self.clients.items()): 
                # --- [تغییر کلیدی: شرط حذف شد تا ادمین هم پیام‌ها را ببیند] ---
                try:
                    client_socket.sendall(header + j)
                except:
                    self.remove_client(username, client_socket)
                        
    def broadcast_file_list(self):
        self.available_files = self._get_file_list_from_dir()
        file_msg = {"type": "FILE_LIST", "files": self.available_files}
        
        with self.lock:
            for username, client_socket in list(self.clients.items()):
                try:
                    send_control(client_socket, file_msg)
                except:
                    self.remove_client(username, client_socket)

    def handle_client(self, client_socket, address):
        username = None
        try:
            hello_msg = recv_control(client_socket)
            if hello_msg["type"] != "HELLO":
                return
            
            username = hello_msg["username"]
            print(f"hello {username}")
            
            with self.lock:
                if username in self.clients:
                    send_control(client_socket, {"type": "ERROR", "message": "Username already taken or connected."})
                    return
                self.clients[username] = client_socket

            if username != "admin": 
                # self.broadcast_message(f"{username} joined", "SERVER")
                send_control(client_socket, {"type": "FILE_LIST", "files": self.available_files}) 
            
            while True:
                msg = recv_control(client_socket)
                
                if msg["type"] == "PMSG":
                    print(msg["text"])
                    self.send_private(msg["text"], msg["recipient"])
                    
                if msg["type"] == "MSG":
                    # اگر ادمین پیام فرستاده، نیاز به برودکست نیست، فقط برای نمایش در پنل ادمین
                    # if username == "admin": 
                    #     continue
                    self.broadcast_message(msg["text"], username)
                
                elif msg["type"] == "FILE_META":
                    # ... (File Meta logic remains the same)
                    filename = msg["filename"]
                    filesize = int(msg["filesize"])
                    filepath = os.path.join(self.files_dir, filename)
                    
                    file_data = recv_all(client_socket, filesize)
                    with open(filepath, "wb") as f:
                        f.write(file_data)
                    
                    self.broadcast_message(f"{username} uploaded file: {filename}", "SERVER")
                    self.broadcast_file_list() 
                    
                elif msg["type"] == "GET_FILE":
                    # ... (Get File logic remains the same)
                    filename = msg["filename"]
                    filepath = os.path.join(self.files_dir, filename)
                    
                    if os.path.exists(filepath):
                        filesize = os.path.getsize(filepath)
                        send_control(client_socket, {"type": "FILE_SEND", "filename": filename, "filesize": filesize})
                        with open(filepath, "rb") as f:
                            while chunk := f.read(4096):
                                client_socket.sendall(chunk)
                    else:
                        send_control(client_socket, {"type": "ERROR", "message": f"File {filename} not found on server."})

                elif msg["type"] == "QUIT":
                    break
        
        except ConnectionError:
            pass 
        except Exception as e:
            print(f"[SERVER ERROR] Error handling client {username}: {e}")
            
        finally:
            if username:
                self.remove_client(username, client_socket)

    def remove_client(self, username, client_socket):
        """Removes a client connection safely."""
        with self.lock:
            if username in self.clients and self.clients[username] == client_socket:
                del self.clients[username]
                if username != "admin":
                    self.broadcast_message(f"{username} left", "SERVER")
                try:
                    client_socket.close()
                except:
                    pass

    def start(self):
        if self.running:
            print("[SERVER] Server is already running.")
            return

        print(f"[SERVER] Starting on {self.host}:{self.port}")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.running = True
        
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[SERVER ERROR] Accept failed: {e}")
                break

        print("[SERVER] Shut down.")

    def start_background(self):
        if not self.running:
            self.server_thread = threading.Thread(target=self.start, daemon=True)
            self.server_thread.start()
            print("[SERVER] Server started in background thread.")

    def safe_shutdown(self):
        if not self.running:
            return

        print("[SERVER] Initiating safe shutdown...")
        self.running = False
        
        with self.lock:
            for username, client_socket in list(self.clients.items()):
                try:
                    send_control(client_socket, {"type": "SERVER_CLOSE", "message": "Server is shutting down."})
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
                except:
                    pass
            self.clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

if __name__ == "__main__":
    server = ChatServer()
    server.start()