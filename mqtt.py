try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'paho-mqtt'])
    import paho.mqtt.client as mqtt

import tkinter as tk
from tkinter import scrolledtext, messagebox
import uuid
import json
import os
import pickle

# MQTT Settings
BROKER = "test.mosquitto.org"
PORT = 1883
HISTORY_FILE = "recent_topics.pkl"

# GUI Class
class MQTTChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MQTT Chatroom")
        self.root.geometry("720x800")
        self.root.configure(bg="#1e272e")

        self.username = tk.StringVar()
        self.topic = tk.StringVar()
        self.current_topic = None
        self.users = {}
        self.recent_topics = self.load_recent_topics()

        # Header
        tk.Label(root, text="MQTT Chat Application", fg="white", bg="#1e272e", font=("Helvetica", 20, "bold")).pack(pady=15)

        # User Entry Section
        entry_frame = tk.Frame(root, bg="#1e272e")
        entry_frame.pack(pady=5, padx=15, fill=tk.X)

        tk.Label(entry_frame, text="Username:", fg="white", bg="#1e272e", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=5)
        self.username_entry = tk.Entry(entry_frame, textvariable=self.username, font=("Helvetica", 12), relief='flat', highlightbackground="#57606f", highlightthickness=1)
        self.username_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        tk.Label(entry_frame, text="Chatroom:", fg="white", bg="#1e272e", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=5)
        self.topic_entry = tk.Entry(entry_frame, textvariable=self.topic, font=("Helvetica", 12), relief='flat', highlightbackground="#57606f", highlightthickness=1)
        self.topic_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.connect_button = tk.Button(root, text="Connect", command=self.connect_to_broker, bg="#0be881", fg="black", font=("Helvetica", 12, "bold"), relief="flat", bd=0, highlightthickness=0)
        self.connect_button.pack(pady=10, padx=15, fill=tk.X)

        self.disconnect_button = tk.Button(root, text="Disconnect", command=self.disconnect_from_broker, state='disabled', bg="#ff5e57", fg="#1e272e", font=("Helvetica", 12, "bold"), relief="flat", bd=0, highlightthickness=0)
        self.disconnect_button.pack(pady=5, padx=15, fill=tk.X)

        # Recent Chatrooms
        tk.Label(root, text="Recent Chatrooms:", fg="white", bg="#1e272e", font=("Helvetica", 12, "bold")).pack(pady=(10, 0))
        self.recent_frame = tk.Frame(root, bg="#1e272e")
        self.recent_frame.pack(padx=15, pady=5, fill=tk.X)
        self.refresh_recent_topics()

        # Chat Display
        self.chat_display = scrolledtext.ScrolledText(root, state='disabled', height=15, font=("Courier New", 12), bg="#d2dae2", relief='flat')
        self.chat_display.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)

        # Connected Users
        tk.Label(root, text="Connected Users:", fg="white", bg="#1e272e", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.user_listbox = tk.Listbox(root, height=5, font=("Helvetica", 12), relief='flat')
        self.user_listbox.pack(padx=15, pady=5, fill=tk.X)

        # Message Input Section
        msg_frame = tk.Frame(root, bg="#1e272e")
        msg_frame.pack(pady=5, padx=15, fill=tk.X)

        self.msg_entry = tk.Entry(msg_frame, font=("Helvetica", 12), state='disabled', relief='flat')
        self.msg_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.send_button = tk.Button(msg_frame, text="Send", command=self.send_message, state='disabled', bg="#00a8ff", fg="white", font=("Helvetica", 12, "bold"), relief="flat", bd=0)
        self.send_button.pack(side=tk.RIGHT, padx=5)

        # MQTT Client
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
        self.disconnect_button.config(state='normal')
        self.msg_entry.config(state='normal')

        if new_topic not in self.recent_topics:
            self.recent_topics.insert(0, new_topic)
            self.recent_topics = self.recent_topics[:5]
            self.save_recent_topics()
            self.refresh_recent_topics()

    def disconnect_from_broker(self):
        if self.current_topic:
            self.client.publish(self.current_topic, json.dumps({
                "type": "leave",
                "user": self.username.get()
            }))
            self.client.unsubscribe(self.current_topic)

        self.current_topic = None
        self.send_button.config(state='disabled')
        self.disconnect_button.config(state='disabled')
        self.msg_entry.config(state='disabled')
        self.append_message("\U0001F50C You have left the chatroom.")
        self.clear_chat()
        self.user_listbox.delete(0, tk.END)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.append_message("[MQTT] \u2705 Connected to broker.")
        else:
            self.append_message("[MQTT] \u274C Connection failed.")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            if not isinstance(data, dict):
                return

            topic = msg.topic
            if topic == self.current_topic:
                msg_type = data.get("type")
                if msg_type == "join":
                    self.users.setdefault(topic, set()).add(data["user"])
                    self.append_message(f"\U0001F464 {data['user']} has joined the chatroom.")
                elif msg_type == "leave":
                    if data["user"] in self.users.get(topic, set()):
                        self.users[topic].remove(data["user"])
                    self.append_message(f"\U0001F44B {data['user']} has left the chatroom.")
                elif msg_type == "message":
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

    def load_recent_topics(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'rb') as f:
                return pickle.load(f)
        return []

    def save_recent_topics(self):
        with open(HISTORY_FILE, 'wb') as f:
            pickle.dump(self.recent_topics, f)

    def refresh_recent_topics(self):
        for widget in self.recent_frame.winfo_children():
            widget.destroy()
        for topic in self.recent_topics:
            btn = tk.Button(self.recent_frame, text=topic, bg="#57606f", fg="white", font=("Helvetica", 11), relief="flat", bd=0, padx=10, pady=5,
                            command=lambda t=topic: self.load_recent_topic(t))
            btn.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.X)

    def load_recent_topic(self, topic):
        if not self.username.get().strip():
            messagebox.showerror("Error", "Please enter a username before joining a chatroom.")
            return
        self.topic.set(topic)
        self.connect_to_broker()

# Run GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = MQTTChatApp(root)
    root.mainloop()
