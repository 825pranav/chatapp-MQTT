import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import scrolledtext, messagebox
import uuid
import json

# MQTT Settings
BROKER = "test.mosquitto.org"
PORT = 1883

# GUI Class
class MQTTChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MQTT Chat App")
        self.root.geometry("600x600")
        self.root.configure(bg="#2C3E50")

        self.username = tk.StringVar()
        self.topic = tk.StringVar()
        self.current_topic = None
        self.users = {}

        # UI Setup
        tk.Label(root, text="Enter Username:", fg="white", bg="#2C3E50", font=("Arial", 12, "bold")).pack(pady=5)
        self.username_entry = tk.Entry(root, textvariable=self.username, font=("Arial", 12))
        self.username_entry.pack(padx=10, pady=5, fill=tk.X)

        tk.Label(root, text="Enter Chatroom:", fg="white", bg="#2C3E50", font=("Arial", 12, "bold")).pack(pady=5)
        self.topic_entry = tk.Entry(root, textvariable=self.topic, font=("Arial", 12))
        self.topic_entry.pack(padx=10, pady=5, fill=tk.X)

        self.connect_button = tk.Button(root, text="Connect", command=self.connect_to_broker, bg="#1ABC9C", fg="white", font=("Arial", 12, "bold"))
        self.connect_button.pack(pady=5, padx=10, fill=tk.X)

        self.chat_display = scrolledtext.ScrolledText(root, state='disabled', height=15, font=("Arial", 12))
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.user_list_label = tk.Label(root, text="Connected Users:", fg="white", bg="#2C3E50", font=("Arial", 12, "bold"))
        self.user_list_label.pack(pady=5)
        self.user_listbox = tk.Listbox(root, height=5, font=("Arial", 12))
        self.user_listbox.pack(padx=10, pady=5, fill=tk.X)

        self.msg_entry = tk.Entry(root, font=("Arial", 12))
        self.msg_entry.pack(padx=10, pady=5, fill=tk.X)

        self.send_button = tk.Button(root, text="Send", command=self.send_message, state='disabled', bg="#3498DB", fg="white", font=("Arial", 12, "bold"))
        self.send_button.pack(pady=5, padx=10, fill=tk.X)

        self.client = mqtt.Client(client_id=str(uuid.uuid4()))
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()

    def connect_to_broker(self):
        if not self.username.get().strip():
            messagebox.showerror("Error", "Username cannot be empty!")
            return

        new_topic = self.topic.get().strip()
        if not new_topic:
            messagebox.showerror("Error", "Chatroom name cannot be empty!")
            return

        if self.current_topic:
            self.client.publish(self.current_topic, json.dumps({"type": "leave", "user": self.username.get()}))
            self.client.unsubscribe(self.current_topic)

        self.current_topic = new_topic
        self.client.subscribe(self.current_topic)
        self.client.publish(self.current_topic, json.dumps({"type": "join", "user": self.username.get()}))

        self.clear_chat()
        self.send_button.config(state='normal')

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.append_message("✅ Connected to MQTT broker.")
        else:
            self.append_message("❌ Failed to connect to broker.")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            if not isinstance(data, dict):
                return  # Ignore non-dictionary messages

            topic = msg.topic
            if topic == self.current_topic:
                if data.get("type") == "join":
                    self.users.setdefault(topic, set()).add(data["user"])
                    self.append_message(f"👋 {data['user']} has joined the chat.")
                elif data.get("type") == "leave":
                    if data["user"] in self.users.get(topic, set()):
                        self.users[topic].remove(data["user"])
                    self.append_message(f"👋 {data['user']} has left the chat.")
                elif data.get("type") == "message":
                    self.append_message(f"{data['user']}: {data['message']}")
                self.update_user_list()
        except json.JSONDecodeError:
            pass

    def send_message(self):
        message = self.msg_entry.get()
        if message and self.current_topic:
            payload = {
                "type": "message",
                "user": self.username.get(),
                "message": message
            }
            self.client.publish(self.current_topic, json.dumps(payload))
            self.msg_entry.delete(0, tk.END)

    def append_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + '\n')
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)

    def update_user_list(self):
        self.user_listbox.delete(0, tk.END)
        users_in_room = self.users.get(self.current_topic, set())
        for user in sorted(users_in_room):
            self.user_listbox.insert(tk.END, user)

    def clear_chat(self):
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')

# Run GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = MQTTChatApp(root)
    root.mainloop()
