# F1 Telegram Bot

A personal Telegram bot to keep track of Formula 1 race schedules, standings, and telemetry data on the go. Powered by Python, `python-telegram-bot`, and the `fastf1` library.

## Features (Planned)
- **/next**: Get upcoming race schedules converted to local time.
- **/standings**: View current driver and constructor championship points.
- **/compare [driver1] [driver2]**: Fetch telemetry comparisons (Speed vs Distance) for specific drivers.
- **Race Alerts**: Proactive notifications before qualifying or the race starts.

## Tech Stack
- **Python 3.12**
- **python-telegram-bot**: To handle the Telegram API interactions.
- **FastF1**: For fetching and plotting F1 telemetry and timing data.
- **python-dotenv**: For securely managing API tokens.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd f1-bot
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Environment Variables:**
   - Create a file named `.env` in the root directory.
   - Add your Telegram Bot Token (obtained from BotFather):
     ```env
     TELEGRAM_BOT_TOKEN=your_token_here
     ```

5. **Run the bot:**
   ```bash
   python bot.py
   ```

## Development Progress
- [x] Initialized project structure and repository.
- [ ] Created basic Telegram bot structure.
- [ ] Integrated FastF1 for basic commands.
- [ ] Deployed bot to a server (Optional).
