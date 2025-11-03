import flet as ft
import models
import json
import socket
from server import ChatServer
import time
import threading
import bcrypt
import sys
from screeninfo import get_monitors

HOST = "127.0.0.1"
PORT = 5001
RUNNING = False
RELOAD = 2
is_running = False

def start_server():
    global server
    try:    
        server = ChatServer()
        server.start_background()
    except Exception as e:
        print(f"something went wrong in starting the server: {e}")
        sys.exit()
    finally:
        RUNNING = True

def connect_to_server(username, page):
    global is_running
    #networking 
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    # Introduce to server
    send_control(client, {"type": "HELLO", "username": username})
    is_running = True

    recv_msg_thread = threading.Thread(target=recv_loop, args=(client, page), daemon=True)
    recv_msg_thread.start()

    updata_user_thread = threading.Thread(target=get_all_users, args=(client, username), daemon=True)
    updata_user_thread.start()

    print("connected")
    return client


def hash_password(password):
    """Generates a secure hash for a given password"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')


class user_control(ft.Row):
    def __init__(self):

        self.kick_button = ft.ElevatedButton(
            text="kick", 
            expand=True, 
            bgcolor=ft.Colors.RED, 
            color=ft.Colors.WHITE, 
            icon= ft.Icons.PERSON_REMOVE_ALT_1_ROUNDED,
            on_click=self.kick_user
            )
        
        self.add_user_button = ft.ElevatedButton(
            text="add user",
            expand=True,
            bgcolor=ft.Colors.GREEN, 
            color=ft.Colors.WHITE, 
            icon= ft.Icons.PERSON_ADD_ALT_1_ROUNDED, 
            on_click=self.add_user
            )
        
        self.remove_user_button = ft.OutlinedButton(
            text="remove user",
            expand=True,
            style= ft.ButtonStyle(
                color= ft.Colors.RED_ACCENT
                ),
            icon= ft.Icons.REMOVE_CIRCLE,
            on_click=self.remove_user
        )
        self.add_group_button = ft.ElevatedButton(
            text="new group",
            expand=True,
            bgcolor=ft.Colors.BLUE_ACCENT, 
            color=ft.Colors.WHITE, 
            icon= ft.Icons.GROUP, 
            on_click=self.add_group
            )

        super().__init__(
            controls=[
                self.kick_button,
                self.add_user_button,
                self.remove_user_button,
                self.add_group_button
            ],
            expand=True,
            alignment=ft.alignment.top_center
        )
    def add_group(self, e):
        self.groupname_input = ft.TextField(label="Group name", width=300, max_length=20)
        self.newgroup_dialog = ft.AlertDialog(
            title="Add New Group",
            content=ft.Container(

                self.groupname_input
                
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: e.page.close(self.newgroup_dialog)),
                ft.ElevatedButton("Add", on_click=self.confirm_newgroup),
            ]
        )
        e.page.open(self.newgroup_dialog)

    def confirm_newgroup(self, e):
        self.groupname = self.groupname_input.value
        if not self.groupname:
            self.groupname_input.error_text = "the group name can't be empty"
            self.newgroup_dialog.update()
        self.res_alert = ft.AlertDialog(
            title="Add New Group",
            actions=[
                ft.TextButton("Ok", on_click=lambda e: e.page.close(self.res_alert))
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        try:
            #adding new group to database
            res = models.add_group_db(self.groupname)

            #showing alert based on db result
            if res:
                self.res_alert.content = ft.Text("successful", color=ft.Colors.GREEN, size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                e.page.open(self.res_alert)
            elif res == None:
                self.res_alert.content = ft.Text("this group exists", color=ft.Colors.RED, size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                e.page.open(self.res_alert)
            elif res == False:
                raise
        except:
            self.res_alert.content = ft.Text("something went wrong", color=ft.Colors.RED, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
            e.page.open(self.res_alert)


    def add_user(self,e):
        self.username_input = ft.TextField(label="Username", width=300)
        self.password_input = ft.TextField(label="Password", width=300, password=True, can_reveal_password=True)
        self.role_input = ft.SegmentedButton(
                        selected_icon=ft.Icon(ft.Icons.CHECK_CIRCLE),
                        selected={"user"},
                        allow_multiple_selection=False,
                        segments=[
                            ft.Segment(
                                value="user",
                                label=ft.Text("user"),
                                icon=ft.Icon(ft.Icons.PERSON_ROUNDED),
                            ),
                            ft.Segment(
                                value="admin",
                                label=ft.Text("admin"),
                                icon=ft.Icon(ft.Icons.SUPERVISED_USER_CIRCLE),
                            ),
                        ],
                    )
        
        self.add_user_dialog = ft.AlertDialog(
            title=ft.Text("Add New User"),
            content=ft.Column(
                [   
                    #prompt for usename and password
                    self.username_input,
                    self.password_input,
                    #select between user and admin
                    self.role_input
                ]
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: e.page.close(self.add_user_dialog)),
                ft.ElevatedButton("Add", on_click=lambda e: self.confirm_add_user(e)),
                
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            alignment=ft.alignment.center
        )
        e.page.open(self.add_user_dialog)

    def confirm_add_user(self, e):
        self.username = self.username_input.value
        self.password = self.password_input.value
        self.role = self.role_input.selected

        if not self.username:
            self.username_input.error_text = "username can not be empty"
            self.add_user_dialog.update()
        if not self.password:
            self.password_input.error_text = "password can not be empty"
            self.password_input.update()

        if self.username and self.password:
            self.role = list(self.role)

            hashed_password = hash_password(self.password)
            if models.add_user_db(self.username, hashed_password, self.role[0]):
                print("Success", f"User {self.username} added with role {self.role[0]}.")
            else:
                print("Error", f"User {self.username} already exists or failed to add.")


            e.page.close(self.add_user_dialog)


    #build a dropdown for showing all users
    def build_user_dropdown(self):
        self.users_list = get_all_users()
        options = []
        for user in self.users_list:
            options.append(
                ft.DropdownOption(
                    key=user,
                    content=ft.Text(f"{user}")   
                )
            )
        return ft.Dropdown(label="users", options=options, expand=True, enable_search=True)

    def kick_user(self, e):
        print(e)
        self.user_list_dropdown = self.build_user_dropdown()
        self.submit_user_button = ft.ElevatedButton(text="kick", color=ft.Colors.RED, expand=True, on_click=self.confirm_kick_user)
        self.text = ft.Text("please select a user", font_family=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.kick_alert = ft.AlertDialog(
            modal=False,
            content=self.user_list_dropdown,
            actions=[self.submit_user_button],
            alignment=ft.alignment.center,
        )

        e.page.open(self.kick_alert)


    def confirm_kick_user(self,e):
        self.kicked_username = self.user_list_dropdown.value
        if self.kicked_username:
            try:
                server.kick_by_username(self.kicked_username)
                print(f"user {self.kicked_username} has been kicked out from the server!")
            except Exception as e:
                print(f"error while kicking the user: {e}")
            
            
    def remove_user(self, e):

        try:
            self.user_list_dropdown = self.build_user_dropdown()
        except Exception as e:
            print(f"something went wrong: {e}")

        self.submit_user_button = ft.ElevatedButton(text="remove", color=ft.Colors.RED, expand=True, on_click=self.confirm_remove_user)
        self.text = ft.Text("please select a user", font_family=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.remove_alert = ft.AlertDialog(
            modal=False,
            content=self.user_list_dropdown,
            actions=[self.submit_user_button],
            alignment=ft.alignment.center,
        )

        e.page.open(self.remove_alert)


    def confirm_remove_user(self, e):
        if self.user_list_dropdown.value:
            remove_username = self.user_list_dropdown.value
            try:
                if models.remove_user_db(remove_username):
                    print(f"user {remove_username} is removed!")
                    server.kick_by_username(remove_username)
                    print(f"user {remove_username} is disconnected!")
            except Exception as e :
                print(f"something went wrong in removing user: {e}")
            finally:
                e.page.close(self.remove_alert)

class Group(ft.Container):
    def __init__(self, group_name, avatar):
        super().__init__(
                        ink=True,
                        height=65,
                        width=280,
                        border_radius=10,
                        margin= ft.margin.only(0,0,0,5),)

        self.group_name = group_name
        self.avatar = avatar
        
        avatar_stack = ft.Stack(
                [
                    ft.CircleAvatar(
                        foreground_image_src=self.avatar,

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


def get_all_users(client, username):
    global is_running

    while is_running:

        request_msg = {"type": "GetAllUser", "username": username}
        send_control(sock=client, data=request_msg)
        time.sleep(RELOAD)
        
        request_msg = {"type": "GETALLGROUPS", "username": username}
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

def recv_loop(client, page):
    global is_running
    global current_recipient

    try:
        while is_running:
            msg = recv_control(client)
            # if msg["type"] == "PMSG_RECV":
            #     if current_recipient == msg["username"]:
            #         show_message(msg, page)
            #         page.update()
        
            if msg["type"] == "RecAllUser":
                refresh_users(page, msg["text"], is_group=False)
            elif msg["type"] == "RECALLGROUPS":
                refresh_users(page, is_group=True, groups=msg["text"])
            # elif msg["type"] == "RECV_HISTORY":
            #     update_user_messages(page, msg["text"])

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
        if is_running:
            print("[CONNECTION LOST] Admin panel connection to server closed unexpectedly.")
    except Exception as e:
        print("Error in user recv loop:", e)
    finally:
        is_running = False 
        pass




def refresh_users(page, users: list = None, is_group: bool= False, groups: list = None):
    global refresh_thread_running

    refresh_thread_running = True # Set the flag when thread starts   

    if refresh_thread_running: 
        try:
            
            if not is_group:
                online_users_container.controls.clear()
                for user in users:
                    # Assuming ChatServer and online_user are defined and work
                    online_users_container.controls.append(
                        online_user(user, avatar="/home/sadra/Desktop/Chatroom/src/assets/profile.png")
                    )
                page.update()
            elif is_group:
                all_groups_container.controls.clear()
                for group in groups:
                    all_groups_container.controls.append(Group(group_name=group, avatar="/home/sadra/Desktop/Chatroom/src/assets/profile.png"))
                page.update()

        except Exception as e:
            # Handle exceptions during update/network operations
            print(f"Error in refresh_users: {e}") 
        
        # Check flag again before sleeping
        # if refresh_thread_running: 
        #     time.sleep(2)
    else:
        print("Refresh thread safely stopped.")


def admin(page):
    global username
    global online_users_container
    global refresh_thread_running
    global all_groups_container

    width, height = get_monitor_info()
    """Creates the login screen View."""
    page.window.height = height // 1.5
    page.window.width = width // 1.5
    time.sleep(0.5)
    page.window.center()
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

    
    #task: adding a dialog error when server is not running and back to login screen!
    try:
        #starting the server
        start_server()
        time.sleep(0.5)
        #coneccting to server as a client
        client = connect_to_server(username, page)
    except Exception as e:
        print(f"Error : {e}")
    # users_status = ChatServer.get_all_users_with_status()
    
    page.window.prevent_close = True
    page.window.on_event = on_app_close

    online_users_container = ft.ListView(
        controls=[],
    )

    all_groups_container = ft.ListView(
        controls=[]
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

    # refresh_users_thread = threading.Thread(target=refresh_users, args=(page,), daemon=True)
    # refresh_users_thread.start()


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
        expand=3,
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
                    tabs_container,
                    control_container
                ]

            )
        ],

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

