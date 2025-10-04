# client_app.py
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, filedialog
import socket, threading, json, os
from typing import Optional

SERVER_HOST="127.0.0.1"; SERVER_PORT=5000
DOWNLOAD_DIR="downloaded/"; os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Username:").grid(row=0)
        tk.Label(master, text="Password:").grid(row=1)
        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master, show="*")
        self.e1.grid(row=0, column=1); self.e2.grid(row=1, column=1)
        return self.e1
    def apply(self):
        self.result=(self.e1.get().strip(), self.e2.get())

class ChatClientApp(tk.Tk):
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        super().__init__()
        self.title("Chat Client")
        self.geometry("700x600")
        self.host = host; self.port = port
        self.sock: Optional[socket.socket]=None
        self.username=None; self.role=None
        # login first
        ok = self.do_login()
        if not ok:
            self.destroy(); return
        self.build_ui()
        self.running=True
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
            while True:
                msg = recv_control(self.sock)
                t = msg.get("type")
                if t=="MSG":
                    self.append_text(f"{msg.get('username')}: {msg.get('text')}")
                elif t=="USER_JOIN":
                    self.append_text(f"[{msg.get('username')} joined]")
                elif t=="USER_LEFT":
                    self.append_text(f"[{msg.get('username')} left]")
                elif t=="FILE_LIST":
                    self.files_list.delete(0,"end")
                    for f in msg.get("files",[]):
                        self.files_list.insert("end", f["filename"])
                elif t=="FILE_SEND":
                    fn = msg.get("filename"); fs = int(msg.get("filesize",0))
                    data = recv_all(self.sock, fs)
                    with open(os.path.join(DOWNLOAD_DIR, fn),"wb") as f:
                        f.write(data)
                    self.append_text(f"[Downloaded {fn}]")
                elif t=="TASK_LIST":
                    tasks = msg.get("tasks",[])
                    self.append_text("[Tasks]")
                    for tk_ in tasks:
                        self.append_text(f"From {tk_['from']} - {tk_['title']}: {tk_['body']}")
                elif t=="TASK_NOTICE":
                    self.append_text(f"[New Task] {msg.get('title')} - {msg.get('body')}")
                elif t=="ERROR":
                    self.append_text("[Error] "+msg.get("message",""))
        except Exception as e:
            print("recv loop ended:", e)
            try: self.sock.close()
            except: pass
            messagebox.showinfo("Disconnected","Connection closed by server")
            self.destroy()

if __name__=="__main__":
    app = ChatClientApp(); app.mainloop()
