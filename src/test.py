import socket
import json
import threading

PORT = 5001

username = "admin"
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

def recv_loop(client):
    global is_running
    global current_recipient

    try:
        while is_running:
            msg = recv_control(client)
            # if msg["type"] == "PMSG_RECV":
            #     if current_recipient == msg["username"]:
            #         show_message(msg, page)
            #         page.update()
        
            # elif msg["type"] == "RecAllUser":
            #     update_contacts_ui(page, msg["text"])

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

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# client.connect(("localhost", PORT))
# Introduce to server
# send_control(client, {"type": "HELLO", "username": username})
is_running = True
# threading.Thread(target=recv_loop, daemon=True).start()
print("connected")

# recv_msg_thread = threading.Thread(target=recv_loop, args=(client,))
# recv_msg_thread.start()