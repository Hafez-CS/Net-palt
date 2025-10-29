import flet as ft
import models
import socket
import threading
import json
import os
import time

HOST = "127.0.0.1"
PORT = 5001
RUNNING = False 
DOWNLOAD_DIR = "downloaded/"

def setup_download_directory(directory_name):
    if not os.path.exists(directory_name):
        print(f"[CLIENT] Download directory '{directory_name}' not found. Creating it now.")
        os.makedirs(directory_name, exist_ok=True)
    else:
        print(f"[CLIENT] Download directory '{directory_name}' found.")

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

# def recv_loop(self):
    try:
        while self.running:
            msg = recv_control(self.client)

            if msg["type"] == "MSG":
                self.after(0, self.show_msg, f"{msg['username']}: {msg['text']}")
            elif msg["type"] == "USER_JOIN":
                self.after(0, self.show_msg, f"[{msg['username']} joined]")
            elif msg["type"] == "USER_LEFT":
                self.after(0, self.show_msg, f"[{msg['username']} left]")
            elif msg["type"] == "FILE_NOTICE":
                self.after(0, self.show_msg, f"[{msg['username']} uploaded file: {msg['filename']}]")
            elif msg["type"] == "FILE_LIST":
                self.after(0, self.update_file_list, msg["files"])
            elif msg["type"] == "FILE_SEND":
                filename = msg["filename"]
                filesize = int(msg["filesize"])
                
                self.after(0, self.show_msg, f"[Receiving file: {filename} ({filesize} bytes)...]")
                
                file_data = recv_all(self.client, filesize)
                setup_download_directory(DOWNLOAD_DIR) 
                with open(DOWNLOAD_DIR + filename, "wb") as f:
                    f.write(file_data)
                
                self.after(0, self.show_msg, f"[Downloaded file: {filename}]")
            
            elif msg["type"] == "KICKED":
                self.after(0, self.show_msg, f"[SERVER]: {msg.get('message', 'You were disconnected by the admin.')}")
                self.after(0, self.on_close, True)
                break
            elif msg["type"] == "SERVER_CLOSE":
                self.after(0, self.show_msg, f"[SERVER]: {msg.get('message', 'Server has closed.')}")
                self.after(0, self.on_close, True)
                break
            
            elif msg["type"] == "ERROR":
                self.after(0, self.show_msg, "[Error: " + msg.get("message","") + "]")
    except ConnectionError:
        self.after(0, self.show_msg, "[CONNECTION LOST] Server connection closed.")
    except Exception as e:
        print("Error in recv loop:", e)
        self.after(0, self.show_msg, "[ERROR] An unexpected error occurred.")
    finally:
            if self.running:
                self.after(0, self.on_close, True)


def connect_to_server(username):
    #networking 
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    # Introduce to server
    send_control(client, {"type": "HELLO", "username": username})
    RUNNING = True
    # threading.Thread(target=recv_loop, daemon=True).start()
    print("connected")
    return client

def show_message(msg):       
        sender = msg["username"]
        username_span_text = f"{sender}: "
        text = msg["text"]

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
        

def recv_loop(client, page):
    global RUNNING
    global current_recipient

    try:
        while True:
            msg = recv_control(client)
            print(msg)
            print(current_recipient)
            if msg["type"] == "PMSG_RECV":
                if current_recipient == msg["username"]:
                    print("in the loop:",msg)
                    show_message(msg)
                    page.update()


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
                #     self.show_msg("[Error: " + msg.get("message","") + "]")
    except socket.error as e:
        if RUNNING:
            print("[CONNECTION LOST] Admin panel connection to server closed unexpectedly.")
    except Exception as e:
        print("Error in user recv loop:", e)
    finally:
        RUNNING = False 
        pass

class contact:
    def __init__(self,page, name, image_path):
        self.page = page
        self.name = name
        self.image_path = image_path
        self.current_user = self.page.session.get("current_username")
        global current_recipient
        current_recipient = None

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


        
        messages = models.get_historical_messages_db(self.current_user, self.name)
        
        # 5. Display the loaded messages
        for msg in messages:
            sender = msg["sender"]
            text = msg["text"]
            
            # Format the message for the chat window
            is_current_user_message = (sender == self.current_user)
            
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

        
        self.page.update()

    def unlock_input(self):
            if text_input.disabled and send_button.disabled and select_file_button.disabled:
                text_input.disabled = False
                send_button.disabled = False
                select_file_button.disabled = False

    
    


def user_chat(page):
    global chat_list_view
    global text_input
    global send_button
    global select_file_button


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

    


    main_container = ft.Container(
        content= ft.ListView(
            width=450,
            height=600,
            expand=True,
        ),
        border_radius=10,
        width=450,
        bgcolor="#002A46",
    )

    #it contains the messages
    chat_list_view =  ft.ListView(
                    controls=[],
                    expand=True,
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
        expand=True,
        height=600,
        alignment=ft.alignment.bottom_center,
        padding=ft.padding.all(30)

    )

    users = get_all_users()

    for user in users:
        user = contact(page, user, "assets/profile.png")
        contact_container = user.container
        print(contact_container)
        main_container.content.controls.append(contact_container)

    print("before tab")
    tabs = [
        ft.Tab(
            text="Contacts",
            content=ft.Container(
                ft.Text("hello"),
                ft.Text("im here"),
            )
        ),
    ]

    all_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=tabs,
        scrollable=True,

    ) 

    print("after tab")



    recv_msg_thread = threading.Thread(target=recv_loop, args=(client,page))
    recv_msg_thread.start()

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
                main_container,
                chat_container,
                ft.Container(all_tabs)]

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

if __name__ == "__main__":
    ft.app(target=user_chat)