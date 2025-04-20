# 🗨️ MQTT Chatroom App

A modern, Tkinter-based GUI chat application that uses the MQTT protocol for real-time communication. Connect to public chatrooms, send messages, and see who's online — all in a sleek Python interface.

![screenshot](https://via.placeholder.com/720x400.png?text=MQTT+Chatroom+App+UI)

## 🚀 Features

- 📡 Connects to public MQTT broker (`broker.hivemq.com`)
- 💬 Join or create chatrooms (topics)
- 🧑‍🤝‍🧑 See live list of connected users
- 📜 Recent chatrooms history
- ✅ Join/leave notifications
- 💾 Stores last 5 recent chatrooms locally
- 🖥️ Fully themed, responsive Tkinter UI

## 🛠️ Requirements

- Python 3.7+
- `paho-mqtt` (auto-installed if missing)

## 📦 Installation

```bash
git clone https://github.com/yourusername/mqtt-chatroom-app.git
cd mqtt-chatroom-app
python mqtt_chat.py
