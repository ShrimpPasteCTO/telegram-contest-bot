from flask import Flask, request
import telebot
import os

# === 1. Configuration ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # We will set this environment variable on Render
GROUP_ID = -1002483696025                # <- **Replace this with your group’s chat ID** (with -100 prefix)
THREAD_ID = 269755                      # <- **Replace this with your contest topic’s thread_id**

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# In-memory storage for contest data (memes and votes)
# For example, we have a list of meme entries for the contest:
memes = [
    {"id": 1, "url": "https://i.imgur.com/5mq5ilu.jpeg", "caption": "Option 1 - Submitted by Adonis", "votes": 0, "voters": set()},
    {"id": 2, "url": "https://i.imgur.com/LryoAx6.jpeg", "caption": "Option 2 - Submitted by Sunflwr Seed", "votes": 0, "voters": set()}
    {"id": 3, "url": "https://i.imgur.com/HqrRIb9.jpeg", "caption": "Option 3 - Submitted by Philip Falana", "votes": 0, "voters": set()}
    {"id": 4, "url": "https://i.imgur.com/10IbWjI.jpeg", "caption": "Option 4 - Submitted by Luis Boxeo", "votes": 0, "voters": set()}
    {"id": 5, "url": "https://i.imgur.com/s4iiDqx.jpeg", "caption": "Option 5 - Submitted by DoomSlayer", "votes": 0, "voters": set()}
    {"id": 6, "url": "https://i.imgur.com/dbPbQMe.jpeg", "caption": "Option 6 - Submitted by Dolphie", "votes": 0, "voters": set()}
    {"id": 7, "url": "https://i.imgur.com/Pe4JKyc.jpeg", "caption": "Option 7 - Submitted by Demmy", "votes": 0, "voters": set()}
    {"id": 8, "url": "https://i.imgur.com/rN42Isl.jpeg", "caption": "Option 8 - Submitted by Defi Boss", "votes": 0, "voters": set()}
    {"id": 9, "url": "https://i.imgur.com/OGLuO8G.jpeg", "caption": "Option 9 - Submitted by Bliss Gold", "votes": 0, "voters": set()}
    {"id": 10, "url": "https://i.imgur.com/yVMzj1J.jpeg", "caption": "Option 10 - Submitted by Sunflwr Seed", "votes": 0, "voters": set()}
]
contest_active = False
