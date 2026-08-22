import logging
import json
import os

logger = logging.getLogger(__name__)

# File di persistenza JSON per garantire che la memoria sopravviva ai riavvii dei server cloud
PERSISTENT_FILE = os.getenv("SENT_ASINS_FILE", "sent_asins.json")

def load_sent_asins() -> set:
    if os.path.exists(PERSISTENT_FILE):
        try:
            with open(PERSISTENT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"📂 Caricati {len(data)} ASIN dal file di persistenza {PERSISTENT_FILE}")
                return set(data)
        except Exception as e:
            logger.error(f"Errore caricamento file persistenza ASIN: {e}")
    return set()

def save_sent_asins():
    try:
        with open(PERSISTENT_FILE, "w", encoding="utf-8") as f:
            json.dump(list(GLOBAL_SENT_ASINS), f)
    except Exception as e:
        logger.error(f"Errore salvataggio file persistenza ASIN: {e}")

# Inizializza la memoria caricando gli ASIN storici
GLOBAL_SENT_ASINS = load_sent_asins()

def is_asin_already_sent(asin: str) -> bool:
    if not asin:
        return False
    clean_asin = asin.strip().upper()
    return clean_asin in GLOBAL_SENT_ASINS

def mark_asin_as_sent(asin: str):
    if not asin:
        return
    clean_asin = asin.strip().upper()
    GLOBAL_SENT_ASINS.add(clean_asin)
    save_sent_asins()
    logger.info(f"🔒 ASIN {clean_asin} registrato nel memory locker (Totale storico inviati: {len(GLOBAL_SENT_ASINS)})")
