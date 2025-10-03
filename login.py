import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.window import Window
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledText

import server_interface
import interface


def check_credentials(username, password):
    global role
    with open ("users.csv", "r") as f:
        lines = f.readlines()
        for line in lines[1:]:  # Skip header
            stored_username, stored_password, role = line.strip().split(",")
            if username == stored_username and password == stored_password:
                return True, username, role
            
        return False, None, None

def admin_start(username):
    server_interface.main()

def user_start(username):
    interface.main(username)


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

        # Login Button
        self.login_button = tb.Button(self.login, text="Login", bootstyle="success", command=self.login_user)
        self.login_button.grid(row=3, column=0, columnspan=2, pady=25, sticky="ew")


    def login_user(self, ):

        username = self.username_input.get()
        password = self.password_input.get()
        if username and password:

            if 1 <len(password) < 8:
                Messagebox.ok(message="Password must be at least 8 characters long.", title="Error",alert=True)           
                return
            
            print(f"Username: {username}, Password: {password}")
            exist, username, role = check_credentials(username, password)
            if exist:
                Messagebox.ok(message=f"Login successful!, role: {role}", title="Success",alert=True)
                login_successful = True
                # self.quit()
                self.logged_in_username = username 
                
                # Destroy the window, which exits mainloop
                self.destroy()


                
            else:
                Messagebox.ok(message="Invalid username or password.", title="Error",alert=True)
                return

        else:
            
            
            Messagebox.ok(message="Please enter both username and password.", title="Error",alert=True)
            return



def main():
    login = Login(themename="superhero")

    app = interface.main(username="sadra")
    # app.mainloop()
    # login.mainloop()

    if login.logged_in_username:
        return login.logged_in_username
    else:
        # Handle case where mainloop exits without successful login (e.g., window closed manually)
        return None 



main()
    # print(role)
    # if role == "admin":
    #     print(role)
    #     admin_start(username)
                   
    # elif role == "user":
    #     print(role)

    #     user_start(username)
