try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'paho-mqtt'])
    import paho.mqtt.client as mqtt

import customtkinter as ctk
import tkinter.messagebox as messagebox
import uuid
import json
import os
import pickle

# MQTT Settings
BROKER = "broker.hivemq.com"
PORT = 1883
HISTORY_FILE = "recent_topics.pkl"

class MQTTChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MQTT Chatroom")
        self.root.geometry("720x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.username = ctk.StringVar()
        self.topic = ctk.StringVar()
        self.current_topic = None
        self.users = {}
        self.recent_topics = self.load_recent_topics()

        # Header
        ctk.CTkLabel(root, text="MQTT Chat Application", font=("Helvetica", 24, "bold")).pack(pady=15)

        # Entry Section
        entry_frame = ctk.CTkFrame(root)
        entry_frame.pack(pady=5, padx=15, fill="x")

        ctk.CTkLabel(entry_frame, text="Username:", font=("Helvetica", 14)).pack(side="left", padx=5)
        self.username_entry = ctk.CTkEntry(entry_frame, textvariable=self.username, font=("Helvetica", 14))
        self.username_entry.pack(side="left", padx=5, expand=True, fill="x")

        ctk.CTkLabel(entry_frame, text="Chatroom:", font=("Helvetica", 14)).pack(side="left", padx=5)
        self.topic_entry = ctk.CTkEntry(entry_frame, textvariable=self.topic, font=("Helvetica", 14))
        self.topic_entry.pack(side="left", padx=5, expand=True, fill="x")

        self.connect_button = ctk.CTkButton(root, text="Connect", command=self.connect_to_broker, fg_color="#0be881", text_color="black")
        self.connect_button.pack(pady=10, padx=15, fill="x")

        self.disconnect_button = ctk.CTkButton(root, text="Disconnect", command=self.disconnect_from_broker, fg_color="#ff5e57", state="disabled", text_color="black")
        self.disconnect_button.pack(pady=5, padx=15, fill="x")

        # Recent Chatrooms
        ctk.CTkLabel(root, text="Recent Chatrooms:", font=("Helvetica", 14, "bold")).pack(pady=(10, 0))
        self.recent_frame = ctk.CTkFrame(root)
        self.recent_frame.pack(padx=15, pady=5, fill="x")
        self.refresh_recent_topics()

        # Chat Display
        self.chat_display = ctk.CTkTextbox(root, state="disabled", height=300, font=("Courier New", 14))
        self.chat_display.pack(padx=15, pady=10, fill="both", expand=True)

        # Connected Users
        ctk.CTkLabel(root, text="Connected Users:", font=("Helvetica", 14, "bold")).pack(pady=5)
        self.user_listbox = ctk.CTkTextbox(root, height=100, font=("Helvetica", 14))
        self.user_listbox.pack(padx=15, pady=5, fill="x")

        # Message Input
        msg_frame = ctk.CTkFrame(root)
        msg_frame.pack(pady=5, padx=15, fill="x")

        self.msg_entry = ctk.CTkEntry(msg_frame, font=("Helvetica", 14), state="disabled")
        self.msg_entry.pack(side="left", padx=5, expand=True, fill="x")

        self.send_button = ctk.CTkButton(msg_frame, text="Send", command=self.send_message, state="disabled", fg_color="#00a8ff")
        self.send_button.pack(side="right", padx=5)

        # MQTT Client
        self.client = mqtt.Client(client_id=str(uuid.uuid4()), protocol=mqtt.MQTTv311)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log

        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to MQTT broker:\n{e}")

    def on_log(self, client, userdata, level, buf):
        print(f"[MQTT LOG]: {buf}")

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

        # Request user list right after joining
        self.client.publish(self.current_topic, json.dumps({"type": "request_user_list", "user": self.username.get()}))

        self.clear_chat()
        self.send_button.configure(state="normal")
        self.disconnect_button.configure(state="normal")
        self.msg_entry.configure(state="normal")

        if new_topic not in self.recent_topics:
            self.recent_topics.insert(0, new_topic)
            self.recent_topics = self.recent_topics[:5]
            self.save_recent_topics()
            self.refresh_recent_topics()

    def disconnect_from_broker(self):
        if self.current_topic:
            self.client.publish(self.current_topic, json.dumps({"type": "leave", "user": self.username.get()}))
            self.client.unsubscribe(self.current_topic)

        self.current_topic = None
        self.send_button.configure(state="disabled")
        self.disconnect_button.configure(state="disabled")
        self.msg_entry.configure(state="disabled")
        self.append_message("\U0001F50C You have left the chatroom.")
        self.clear_chat()
        self.user_listbox.configure(state="normal")
        self.user_listbox.delete("1.0", "end")
        self.user_listbox.configure(state="disabled")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.append_message("[MQTT] ✅ Connected to broker.")
        else:
            self.append_message(f"[MQTT] ❌ Connection failed with code {rc}.")

    def on_disconnect(self, client, userdata, rc):
        self.append_message("[MQTT] ⚠️ Disconnected from broker.")

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
                    self.client.publish(self.current_topic, json.dumps({"type": "update_user_list", "users": list(self.users[topic])}))
                elif msg_type == "leave":
                    if data["user"] in self.users.get(topic, set()):
                        self.users[topic].remove(data["user"])
                    self.append_message(f"\U0001F44B {data['user']} has left the chatroom.")
                    self.client.publish(self.current_topic, json.dumps({"type": "update_user_list", "users": list(self.users[topic])}))
                elif msg_type == "message":
                    self.append_message(f"{data['user']}: {data['message']}")
                elif msg_type == "update_user_list":
                    self.users[topic] = set(data["users"])
                    self.update_user_list()
                elif msg_type == "request_user_list":
                    # Respond with user list if I'm already in the room
                    if self.username.get() in self.users.get(topic, set()):
                        self.client.publish(self.current_topic, json.dumps({
                            "type": "update_user_list",
                            "users": list(self.users[topic])
                        }))

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
            self.msg_entry.delete(0, "end")

    def append_message(self, message):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", message + '\n')
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def update_user_list(self):
        self.user_listbox.configure(state="normal")
        self.user_listbox.delete("1.0", "end")
        users_in_room = self.users.get(self.current_topic, set())
        for user in sorted(users_in_room):
            self.user_listbox.insert("end", user + "\n")
        self.user_listbox.configure(state="disabled")

    def clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

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
            btn = ctk.CTkButton(self.recent_frame, text=topic, command=lambda t=topic: self.load_recent_topic(t), height=30, width=140)
            btn.pack(side="left", padx=5, pady=2)

    def load_recent_topic(self, topic):
        if not self.username.get().strip():
            messagebox.showerror("Error", "Please enter a username before joining a chatroom.")
            return
        self.topic.set(topic)
        self.connect_to_broker()

# Run GUI
if __name__ == "__main__":
    root = ctk.CTk()
    app = MQTTChatApp(root)
    root.mainloop()
