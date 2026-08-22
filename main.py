import os
import sys
from telegram.ext import ApplicationBuilder, CommandHandler
from config import TELEGRAM_BOT_TOKEN, CHECK_INTERVAL_MINUTES
from telegram_bot import (
    start_command,
    add_product_command,
    scan_deals_command,
    list_products_command,
    remove_product_command,
    force_check_command,
    check_prices_job,
)

def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("\n⚠️ TELEGRAM_BOT_TOKEN non impostato nelle variabili d'ambiente cloud!\n")
        return

    # Inizializza l'applicazione Telegram Bot con timeout aumentato a 30s per i server cloud
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .get_updates_connect_timeout(30.0)
        .get_updates_read_timeout(30.0)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("add", add_product_command))
    app.add_handler(CommandHandler("scan_deals", scan_deals_command))
    app.add_handler(CommandHandler("list", list_products_command))
    app.add_handler(CommandHandler("remove", remove_product_command))
    app.add_handler(CommandHandler("check", force_check_command))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_prices_job,
            interval=CHECK_INTERVAL_MINUTES * 60,
            first=10
        )

    print("Bot Amazon avviato ed in ascolto 24/7 nel Cloud...")
    app.run_polling()

if __name__ == "__main__":
    main()
