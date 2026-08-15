import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

# Mini Server Web per soddisfare l'Health Check del piano GRATUITO (Web Service) di Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot Telegram Amazon Online 24/7!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server attivo sulla porta {port}")
    server.serve_forever()

def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("\n⚠️ TELEGRAM_BOT_TOKEN non impostato nelle variabili d'ambiente cloud!\n")
        return

    # Avvia il server HTTP in un thread separato per abilitare il piano FREE su Render
    threading.Thread(target=run_health_check_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

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

    print("Bot Amazon avviato ed in ascolto 24/7 nel Cloud (Piano Free)...")
    app.run_polling()

if __name__ == "__main__":
    main()

