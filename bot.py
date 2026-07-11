import os
import logging
from flask import Flask
from threading import Thread
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)

# --- CONFIGURATION ---
TOKEN = '8941926536:AAFQgl0vpk16eJTrLaSDuoFOjLMyHAogrI8'
ADMIN_IDS = [8859978464, 1411115615] 

# --- WEB SERVER (Keeps the bot awake) ---
app_server = Flask(__name__)
@app_server.route('/')
def home():
    return "Bot is alive and running!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app_server.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
CHOOSING, DEPOSIT_INSTRUCTION, UPLOADING = range(3)
logging.basicConfig(level=logging.INFO)

async def forward_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only forward if the sender is NOT an admin
    if update.effective_user.id in ADMIN_IDS:
        return
    
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.forward_message(
                chat_id=admin_id, 
                from_chat_id=update.effective_chat.id, 
                message_id=update.effective_message.message_id
            )
        except Exception as e:
            logging.error(f"Forwarding failed to {admin_id}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_all_messages(update, context)
    reply_keyboard = [['Vantage', 'XM']]
    await update.message.reply_text("Welcome! Please choose a platform:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CHOOSING

async def choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_all_messages(update, context)
    user_choice = update.message.text
    if user_choice not in ['Vantage', 'XM']:
        await update.message.reply_text("Invalid selection. Please use the buttons.")
        return CHOOSING
    
    context.user_data['platform'] = user_choice
    steps = "📌 Vantage details..." if user_choice == 'Vantage' else "📌 XM details..."
    await update.message.reply_text(f"{steps}\n\nMinimum deposit is 100 USD. Reply 'OK' to confirm.")
    return DEPOSIT_INSTRUCTION

async def deposit_ack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_all_messages(update, context)
    if update.message.text.upper() == 'OK':
        await update.message.reply_text("Please upload your deposit screenshot.")
        return UPLOADING
    await update.message.reply_text("Please reply 'OK' to proceed.")
    return DEPOSIT_INSTRUCTION

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_all_messages(update, context)
    await update.message.reply_text("Thank you! Please fill this form: https://forms.gle/XY3QQGosPehAkK6M6")
    return ConversationHandler.END

if __name__ == '__main__':
    # Start web server
    Thread(target=run_web_server, daemon=True).start()
    
    # Start bot
    app_bot = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice)],
            DEPOSIT_INSTRUCTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_ack)],
            UPLOADING: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, upload)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
    )
    app_bot.add_handler(conv_handler)
    app_bot.run_polling()