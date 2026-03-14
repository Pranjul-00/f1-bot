import os
import logging
import fastf1
import datetime
import json
import requests
from zoneinfo import ZoneInfo, available_timezones
from rapidfuzz import process, utils
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

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

# Major F1 Countries and their primary timezones
MAJOR_F1_COUNTRIES = {
    "🇮🇳 India": "Asia/Kolkata",
    "🇬🇧 UK": "Europe/London",
    "🇮🇹 Italy": "Europe/Rome",
    "🇧🇷 Brazil": "America/Sao_Paulo",
    "🇯🇵 Japan": "Asia/Tokyo",
    "🇦🇪 UAE": "Asia/Dubai",
    "🇸🇦 Saudi Arabia": "Asia/Riyadh",
    "🇸🇬 Singapore": "Asia/Singapore",
    "🇧🇭 Bahrain": "Asia/Bahrain",
    "🇦🇺 Australia": "MULTIPLE_AU",
    "🇺🇸 USA": "MULTIPLE_US",
    "🇨🇦 Canada": "MULTIPLE_CA",
    "🇲🇽 Mexico": "America/Mexico_City",
    "🇲🇨 Monaco": "Europe/Monaco",
    "🇪🇸 Spain": "Europe/Madrid",
    "🇭🇺 Hungary": "Europe/Budapest",
    "🇧🇪 Belgium": "Europe/Brussels",
    "🇳🇱 Netherlands": "Europe/Amsterdam",
    "🇦🇹 Austria": "Europe/Vienna",
    "🇦🇿 Azerbaijan": "Asia/Baku",
    "🇶🇦 Qatar": "Asia/Qatar"
}

# Sub-timezones for countries with multiple zones
SUB_TZS = {
    "MULTIPLE_AU": [
        ("Melbourne/Sydney", "Australia/Melbourne"),
        ("Perth", "Australia/Perth"),
        ("Brisbane", "Australia/Brisbane"),
        ("Adelaide", "Australia/Adelaide")
    ],
    "MULTIPLE_US": [
        ("Eastern (NY/Miami)", "America/New_York"),
        ("Central (Austin/Chicago)", "America/Chicago"),
        ("Mountain (Denver)", "America/Denver"),
        ("Pacific (Vegas/LA)", "America/Los_Angeles")
    ],
    "MULTIPLE_CA": [
        ("Eastern (Toronto)", "America/Toronto"),
        ("Western (Vancouver)", "America/Vancouver"),
        ("Atlantic (Halifax)", "America/Halifax")
    ]
}

# Main menu keyboard
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup([
    ['🏎️ Next Race', '🏎️ Latest Results'],
    ['🏆 Standings', '🌍 Set Timezone'],
    ['ℹ️ Help']
], resize_keyboard=True)

async def post_init(application):
    """Set the bot's commands menu in Telegram."""
    commands = [
        BotCommand("start", "Start the bot and show menu"),
        BotCommand("next", "Get upcoming race schedule"),
        BotCommand("results", "View last race results"),
        BotCommand("settimezone", "Search or select your timezone"),
        BotCommand("standings", "View championship standings"),
        BotCommand("help", "Show help information")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🏎️ *Welcome to the F1 Bot!* 🏎️\n\n"
        "I've added a menu at the bottom of your screen. You can now tap the buttons to navigate!\n\n"
        "If you don't see the buttons, look for a small icon with four dots in your message bar."
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=welcome_message,
        reply_markup=MAIN_MENU_KEYBOARD,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from the main menu keyboard."""
    text = update.message.text
    if text == '🏎️ Next Race':
        await next_race(update, context)
    elif text == '🏎️ Latest Results':
        await latest_results(update, context)
    elif text == '🏆 Standings':
        await standings_menu(update, context)
    elif text == '🌍 Set Timezone':
        await set_timezone(update, context)
    elif text == 'ℹ️ Help':
        await help_command(update, context)

async def latest_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and send the results of the last Grand Prix."""
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Fetching latest race results... 🏎️")
    
    url = "https://api.jolpi.ca/ergast/f1/current/last/results.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        race = data['MRData']['RaceTable']['Races'][0]
        
        race_name = race.get('raceName', 'Grand Prix')
        season = race.get('season', '')
        results = race.get('Results', [])
        
        text = f"🏁 *Results: {season} {race_name}*\n\n"
        
        for res in results[:10]: # Top 10
            pos = res.get('position', '?')
            driver = res.get('Driver', {})
            name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}"
            team = res.get('Constructor', {}).get('name', 'Unknown')
            pts = res.get('points', '0')
            
            text += f"{pos}. *{name}* - {pts} pts ({team})\n"
            
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error in latest_results: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Sorry, I couldn't fetch the latest results.")

async def standings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show buttons to choose between Driver and Constructor standings."""
    keyboard = [
        [InlineKeyboardButton("🏎️ Driver Standings", callback_data="standings_drivers")],
        [InlineKeyboardButton("🏁 Team Standings", callback_data="standings_constructors")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which standings would you like to see?", reply_markup=reply_markup)

async def fetch_standings(standings_type: str):
    """Fetch standings from Jolpica API."""
    url = f"https://api.jolpi.ca/ergast/f1/current/{standings_type}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['MRData']['StandingsTable']['StandingsLists'][0]
    except Exception as e:
        logging.error(f"Error fetching standings: {e}")
        return None

async def standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle standings selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "standings_drivers":
        data = await fetch_standings("driverStandings")
        if not data or 'DriverStandings' not in data:
            await query.edit_message_text("Sorry, I couldn't fetch the driver standings right now.")
            return
        
        standings = data['DriverStandings']
        text = f"🏆 *Driver Standings ({data.get('season', 'Current')})*\n\n"
        for entry in standings[:15]: # Show top 15
            pos = entry.get('position', '?')
            driver = entry.get('Driver', {})
            name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}"
            pts = entry.get('points', '0')
            constructors = entry.get('Constructors', [{}])
            team = constructors[0].get('name', 'Unknown')
            text += f"{pos}. *{name}* - {pts} pts ({team})\n"
        
        await query.edit_message_text(text=text, parse_mode='Markdown')

    elif query.data == "standings_constructors":
        data = await fetch_standings("constructorStandings")
        if not data or 'ConstructorStandings' not in data:
            await query.edit_message_text("Sorry, I couldn't fetch the constructor standings right now.")
            return
        
        standings = data['ConstructorStandings']
        text = f"🏁 *Constructor Standings ({data.get('season', 'Current')})*\n\n"
        for entry in standings:
            pos = entry.get('position', '?')
            constructor = entry.get('Constructor', {})
            name = constructor.get('name', 'Unknown')
            pts = entry.get('points', '0')
            wins = entry.get('wins', '0')
            text += f"{pos}. *{name}* - {pts} pts ({wins} wins)\n"
        
        await query.edit_message_text(text=text, parse_mode='Markdown')

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for a timezone or show the major F1 countries menu."""
    # Check if this was called from a command with arguments or from a button
    args = context.args if hasattr(context, 'args') else None
    
    if args:
        # User is searching for a timezone (e.g., /settimezone London)
        search_query = " ".join(args)
        
        matches = process.extract(
            search_query, 
            CLEAN_TZS, 
            processor=utils.default_process,
            limit=5
        )
        
        keyboard = []
        for match_str, score, index in matches:
            keyboard.append([InlineKeyboardButton(match_str, callback_data=f"tz_{match_str}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_tz")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"I found these matches for '{search_query}':", 
            reply_markup=reply_markup
        )
        return

    # No arguments or button tap? Show the major F1 countries menu
    keyboard = []
    countries = list(MAJOR_F1_COUNTRIES.keys())
    for i in range(0, len(countries), 2):
        row = [InlineKeyboardButton(countries[i], callback_data=f"country_{countries[i]}")]
        if i + 1 < len(countries):
            row.append(InlineKeyboardButton(countries[i+1], callback_data=f"country_{countries[i+1]}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🌐 Other (Regions List)", callback_data="back_to_regions")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select your country or type `/settimezone CityName` to search:", 
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

    if data.startswith("country_"):
        country_name = data.split("_")[1]
        tz_value = MAJOR_F1_COUNTRIES[country_name]
        
        if tz_value.startswith("MULTIPLE_"):
            options = SUB_TZS[tz_value]
            keyboard = []
            for display_name, actual_tz in options:
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"tz_{actual_tz}")])
            keyboard.append([InlineKeyboardButton("⬅️ Back to Countries", callback_data="back_to_countries")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Select your region in {country_name}:", reply_markup=reply_markup)
        else:
            await finalize_timezone(update, tz_value)

    elif data == "back_to_countries":
        keyboard = []
        countries = list(MAJOR_F1_COUNTRIES.keys())
        for i in range(0, len(countries), 2):
            row = [InlineKeyboardButton(countries[i], callback_data=f"country_{countries[i]}")]
            if i + 1 < len(countries):
                row.append(InlineKeyboardButton(countries[i+1], callback_data=f"country_{countries[i+1]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🌐 Other (Regions List)", callback_data="back_to_regions")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select your country or search with `/settimezone City`:", reply_markup=reply_markup, parse_mode='Markdown')

    elif data == "back_to_regions":
        regions = sorted(list(set([tz.split("/")[0] for tz in CLEAN_TZS])))
        keyboard = []
        for i in range(0, len(regions), 2):
            row = [InlineKeyboardButton(regions[i], callback_data=f"region_{regions[i]}")]
            if i + 1 < len(regions):
                row.append(InlineKeyboardButton(regions[i+1], callback_data=f"region_{regions[i+1]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back to Countries", callback_data="back_to_countries")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select your global region:", reply_markup=reply_markup)

    elif data.startswith("region_"):
        region = data.split("_")[1]
        tzs = sorted([tz for tz in CLEAN_TZS if tz.startswith(region + "/")])
        keyboard = []
        limit = 20
        for i in range(0, min(len(tzs), limit), 2):
            display_name = tzs[i].split("/", 1)[1].replace("_", " ")
            row = [InlineKeyboardButton(display_name, callback_data=f"tz_{tzs[i]}")]
            if i + 1 < len(tzs) and i + 1 < limit:
                display_name_2 = tzs[i+1].split("/", 1)[1].replace("_", " ")
                row.append(InlineKeyboardButton(display_name_2, callback_data=f"tz_{tzs[i+1]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back to Regions", callback_data="back_to_regions")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Select your city in {region}:", reply_markup=reply_markup)

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
    
    # Get the abbreviation (e.g., IST)
    now = datetime.datetime.now(ZoneInfo(tz_name))
    tz_abbr = now.strftime('%Z')
    
    await query.edit_message_text(
        text=f"✅ Timezone set to *{tz_name}* ({tz_abbr}). Your results will now be localized!", 
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
    # Handle both command calls and button taps
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Checking the calendar... 🏁")
    
    try:
        user_id = str(update.effective_user.id)
        prefs = load_prefs()
        user_tz_name = prefs.get(user_id, {}).get('timezone', 'UTC')
        user_tz = ZoneInfo(user_tz_name)

        remaining = fastf1.get_events_remaining()
        
        if remaining.empty:
            await context.bot.send_message(chat_id=chat_id, text="The season has ended!")
            return

        next_event = remaining.iloc[0]
        event_name = next_event['EventName']
        now_in_tz = datetime.datetime.now(user_tz)
        tz_abbr = now_in_tz.strftime('%Z')
        
        schedule_text = f"📍 *Next Event: {event_name}*\n"
        schedule_text += f"🌍 Timezone: {user_tz_name} ({tz_abbr})\n\n"
        
        now = datetime.datetime.now(datetime.timezone.utc)
        countdown_shown = False

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

        await context.bot.send_message(chat_id=chat_id, text=schedule_text, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error in /next: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="Sorry, I had trouble fetching the schedule.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Show the main menu keyboard\n"
        "/next - Get upcoming race schedule\n"
        "/results - View results of the last Grand Prix\n"
        "/settimezone - Pick or search for your timezone\n"
        "/standings - View championship standings\n\n"
        "You can also use the buttons below your message bar for quick access!"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='Markdown')

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("Error: Please set the TELEGRAM_BOT_TOKEN in your .env file.")
        exit(1)

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("next", next_race))
    app.add_handler(CommandHandler("results", latest_results))
    app.add_handler(CommandHandler("settimezone", set_timezone))
    app.add_handler(CommandHandler("standings", standings_menu))
    app.add_handler(CallbackQueryHandler(standings_callback, pattern="^standings_"))
    app.add_handler(CallbackQueryHandler(timezone_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling()
