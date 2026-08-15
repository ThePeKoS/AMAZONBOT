import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from database import DatabaseManager
from amazon_tracker import extract_asin, fetch_amazon_product
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, MIN_DISCOUNT_PERCENT
from deduplicator import is_asin_already_sent, mark_asin_as_sent

logger = logging.getLogger(__name__)
db = DatabaseManager()

# In-Memory Cache degli ASIN già pubblicati nel canale per prevenire duplicati
SENT_ASINS_CACHE = set()

def detect_category_hashtag(title: str) -> str:
    """Rileva la categoria dal titolo del prodotto e restituisce gli Hashtag correlati."""
    title_lower = title.lower()
    hashtags = []
    
    if any(k in title_lower for k in ["ps5", "ps4", "playstation", "xbox", "nintendo", "gaming", "console", "joystick"]):
        hashtags.append("#Gaming")
    if any(k in title_lower for k in ["pc", "laptop", "notebook", "ram", "ssd", "monitor", "tastiera", "mouse", "computer", "intel", "amd"]):
        hashtags.append("#Informatica")
    if any(k in title_lower for k in ["smartphone", "iphone", "samsung", "xiaomi", "redmi", "auricolari", "cuffie", "smartwatch"]):
        hashtags.append("#Elettronica")
    if any(k in title_lower for k in ["tv", "smart tv", "soundbar", "altoparlante", "speaker", "proiettore"]):
        hashtags.append("#Tech")
    if any(k in title_lower for k in ["casa", "cucina", "robot", "aspirapolvere", "friggitrice", "macchina caffe"]):
        hashtags.append("#Casa")

    if not hashtags:
        hashtags.append("#OffertaAmazon")

    return " ".join(hashtags)

def format_deal_message(deal_info: dict) -> str:
    """Formatta il messaggio dell'offerta per il canale o la chat con uno stile ricco ed hashtag."""
    title = deal_info['title']
    current_price = deal_info['current_price']
    previous_price = deal_info['previous_price']
    discount = deal_info['discount_percent']
    url = deal_info['url']
    hashtags = detect_category_hashtag(title)

    msg = (
        f"🔥 **SUPER OFFERTA AMAZON (-{discount:.0f}%)** 🔥\n\n"
        f"📦 **{title[:120]}...**\n\n"
        f"❌ Prezzo precedente: ~~{previous_price:.2f}€~~\n"
        f"✅ **Nuovo Prezzo: {current_price:.2f}€**\n"
        f"📉 **Risparmi: {(previous_price - current_price):.2f}€ (-{discount:.0f}%)**\n\n"
        f"{hashtags}\n\n"
        f"🔗 [Acquista ora su Amazon]({url})"
    )
    return msg

async def send_deal_to_channel(context: ContextTypes.DEFAULT_TYPE, deal_info: dict):
    """Invia il post di offerta al canale Telegram specificato evitando i duplicati."""
    asin = deal_info.get("asin")
    current_price = deal_info.get("current_price", 0.0)

    # 1. Controllo in-memory locker
    if asin and is_asin_already_sent(asin):
        logger.info(f"🚫 [BLOCKED DUP] ASIN {asin} già inviato al canale.")
        return

    # 2. Controllo database locale
    if asin and db.is_deal_already_sent(asin, current_price):
        mark_asin_as_sent(asin)
        logger.info(f"🚫 [DB BLOCKED DUP] ASIN {asin} registrato nel DB come già pubblicato.")
        return

    text = format_deal_message(deal_info)
    image_url = deal_info.get("image_url")
    
    reply_markup = None
    if deal_info.get("url"):
        keyboard = [[InlineKeyboardButton("🛒 Vai all'Offerta", url=deal_info["url"])]]
        reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if image_url:
            await context.bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=image_url,
                caption=text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                read_timeout=30.0,
                write_timeout=30.0,
                connect_timeout=30.0
            )
        else:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                read_timeout=30.0,
                write_timeout=30.0,
                connect_timeout=30.0
            )
        
        # Segna l'ASIN nel memory locker e nel DB
        if asin:
            mark_asin_as_sent(asin)
            db.mark_deal_as_sent(asin, current_price)

        logger.info(f"✅ Offerta inviata al canale per ASIN {deal_info['asin']}")
    except Exception as e:
        logger.error(f"Errore durante l'invio al canale Telegram: {e}")



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Risposta al comando /start"""
    await update.message.reply_text(
        "👋 **Benvenuto nel Bot Amazon Price Tracker!**\n\n"
        "Ecco come ottenere ed inviare i prodotti scontati sul tuo canale:\n\n"
        "1️⃣ **Aggiunta Manuale:**\n"
        "🔹 `/add <url_o_asin>` - Aggiungi un singolo prodotto da monitorare\n"
        "   *(Es: `/add B08N5WRWNW` oppure incollando l'URL Amazon)*\n\n"
        "2️⃣ **Scansione Automatica Offerte Amazon:**\n"
        "🔥 `/scan_deals` - Cerca automaticamente i prodotti in offerta su Amazon e li aggiunge al tracciamento!\n\n"
        "3️⃣ **Gestione e Controllo:**\n"
        "📋 `/list` - Lista dei prodotti attualmente in monitoraggio\n"
        "🗑️ `/remove <asin>` - Rimuovi un prodotto dal monitoraggio\n"
        "🚀 `/check` - Effettua subito la verifica prezzi ed invia le offerte rilevate sul Canale Telegram!",
        parse_mode="Markdown"
    )

async def scan_deals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cerca ed aggiunge automaticamente le offerte del giorno su Amazon."""
    await update.message.reply_text("🔍 **Ricerca in corso delle migliori offerte del giorno su Amazon...**\nAttendere qualche secondo.", parse_mode="Markdown")
    
    from amazon_deals_scraper import fetch_popular_deals
    deals = fetch_popular_deals(limit=10)

    if not deals:
        await update.message.reply_text("⚠️ Nessuna nuova offerta automatica trovata al momento. Puoi aggiungere prodotti manualmente con `/add <link>`.", parse_mode="Markdown")
        return

    added_count = 0
    msg = "🔥 **Prodotti trovati in offerta ed aggiunti al tracciamento:**\n\n"

    for d in deals:
        res = db.add_or_update_product(
            asin=d["asin"],
            title=d["title"],
            url=d["url"],
            image_url=d["image_url"],
            price=d["price"]
        )
        added_count += 1
        msg += f"• **{d['title'][:50]}...**\n  💰 Prezzo: **{d['price']:.2f}€** | ASIN: `{d['asin']}`\n\n"

    msg += f"✅ **Aggiunti {added_count} prodotti al database!**\nUsa `/check` per inviarli sul tuo canale Telegram."
    await update.message.reply_text(msg, parse_mode="Markdown")


async def add_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiunge un nuovo prodotto dal comando /add <link_o_asin>"""
    if not context.args:
        await update.message.reply_text("⚠️ Per favore specifica l'URL o l'ASIN del prodotto Amazon.\nEsempio: `/add B08N5WRWNW`", parse_mode="Markdown")
        return

    user_input = context.args[0]
    asin = extract_asin(user_input)

    if not asin:
        await update.message.reply_text("❌ ASIN o URL Amazon non valido.")
        return

    await update.message.reply_text(f"🔍 Recupero informazioni per l'ASIN `{asin}`...", parse_mode="Markdown")
    product_data = fetch_amazon_product(asin)

    if not product_data:
        await update.message.reply_text("❌ Impossibile recuperare le informazioni del prodotto Amazon. Verifica il link.")
        return

    result = db.add_or_update_product(
        asin=product_data["asin"],
        title=product_data["title"],
        url=product_data["url"],
        image_url=product_data["image_url"],
        price=product_data["price"]
    )

    await update.message.reply_text(
        f"✅ Prodotto registrato con successo!\n\n"
        f"📌 **Titolo:** {result['title']}\n"
        f"💰 **Prezzo Attuale:** {result['current_price']:.2f}€",
        parse_mode="Markdown"
    )

async def list_products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elenca tutti i prodotti salvati."""
    products = db.get_all_products()
    if not products:
        await update.message.reply_text("📭 Nessun prodotto attualmente monitorato.")
        return

    msg = "📋 **Prodotti Attualmente Monitorati:**\n\n"
    for p in products:
        msg += f"• **ASIN:** `{p['asin']}` | 💰 **Prezzo:** {p['current_price']:.2f}€\n  {p['title'][:60]}...\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def remove_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rimuove un prodotto tramite /remove <asin>"""
    if not context.args:
        await update.message.reply_text("⚠️ Specifica l'ASIN da rimuovere: `/remove B08N5WRWNW`", parse_mode="Markdown")
        return

    asin = context.args[0].upper()
    success = db.remove_product(asin)
    if success:
        await update.message.reply_text(f"🗑️ Prodotto `{asin}` rimosso dal tracciamento.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Prodotto `{asin}` non trovato nel database.", parse_mode="Markdown")

async def check_prices_job(context: ContextTypes.DEFAULT_TYPE):
    """Job periodico per la scansione automatica di TUTTE le super offerte Amazon ed invio al canale."""
    logger.info("🔥 Avvio della scansione globale Super Offerte e Sconti Amazon...")
    
    from amazon_super_deals import scan_all_super_deals
    # Scansiona Amazon filtrando solo i prodotti con sconti elevati (es. >= MIN_DISCOUNT_PERCENT %)
    super_deals = scan_all_super_deals(min_discount_filter=MIN_DISCOUNT_PERCENT, max_results=20)

    logger.info(f"Trovate {len(super_deals)} super offerte su Amazon!")

    for deal in super_deals:
        # Invia direttamente il post al Canale Telegram
        await send_deal_to_channel(context, deal)

async def force_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Avvia manualmente la scansione globale dei Super Sconti Amazon ed invio al Canale"""
    await update.message.reply_text("🔥 **Scansione globale di TUTTE le Super Offerte Amazon avviata...**\nIl bot cercherà i prodotti con i maggiori sconti e li pubblicherà sul Canale!", parse_mode="Markdown")
    await check_prices_job(context)
    await update.message.reply_text("✅ **Scansione completata! Le offerte migliori sono state inviate sul canale.**", parse_mode="Markdown")

