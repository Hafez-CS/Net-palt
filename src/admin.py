import flet as ft
import models
import json
import socket
from server import ChatServer
import time
import threading

HOST = "127.0.0.1"
PORT = 5000

def start_server():
    global server
    server = ChatServer()
    server.start_background()


class online_user(ft.Container):

    def __init__(self,username, avatar ):
        # self.vertical_alignment = ft.CrossAxisAlignment.START
        super().__init__(on_click=self.on_click_p,
                        ink=True,
                        height=65,
                        width=280,
                        border_radius=10,
                        margin= ft.margin.only(0,0,0,5),

                )
        
        self.username = username
        self.avatar = avatar
        self.status = self.get_status()
        status_container = ft.Container()
        
        avatar_stack = ft.Stack(
                [
                    ft.CircleAvatar(
                        foreground_image_src=self.avatar,

                    ),

                ],
                width=40,
                height=40,
            )
        
        if self.status :
            print("here green")
            avatar_stack.controls.append(
                ft.Container(
                        content=ft.CircleAvatar(bgcolor=ft.Colors.GREEN, radius=5),
                        alignment=ft.alignment.bottom_left,
                    ),
            )
        else:
            print("im in black")
            avatar_stack.controls.append(
                ft.Container(
                        content=ft.CircleAvatar(bgcolor=ft.Colors.GREY_600, radius=5),
                        alignment=ft.alignment.bottom_left,
                    ),
            )

        self.content = ft.Row(
                    [
                        avatar_stack,
                        ft.Text(self.username, size=20),                       
                    ],
                    
            )


    def get_status(self):
        # Access the server's client list using the safe, thread-locked method
        self.online_set = server.get_online_usernames()
        if self.username in self.online_set:
            return True
        else:
            return False
    
    def on_click_p(self, e):
        print("clicked")

def get_all_users():
    models.init_db()
    users = models.get_all_users_db()
    return users

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


def connect_to_server(username):
    #networking 
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    # Introduce to server
    send_control(client, {"type": "HELLO", "username": username})
    is_running = True
    # threading.Thread(target=recv_loop, daemon=True).start()
    print("connected")
    return client


def get_online_users():
    pass

def refresh_users(page):
    while True:
        online_users_container.controls.clear()
        all_users = get_all_users()
        for user in all_users:
            online_users_container.controls.append(
                online_user(user, avatar="/home/sadra/Desktop/Chatroom/src/assets/profile.png")
            )
        page.update()
        time.sleep(2)

def admin(page):
    global username
    global online_users_container

    username = page.session.get("current_username")


    #task: adding a dialog error when server is not running and back to login screen!
    try:
        #starting the server
        start_server()
        time.sleep(1)

        #coneccting to server as a client
        client = connect_to_server(username)
    except Exception as e:
        print(f"Error : {e}")
    # users_status = ChatServer.get_all_users_with_status()
    

    online_users_container = ft.ListView(
        controls=[],
        height=700,
        width=300,
    )

    users_section = ft.Container(
        online_users_container,
        border_radius=10,
        bgcolor= ft.Colors.GREY_900,
        padding=10,
    )


    refresh_users_thread = threading.Thread(target=refresh_users, args=(page,))
    refresh_users_thread.start()

    #task: adding the topbar menu and the back button when its clicked go to the login page
    return ft.View(
        "/admin",
        controls=[
            users_section
        ],

    )



