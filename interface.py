import tkinter as tk
from tkinter import PhotoImage, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.window import Window
from ttkbootstrap.scrolled import ScrolledText
import threading
import socket
import json
import os 


DOWNLOAD_DIR = "downloaded/"


def setup_download_directory(directory_name):
    if not os.path.exists(directory_name):
        print(f"[CLIENT] Download directory '{directory_name}' not found. Creating it now.")

        os.makedirs(directory_name, exist_ok=True)
    else:
        print(f"[CLIENT] Download directory '{directory_name}' found.")
 
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



class App(tb.Toplevel):
    def __init__(self, parent, theme_name, username= "User", host="127.0.0.1", port=5000):
        self.theme_name = theme_name
        super().__init__()
        self.parent = parent

        self.title("Messenger")
        self.geometry("600x700")

        self.username = username

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        #header

        header = tb.Frame(self, padding=10)
        header.grid(row= 0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        # header.pack(side= TOP, fill= X)
        title_lable = tb.Label(header, text=f"Chat - {self.username}", font=("Segoe UI", 16, "bold"))
        title_lable.grid(row=0,column=0,sticky="w")
        #online dot 
        status_dot = tb.Label(header, text="●", font=("Segoe UI", 12), foreground="lightgreen")
        status_dot.grid(row=0, column=2, padx=(8, 0))


        #body

        body = tb.Frame(self, padding=(12, 0, 12, 0))
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        #chat area
        chat_container = tb.Frame(body)
        chat_container.grid(row=0, column=0, sticky="nsew")
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_columnconfigure(0, weight=1)

        self.text_area = ScrolledText(chat_container, bootstyle="primary, round")
        self.text_area.grid(row=0, column=0, sticky="nsew")

        #file area

        self.file_frame = tb.LabelFrame(body,text="Files", bootstyle="primary")
        self.file_frame.grid(row=2, column=0, sticky="nsew")
        self.file_listbox = tb.Treeview(self.file_frame, bootstyle="dark", columns=("Size",))
        self.file_listbox.heading("#0", text="Filename")
        self.file_listbox.heading("Size", text="Size (bytes)")
        self.file_listbox.column("#0", stretch=tk.YES)
        self.file_listbox.column("Size", anchor=tk.E, width=100)
        self.file_listbox.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.file_frame.grid_columnconfigure(0, weight=1)

        #download button 
        self.download_button = tb.Button(self.file_frame, text="Download", bootstyle=SUCCESS, command=self.download_file)
        self.download_button.grid(row=0, column=1,sticky="e", padx=(0,5))

        
        #input bar
        input_bar = tb.Frame(self, padding=10)
        input_bar.grid(row= 2, column=0, sticky="ew")
        input_bar.grid_columnconfigure(2, weight=1)

        self.send_button = tb.Button(input_bar, text="Send", bootstyle=("success"), command=self.proccess_msg)
        self.send_button.grid(row=0, column=3, sticky = "e", padx= 5)


        self.file_button = tb.Button(input_bar, text="File", bootstyle=INFO, command=self.send_file)
        self.file_button.grid(row=0, column=1, sticky = "w",padx= 5)

        self.entry_var = tk.StringVar()
        self.message_entry = tb.Entry(input_bar, width= 50, textvariable=self.entry_var)
        self.message_entry.grid(row=0, column=2, sticky = "ew")
        self.message_entry.focus()


        #networking 

        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host, self.port))

        # Introduce to server
        send_control(self.client, {"type": "HELLO", "username": self.username})

        self.running = True
        threading.Thread(target=self.recv_loop, daemon=True).start()

        # On close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def proccess_msg(self, event=None):
        text = self.message_entry.get().strip()
        if not text:
            return
        send_control(self.client, {"type": "MSG", "text": text})
        self.entry_var.set("")

    def show_msg(self, msg):
        self.text_area.text.config(state="normal")
        self.text_area.insert(tk.END, msg + "\n")
        self.text_area.see(tk.END)
        self.text_area.text.config(state="disabled")


    # =========================
    # File functions
    # =========================
    def send_file(self):
        filepath = filedialog.askopenfilename(title="Choose file")
        if not filepath:
            return
        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        # Send metadata first
        send_control(self.client, {"type": "FILE_META", "filename": filename, "filesize": filesize})

        # Send file data
        with open(filepath, "rb") as f:
            while chunk := f.read(4096):
                self.client.sendall(chunk)

        self.show_msg(f"[You uploaded file: {filename}]")

    def download_file(self):
        # FIX 2: Use Treeview selection logic
        selection = self.file_listbox.selection()
        if not selection:
            return
        
        # Get the filename from the Treeview item's text field (heading #0)
        selected_item_id = selection[0]
        filename = self.file_listbox.item(selected_item_id, 'text')

        # filename will be an empty string if it's the root item or somehow invalid, check again
        if not filename:
            return

        send_control(self.client, {"type": "GET_FILE", "filename": filename})
        self.show_msg(f"[Requesting file: {filename}]")

    # =========================
    # Receiving loop
    # =========================
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
                    elif msg["type"] == "FILE_NOTICE":
                        self.show_msg(f"[{msg['username']} uploaded file: {msg['filename']}]")
                        # FIX 3.1: Removed file list insertion here, rely on FILE_LIST update
                    elif msg["type"] == "FILE_LIST":
                        # FIX 3.2: Clear all existing items in Treeview
                        self.file_listbox.delete(*self.file_listbox.get_children())
                        for f in msg["files"]:
                            # FIX 3.3: Insert into Treeview with values
                            self.file_listbox.insert("", "end", text=f["filename"], values=(f["filesize"],))
                    elif msg["type"] == "FILE_SEND":
                        filename = msg["filename"]
                        filesize = int(msg["filesize"])
                        
                        self.show_msg(f"[Receiving file: {filename} ({filesize} bytes)...]")
                        
                        # FIX: Use recv_all to guarantee all bytes are read before moving on
                        file_data = recv_all(self.client, filesize)
                        with open(DOWNLOAD_DIR + filename, "wb") as f:
                            f.write(file_data)
                        
                        self.show_msg(f"[Downloaded file: {filename}]")
                    elif msg["type"] == "ERROR":
                        self.show_msg("[Error: " + msg.get("message","") + "]")
            except Exception as e:
                # ... (rest of recv_loop)
                print("Error in recv loop:", e)
                self.destroy()

    # =========================
    # Close handler
    # =========================
    def on_close(self):
        try:
            send_control(self.client, {"type": "QUIT"})
            self.client.close()
        except:
            pass
        self.running = False
        self.destroy()    



if __name__ == "__main__":
    setup_download_directory(DOWNLOAD_DIR)
    # app = App(theme_name="superhero", host="127.0.0.1", port=5000, username=username)
    login = Login(themename="superhero")
    # app = App(theme_name="superhero", host="127.0.0.1", port=5000)
    # app.withdraw()  # Start with main app hidden   

    login.mainloop()