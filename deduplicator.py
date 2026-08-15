import logging

logger = logging.getLogger(__name__)

# Registro Globale In-Memory per gli ASIN inviati
GLOBAL_SENT_ASINS = set()

def is_asin_already_sent(asin: str) -> bool:
    return asin in GLOBAL_SENT_ASINS

def mark_asin_as_sent(asin: str):
    GLOBAL_SENT_ASINS.add(asin)
    logger.info(f"🔒 ASIN {asin} registrato nel memory locker anti-duplicati (Totale inviati: {len(GLOBAL_SENT_ASINS)})")
