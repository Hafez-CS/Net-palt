# server_interface.py
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.window import Window
from ttkbootstrap.constants import * 
from server import ChatServer
import threading, json, socket, bcrypt
import models

REFRESH_MS = 2000

def hash_password(password):

    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')


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

def send_control(sock, data: dict):
    """Send a JSON control message with a fixed header length"""
    j = json.dumps(data).encode('utf-8')
    header = f"{len(j):010d}".encode('utf-8')
    sock.sendall(header + j)

class ServerAdminGUI(ttk.Toplevel):
    def __init__(self, server: ChatServer, host, port):
        super().__init__()
        self.server = server
        self.host = host
        self.port = port
        win_height = Window.winfo_screenheight(self)
        win_width = Window.winfo_screenwidth(self)        
        self.geometry(f"{win_width//2}x{int(win_height//1.2)}+{win_width//2 -(win_width//2)//2}+{win_height//2 - int(win_height//1.2)//2}")

        self.title("Server Admin Panel - ttkbootstrap (Superhero)")
        # حذف تنظیمات هندسی ثابت برای انعطاف‌پذیری بیشتر، یا می‌توانید آن را نگه دارید.
        # root.geometry("700x500") 

        self.selected_username = None
        self.map_display = {} # برای نگهداری نگاشت نام نمایشی به نام کاربری واقعی

        # Frame اصلی برای padding و ساختاردهی
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=YES)

        # ---------------------------------------------
        ## Connected Users
        # ---------------------------------------------
        
        ttk.Label(main_frame, text="Connected Users", bootstyle="primary").pack(anchor=tk.W, pady=(5, 0))
        
        # استفاده از ScrolledText/ScrolledFrame برای لیست کاربران در صورت نیاز به اسکرول
        # در اینجا از یک Frame و Scrollbar معمولی استفاده می‌کنیم
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=X, padx=5, pady=5)

        # Scrollbar
        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side=RIGHT, fill=Y)

        # Listbox
        self.users_list = tk.Listbox(
            list_frame, 
            height=10, 
            selectmode=tk.SINGLE,
            yscrollcommand=list_scrollbar.set,
            # تنظیمات Listbox برای مطابقت با ظاهر ttkbootstrap
            bg=self.style.colors.get('bg'), 
            fg=self.style.colors.get('fg'),
            selectbackground=self.style.colors.get('primary'),
            selectforeground=self.style.colors.get('light'),
            font=('Segoe UI', 10)
        )
        self.users_list.pack(side=LEFT, fill=BOTH, expand=YES)
        list_scrollbar.config(command=self.users_list.yview)

        # اضافه کردن رویداد به Listbox برای تشخیص انتخاب کاربر
        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)

        # دکمه‌های کاربران
        user_btn_frame = ttk.Frame(main_frame, padding=(0, 5))
        user_btn_frame.pack(fill=X)
        
        # استفاده از bootstyle برای دکمه Kick
        ttk.Button(user_btn_frame, text="Kick", command=self.start_kick_thread, bootstyle="danger").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(user_btn_frame, text="Refresh", command=self.refresh_users, bootstyle="info-outline").pack(side=tk.LEFT)
        ttk.Button(user_btn_frame, text="Add User", command=self.add_user, bootstyle="success-outline").pack(side=tk.LEFT, padx=5)
        ttk.Button(user_btn_frame, text="remove User", command=self.remove_user, bootstyle="danger-outline").pack(side=tk.LEFT, padx=(0,5))

        # ---------------------------------------------
        # Chat History Section
        # ---------------------------------------------
        ttk.Separator(main_frame, orient='horizontal').pack(fill=X, pady=10)
        ttk.Label(main_frame, text="Chat History", bootstyle="primary").pack(anchor=tk.W, padx=5)
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        from ttkbootstrap.scrolled import ScrolledText
        self.chat_text = ScrolledText(chat_frame, height=12, font=('Segoe UI', 10), bootstyle="light")
        self.chat_text.pack(fill=BOTH, expand=YES)
        self.chat_text.text.config(state="disabled")
        self.show_message("Welcome to the Server Admin Chat History!")

        # ---------------------------------------------
        ## Broadcast
        # ---------------------------------------------
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=X, pady=10)
        
        ttk.Label(main_frame, text="Broadcast Message", bootstyle="primary").pack(anchor=tk.W, padx=5)
        
        broadcast_frame = ttk.Frame(main_frame)
        broadcast_frame.pack(fill=X, padx=5, pady=3)
        
        self.msg_entry = ttk.Entry(broadcast_frame, width=50, bootstyle="default")
        self.msg_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        
        ttk.Button(broadcast_frame, text="Send", command=self.broadcast, bootstyle="success").pack(side=LEFT)

        # ---------------------------------------------
        ## Server Control
        # ---------------------------------------------
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=X, pady=10)
        
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(pady=10)
        # دکمه Stop با استایل خطر
        ttk.Button(ctrl_frame, text="Stop Server", command=self.stop_server, bootstyle="danger-outline").pack(side=tk.LEFT, padx=5)
        # دکمه Start با استایل موفقیت
        ttk.Button(ctrl_frame, text="Start Server", command=self.start_server, bootstyle="success-outline").pack(side=tk.LEFT, padx=5)

        self.refresh_users()
        self._periodic()

        #networking
        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        # Introduce to server
        send_control(self.client, {"type": "HELLO", "username": "admin"})

        self.running = True
        rec_message = threading.Thread(target=self.recv_loop, daemon=True)
        rec_message.start()

    def add_user(self):
        new_user = AddUser(self)
        new_user.mainloop()
    def remove_user(self):
        pass
    def on_user_select(self, event):
        """Called when a user is selected in the listbox"""
        sel = self.users_list.curselection()
        if sel:
            disp = self.users_list.get(sel[0])
            # اطمینان از اینکه map_display قبل از استفاده مقداردهی شده است
            self.selected_username = self.map_display.get(disp) if hasattr(self, 'map_display') else None
            print(f"Selected: {self.selected_username}")
        else:
            self.selected_username = None

    def start_kick_thread(self):
        """Starts a new thread to kick the selected user to avoid blocking the UI."""
        if not self.selected_username: # بهتر است از self.selected_username مستقیماً استفاده شود
            messagebox.showwarning("Warning","No user selected.")
            return
        # استفاده از نام کاربری که در on_user_select تنظیم شده است
        threading.Thread(target=self._kick_worker, daemon=True).start()


    def _kick_worker(self):
        # این متد در یک نخ مجزا (Worker Thread) اجرا می‌شود
        username_to_kick = self.selected_username
        if not username_to_kick: return

        try:
            # عملیات بالقوه مسدودکننده
            self.server.kick_by_username(username_to_kick)
            print(f"Kicked user: {username_to_kick}")
        except Exception as e:
            print(f"Kick Error for {username_to_kick}: {e}")
            # می‌توان در صورت خطا یک messagebox در نخ اصلی نمایش داد
            self.after(0, lambda: messagebox.showerror("Kick Error", f"Failed to kick {username_to_kick}: {e}"))
        finally:
            # به‌روزرسانی UI باید در نخ اصلی (Main Thread) انجام شود
            # استفاده از root.after(0, ...)
            self.after(0, self.refresh_users)
            # ریست کردن انتخاب در نخ اصلی
            self.after(0, lambda: setattr(self, 'selected_username', None))


    def refresh_users(self):
        """Refreshes the list of connected users."""
        if not self.server.running:
            # سرور در حال اجرا نیست، فقط پیام را نمایش می‌دهیم
            self.users_list.delete(0, tk.END)
            self.users_list.insert(tk.END, "Server is not running.")
            return
            
        try:
            self.users_list.delete(0, tk.END)
            clients = self.server.list_clients()
            self.map_display = {}
            for c in clients:
                # نمایش نام کاربری و آدرس
                display = f"{c['username']} ({c['addr']})"
                self.users_list.insert(tk.END, display)
                # نگاشت نام نمایشی به نام کاربری واقعی
                self.map_display[display] = c["username"]
        except Exception as e:
            # در صورت بروز خطا، آن را چاپ می‌کنیم و از کرش جلوگیری می‌کنیم
            print(f"[GUI ERROR] Could not refresh user list: {e}")
            self.users_list.delete(0, tk.END)
            self.users_list.insert(tk.END, "Server is not running or an error occurred.")
        
        # اگر کاربر قبلی در لیست نبود، انتخاب را پاک کن
        if self.selected_username and not any(v == self.selected_username for v in self.map_display.values()):
            self.selected_username = None
            self.users_list.selection_clear(0, END)


    def broadcast(self):
        """Sends a broadcast message from the admin."""
        txt = self.msg_entry.get().strip()
        if txt:
            self.server.broadcast_admin(txt)
            self.msg_entry.delete(0, tk.END)
            self.show_message(f"[ADMIN]: {txt}")

    def show_message(self, msg):
        """Appends a message to the chat history section."""
        self.chat_text.text.config(state="normal")
        self.chat_text.insert(tk.END, msg + "\n")
        self.chat_text.see(tk.END)
        self.chat_text.text.config(state="disabled")

    def show_msg(self, msg):
        """Appends a message to the chat history section (for server events and user messages)."""
        self.chat_text.text.config(state="normal")
        self.chat_text.insert(tk.END, msg + "\n")
        self.chat_text.see(tk.END)
        self.chat_text.text.config(state="disabled")

    def stop_server(self):
        """Stops the server safely."""
        self.server.safe_shutdown()
        self.refresh_users() # به‌روزرسانی لیست کاربران
        messagebox.showinfo("Stopped", "Server stopped")

    def start_server(self):
        """Starts the server in a background thread."""
        if not self.server.running:
            self.server.start_background()
            messagebox.showinfo("Started", "Server started in background")
        else:
             messagebox.showwarning("Running", "Server is already running")

    def _periodic(self):
        """A recurring function to refresh the UI."""
        if self.server.running:
            self.refresh_users()
        # ادامه دادن چرخه با استفاده از REFRESH_MS
        self.after(REFRESH_MS, self._periodic)

    def recv_loop(self):
        try:
            while self.running:
                msg = recv_control(self.client)

                if msg["type"] == "MSG":
                    self.show_msg(f"{msg['username']}: {msg['text']}")
                elif msg["type"] == "USER_JOIN":
                    self.show_msg(f"[{msg['username']} joined]")
                elif msg["type"] == "USER_LEFT":
                    self.show_msg(f"[{msg['username']} left]")
                elif msg["type"] == "ERROR":
                    self.show_msg("[Error: " + msg.get("message","") + "]")
        except Exception as e:
            # ... (rest of recv_loop)
            print("Error in recv loop:", e)
            self.destroy()


class AddUser(ttk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add New User")
        win_height = Window.winfo_screenheight(self)
        win_width = Window.winfo_screenwidth(self)
        print(win_height, win_width)
        self.geometry(f"{win_width//5}x{win_height//3}+{win_width//2 -(win_width//5)//2}+{win_height//2 - (win_height//3)//2}")
        self.resizable(False, False)

        ttk.Label(self, text="Username:").pack(pady=(20, 5))
        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(pady=5)

        ttk.Label(self, text="Password:").pack(pady=5)
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(pady=5)

        ttk.Label(self, text="Role:").pack(pady=5)
        role_options = ["admin", "user"]
        role_var = ttk.StringVar(value=role_options[1])
        self.role_button = ttk.Combobox(self, text="user", textvariable=role_var, values=role_options, state="readonly")
        self.role_button.pack(pady=5)
 # Default role

        ttk.Button(self, text="Add User", command=self.add_user).pack(pady=20)

    def add_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not self.role_button.get():
            messagebox.showwarning("Input Error", "Please select a role.")
            return
        role = self.role_button.get()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Username and Password cannot be empty.")
            return
        
        #add to db
        password = hash_password(password)
        models.add_user_db(username, password, role)

        print(f"Adding user: {username} with role: {role}")
        
        messagebox.showinfo("Success", f"User {username} added with role {role}.")
        self.destroy()

if __name__ == "__main__":
    srv = ChatServer()
    srv.start_background()
    gui = ServerAdminGUI( srv, host="127.0.0.1", port=5000)
    gui.mainloop()
