import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configurations
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@your_channel_username")

# Min discount percentage to trigger notification (e.g., 10 means >= 10% price drop)
MIN_DISCOUNT_PERCENT = float(os.getenv("MIN_DISCOUNT_PERCENT", "5.0"))

# Check interval in minutes
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

# Database path
DB_PATH = os.getenv("DB_PATH", "amazon_tracker.db")

# User Agent per lo scraping Amazon
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
