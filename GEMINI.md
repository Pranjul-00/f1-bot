# F1 Telegram Bot

## Project Overview
This is a personal Telegram bot designed to keep track of Formula 1 race schedules, standings, results, and provide telemetry data. The bot features an interactive persistent keyboard menu, smart timezone handling (including multi-zone countries via fuzzy search), and uses a modern async Python architecture.

**Main Technologies:**
- **Python 3.12**
- **python-telegram-bot:** Asynchronous Telegram API integration.
- **FastF1:** Deep F1 data and telemetry fetching.
- **Jolpica API:** Successor to Ergast API for fetching race results and standings.
- **RapidFuzz:** Used for fuzzy matching when searching for timezones.

**Architecture Details:**
- **Entry Point:** The main logic is contained within `bot.py`, which sets up the Telegram `ApplicationBuilder` and defines command/message handlers.
- **State/Storage:** 
  - User preferences (like timezones) are stored in a simple local JSON file: `user_prefs.json`.
  - FastF1 API responses are cached in the `fastf1_cache/` directory to reduce load.
- **Security:** API tokens (e.g., `TELEGRAM_BOT_TOKEN`) are managed securely via a `.env` file and are not committed to source control.

## Building and Running

**Setup:**
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

**Configuration:**
Create a `.env` file in the root directory and add your Telegram bot token:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**Running the Bot:**
Execute the main script:
```bash
python bot.py
```

## Development Conventions
- **Async Handlers:** Telegram command and callback handlers are implemented as asynchronous functions (`async def`).
- **Logging:** Standard Python `logging` is configured at the INFO level to track bot activity and errors.
- **Message Formatting:** Responses sent to Telegram heavily utilize Markdown parsing for bold text and better formatting.
- **Error Handling:** API calls (like to Jolpica) are wrapped in `try/except` blocks with appropriate error logging to avoid crashing the bot if external services fail.
- **Git Hygiene:** Ensure `.env`, `user_prefs.json`, `fastf1_cache/`, and `venv/` remain excluded from source control (verify via `.gitignore`).
