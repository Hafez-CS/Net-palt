# server_interface.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from server import ChatServer, list_users_db, add_user_db, remove_user_db, create_group_db, list_groups_db
import threading

REFRESH_MS = 1500

class ServerAdminGUI():
    def __init__(self, root, server: ChatServer):
        self.root = root
        self.server = server
        root.title("Server Admin Panel")
        root.geometry("900x600")

        # Left: users & actions
        left = ttk.Frame(root); left.pack(side="left", fill="y", padx=10, pady=10)
        ttk.Label(left, text="Users (DB)").pack()
        self.users_box = tk.Listbox(left, width=30, height=20)
        self.users_box.pack()
        ttk.Button(left, text="Refresh", command=self.refresh_users).pack(pady=5)
        ttk.Button(left, text="Add User", command=self.add_user).pack(fill="x")
        ttk.Button(left, text="Remove User", command=self.remove_user).pack(fill="x")
        ttk.Button(left, text="Kick Selected", command=self.kick_selected).pack(fill="x", pady=(5,0))

        # Middle: groups
        mid = ttk.Frame(root); mid.pack(side="left", fill="y", padx=10, pady=10)
        ttk.Label(mid, text="Groups").pack()
        self.groups_box = tk.Listbox(mid, width=30, height=10)
        self.groups_box.pack()
        ttk.Button(mid, text="Create Group", command=self.create_group).pack(pady=5)
        ttk.Button(mid, text="Refresh Groups", command=self.refresh_groups).pack()

        ttk.Label(mid, text="Assign user to selected group:").pack(pady=(10,0))
        self.assign_user_entry = ttk.Entry(mid)
        self.assign_user_entry.pack()
        ttk.Button(mid, text="Assign", command=self.assign_user).pack(pady=5)

        # Right: connected clients and tasks
        right = ttk.Frame(root); right.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ttk.Label(right, text="Connected Clients (live)").pack()
        self.clients_box = tk.Listbox(right, width=40, height=10)
        self.clients_box.pack(fill="x")
        ttk.Button(right, text="Refresh Clients", command=self.refresh_clients).pack(pady=5)

        ttk.Label(right, text="Send Task to user").pack(pady=(10,0))
        self.task_to = ttk.Entry(right); self.task_to.pack(fill="x")
        self.task_title = ttk.Entry(right); self.task_title.pack(fill="x", pady=2)
        self.task_body = tk.Text(right, height=6); self.task_body.pack(fill="both", pady=5)
        ttk.Button(right, text="Send Task", command=self.send_task).pack()

        # status
        self.status_label = ttk.Label(root, text="Status: idle")
        self.status_label.pack(side="bottom", fill="x")

        self.refresh_users()
        self.refresh_groups()
        self._periodic()

    def _periodic(self):
        self.refresh_clients()
        self.root.after(REFRESH_MS, self._periodic)

    def refresh_users(self):
        self.users_box.delete(0, tk.END)
        for u in list_users_db():
            self.users_box.insert(tk.END, f"{u['username']} ({u['role']})")

    def refresh_groups(self):
        self.groups_box.delete(0, tk.END)
        for g in list_groups_db():
            self.groups_box.insert(tk.END, f"{g['id']} - {g['name']}")

    def refresh_clients(self):
        self.clients_box.delete(0, tk.END)
        for c in self.server.list_clients():
            self.clients_box.insert(tk.END, f"{c['username']} @ {c['addr']}")

    def add_user(self):
        u = simpledialog.askstring("New user", "Username:", parent=self.root)
        if not u: return
        p = simpledialog.askstring("New user", "Password:", parent=self.root, show="*")
        if p is None: return
        role = simpledialog.askstring("Role", "Role (admin/user):", parent=self.root) or "user"
        add_user_db(u,p,role)
        messagebox.showinfo("Added", f"User {u} added with role {role}")
        self.refresh_users()

    def remove_user(self):
        sel = self.users_box.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a user")
            return
        display = self.users_box.get(sel[0])
        username = display.split()[0]
        remove_user_db(username)
        # also remove active connection
        threading.Thread(target=self.server.remove_user, args=(username,), daemon=True).start()
        self.refresh_users()

    def create_group(self):
        name = simpledialog.askstring("Group name", "Enter group name:", parent=self.root)
        if not name: return
        create_group_db(name)
        self.refresh_groups()

    def assign_user(self):
        sel = self.groups_box.curselection()
        if not sel:
            messagebox.showwarning("Select group", "Select a group first")
            return
        group_display = self.groups_box.get(sel[0])
        gid = int(group_display.split(" - ")[0])
        username = self.assign_user_entry.get().strip()
        if username == "":
            messagebox.showwarning("Input", "Enter username")
            return
        add_user_to_group_db(gid, username)
        messagebox.showinfo("Assigned", f"{username} added to group id {gid}")

    def kick_selected(self):
        sel = self.clients_box.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a connected client")
            return
        display = self.clients_box.get(sel[0])
        username = display.split()[0]
        threading.Thread(target=self.server.kick_by_username, args=(username,), daemon=True).start()
        self.refresh_clients()

    def send_task(self):
        to = self.task_to.get().strip()
        title = self.task_title.get().strip()
        body = self.task_body.get("1.0", tk.END).strip()
        if not to or not title:
            messagebox.showwarning("Input", "Specify to and title")
            return
        self.server.send_task(to, "ADMIN", title, body)
        messagebox.showinfo("Sent", f"Task sent to {to}")

def main():
    srv = ChatServer()
    srv.start_background()
    root = tk.Tk()
    ServerAdminGUI(root, srv)
    root.mainloop()

if __name__ == "__main__":
    main()
