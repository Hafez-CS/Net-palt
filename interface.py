# client_app.py
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, filedialog
import socket, threading, json, os
from typing import Optional


DOWNLOAD_DIR = "downloaded/"


def setup_download_directory(directory_name):
    if not os.path.exists(directory_name):
        print(f"[CLIENT] Download directory '{directory_name}' not found. Creating it now.")

def send_control(sock, data: dict):
    j = json.dumps(data).encode('utf-8')
    header = f"{len(j):010d}".encode('utf-8')
    sock.sendall(header + j)

def recv_all(sock, n):
    buf = bytearray()
    while len(buf)<n:
        chunk = sock.recv(n-len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf.extend(chunk)
    return bytes(buf)

def recv_control(sock):
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

    def do_login(self):
        dlg = LoginDialog(self, title="Login")
        if not dlg.result: return False
        username,password = dlg.result
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            send_control(sock, {"type":"HELLO","username":username,"password":password})
            resp = recv_control(sock)
            if resp.get("type")=="ERROR":
                messagebox.showerror("Login failed", resp.get("message",""))
                sock.close(); return self.do_login()  # allow retry
            if resp.get("type")=="WELCOME":
                self.sock = sock; self.username=resp.get("username"); self.role=resp.get("role")
                # server may send other initial messages; handle them later in recv_loop
                return True
        except Exception as e:
            messagebox.showerror("Connection error", str(e)); return False

    def build_ui(self):
        self.text = scrolledtext.ScrolledText(self, state="disabled", height=20)
        self.text.pack(fill="both", expand=True)
        frm = tk.Frame(self); frm.pack(fill="x")
        self.entry = tk.Entry(frm); self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e:self.send_msg())
        tk.Button(frm, text="Send", command=self.send_msg).pack(side="left")
        tk.Button(frm, text="File", command=self.send_file).pack(side="left")
        self.files_list = tk.Listbox(self, height=6)
        self.files_list.pack(fill="x")
        tk.Button(self, text="Download", command=self.download_selected).pack()
        tk.Button(self, text="Show tasks", command=self.request_tasks).pack()

    def send_msg(self):
        t = self.entry.get().strip()
        if not t: return
        send_control(self.sock, {"type":"MSG","text":t})
        self.entry.delete(0, "end")

    def send_file(self):
        path = filedialog.askopenfilename()
        if not path: return
        fname = os.path.basename(path); fsize = os.path.getsize(path)
        send_control(self.sock, {"type":"FILE_META","filename":fname,"filesize":fsize})
        with open(path,"rb") as f:
            while chunk:=f.read(4096):
                self.sock.sendall(chunk)
        self.append_text(f"[You uploaded {fname}]")

    def download_selected(self):
        sel = self.files_list.curselection()
        if not sel: return
        fname = self.files_list.get(sel[0])
        send_control(self.sock, {"type":"GET_FILE","filename":fname})

    def append_text(self, s):
        self.text.config(state="normal"); self.text.insert("end", s+"\n"); self.text.see("end"); self.text.config(state="disabled")

    def request_tasks(self):
        # server already sent tasks at login; can implement refresh command if needed
        send_control(self.sock, {"type":"REQUEST_TASKS"})

    def recv_loop(self):
        try:
            send_control(self.client, {"type": "QUIT"})
            self.client.close()
        except:
            pass
        self.running = False
        self.destroy()    



if __name__ == "__main__":
    setup_download_directory(DOWNLOAD_DIR)
