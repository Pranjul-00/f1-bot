import os
import logging
import fastf1
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Enable cache for fastf1
if not os.path.exists('fastf1_cache'):
    os.makedirs('fastf1_cache')
fastf1.Cache.enable_cache('fastf1_cache')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🏎️ Welcome to the F1 Bot! 🏎️\n\n"
        "I can help you keep track of race schedules, standings, and telemetry!\n\n"
        "Try these commands:\n"
        "/next - Get the upcoming race schedule\n"
        "/help - Show all available commands"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def next_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and send the upcoming F1 race schedule."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Checking the calendar... 🏁")
    
    try:
        # Get remaining events for the current year
        remaining = fastf1.get_events_remaining()
        
        if remaining.empty:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="The season has ended! Check back soon for the next year's schedule."
            )
            return

        next_event = remaining.iloc[0]
        event_name = next_event['EventName']
        event_date = next_event['EventDate'].strftime('%Y-%m-%d')
        
        schedule_text = f"📍 *Next Event: {event_name}*\n📅 Date: {event_date}\n\n*Schedule (UTC):*\n"
        
        # Build the schedule string dynamically
        for i in range(1, 6):
            name_key = f'Session{i}'
            date_key = f'Session{i}DateUtc'
            
            if name_key in next_event and next_event[name_key]:
                session_name = next_event[name_key]
                session_time = next_event[date_key]
                if session_time and not isinstance(session_time, float):  # Check if it's a valid time object
                    time_str = session_time.strftime('%a %H:%M')
                    schedule_text += f"• {session_name}: {time_str}\n"

        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=schedule_text,
            parse_mode='Markdown'
        )

    except Exception as e:
        logging.error(f"Error in /next: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Sorry, I had trouble fetching the schedule. Please try again later."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/next - Get the upcoming race schedule\n"
        "/help - Show this message\n\n"
        "More data features coming soon!"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("Error: Please set the TELEGRAM_BOT_TOKEN in your .env file.")
        exit(1)

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("next", next_race))

    print("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling()
