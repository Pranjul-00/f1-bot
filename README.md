# F1 Telegram Bot 🏎️🤖

A personal Telegram bot to keep track of Formula 1 race schedules, standings, results, and telemetry data on the go.

## Features
- **🏎️ Next Race**: Get the upcoming race weekend schedule converted to your local time with a countdown to the next session.
- **🏎️ Latest Results**: View the top 10 finishers of the most recent Grand Prix.
- **🏆 Standings**: View current Driver and Constructor championship points.
- **🌍 Smart Timezone**: Interactive menu to set your timezone by country (including multi-zone support for USA/Australia/Canada) or fuzzy search by city.
- **📱 Tap Interface**: Persistent reply keyboard menu for easy navigation without typing.

## Planned Features
- **📊 Telemetry Comparison**: Fetch speed vs distance graphs for driver comparisons using FastF1.
- **🔔 Race Alerts**: Proactive notifications before sessions start.

## Tech Stack
- **Python 3.12**
- **python-telegram-bot**: Telegram API integration.
- **FastF1**: Deep F1 data and telemetry.
- **Jolpica API**: Race results and standings (Ergast successor).
- **RapidFuzz**: Fuzzy matching for timezone searching.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/f1-bot.git
   cd f1-bot
   ```

2. **Setup Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   - Create a `.env` file:
     ```env
     TELEGRAM_BOT_TOKEN=your_bot_token_here
     ```

4. **Run the Bot:**
   ```bash
   python bot.py
   ```

## Security & Safety
- **No Secrets**: API tokens are managed via `.env` and excluded from git.
- **User Privacy**: Timezone preferences are stored locally in `user_prefs.json` (excluded from git).
- **Caching**: Uses `fastf1_cache/` to reduce API load.
