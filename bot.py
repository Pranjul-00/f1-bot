import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables from .env file
load_dotenv()

# Enable logging so we can see any errors in the terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🏎️ Welcome to the F1 Bot! 🏎️\n\n"
        "I'm currently under development, but soon I'll be able to fetch "
        "race schedules, standings, and telemetry!\n\n"
        "Try typing /help to see what I can do."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this message\n\n"
        "More commands coming soon!"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

if __name__ == '__main__':
    # Retrieve the token from the .env file
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("Error: Please set the TELEGRAM_BOT_TOKEN in your .env file.")
        exit(1)

    # Create the application and pass it your bot's token.
    app = ApplicationBuilder().token(token).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("Bot is starting... Press Ctrl+C to stop.")
    # Run the bot until the user presses Ctrl-C
    app.run_polling()
