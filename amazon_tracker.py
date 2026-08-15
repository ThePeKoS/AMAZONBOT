import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import logging
from config import HEADERS

logger = logging.getLogger(__name__)

def extract_asin(url_or_asin: str) -> Optional[str]:
    """Estrazione dell'ASIN da un URL Amazon o validazione stringa ASIN."""
    asin_match = re.search(r"(?:dp|product|gp/product)/([A-Z0-9]{10})", url_or_asin, re.IGNORECASE)
    if asin_match:
        return asin_match.group(1).upper()
    
    # Se inserito direttamente l'ASIN di 10 caratteri alfanumerici
    if len(url_or_asin.strip()) == 10 and url_or_asin.strip().isalnum():
        return url_or_asin.strip().upper()
    
    return None

def fetch_amazon_product(asin: str) -> Optional[Dict[str, Any]]:
    """
    Effettua lo scraping della pagina del prodotto Amazon via ASIN.
    Estrarre: titolo, prezzo attuale, URL immagine, URL prodotto.
    """
    url = f"https://www.amazon.it/dp/{asin}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            logger.error(f"Errore HTTP {response.status_code} per l'ASIN {asin}")
            return None

        soup = BeautifulSoup(response.content, "lxml")

        # 1. Titolo del prodotto
        title_tag = soup.find("id", "productTitle") or soup.find("span", {"id": "productTitle"})
        if not title_tag:
            logger.warning(f"Impossibile trovare il titolo per l'ASIN {asin}")
            return None
        title = title_tag.get_text().strip()

        # 2. Prezzo del prodotto
        price = None
        # Prova vari selettori di prezzo usati da Amazon
        price_whole = soup.find("span", {"class": "a-price-whole"})
        price_fraction = soup.find("span", {"class": "a-price-fraction"})

        if price_whole:
            whole_str = price_whole.get_text().replace(".", "").replace(",", "").strip()
            fraction_str = price_fraction.get_text().strip() if price_fraction else "00"
            try:
                price = float(f"{whole_str}.{fraction_str}")
            except ValueError:
                pass

        if price is None:
            # Fallback selettore classico a-offscreen
            offscreen_price = soup.find("span", {"class": "a-offscreen"})
            if offscreen_price:
                price_text = offscreen_price.get_text().replace("€", "").replace(".", "").replace(",", ".").strip()
                try:
                    price = float(re.findall(r"\d+\.?\d*", price_text)[0])
                except (ValueError, IndexError):
                    pass

        if price is None:
            logger.warning(f"Impossibile estrarre il prezzo per l'ASIN {asin}")
            return None

        # 3. Immagine principale
        image_url = None
        img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "imgBlkFront"})
        if img_tag:
            image_url = img_tag.get("src") or img_tag.get("data-old-hires")

        return {
            "asin": asin,
            "title": title,
            "url": url,
            "image_url": image_url,
            "price": price
        }

    except Exception as e:
        logger.error(f"Eccezione durante lo scraping dell'ASIN {asin}: {e}")
        return None
