# ... (existing imports and utility functions)

# =========================
# Chat Server
# =========================
class ChatServer:
    # ... (existing __init__, _get_file_list_from_dir, get_all_users_with_status, check_status, kick_by_username)

    def _send_private_message_to_online_user(self, client_socket, sender_username, message):
        """
        Helper function to send a private message control frame to a specific client socket.
        """
        msg = {"type": "PMSG_RECV", "username": sender_username, "text": message}
        try:
            send_control(client_socket, msg)
            return True
        except Exception as e:
            # If sending fails, remove the client as they are likely disconnected
            print(f"[SERVER ERROR] Failed to send private message: {e}")
            # Note: The caller (send_private) should handle client removal if needed, 
            # but for simplicity here we just return False.
            return False

    def send_private(self, msg, sender_username, recipient_username):
        """
        Sends a private message to a recipient. 
        Logs the message to the database and attempts to send over the socket if the recipient is online.
        """
        is_sent_over_socket = False
        recipient_socket = None

        # 1. Check if the recipient is currently online and get their socket
        with self.lock:
            recipient_socket = self.clients.get(recipient_username)

        # 2. If online, attempt to send the message over the socket
        if recipient_socket:
            print(f"Attempting to send private message from {sender_username} to {recipient_username}: {msg}")
            
            # Use the new helper function to send the control message
            is_sent_over_socket = self._send_private_message_to_online_user(
                recipient_socket, sender_username, msg
            )
            
            if is_sent_over_socket:
                print(f"[PM] Message delivered to online user: {recipient_username}")
            else:
                # If sending failed, the user might have just disconnected.
                # The handle_client loop will eventually clean this up, 
                # but we can also trigger a cleanup here.
                print(f"[PM] Failed to send message to {recipient_username}. Marking as offline.")
                # We will rely on the main thread/loop to eventually call remove_client. 
                # For a private message, we just log it as is.
        else:
            print(f"[PM] User {recipient_username} is offline. Message will be logged only.")  
        
        # 3. Always log the message to the database
        models.add_message_db(
            sender_username=sender_username,
            recipient_username=recipient_username,
            text=msg,
            is_group=False
        )
        print("[PM] Message added to DB.")
        
        return is_sent_over_socket

    # ... (rest of the ChatServer class: broadcast_admin, broadcast_message, etc.)

    # ... (Update handle_client to use the new parameter names)
    def handle_client(self, client_socket, address):
        # ... (other logic)
        
        # In handle_client's while True loop:
        # ...
        if msg["type"] == "PMSG":
            # The client sends: {"type": "PMSG", "username": sender, "text": message, "recipient": recipient}
            self.send_private(msg["text"], msg["username"], msg["recipient"])
            
        # ... (rest of handle_client)