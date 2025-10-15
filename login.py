# login.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.window import Window
from ttkbootstrap.dialogs import Messagebox
import server_interface
import interface
import sqlite3, bcrypt
from server import ChatServer
import models 

# --- [تعریف نام تم] ---
THEME_NAME = "superhero" 
# -----------------------

def autenticate_user(username, password):
    user_data = models.get_user_by_username(username)
    if user_data:
        _, stored_password_hash, role = user_data
        if models.check_password_hash(password, stored_password_hash): 
            return True, username, role
    return False, None, None


def show_chatroom(parent, username, role):
    if role == "user":
        parent.withdraw()
        app = interface.App(parent=parent, theme_name=THEME_NAME, host="127.0.0.1", port=5000, username=username)
        app.mainloop()
    elif role == "admin":
        parent.withdraw()
        srv = ChatServer()
        if not srv.running:
             srv.start_background()
        
        app = server_interface.ServerAdminGUI(srv, host="127.0.0.1", port=5000, theme_name=THEME_NAME)
        app.mainloop()

class Login(Window):
    def __init__(self, themename):
        super().__init__(themename=themename)
        self.geometry("400x500")
        self.title("Login")
        self.resizable(False, False)


        # Center frame
        self.login = tb.Frame(self, padding=30)
        self.login.place(relx=0.5, rely=0.5, anchor="center")


        # Title
        self.title_label = tb.Label(
            self.login, text="Welcome Back!", 
            font=("Helvetica", 20, "bold"),
            bootstyle="primary"
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Username
        self.user = tb.Label(self.login, text="Username:", bootstyle="info")
        self.user.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.username_input = tb.Entry(self.login, width=25, bootstyle="info")
        self.username_input.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Password
        self.password = tb.Label(self.login, text="Password:", bootstyle="info")
        self.password.grid(row=2, column=0, padx=10, pady=10, sticky="ew", )

        self.password_input = tb.Entry(self.login, width=25, bootstyle="info", show="*",)
        self.password_input.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        self.password_input.bind('<Return>', lambda e: self.login_user()) 

        # Login Button
        self.login_button = tb.Button(self.login, text="Login", bootstyle="success", command=self.login_user)
        self.login_button.grid(row=3, column=0, columnspan=2, pady=25, sticky="ew")


    def login_user(self, event=None): 

        username = self.username_input.get()
        password = self.password_input.get()
        if username and password:

            if len(password) < 4: 
                Messagebox.ok(message="Password must be at least 4 characters long.", title="Error",alert=True)
                return
            
            exist, username, role = autenticate_user(username, password)
            if exist:
                Messagebox.ok(message=f"Login successful! Role: {role}", title="Success",alert=True)
                show_chatroom(self, username, role)
                
            else:
                Messagebox.ok(message="Invalid username or password.", title="Error",alert=True)
                return
        else: 
            Messagebox.ok(message="Please enter both username and password.", title="Error",alert=True)
            return


if __name__ == "__main__":
    models.init_db() 
    login = Login(themename=THEME_NAME)
    login.mainloop()