import flet as ft
import models
import json
import socket
from server import ChatServer
import time
import threading


HOST = "127.0.0.1"
PORT = 5001

def start_server():
    global server
    server = ChatServer()
    server.start_background()

class user_control(ft.Row):
    def __init__(self):

        self.kick_button = ft.ElevatedButton(text="kick", expand=True, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, icon= ft.Icons.PERSON_REMOVE_ALT_1_ROUNDED)
        self.add_user_button = ft.ElevatedButton(text="add user",expand=True, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, icon= ft.Icons.PERSON_ADD_ALT_1_ROUNDEDgit)
        self.remove_user_button = ft.OutlinedButton(
            text="remove user",
            expand=True,
            style= ft.ButtonStyle(
                color= ft.Colors.RED_ACCENT
                ),
            icon= ft.Icons.REMOVE_CIRCLE,
        )


        super().__init__(
            controls=[
                self.kick_button,
                self.add_user_button,
                self.remove_user_button
            ],
            expand=True,
            alignment=ft.alignment.top_center
        )
        



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
            avatar_stack.controls.append(
                ft.Container(
                        content=ft.CircleAvatar(bgcolor=ft.Colors.GREEN, radius=5),
                        alignment=ft.alignment.bottom_left,
                    ),
            )
        else:
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
    global refresh_thread_running

    refresh_thread_running = True # Set the flag when thread starts
    print("Refresh thread started.")
    
    # Loop while the global flag is True
    while refresh_thread_running: 
        try:
            online_users_container.controls.clear()
            all_users = get_all_users()
            for user in all_users:
                # Assuming ChatServer and online_user are defined and work
                online_users_container.controls.append(
                    online_user(user, avatar="/home/sadra/Desktop/Chatroom/src/assets/profile.png")
                )
            page.update()
        except Exception as e:
            # Handle exceptions during update/network operations
            print(f"Error in refresh_users: {e}") 
        
        # Check flag again before sleeping
        if refresh_thread_running: 
            time.sleep(2)
    
    print("Refresh thread safely stopped.")


def admin(page):
    global username
    global online_users_container
    global refresh_thread_running

    # username = page.session.get("current_username")
    username = "admin"

    def on_app_close(e: ft.ControlEvent):
        if e.data == "close":
            """Handler for the window closing event."""
            print("Initiating clean application shutdown...")
            
            # Stop the User Refreshing Thread
            global refresh_thread_running
            refresh_thread_running = False
            
            # Optional: Give the thread a moment to finish
            time.sleep(0.5) 

            # Safely Shutdown the Chat Server
            if 'server' in globals() and server:
                server.safe_shutdown() 
                print("ChatServer shutdown requested.")
            
            # Explicitly Destroy the Flet Window
            page.window.destroy()
            print("Flet window destroyed.")

        else:
            print("not closing")
    
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
    
    page.window.prevent_close = True
    page.window.on_event = on_app_close

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
        height=700
    )


    refresh_users_thread = threading.Thread(target=refresh_users, args=(page,), daemon=True)
    refresh_users_thread.start()


#it contains the messages
    chat_list_view =  ft.ListView(
        controls=[],
        expand=True,
    )
    #these are buttons and the text input
    select_file_button = ft.IconButton(
        ft.Icons.FILE_OPEN,
        on_click=lambda e: print("file open clicked"),
        disabled=True
    )


    text_input = ft.TextField(
        label="Type a message",
        expand=True,
        border_radius=10,
        bgcolor="#004466",
        color=ft.Colors.WHITE,
        focused_border_color=ft.Colors.BLUE_200,
        height=50,
        # on_submit= process_messege,
        disabled=True
    )

    send_button = ft.IconButton(ft.Icons.SEND,
                                #  on_click=process_messege,
                                 disabled=True
                                 )
    
    chat_container = ft.Container(
        ft.Column([

            ft.Container(
                chat_list_view,
                expand=True,
                border_radius=10,
                bgcolor="#001F2E",
                padding=ft.padding.all(10)

            ),

            ft.Row(
                [
                    select_file_button,
                    text_input,
                    send_button,
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
            

        ],
        alignment=ft.MainAxisAlignment.END,
        ),
        bgcolor="#002D44",
        border_radius=10,
        expand=True,
        height=600,
        alignment=ft.alignment.bottom_center,
        padding=ft.padding.all(30)

    )


    user_control_buttons = user_control()
    control_container = ft.Container(
        ft.Column(
            [
                ft.Container(
                    user_control_buttons,
                    alignment = ft.alignment.top_center
                ),
                chat_container
            ],
            expand=True,
        
        ),
        bgcolor="#002D44",
        expand=True,
        height=700,
        alignment=ft.alignment.bottom_center,
        padding=ft.padding.all(5),
        border_radius=10
    )

    #task: adding the topbar menu and the back button when its clicked go to the login page
    return ft.View(
        "/admin",
        controls=[
            ft.Row(
                [
                    users_section,
                    control_container
                ]

            )
        ],

    )



