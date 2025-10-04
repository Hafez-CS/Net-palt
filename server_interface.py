# server_interface.py
import tkinter as tk
from tkinter import ttk, messagebox
from server import ChatServer
import threading # اضافه کردن کتابخانه threading

REFRESH_MS = 2000

class ServerAdminGUI(tb):
    def __init__(self, root, server: ChatServer):
        self.root = root
        self.server = server

        root.title("Server Admin Panel")
        root.geometry("700x500")

        # یک متغیر برای نگهداری نام کاربری انتخاب شده
        self.selected_username = None

        # لیست کاربران
        ttk.Label(root, text="Connected Users").pack(anchor=tk.W)
        self.users_list = tk.Listbox(root, height=10)
        self.users_list.pack(fill=tk.X, padx=5, pady=5)
        # اضافه کردن رویداد به Listbox برای تشخیص انتخاب کاربر
        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)

        btn_frame = ttk.Frame(root)
        btn_frame.pack()
        # تغییر: فراخوانی متد جدید برای اجرای کیک در نخ جداگانه
        ttk.Button(btn_frame, text="Kick", command=self.start_kick_thread).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_users).pack(side=tk.LEFT)

        # Broadcast
        ttk.Label(root, text="Broadcast Message").pack(anchor=tk.W, padx=5)
        self.msg_entry = ttk.Entry(root, width=50)
        self.msg_entry.pack(padx=5, pady=3)
        ttk.Button(root, text="Send", command=self.broadcast).pack()

        # کنترل سرور
        ctrl_frame = ttk.Frame(root)
        ctrl_frame.pack(pady=10)
        ttk.Button(ctrl_frame, text="Stop Server", command=self.stop_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Start Server", command=self.start_server).pack(side=tk.LEFT, padx=5)

        self.refresh_users()
        self._periodic()

    def on_user_select(self, event):
        """Called when a user is selected in the listbox"""
        sel = self.users_list.curselection()
        if sel:
            disp = self.users_list.get(sel[0])
            self.selected_username = self.map_display.get(disp)
            print(f"Selected: {self.selected_username}")

    def start_kick_thread(self):
        """Starts a new thread to kick the selected user to avoid blocking the UI."""
        if not getattr(self,"selected_username",None):
            messagebox.showwarning("warning","هیچ کاربری انتخاب نشده است.")
            return
        threading.Thread(target=self._kick_worker,daemon=True).start()


    def _kick_worker(self):
        username = self.selected_username
        try:
            self.server.kick_by_username(username)
        except Exception as e:
            print("Kick Error:", e)
        finally:

            try:
                self.root.after(0,self.refresh_users)

            except Exception:
                pass            
            
        
    def _perform_kick(self):
        """Actual kick logic that runs in the new thread."""
        try:
            self.server.kick_by_username(self.selected_username)
            # بعد از اتمام عملیات، به نخ اصلی میگیم که رابط کاربری رو به‌روزرسانی کنه
            self.root.after(100, self.refresh_users)
        except Exception as e:
            print(f"[ERROR] Could not kick user: {e}")
        finally:
            self.selected_username = None  # ریست کردن انتخاب

    def refresh_users(self):
        # بررسی می‌کنیم که سرور در حال اجرا هست یا نه
        if not self.server.running:
            return
            
        try:
            self.users_list.delete(0, tk.END)
            clients = self.server.list_clients()
            self.map_display = {}
            for c in clients:
                # نمایش نام کاربری و آدرس
                display = f"{c['username']} ({c['addr']})"
                self.users_list.insert(tk.END, display)
                # ذخیره نام کاربری به جای fileno
                self.map_display[display] = c["username"]
        except Exception as e:
            # در صورت بروز خطا، آن را چاپ می‌کنیم و از کرش جلوگیری می‌کنیم
            print(f"[GUI ERROR] Could not refresh user list: {e}")
            self.users_list.delete(0, tk.END)
            self.users_list.insert(tk.END, "Server is not running or an error occurred.")

    def kick_selected(self):
        # این متد دیگر مورد استفاده نیست
        pass

    def broadcast(self):
        txt = self.msg_entry.get().strip()
        if txt:
            self.server.broadcast_admin(txt)
            self.msg_entry.delete(0, tk.END)

    def stop_server(self):
        self.server.safe_shutdown()
        messagebox.showinfo("Stopped", "Server stopped")

    def start_server(self):
        if not self.server.running:
            self.server.start_background()
            messagebox.showinfo("Started", "Server started")

    def _periodic(self):
        # این تابع همیشه اجرا می‌شه
        # اما تنها در صورتی refresh_users رو صدا می‌زنه که سرور در حال اجرا باشه
        if self.server.running:
            self.refresh_users()
        self.root.after(REFRESH_MS, self._periodic)

def main():
    srv = ChatServer()
    srv.start_background()
    root = tk.Tk()
    ServerAdminGUI(root, srv)
    root.mainloop()

if __name__ == "__main__":
    main()