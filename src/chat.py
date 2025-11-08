import flet as ft
import models
import socket
import threading
import json
import os
import time
from screeninfo import get_monitors
import random

# HOST = "192.168.43.213"
HOST = "127.0.0.1"

PORT = 5001
is_running = False 
DOWNLOAD_DIR = "downloaded/"
RELOAD = 2
current_recipient = None

colors = {
    "red" : ft.Colors.RED,
    "blue" : ft.Colors.BLUE,
    "white" : ft.Colors.WHITE,
    "black" : ft.Colors.BLACK,
    "grey" : ft.Colors.GREY,
    "green" : ft.Colors.GREEN
}

def setup_download_directory(directory_name):
    if not os.path.exists(directory_name):
        print(f"[CLIENT] Download directory '{directory_name}' not found. Creating it now.")
        os.makedirs(directory_name, exist_ok=True)
    else:
        print(f"[CLIENT] Download directory '{directory_name}' found.")

def connect_to_server(username):
    global is_running
    #networking 
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    # Introduce to server
    send_control(client, {"type": "HELLO", "username": username})
    is_running = True
    # threading.Thread(target=recv_loop, daemon=True).start()
    print("connected")
    return client

def get_historical_messages(user1, user2):
    global client
    msg = {
        "type": "GET_HISTORY",
        "user1": user1,
        "user2": user2,
    }
    try:
        send_control(client, msg)
    except Exception as e:
        print(f"something went wrong in get_historical_messages: {e}")


def get_all_users(client, username):
    global is_running

    while is_running:

        request_msg = {"type": "GetAllUser", "username": username}
        send_control(sock=client, data=request_msg)
        time.sleep(RELOAD)
        
        request_msg = {"type": "GETUSERGROUPS", "username": username}
        send_control(sock=client, data=request_msg)
        time.sleep(RELOAD)

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

def show_message(msg, page):       
    sender = msg["username"]
    username_span_text = f"{sender}: "
    text = msg["text"]

    text_style = ft.TextStyle(size=16, color=ft.Colors.BLUE_GREY_100, italic=True)
    alignment = ft.MainAxisAlignment.START

    chat_list_view.controls.append(
            ft.Container(
                ft.Row(
                    [
                    ft.Text(
                        spans=[
                            ft.TextSpan(username_span_text, style=text_style),
                            ft.TextSpan(text, style=ft.TextStyle(color=ft.Colors.WHITE))
                        ],
                        size=18
                    )
                    ],
                    alignment=alignment # Align messages based on sender
                ),
                padding=10,
                bgcolor=ft.Colors.BLACK,
                expand=True,
                # height=20,
                ink=True
            )
        )
    page.update()

def recv_loop(client, page):
    global is_running
    global current_recipient

    try:
        while is_running:
            msg = recv_control(client)
            if msg["type"] == "PMSG_RECV":
                if current_recipient == msg["username"]:
                    show_message(msg, page)
                    page.update()
        
            elif msg["type"] == "RecAllUser":
                update_contacts_ui(page, msg["text"], is_group=False)

            elif msg["type"] == "RECUSERGROUPS":
                update_contacts_ui(page, is_group=True, groups=msg["text"])

            elif msg["type"] == "RECV_HISTORY":
                update_user_messages(page, msg["text"])

                # if msg["type"] == "MSG":
                #     self.show_msg(f"{msg['username']}: {msg['text']}")
                # elif msg["type"] == "USER_JOIN":
                #     self.show_msg(f"[{msg['username']} joined]")
                # elif msg["type"] == "USER_LEFT":
                #     self.show_msg(f"[{msg['username']} left]")
                # elif msg["type"] == "SERVER_CLOSE": 
                #     self.show_msg(f"[SERVER]: {msg.get('message', 'Server has closed.')}")
                #     break
                # elif msg["type"] == "ERROR":
                #     self.show_msg("[Error: " + msg.get("message","") + "]")elif msg["type"] == "RECALLGROUPS":
            #     refresh_users(page, is_group=True, groups=msg["text"])
    except socket.error as e:
        if is_running:
            print("[CONNECTION LOST] Admin panel connection to server closed unexpectedly.")
            page.window.destroy()


    except Exception as e:
        print("Error in user recv loop:", e)
    finally:
        is_running = False 
        pass

class Group(ft.Container):
    def __init__(self, group_name, avatar):
        super().__init__(
                        height=65,
                        width=280,
                        border_radius=10,
                        margin= ft.margin.only(0,0,0,5),
                        ink=True,
                        # on_click=self.group_profile
                        )

        self.group_name = group_name
        self.avatar = avatar
        self.is_cliked = False
        avatar_stack = ft.Stack(
                [
                    ft.CircleAvatar(
                        foreground_image_src=self.avatar,
                        bgcolor= colors["green"]
                    ),
                ],
                width=40,
                height=40,
            )
        
        self.content = ft.Row(
                [
                    avatar_stack,
                    ft.Text(self.group_name, size=20),                       
                ],
            )
        

class contact:
    def __init__(self,page, name, image_path):
        self.page = page
        self.name = name
        self.image_path = image_path
        self.current_user = self.page.session.get("current_username")
        

        # self.current_user = "sadra"

        self.container = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        ft.CircleAvatar(
                        content=ft.Image(src=self.image_path),
                        radius=20,
                       ),
                       border_radius=30,
                    )
                    ,
                    ft.Text(self.name, size=16)
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
            ),
            padding=ft.padding.all(10),
            width=280,
            height=65,
            border_radius=10,
            alignment=ft.alignment.center_left,
            ink=True,
            on_click=self.on_click
        )

    def on_click(self, e):
        global current_recipient
        current_recipient = self.name
        self.unlock_input()
        chat_list_view.controls.clear()
        chat_list_view.controls.append(
            ft.Text(f" -- Chat With {self.name} -- ", size=20, weight=ft.FontWeight.BOLD)
        )

        self.page.update()

        get_historical_messages(self.current_user, self.name)
        
        

    def unlock_input(self):
            if text_input.disabled and send_button.disabled and select_file_button.disabled:
                text_input.disabled = False
                send_button.disabled = False
                select_file_button.disabled = False

    
    
def update_contacts_ui(page, users: list = None, is_group: bool= False, groups: list = None):
    global refresh_thread_running
    global users_list
    refresh_thread_running = True # Set the flag when thread starts   
    users_list = users

    if refresh_thread_running:
        try:
            if not is_group:
                online_users_container.controls.clear() 
                for user in users:
                    online_users_container.controls.append(
                        contact(page, user, image_path="assets/profile.png").container
                    )
            elif is_group:
                all_groups_container.controls.clear()
                for group in groups:
                    all_groups_container.controls.append(Group(group_name=group, avatar="assets/profile.png"))

        except Exception as e:
            print(f"Error in refresh_users: {e}") 

    page.update()
    print("cantacts are reloaded!")

def update_user_messages(page, messages):

    # 5. Display the loaded messages
    for msg in messages:
        sender = msg["sender"]
        text = msg["text"]
        
        # Format the message for the chat window
        is_current_user_message = (sender == username)
        
        # Use the existing show_messege logic for consistency, 
        # or define a simple display logic here
        
        username_span_text = f"{sender}: "
        if is_current_user_message:
            # Align to the right and use a different style for self-sent messages
            text_style = ft.TextStyle(size=16, color="#787878", italic=True)
            alignment = ft.MainAxisAlignment.END
        else:
            # Align to the left for messages from the contact
            text_style = ft.TextStyle(size=16, color=ft.Colors.BLUE_GREY_100, italic=True)
            alignment = ft.MainAxisAlignment.START

        chat_list_view.controls.append(
            ft.Row(
                [
                    ft.Text(
                        spans=[
                            ft.TextSpan(username_span_text, style=text_style),
                            ft.TextSpan(text, style=ft.TextStyle(color=ft.Colors.WHITE))
                        ],
                        size=18
                    )
                ],
                alignment=alignment # Align messages based on sender
            )
        )

    
    page.update()


def user_chat(page):
    global chat_list_view
    global text_input
    global send_button
    global select_file_button
    global username
    global online_users_container
    global all_groups_container
    global client

    width, height = get_monitor_info()
    """Creates the login screen View."""
    page.window.height = height // 1.5
    page.window.width = width // 1.5
    # page.window.resizable = False
    page.window.center()

    # page.session.set("current_username", "sadra")
    username = page.session.get("current_username")
    # username = "sadra"
    client = connect_to_server(username)

    def process_messege(e):
        msg = text_input.value
        recipient = current_recipient
        if msg:
            show_messege(msg.strip())
            send_control(client, {"type": "PMSG","username": username, "recipient":recipient, "text": msg.strip()})

    def show_messege(msg):
        text_style = ft.TextStyle(size=16, color="#787878", italic=True)
        alignment = ft.MainAxisAlignment.END

        username_span_text = f"{username}: "
        
        chat_list_view.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            spans=[
                                ft.TextSpan(username_span_text, style=text_style),
                                ft.TextSpan(msg, style=ft.TextStyle(color=ft.Colors.WHITE))
                            ],
                            size=18
                        )
                    ],
                    alignment=alignment # Align messages based on sender
                )
            )
        text_input.value = ""

        page.update()

    #it contains users in contact tab
    online_users_container = ft.ListView(
            controls=[]
        )
    #it contains groups in group tab
    all_groups_container = ft.ListView(
        controls=[]
    )

    #it contains the messages
    chat_list_view =  ft.ListView(
                    controls=[],
                    expand=True,
                    auto_scroll=True
                )
    #these are buttons and the text input
    select_file_button = ft.IconButton(ft.Icons.FILE_OPEN,
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
        on_submit= process_messege,
        disabled=True
    )

    send_button = ft.IconButton(ft.Icons.SEND,
                                 on_click=process_messege,
                                 disabled=True
                                 )
    
    #containing all the controls that handels the messages
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
        expand=3,
        height=600,
        alignment=ft.alignment.bottom_center,
        padding=ft.padding.all(30)

    )


    contact_tab = ft.Tab(
            text="Contacts",
            content=ft.Container(
                content= online_users_container,
                border_radius=10,
                bgcolor="#002A46",
            )
        )
    
    group_tab = ft.Tab(
        text="Groups",
        content=ft.Container(
            all_groups_container,
            border_radius=10,
            bgcolor="#002A46",
        )
    )
    
    tabs = [
        contact_tab,
        group_tab
    ]

    tabs_container = ft.Container(
        ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=tabs,
        scrollable=True,
        ),
        expand=1,
        height=700,
        border_radius=10,
        bgcolor="#002A46",
        padding=10

    )




    recv_msg_thread = threading.Thread(target=recv_loop, args=(client,page))
    recv_msg_thread.start()

    updata_user_thread = threading.Thread(target=get_all_users, args=(client, username))
    updata_user_thread.start()

    #on closing the program
    def on_app_close(e):
        if e.data == "close":
            print("closing the client")
            send_control(client, {"type": "QUIT"})
            time.sleep(2)
            print("closed")

            page.window.destroy()


    page.window.prevent_close = True
    page.window.on_event = on_app_close
    
    return ft.View(
        "/main",
        [
            ft.Row(controls=[
                tabs_container,
                chat_container,
                # ft.Container(all_tabs)
                ]

            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        auto_scroll=True,
        appbar= ft.AppBar(
            title=ft.Text(f"Chat as {username} 💬"),
            center_title=True,
            bgcolor="#001F2E",
            actions=[
                ft.IconButton(ft.Icons.SEARCH, on_click=lambda e: print("Search clicked")),
                ft.IconButton(ft.Icons.MORE_VERT, on_click=lambda e: print("More clicked")),
            ],
        )

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


if __name__ == "__main__":
    ft.app(target=user_chat)