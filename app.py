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
    {"id": 2, "url": "https://i.imgur.com/LryoAx6.jpeg", "caption": "Option 2 - Submitted by Sunflwr Seed", "votes": 0, "voters": set()},
    {"id": 3, "url": "https://i.imgur.com/HqrRIb9.jpeg", "caption": "Option 3 - Submitted by Philip Falana", "votes": 0, "voters": set()},
    {"id": 4, "url": "https://i.imgur.com/2w7tAhx.jpg", "caption": "Option 4 - Submitted by Luis Boxeo", "votes": 0, "voters": set()},
    {"id": 5, "url": "https://i.imgur.com/s4iiDqx.jpeg", "caption": "Option 5 - Submitted by DoomSlayer", "votes": 0, "voters": set()},
    {"id": 6, "url": "https://i.imgur.com/dbPbQMe.jpeg", "caption": "Option 6 - Submitted by Dolphie", "votes": 0, "voters": set()},
    {"id": 7, "url": "https://i.imgur.com/Pe4JKyc.jpeg", "caption": "Option 7 - Submitted by Demmy", "votes": 0, "voters": set()},
    {"id": 8, "url": "https://i.imgur.com/rN42Isl.jpeg", "caption": "Option 8 - Submitted by Defi Boss", "votes": 0, "voters": set()},
    {"id": 9, "url": "https://i.imgur.com/OGLuO8G.jpeg", "caption": "Option 9 - Submitted by Bliss Gold", "votes": 0, "voters": set()},
    {"id": 10, "url": "https://i.imgur.com/yVMzj1J.jpeg", "caption": "Option 10 - Submitted by Sunflwr Seed", "votes": 0, "voters": set()}
]
contest_active = False

@bot.message_handler(commands=['getfileid'])
def get_file_id(message):
    # This will reply with the file_id of any photo you send
    if message.photo:
        # Telegram sends multiple sizes; use the largest
        file_id = message.photo[-1].file_id
        bot.reply_to(message, f"File ID:\n`{file_id}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Please send me a photo after this command.")

# === 2. Bot Command Handlers ===

@bot.message_handler(commands=['startcontest'])
def start_contest(message):
    global contest_active
    # Only allow contest start in the group (you can add a check for admin user here if desired)
    if message.chat.id != GROUP_ID:
        bot.reply_to(message, "Please use this command in the contest group.")
        return
    if contest_active:
        bot.reply_to(message, "A contest is already running!")
        return

    contest_active = True
    # Post each meme in the contest topic with a vote button
    for meme in memes:
        # Create an inline keyboard with a single "Vote" button starting at 0 votes
        keyboard = telebot.types.InlineKeyboardMarkup()
        vote_button = telebot.types.InlineKeyboardButton(f"👍 Vote 0", callback_data=f"vote_{meme['id']}")
        keyboard.add(vote_button)
        # Send the meme to the group topic. If it's an image, use send_photo; for text, could use send_message.
        bot.send_photo(chat_id=GROUP_ID, photo=meme['url'], caption=meme['caption'],
                       reply_markup=keyboard, message_thread_id=THREAD_ID)
    # Acknowledge the contest started
    bot.reply_to(message, "🎉 Contest started! Vote for your favorite meme above by clicking the buttons.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
    # This function is called whenever an inline button with callback_data starting with "vote_" is pressed.
    if not contest_active:
        bot.answer_callback_query(call.id, "❗ Contest is not active right now.")
        return

    user_id = call.from_user.id
    meme_id = int(call.data.split("_")[1])  # extract the meme id from callback data, e.g. "vote_2" -> 2

    # Find the meme that was voted for
    for meme in memes:
        if meme['id'] == meme_id:
            # Prevent the same user from voting multiple times on the same meme
            if user_id in meme['voters']:
                bot.answer_callback_query(call.id, "✅ You already voted for this meme.")
            else:
                meme['voters'].add(user_id)
                meme['votes'] += 1
                # Update the button text to reflect the new vote count
                new_button = telebot.types.InlineKeyboardButton(f"👍 Vote {meme['votes']}", callback_data=call.data)
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=telebot.types.InlineKeyboardMarkup().add(new_button))
                bot.answer_callback_query(call.id, "✅ Vote recorded!")
            break

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    if not contest_active:
        bot.reply_to(message, "No contest is running at the moment.")
        return
    # Compile the leaderboard
    result_text = "🏆 *Contest Leaderboard:* 🏆\n\n"
    # Sort memes by votes (descending)
    sorted_memes = sorted(memes, key=lambda m: m['votes'], reverse=True)
    for m in sorted_memes:
        result_text += f"{m['caption']}: *{m['votes']}* votes\n"
    # Send the leaderboard (Markdown for bold numbers)
    bot.reply_to(message, result_text, parse_mode="Markdown")

@bot.message_handler(commands=['endcontest'])
def end_contest(message):
    global contest_active
    if not contest_active:
        bot.reply_to(message, "There is no active contest to end.")
        return

    # End the contest
    contest_active = False
    # Determine the winner and final standings
    sorted_memes = sorted(memes, key=lambda m: m['votes'], reverse=True)
    winner = sorted_memes[0]
    result_text = "🎉 **Contest Ended! Final Results:** 🎉\n\n"
    for m in sorted_memes:
        result_text += f"{m['caption']}: *{m['votes']}* votes\n"
    result_text += f"\n🏅 **Winner:** {winner['caption']} with *{winner['votes']}* votes! 🏅"
    bot.reply_to(message, result_text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    """
    Whenever you DM this bot a photo, it will reply with that photo’s file_id.
    """
    # Telegram sends multiple sizes; take the largest one
    file_id = message.photo[-1].file_id
    bot.reply_to(message, f"📎 file_id:\n`{file_id}`", parse_mode="Markdown")


# === 3. Webhook Setup ===

# Route for Telegram webhook POST requests
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    """Process incoming updates from Telegram"""
    data = request.get_json()  # raw update JSON

    # DEBUG: if someone sends a photo, reply with its file_id
    if 'message' in data and 'photo' in data['message']:
        photo_sizes = data['message']['photo']
        file_id = photo_sizes[-1]['file_id']  # largest size
        chat_id = data['message']['chat']['id']
        # send back the file_id so you can copy it
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"Here is the file_id:\n`{file_id}`",
            "parse_mode": "Markdown"
        })

    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        # Feed this update to the TeleBot
        bot.process_new_updates([update])
    return "OK", 200

# A simple index route for health check or root URL
@app.route('/')
def index():
    return "Bot is alive!", 200

# Start the Flask server with webhook enabled
if __name__ == "__main__":
    # Remove any previous webhook (just in case)
    bot.remove_webhook()
    # Set new webhook to the URL of our Render app + BOT_TOKEN path
    WEBHOOK_URL = "https://meme-contest-bot.onrender.com/" + BOT_TOKEN
    bot.set_webhook(url=WEBHOOK_URL)
    # Run Flask web server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
