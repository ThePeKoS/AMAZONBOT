import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import logging
from config import HEADERS

logger = logging.getLogger(__name__)

# Categorie/Filtri Amazon Offerte (Es. Offerte del giorno, Informatica, Elettronica, Casa)
DEALS_URLS = [
    "https://www.amazon.it/gp/goldbox",  # Pagina principale offerte Amazon
]

def extract_asin_from_text(text: str) -> Optional[str]:
    """Estrazione dell'ASIN da qualsiasi URL o stringa."""
    asin_match = re.search(r"(?:dp|product|gp/product|dlc|offer)/([A-Z0-9]{10})", text, re.IGNORECASE)
    if asin_match:
        return asin_match.group(1).upper()
    if len(text.strip()) == 10 and text.strip().isalnum():
        return text.strip().upper()
    return None

def fetch_popular_deals(limit: int = 15) -> List[Dict[str, Any]]:
    """
    Scansiona le pagine delle offerte di Amazon per scoprire automaticamente i prodotti scontati.
    Ritorna una lista di dizionari con i prodotti trovati.
    """
    discovered_asins = set()
    found_products = []

    for deals_url in DEALS_URLS:
        try:
            logger.info(f"Ricerca offerte automatiche su: {deals_url}")
            response = requests.get(deals_url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.content, "lxml")

            # Cerca tutti i link che contengono un ASIN prodotto
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                asin = extract_asin_from_text(href)
                if asin and asin not in discovered_asins:
                    discovered_asins.add(asin)
                    
                    # Recupera le informazioni di dettaglio
                    from amazon_tracker import fetch_amazon_product
                    p_info = fetch_amazon_product(asin)
                    if p_info:
                        found_products.append(p_info)
                        if len(found_products) >= limit:
                            break

        except Exception as e:
            logger.error(f"Errore durante lo scraping delle offerte: {e}")

    return found_products
