import os
import logging
import fastf1
import datetime
import json
from zoneinfo import ZoneInfo, available_timezones
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

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

# Common regions for timezone selection
REGIONS = ["Africa", "America", "Asia", "Atlantic", "Australia", "Europe", "Indian", "Pacific", "UTC"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🏎️ Welcome to the F1 Bot! 🏎️\n\n"
        "I can help you keep track of race schedules, standings, and telemetry!\n\n"
        "Try these commands:\n"
        "/next - Get the upcoming race schedule\n"
        "/settimezone - Select your local timezone from a list\n"
        "/help - Show all available commands"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the interactive timezone selection process."""
    keyboard = []
    # Create buttons for regions in 2 columns
    for i in range(0, len(REGIONS), 2):
        row = [InlineKeyboardButton(REGIONS[i], callback_data=f"region_{REGIONS[i]}")]
        if i + 1 < len(REGIONS):
            row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"region_{REGIONS[i+1]}"))
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select your region:", reply_markup=reply_markup)

async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle region and timezone selections."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("region_"):
        region = data.split("_")[1]
        
        if region == "UTC":
            await finalize_timezone(update, "UTC")
            return

        # Find timezones in this region
        tzs = sorted([tz for tz in available_timezones() if tz.startswith(region + "/")])
        
        # If too many, just show a few common ones or paginate? 
        # For simplicity, let's show the first 20 and a message.
        keyboard = []
        limit = 20
        for i in range(0, min(len(tzs), limit), 2):
            row = [InlineKeyboardButton(tzs[i].split("/")[-1], callback_data=f"tz_{tzs[i]}")]
            if i + 1 < len(tzs) and i + 1 < limit:
                row.append(InlineKeyboardButton(tzs[i+1].split("/")[-1], callback_data=f"tz_{tzs[i+1]}"))
            keyboard.append(row)
        
        # Add a "Back" button
        keyboard.append([InlineKeyboardButton("⬅️ Back to Regions", callback_data="back_to_regions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"Select your city in {region}:"
        if len(tzs) > limit:
            text += f"\n(Showing first {limit} - if yours isn't here, use `/settimezone Name`)"
            
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    elif data == "back_to_regions":
        keyboard = []
        for i in range(0, len(REGIONS), 2):
            row = [InlineKeyboardButton(REGIONS[i], callback_data=f"region_{REGIONS[i]}")]
            if i + 1 < len(REGIONS):
                row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"region_{REGIONS[i+1]}"))
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select your region:", reply_markup=reply_markup)

    elif data.startswith("tz_"):
        tz_name = data.split("_", 1)[1]
        await finalize_timezone(update, tz_name)

async def finalize_timezone(update: Update, tz_name: str):
    """Save the selected timezone and inform the user."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    prefs = load_prefs()
    prefs[user_id] = {'timezone': tz_name}
    save_prefs(prefs)
    
    await query.edit_message_text(text=f"✅ Timezone set to *{tz_name}*. Your `/next` results will now be localized!", parse_mode='Markdown')

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
                    if session_time_utc.tzinfo is None:
                        session_time_utc = session_time_utc.replace(tzinfo=datetime.timezone.utc)
                    
                    local_time = session_time_utc.astimezone(user_tz)
                    # Changed to 12-hour format with AM/PM
                    time_str = local_time.strftime('%a %I:%M %p')
                    
                    line = f"• {session_name}: {time_str}"
                    
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
        "/next - Get the upcoming race schedule with local times (12h format) and countdown\n"
        "/settimezone - Select your timezone from an interactive menu\n"
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
    app.add_handler(CallbackQueryHandler(timezone_callback))

    print("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling()
