import flet as ft
import models
import socket
import json 
from screeninfo import get_monitors

# HOST = "127.0.0.1"
HOST = "192.168.43.213"
PORT = 5001
user_admin = {
    "username" : "admin",
    "password" : "admin"
}

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

def login_view(page):
    width, height = get_monitor_info()
    """Creates the login screen View."""
    page.window.height = height // 2
    page.window.width = width // 3
    # page.window.resizable = False
    page.window.center()
    def autenticate_user(e):

        input_username = username.value 
        input_password = password.value

        if not input_username or input_password:
            error = ft.AlertDialog(
                title=ft.Text("empty fiealds"),
                content=ft.Text("please fill the fields and try again."),
                alignment=ft.alignment.center
                )
            page.open(error)

        if input_username == "admin" and input_password == "admin":
            page.go("/admin")

        login_client_socket = None
        
        try:
            login_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            login_client_socket.connect((HOST, PORT))
            hello_msg = {
                "type": "HELLO",
                "username": "login" + input_username
            }
            send_control(login_client_socket, hello_msg)

            # 2. آماده‌سازی پیام احراز هویت
            login_request = {
                "type": "LOGIN_REQUEST",
                "username": input_username,
                "password": input_password # توجه: ارسال رمز عبور به صورت ساده امن نیست، اما برای تست اولیه قابل استفاده است.
            }

            # 3. ارسال درخواست به سرور
            send_control(login_client_socket, login_request)

            # 4. دریافت پاسخ از سرور
            response = recv_control(login_client_socket)
            msg = response["text"]
            # 5. پردازش پاسخ
            if response.get("type") == "LOGIN_SUCCESS":
                user_role = msg["role"]
                
                # ذخیره نام کاربری و هدایت به صفحه اصلی
                page.session.set("current_username", input_username)
                if user_role == "user":
                    print("in page go")
                    page.go("/main")
                elif user_role == "admin":
                    page.go("/admin")
                    
            elif response.get("type") == "LOGIN_FAILURE":
                # سرور پاسخ داده که احراز هویت شکست خورده (نام کاربری یا رمز عبور اشتباه است)
                error_message = response.get("message", "Incorrect username or password.")
                error = ft.AlertDialog(
                    title=ft.Text("Login Failed"),
                    content=ft.Text(error_message),
                    alignment=ft.alignment.center
                )
                page.open(error)

            else:
                # پاسخ غیرمنتظره از سرور
                error = ft.AlertDialog(
                    title=ft.Text("Server Error"),
                    content=ft.Text("Received an unexpected response from the server."),
                    alignment=ft.alignment.center
                )
                page.open(error)

        except ConnectionRefusedError:
            error = ft.AlertDialog(
                title=ft.Text("Connection Error"),
                content=ft.Text("Could not connect to the chat server."),
                alignment=ft.alignment.center
            )
            page.open(error)

        except Exception as e:
            error = ft.AlertDialog(
                title=ft.Text("An Error Occurred"),
                content=ft.Text(f"An error occurred during login: {e}"),
                alignment=ft.alignment.center
            )
            page.open(error)

        finally:
            # 6. بستن سوکت موقت (اگر باز است)
            if login_client_socket:
                # ارسال پیام خداحافظی به سرور قبل از بستن
                try:
                    send_control(login_client_socket, {"type": "BYE", "username": input_username})
                except:
                    pass # اگر سوکت مشکل دارد، مهم نیست
                login_client_socket.close()



    username = ft.TextField(label="Username", width=300, icon=ft.Icons.EMAIL)
    password = ft.TextField(
                            label="Password",
                            width=300,
                            password=True,
                            can_reveal_password=True,
                            icon=ft.Icons.LOCK
                        )
    return ft.View(
        "/",  # Define the route for this view
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Welcome Back! 🔒", size=24, weight=ft.FontWeight.BOLD),
                        username,
                        password,

                        ft.ElevatedButton(
                            "Login",
                            width=300,
                            bgcolor=ft.Colors.BLUE_600,
                            color=ft.Colors.WHITE,
                            on_click=autenticate_user
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15
                ),
                alignment=ft.alignment.center,
                padding=25,
                width=page.width if page.width < 400 else 400,
                # Optional: Add a rounded border for a card-like look
                border_radius=10, 
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.Colors.BLACK26)
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

def get_monitor_info():
    for m in get_monitors():
        if m.is_primary:
            primary_monitor = m
            break
    
    if primary_monitor:
        width = primary_monitor.width
        height = primary_monitor.height

    return width, height