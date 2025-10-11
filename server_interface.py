# server_interface.py 
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.window import Window
from ttkbootstrap.constants import *
from server import ChatServer
import threading, json, socket, bcrypt
import models 
import time
from ttkbootstrap.scrolled import ScrolledText

REFRESH_MS = 2000

ONLINE_ICON = "💻"
OFFLINE_ICON = "🖥️"
ONLINE_COLOR = "green"
OFFLINE_COLOR = "grey"

def hash_password(password):
    """Generates a secure hash for a given password (برای استفاده در AddUser)"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')

# توابع Utility: recv_all، recv_control، send_control
def send_control(sock, data: dict):
    """Send a JSON control message with a fixed header length"""
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


class ServerAdminGUI(ttk.Toplevel):
    def __init__(self, server: ChatServer, host, port, theme_name):
        super().__init__()
        
        style = ttk.Style(theme=theme_name)
        self.theme_name = theme_name
        
        self.server = server
        self.host = host
        self.port = port
        
        win_height = Window.winfo_screenheight(self)
        win_width = Window.winfo_screenwidth(self)
        self.geometry(f"{win_width//2}x{int(win_height//1.2)}+{win_width//2 -(win_width//2)//2}+{win_height//2 - int(win_height//1.2)//2}")

        self.title(f"Server Admin Panel - ttkbootstrap ({theme_name.capitalize()})")
        
        self.selected_username = None
        self.map_display = {} 

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=YES)

        # ---------------------------------------------
        ## Connected Users
        # ---------------------------------------------
        
        ttk.Label(main_frame, text="All Users (Online/Offline)", bootstyle="primary").pack(anchor=tk.W, pady=(5, 0))
        
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=X, padx=5, pady=5)

        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side=RIGHT, fill=Y)

        self.users_list = tk.Listbox(
            list_frame, 
            height=10, 
            selectmode=tk.SINGLE,
            yscrollcommand=list_scrollbar.set,
            bg=style.colors.get('inputbg'), 
            fg=style.colors.get('fg'),
            selectbackground=style.colors.get('primary'),
            selectforeground=style.colors.get('light'),
            font=('Segoe UI', 12) 
        )
        self.users_list.pack(side=LEFT, fill=BOTH, expand=YES)
        list_scrollbar.config(command=self.users_list.yview)

        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)

        user_btn_frame = ttk.Frame(main_frame, padding=(0, 5))
        user_btn_frame.pack(fill=X)
        
        ttk.Button(user_btn_frame, text="Kick", command=self.start_kick_thread, bootstyle="danger").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(user_btn_frame, text="Refresh", command=self.refresh_users, bootstyle="info-outline").pack(side=tk.LEFT)
        ttk.Button(user_btn_frame, text="Add User", command=self.add_user, bootstyle="success-outline").pack(side=tk.LEFT, padx=5)
        ttk.Button(user_btn_frame, text="Remove User", command=self.remove_user, bootstyle="danger-outline").pack(side=tk.LEFT, padx=(0,5))

        # ---------------------------------------------
        # Chat History Section
        # ---------------------------------------------
        ttk.Separator(main_frame, orient='horizontal').pack(fill=X, pady=10)
        ttk.Label(main_frame, text="Chat History", bootstyle="primary").pack(anchor=tk.W, padx=5)
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(fill=BOTH, expand=YES, padx=5, pady=5)

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
        self.msg_entry.bind('<Return>', lambda e: self.broadcast())

        # ---------------------------------------------
        ## Server Control
        # ---------------------------------------------
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=X, pady=10)
        
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(pady=10)
        ttk.Button(ctrl_frame, text="Stop Server", command=self.stop_server, bootstyle="danger-outline").pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Start Server", command=self.start_server, bootstyle="success-outline").pack(side=tk.LEFT, padx=5)

        self.refresh_users()
        self._periodic()

        #networking (ارتباط پنل ادمین با سرور)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        send_control(self.client, {"type": "HELLO", "username": "admin"})

        self.running = True
        threading.Thread(target=self.recv_loop, daemon=True).start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        try:
            # قبل از destroy مطمئن می‌شویم که سوکت پنل ادمین بسته شود
            self.client.close()
        except:
            pass
        self.destroy()

    def add_user(self):
        # self (ServerAdminGUI) را به عنوان parent ارسال می‌کنیم
        new_user = AddUser(self, self.theme_name) 
        new_user.mainloop()

    def remove_user(self):
        if not self.selected_username:
            messagebox.showwarning("Warning","No user selected.")
            return
        
        if self.selected_username == "admin":
             messagebox.showerror("Error","Cannot remove the admin user.")
             return
             
        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to permanently remove user {self.selected_username}?"):
            try:
                if models.remove_user_db(self.selected_username):
                    self.server.kick_by_username(self.selected_username) 
                    messagebox.showinfo("Success", f"User {self.selected_username} has been removed.")
                    self.selected_username = None
                    self.refresh_users()
                else:
                    messagebox.showwarning("Warning", f"User {self.selected_username} not found in database.")
                    self.refresh_users()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove user: {e}")
            
    def on_user_select(self, event):
        sel = self.users_list.curselection()
        if sel:
            disp = self.users_list.get(sel[0])
            self.selected_username = self.map_display.get(disp)
        else:
            self.selected_username = None

    def start_kick_thread(self):
        if not self.selected_username: 
            messagebox.showwarning("Warning","No user selected.")
            return
        if self.selected_username == "admin":
             messagebox.showerror("Error","Cannot kick the admin connection.")
             return
             
        threading.Thread(target=self._kick_worker, daemon=True).start()


    def _kick_worker(self):
        username_to_kick = self.selected_username
        if not username_to_kick: return

        try:
            is_kicked = self.server.kick_by_username(username_to_kick)
            if is_kicked:
                print(f"Kicked user: {username_to_kick}")
            else:
                print(f"User {username_to_kick} was already offline or kick failed.")

        except Exception as e:
            print(f"Kick Error for {username_to_kick}: {e}")
            self.after(0, lambda: messagebox.showerror("Kick Error", f"Failed to kick {username_to_kick}: {e}"))
        finally:
            self.after(0, self.refresh_users)
            self.after(0, lambda: setattr(self, 'selected_username', None))


    def refresh_users(self):
        if not self.server.running:
            self.users_list.delete(0, tk.END)
            self.users_list.insert(tk.END, "Server is not running.")
            return
            
        try:
            self.users_list.delete(0, tk.END)
            all_users = self.server.get_all_users_with_status()
            self.map_display = {}
            
            for i, user in enumerate(all_users):
                username = user["username"]
                is_online = user["is_online"]
                
                if is_online:
                    status_char = ONLINE_ICON
                    color = ONLINE_COLOR
                else:
                    status_char = OFFLINE_ICON
                    color = OFFLINE_COLOR

                display = f"{status_char}  {username}"
                
                self.users_list.insert(tk.END, display)
                self.users_list.itemconfig(tk.END, {'fg': color})

                self.map_display[display] = username 
            
            if self.selected_username and not any(v == self.selected_username for v in self.map_display.values()):
                self.selected_username = None
                self.users_list.selection_clear(0, END)

        except Exception as e:
            print(f"[GUI ERROR] Could not refresh user list: {e}")
            self.users_list.delete(0, tk.END)
            self.users_list.insert(tk.END, "Server is not running or an error occurred.")

    def broadcast(self, event=None): 
        txt = self.msg_entry.get().strip()
        if txt:
            self.server.broadcast_admin(txt) 
            self.msg_entry.delete(0, tk.END)
            self.show_message(f"[ADMIN]: {txt}") 

    def show_message(self, msg):
        """Appends a message to the chat history section (برای پیام‌های ادمین و سیستم)."""
        self._append_chat(msg)

    def show_msg(self, msg):
        """Appends a message to the chat history section (برای پیام‌های ورودی از سرور)."""
        self.after(0, self._append_chat, msg)

    def _append_chat(self, msg):
        """Internal function to safely append text in main thread."""
        if not self.winfo_exists(): return
        if not self.chat_text.text.winfo_exists(): return

        self.chat_text.text.config(state="normal")
        self.chat_text.insert(tk.END, msg + "\n")
        self.chat_text.see(tk.END)
        self.chat_text.text.config(state="disabled")

    def stop_server(self):
        self.server.safe_shutdown()
        self.refresh_users() 
        messagebox.showinfo("Stopped", "Server stopped")

    def start_server(self):
        if not self.server.running:
            self.server.start_background()
            messagebox.showinfo("Started", "Server started in background")
        else:
            messagebox.showwarning("Running", "Server is already running")

    def _periodic(self):
        self.refresh_users()
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
                elif msg["type"] == "SERVER_CLOSE": 
                    self.show_msg(f"[SERVER]: {msg.get('message', 'Server has closed.')}")
                    break
                elif msg["type"] == "ERROR":
                    self.show_msg("[Error: " + msg.get("message","") + "]")
        except socket.error as e:
            # مدیریت خطای سوکت هنگام قطع ارتباط غیرمنتظره
            if self.running:
                self.show_msg("[CONNECTION LOST] Admin panel connection to server closed unexpectedly.")
        except Exception as e:
            print("Error in admin recv loop:", e)
        finally:
            self.running = False
            # در صورت خروج غیرعادی، تلاش می‌کنیم سوکت را ببندیم
            try:
                self.client.close()
            except:
                pass


class AddUser(ttk.Toplevel):
    def __init__(self, parent, theme_name):
        super().__init__(parent)
        
        # --- [تغییر اعمال شده: ذخیره مرجع parent (ServerAdminGUI)] ---
        self.parent = parent 
        # -------------------------------------------------------------
        
        ttk.Style(theme=theme_name)
        
        self.title("Add New User")
        
        win_height = Window.winfo_screenheight(self)
        win_width = Window.winfo_screenwidth(self)
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
        self.role_button = ttk.Combobox(self, textvariable=role_var, values=role_options, state="readonly")
        self.role_button.pack(pady=5)

        ttk.Button(self, text="Add User", command=self.add_user).pack(pady=20)
        
    def add_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_button.get()
        
        if not username or not password or not role:
            messagebox.showwarning("Input Error", "Username, Password, and Role cannot be empty.")
            return
        
        hashed_password = hash_password(password)
        if models.add_user_db(username, hashed_password, role):
            messagebox.showinfo("Success", f"User {username} added with role {role}.")
            # --- [استفاده از self.parent] ---
            self.parent.refresh_users() 
            # --------------------------------
            self.destroy()
        else:
            messagebox.showerror("Error", f"User {username} already exists or failed to add.")