import os
import logging
import fastf1
import datetime
import json
from zoneinfo import ZoneInfo, available_timezones
from rapidfuzz import process, utils
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

# Filter out technical and deprecated timezones for a cleaner list
CLEAN_TZS = sorted([
    tz for tz in available_timezones() 
    if not any(x in tz for x in ["Etc/", "SystemV/", "posix", "right", "US/", "Canada/", "Brazil/", "Mexico/"])
    and "/" in tz  # Keep only Continent/City format
])

REGIONS = sorted(list(set([tz.split("/")[0] for tz in CLEAN_TZS])))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🏎️ Welcome to the F1 Bot! 🏎️\n\n"
        "I can help you keep track of race schedules, standings, and telemetry!\n\n"
        "Try these commands:\n"
        "/next - Get the upcoming race schedule\n"
        "/settimezone - Search for or select your timezone\n"
        "/help - Show all available commands"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for a timezone or show the region selection menu."""
    if context.args:
        # User is searching for a timezone (e.g., /settimezone London)
        search_query = " ".join(context.args)
        
        # Use fuzzy matching to find the best 5 matches
        matches = process.extract(
            search_query, 
            CLEAN_TZS, 
            processor=utils.default_process,
            limit=5
        )
        
        keyboard = []
        for match_str, score, index in matches:
            # Match is (string, score, index)
            keyboard.append([InlineKeyboardButton(match_str, callback_data=f"tz_{match_str}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_tz")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"I found these matches for '{search_query}':", 
            reply_markup=reply_markup
        )
        return

    # No arguments? Show the region menu
    keyboard = []
    for i in range(0, len(REGIONS), 2):
        row = [InlineKeyboardButton(REGIONS[i], callback_data=f"region_{REGIONS[i]}")]
        if i + 1 < len(REGIONS):
            row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"region_{REGIONS[i+1]}"))
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select your region or type `/settimezone YourCity` to search:", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle region and timezone selections."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "cancel_tz":
        await query.edit_message_text("Timezone selection cancelled.")
        return

    if data.startswith("region_"):
        region = data.split("_")[1]
        
        # Find timezones in this region
        tzs = sorted([tz for tz in CLEAN_TZS if tz.startswith(region + "/")])
        
        keyboard = []
        limit = 30 # Show more cities now
        for i in range(0, min(len(tzs), limit), 2):
            # Display name is just the city (everything after the first slash)
            display_name = tzs[i].split("/", 1)[1].replace("_", " ")
            row = [InlineKeyboardButton(display_name, callback_data=f"tz_{tzs[i]}")]
            
            if i + 1 < len(tzs) and i + 1 < limit:
                display_name_2 = tzs[i+1].split("/", 1)[1].replace("_", " ")
                row.append(InlineKeyboardButton(display_name_2, callback_data=f"tz_{tzs[i+1]}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Regions", callback_data="back_to_regions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"Select your city in {region}:"
        if len(tzs) > limit:
            text += f"\n(Showing top {limit}. If yours is missing, try `/settimezone CityName`)"
            
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    elif data == "back_to_regions":
        keyboard = []
        for i in range(0, len(REGIONS), 2):
            row = [InlineKeyboardButton(REGIONS[i], callback_data=f"region_{REGIONS[i]}")]
            if i + 1 < len(REGIONS):
                row.append(InlineKeyboardButton(REGIONS[i+1], callback_data=f"region_{REGIONS[i+1]}"))
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select your region or search with `/settimezone City`:", reply_markup=reply_markup, parse_mode='Markdown')

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
    
    await query.edit_message_text(text=f"✅ Timezone set to *{tz_name}*. Your `/next` results will now be in 12h format and localized!", parse_mode='Markdown')

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
        "/next - Get upcoming race schedule with local times and countdown\n"
        "/settimezone - Search for your city (e.g., `/settimezone London`) or pick from a list\n"
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
