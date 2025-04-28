from flask import Flask, request
import telebot
import os
import requests
import time
import random
from collections import Counter


# === 1. Configuration ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # We will set this environment variable on Render
GROUP_ID = -1002483696025                # <- **Replace this with your group’s chat ID** (with -100 prefix)
THREAD_ID = 269755                      # <- **Replace this with your contest topic’s thread_id**

# === Voting setup ===
VOTE_SCORES     = {'🔥': 1, '😂': 2, '💀': 3}
votes           = {}   # message_id → { user_id → emoji }
user_vote_count = {}   # user_id    → number of memes they’ve voted on (max 5)
posted_memes    = {}   # remember message_ids we post, in order
user_votes = {}   # user_id → set of meme_ids they voted for


bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# In-memory storage for contest data (memes and votes)
# For example, we have a list of meme entries for the contest:
memes = [
    {"id": 1, "url": "https://i.imgur.com/5mq5ilu.jpeg", "caption": "Option 1 - Submitted by Adonis", "votes": 0, "voters": set()},
    {"id": 2, "url": "https://i.imgur.com/LryoAx6.jpeg", "caption": "Option 2 - Submitted by Sunflwr Seed", "votes": 0, "voters": set()},
    {"id": 3, "url": "https://i.imgur.com/HqrRIb9.jpeg", "caption": "Option 3 - Submitted by Philip Falana", "votes": 0, "voters": set()},
    {"id": 4, "url": "AgACAgEAAxkBAAMGaA06GDPNM0Yh760rtxFJzgdODQoAAqqsMRvBBGlEciNYC5YpdKcBAAMCAANtAAM2BA", "caption": "Option 4 - Submitted by Luis Boxeo", "votes": 0, "voters": set()},
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

    # ─── WIPE OUT OLD VOTES ─────────────
    votes.clear()
    user_vote_count.clear()
    posted_memes.clear()
    user_votes.clear()

    # ──────────────────────────────────

    contest_active = True

    for meme in memes:
        try:
            kb = telebot.types.InlineKeyboardMarkup(row_width=3)
            buttons = [
                telebot.types.InlineKeyboardButton(f"🔥 1pt", callback_data=f"🔥_{meme['id']}"),
                telebot.types.InlineKeyboardButton(f"😂 2pt", callback_data=f"😂_{meme['id']}"),
                telebot.types.InlineKeyboardButton(f"💀 3pt", callback_data=f"💀_{meme['id']}"),
            ]
            kb.add(*buttons)

            # Send the meme
            msg = bot.send_photo(
                chat_id=GROUP_ID,
                photo=meme['url'],
                caption=meme['caption'],
                reply_markup=kb,
                message_thread_id=THREAD_ID
            )

            # Record the sent message ID
            posted_memes[meme['id']] = msg.message_id

            time.sleep(0.2)  # small pause between sending

        except Exception as e:
            print(f"Error posting meme {meme['id']}: {e}")

    # Acknowledge the contest started
    bot.reply_to(message, "🎉 Contest started! Vote for your favorite meme above by clicking the buttons.")

@bot.callback_query_handler(func=lambda call: "_" in call.data and call.data.split("_")[0] in VOTE_SCORES)
def handle_vote(call):
    if not contest_active:
        return bot.answer_callback_query(call.id, "❗ Contest is not active.", show_alert=True)

    user_id = call.from_user.id
    emoji, mid_s = call.data.split("_")
    meme_id = int(mid_s)

    votes.setdefault(meme_id, {})
    user_vote_count.setdefault(user_id, 0)
    user_votes.setdefault(user_id, set())

    # Check if user already voted for this meme
    if user_id in votes[meme_id]:
        return bot.answer_callback_query(call.id, "⚠️ You've already voted for this meme!")

    # Check if user has used all 5 votes
    if user_vote_count[user_id] >= 5:
        return bot.answer_callback_query(call.id, "❌ You've used all 5 votes!", show_alert=True)

    # Record the vote
    votes[meme_id][user_id] = emoji
    user_vote_count[user_id] += 1
    user_votes[user_id].add(meme_id)

    bot.answer_callback_query(call.id, f"✅ You voted {emoji}!", show_alert=True)


def offer_unvote_options(call, user_id, new_meme_id, new_emoji):
    keyboard = telebot.types.InlineKeyboardMarkup()

    for old_meme_id in user_votes[user_id]:
        caption = next(m['caption'] for m in memes if m['id'] == old_meme_id)
        button = telebot.types.InlineKeyboardButton(
            f"Unvote {caption}",
            callback_data=f"unvote_{old_meme_id}_{new_meme_id}_{new_emoji}"
        )
        keyboard.add(button)

    bot.send_message(
        call.message.chat.id,
        "🚨 You've already used all 5 votes! Choose a meme to unvote first:",
        reply_markup=keyboard,
        message_thread_id=THREAD_ID
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("unvote_"))
def handle_unvote(call):
    if not contest_active:
       return bot.answer_callback_query(call.id, "❗ Contest is not active.", show_alert=True)


    user_id = call.from_user.id
    parts = call.data.split("_")
    old_meme_id = int(parts[1])
    new_meme_id = int(parts[2])
    new_emoji = parts[3]

    # Remove old vote
    if user_id in votes.get(old_meme_id, {}):
        del votes[old_meme_id][user_id]
        user_vote_count[user_id] -= 1
        user_votes[user_id].remove(old_meme_id)

    # Record new vote
    votes.setdefault(new_meme_id, {})
    votes[new_meme_id][user_id] = new_emoji
    user_vote_count[user_id] += 1
    user_votes[user_id].add(new_meme_id)

    bot.answer_callback_query(call.id, "✅ Vote changed successfully!", show_alert=True)


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
                bot.answer_callback_query(call.id, "✅ You already voted for this meme.", show_alert=True)
            else:
                meme['voters'].add(user_id)
                meme['votes'] += 1
                # Update the button text to reflect the new vote count
                
                bot.answer_callback_query(call.id, "✅ Vote recorded!", show_alert=True)
            break

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    if not contest_active:
        bot.reply_to(message, "No contest is running at the moment.")
        return

    if not posted_memes:
        bot.reply_to(message, "No memes posted yet!")
        return

    result_text = "🏆 *Current Leaderboard:*\n\n"

    scores = {}
    for meme in memes:
        meme_id = meme['id']
        meme_votes = votes.get(meme_id, {})
        total = 0
        for emoji_list in meme_votes.values():
            for emoji in emoji_list:
                total += VOTE_SCORES.get(emoji, 0)
        scores[meme_id] = total


    # First, group memes by score
    score_groups = {}
    for meme_id, score in scores.items():
        score_groups.setdefault(score, []).append(meme_id)

    # Then, sort scores descending
    sorted_scores = sorted(score_groups.keys(), reverse=True)

    # Now build a fully sorted list with tiebreakers
    ranked = []
    for score in sorted_scores:
        tied_memes = score_groups[score]

        if len(tied_memes) == 1:
            # No tie, just add
            ranked.append((tied_memes[0], score))
        else:
            # Tie, break it by heavier votes
            def tiebreaker_key(meme_id):
                meme_votes = votes.get(meme_id, {})
                count = Counter()
                for emoji_list in meme_votes.values():
                    for emoji in emoji_list:
                        count[emoji] += 1
                return (
                    count.get('💀', 0),  # prioritize 💀
                    count.get('😂', 0),  # then 😂
                    count.get('🔥', 0)   # then 🔥
                )
            tied_sorted = sorted(tied_memes, key=tiebreaker_key, reverse=True)
            for meme_id in tied_sorted:
                ranked.append((meme_id, score))
    

    for rank, (meme_id, score) in enumerate(ranked, 1):
        caption = next(m['caption'] for m in memes if m['id'] == meme_id)
        result_text += f"{rank}. {caption} — *{score}* pts\n"

    result_text += "\n\n📝 _Note: Ties are broken by counting the number of higher-weighted emoji votes (💀 > 😂 > 🔥)._"
    bot.reply_to(message, result_text, parse_mode="Markdown")


@bot.message_handler(commands=['endcontest'])
def end_contest(message):
    global contest_active

    if not contest_active:
        bot.reply_to(message, "There is no active contest to end.")
        return

    contest_active = False

    if not posted_memes:
        bot.reply_to(message, "No memes were posted.")
        return

    scores = {}
    for meme in memes:
        meme_id = meme['id']
        meme_votes = votes.get(meme_id, {})
        total = 0
        for emoji_list in meme_votes.values():
            for emoji in emoji_list:
                total += VOTE_SCORES.get(emoji, 0)
        scores[meme_id] = total


    # First, group memes by score
    score_groups = {}
    for meme_id, score in scores.items():
        score_groups.setdefault(score, []).append(meme_id)

    # Then, sort scores descending
    sorted_scores = sorted(score_groups.keys(), reverse=True)

    # Now build a fully sorted list with tiebreakers
    ranked = []
    for score in sorted_scores:
        tied_memes = score_groups[score]

        if len(tied_memes) == 1:
            ranked.append((tied_memes[0], score))
        else:
            def tiebreaker_key(meme_id):
                meme_votes = votes.get(meme_id, {})
                all_emojis = []
                for emoji_list in meme_votes.values():
                    all_emojis.extend(emoji_list)
                count = Counter(all_emojis)
                return (
                    count.get('💀', 0),
                    count.get('😂', 0),
                    count.get('🔥', 0)
                )
            tied_sorted = sorted(tied_memes, key=tiebreaker_key, reverse=True)
            for meme_id in tied_sorted:
                ranked.append((meme_id, score))


    result_text = "🎉 *Contest Ended! Final Results:*\n\n"

    place_labels = ["🥇 1st Place", "🥈 2nd Place", "🥉 3rd Place"]

    for idx, (meme_id, score) in enumerate(ranked, 1):
        caption = next(m['caption'] for m in memes if m['id'] == meme_id)
        if idx <= 3:
            label = place_labels[idx-1]
            result_text += f"{label}: {caption} — *{score}* pts\n"
        else:
            result_text += f"{idx}. {caption} — *{score}* pts\n"


    # --- Smart Tiebreaker Winner Picking (💀 > 😂 > 🔥) ---

    top_score = ranked[0][1]
    top_memes = [meme_id for meme_id, score in ranked if score == top_score]

    if len(top_memes) == 1:
        winner_caption = next(m['caption'] for m in memes if m['id'] == top_memes[0])
        result_text += f"\n🏅 *Winner:* {winner_caption} — *{top_score}* pts! 🏆"
    else:
        def tiebreaker_sort_key(meme_id):
            meme_votes = votes.get(meme_id, {})
            all_emojis = []
            for emoji_list in meme_votes.values():
                all_emojis.extend(emoji_list)
            count = Counter(all_emojis)
           
            return (
                count.get('💀', 0),  # prioritize 💀 votes first
                count.get('😂', 0),  # then 😂 votes
                count.get('🔥', 0)   # then 🔥 votes
            )

        # Sort tied memes by heavier votes first
        top_memes_sorted = sorted(top_memes, key=tiebreaker_sort_key, reverse=True)

        winner_id = top_memes_sorted[0]
        winner_caption = next(m['caption'] for m in memes if m['id'] == winner_id)

        result_text += f"\n🏅 *Winner (Tiebreaker: Heaviest Votes!)* {winner_caption} — *{top_score}* pts! 🏆"


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
