import os
import logging
import fastf1
import datetime
import json
from zoneinfo import ZoneInfo, available_timezones
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

# Simple JSON storage for user preferences
PREFS_FILE = 'user_prefs.json'

def load_prefs():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_prefs(prefs):
    with open(PREFS_FILE, 'w') as f:
        json.dump(prefs, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🏎️ Welcome to the F1 Bot! 🏎️\n\n"
        "I can help you keep track of race schedules, standings, and telemetry!\n\n"
        "Try these commands:\n"
        "/next - Get the upcoming race schedule\n"
        "/settimezone <name> - Set your local timezone (e.g., Asia/Kolkata)\n"
        "/help - Show all available commands"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow users to set their local timezone."""
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please provide a timezone name. Example: `/settimezone Asia/Kolkata`",
            parse_mode='Markdown'
        )
        return

    tz_name = context.args[0]
    if tz_name not in available_timezones():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ '{tz_name}' is not a valid timezone. Please use a valid IANA name like `Europe/London` or `America/New_York`.",
            parse_mode='Markdown'
        )
        return

    user_id = str(update.effective_user.id)
    prefs = load_prefs()
    prefs[user_id] = {'timezone': tz_name}
    save_prefs(prefs)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Timezone set to *{tz_name}*. Your `/next` results will now be localized!",
        parse_mode='Markdown'
    )

async def get_countdown(target_time):
    """Calculate time remaining until the target time."""
    now = datetime.datetime.now(datetime.timezone.utc)
    diff = target_time - now
    
    if diff.total_seconds() < 0:
        return None
    
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    
    return " ".join(parts)

async def next_race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and send the upcoming F1 race schedule with localization and countdown."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Checking the calendar... 🏁")
    
    try:
        user_id = str(update.effective_user.id)
        prefs = load_prefs()
        user_tz_name = prefs.get(user_id, {}).get('timezone', 'UTC')
        user_tz = ZoneInfo(user_tz_name)

        remaining = fastf1.get_events_remaining()
        
        if remaining.empty:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="The season has ended! Check back soon for the next year's schedule."
            )
            return

        next_event = remaining.iloc[0]
        event_name = next_event['EventName']
        
        schedule_text = f"📍 *Next Event: {event_name}*\n"
        if user_tz_name != 'UTC':
            schedule_text += f"🌍 Timezone: {user_tz_name}\n"
        schedule_text += "\n"
        
        now = datetime.datetime.now(datetime.timezone.utc)
        countdown_shown = False

        # Build the schedule string dynamically
        for i in range(1, 6):
            name_key = f'Session{i}'
            date_key = f'Session{i}DateUtc'
            
            if name_key in next_event and next_event[name_key]:
                session_name = next_event[name_key]
                session_time_utc = next_event[date_key]
                
                if session_time_utc and not isinstance(session_time_utc, float):
                    # Ensure it's offset-aware UTC
                    if session_time_utc.tzinfo is None:
                        session_time_utc = session_time_utc.replace(tzinfo=datetime.timezone.utc)
                    
                    # Convert to user timezone
                    local_time = session_time_utc.astimezone(user_tz)
                    time_str = local_time.strftime('%a %H:%M')
                    
                    line = f"• {session_name}: {time_str}"
                    
                    # Add countdown for the first future session
                    if not countdown_shown and session_time_utc > now:
                        countdown = await get_countdown(session_time_utc)
                        if countdown:
                            line += f" *(Starts in {countdown})*"
                            countdown_shown = True
                    
                    schedule_text += line + "\n"

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
        "/next - Get the upcoming race schedule with local times and countdown\n"
        "/settimezone <name> - Set your local timezone (e.g., `Asia/Kolkata` or `Europe/Berlin`)\n"
        "/help - Show this message\n\n"
        "More data features coming soon!"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='Markdown')

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("Error: Please set the TELEGRAM_BOT_TOKEN in your .env file.")
        exit(1)

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("next", next_race))
    app.add_handler(CommandHandler("settimezone", set_timezone))

    print("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling()
