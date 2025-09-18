import socket
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import json
import os
#if doenst exist
try:
    from PIL import Image, ImageTk
except:
    Image = None
    ImageTk = None
# =========================
# Utility functions for JSON protocol
# =========================
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


# =========================
# Chat App with Tkinter
# =========================
class MyApp(tk.Tk):
    def __init__(self, host="127.0.0.1", port=5000, username="User"):
        super().__init__()
        self.title("Messenger")
        self.geometry("600x700")
        self.configure(bg="#F7F7FA")

        # Keep username
        self.username = username

        # --- Colors
        self.color_bg = "#F7F7FA"
        self.color_panel = "#FFFFFF"
        self.color_border = "#E5E7EB"
        self.color_text = "#111827"
        self.color_muted = "#6B7280"
        self.color_primary = "#2563EB"
        self.color_success = "#10B981"

        # --- Layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Header
        header = ttk.Frame(self, padding=(12, 12, 12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # --- Input Bar
        input_bar = ttk.Frame(self, padding=(12, 8, 12, 12))
        input_bar.grid(row=3, column=0, sticky="ew")
        input_bar.grid_columnconfigure(1, weight=1)

        # Load and resize chat icon (send.png)
        if Image and ImageTk:
            chat_icon_path = os.path.join(os.path.dirname(__file__), "icons", "send.png")
            chat_img = Image.open(chat_icon_path)
            chat_img = chat_img.resize((24, 24), Image.LANCZOS)
            self.chat_icon = ImageTk.PhotoImage(chat_img)
            avatar = ttk.Label(header, image=self.chat_icon)
            self.send_icon = ImageTk.PhotoImage(chat_img)
            self.send_button = ttk.Button(input_bar,image=self.send_icon ,text="Send", command=self.proccess_msg)
        else:
            avatar = ttk.Label(header, text="💬", font=("Segoe UI Emoji", 16))
            self.send_button = ttk.Button(input_bar, text="Send", command=self.proccess_msg)
        avatar.grid(row=0, column=0, padx=(0, 8))
        self.send_button.grid(row=0, column=2, padx=(8, 0))

        title_lbl = ttk.Label(header, text=f"Chat – {self.username}", font=("Segoe UI", 12, "bold"))
        title_lbl.grid(row=0, column=1, sticky="w")

        status_dot = ttk.Label(header, text="●", foreground=self.color_success)
        status_dot.grid(row=0, column=2, padx=(8, 0))

        # --- Chat Panel
        body = ttk.Frame(self, padding=(12, 0, 12, 0))
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        chat_container = tk.Frame(body, bg=self.color_panel, highlightthickness=1, highlightbackground=self.color_border)
        chat_container.grid(row=0, column=0, sticky="nsew")
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_columnconfigure(0, weight=1)

        self.text_area = scrolledtext.ScrolledText(
            chat_container, wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, bg=self.color_panel, fg=self.color_text,
            font=("Segoe UI", 10), padx=8, pady=8
        )
        self.text_area.grid(row=0, column=0, sticky="nsew")

        # --- File List Panel
        file_frame = ttk.LabelFrame(self, text="Files", padding=(12, 8))
        file_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)

        self.file_listbox = tk.Listbox(file_frame, height=6)
        self.file_listbox.grid(row=0, column=0, sticky="ew")
        file_frame.grid_columnconfigure(0, weight=1)

        # Load and resize download icon
        if Image and ImageTk:
            download_icon_path = os.path.join(os.path.dirname(__file__), "icons", "download.png")
            download_img = Image.open(download_icon_path)
            download_img = download_img.resize((18, 18), Image.LANCZOS)
            self.download_icon = ImageTk.PhotoImage(download_img)
            self.download_btn = ttk.Button(file_frame, image=self.download_icon, text="Download Selected", compound="left", command=self.download_file)
        else:
            self.download_btn = ttk.Button(file_frame, text="Download Selected", command=self.download_file)
        self.download_btn.grid(row=0, column=1, padx=(8, 0))


        # Load and resize file icon
        if Image and ImageTk:
            file_icon_path = os.path.join(os.path.dirname(__file__), "icons", "file.png")
            file_img = Image.open(file_icon_path)
            file_img = file_img.resize((20, 20), Image.LANCZOS)
            self.file_icon = ImageTk.PhotoImage(file_img)
            self.choose_file = ttk.Button(input_bar, image=self.file_icon, width=3, command=self.send_file)
        else:
            self.choose_file = ttk.Button(input_bar, text="📎", width=3, command=self.send_file)
        self.choose_file.grid(row=0, column=0, padx=(0, 8))

        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(input_bar, textvariable=self.entry_var)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.entry.bind("<Return>", self.proccess_msg)



        # --- Networking
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

    # =========================
    # Message functions
    # =========================
    def proccess_msg(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        send_control(self.client, {"type": "MSG", "text": text})
        self.entry_var.set("")

    def show_msg(self, msg):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, msg + "\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

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
        selection = self.file_listbox.curselection()
        if not selection:
            return
        filename = self.file_listbox.get(selection[0])
        send_control(self.client, {"type": "GET_FILE", "filename": filename})

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
                    self.file_listbox.insert(tk.END, msg["filename"])
                elif msg["type"] == "FILE_LIST":
                    self.file_listbox.delete(0, tk.END)
                    for f in msg["files"]:
                        self.file_listbox.insert(tk.END, f["filename"])
                elif msg["type"] == "FILE_SEND":
                    filename = msg["filename"]
                    filesize = int(msg["filesize"])
                    with open("downloaded_" + filename, "wb") as f:
                        remaining = filesize
                        while remaining > 0:
                            chunk = self.client.recv(min(4096, remaining))
                            if not chunk:
                                break
                            f.write(chunk)
                            remaining -= len(chunk)
                    self.show_msg(f"[Downloaded file: {filename}]")
                elif msg["type"] == "ERROR":
                    self.show_msg("[Error: " + msg.get("message","") + "]")
        except Exception as e:
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


# =========================
# Run App
# =========================
if __name__ == "__main__":
    if Image is None or ImageTk is None:
        import sys
        print("Pillow is required for icons. Installing...")
        os.system(f"{sys.executable} -m pip install pillow")
        from PIL import Image, ImageTk
    username = input("What's your name? ").strip() or "User"
    app = MyApp(host="127.0.0.1", port=5000, username=username)
    app.mainloop()
