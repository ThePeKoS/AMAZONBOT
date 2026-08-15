import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any
import logging
from config import HEADERS
from database import DatabaseManager

logger = logging.getLogger(__name__)
db = DatabaseManager()

# Sezioni delle Offerte Lampo e Super Sconti di Amazon Italia
SUPER_DEALS_SECTIONS = [
    "https://www.amazon.it/gp/goldbox",  # Offerte del giorno / Offerte Lampo
    "https://www.amazon.it/deals",     # Sezione principale Offerte
    "https://www.amazon.it/s?k=offerta+del+giorno", # Ricerca prodotti in promozione
]

def parse_price_text(text: str) -> float:
    """Converte stringhe prezzo tipo '29,99 €' o '29.99' in float."""
    clean = text.replace("€", "").replace(".", "").replace(",", ".").strip()
    match = re.search(r"\d+\.?\d*", clean)
    if match:
        return float(match.group(0))
    return 0.0

def scan_all_super_deals(min_discount_filter: float = 20.0, max_results: int = 30) -> List[Dict[str, Any]]:
    """
    Effettua lo scraping avanzato di tutte le sezioni promozioni/offerte di Amazon Italia,
    filtra esclusivamente i prodotti con SUPER SCONTO (es. >= 20% o 30%)
    e li restituisce pronti per l'invio nel canale Telegram.
    """
    found_deals = []
    seen_asins = set()

    for url in SUPER_DEALS_SECTIONS:
        logger.info(f"Scansione Super Offerte su: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.content, "lxml")

            # Cerca blocchi/card prodotti nelle pagine di offerta
            # Amazon usa vari container per le griglie di offerte
            cards = soup.find_all("div", {"data-asin": True}) or soup.find_all("div", {"class": re.compile(r"deal|product|Grid")})

            for card in cards:
                asin = card.get("data-asin")
                if not asin:
                    # Cerca l'ASIN dai link interni
                    link = card.find("a", href=True)
                    if link:
                        m = re.search(r"(?:dp|product)/([A-Z0-9]{10})", link["href"])
                        if m:
                            asin = m.group(1)

                if not asin or asin in seen_asins:
                    continue

                seen_asins.add(asin)

                # Estrazione prezzo attuale e sconto/prezzo di listino dalla card o dalla pagina del prodotto
                # Prova prima rapida sulla card
                price_elem = card.find("span", {"class": "a-price-whole"})
                offscreen = card.find("span", {"class": "a-offscreen"})
                strike_price_elem = card.find("span", {"class": "a-text-price"}) or card.find("span", {"class": "a-price-basis"})

                current_price = 0.0
                list_price = 0.0

                if price_elem:
                    current_price = parse_price_text(price_elem.get_text())
                elif offscreen:
                    current_price = parse_price_text(offscreen.get_text())

                if strike_price_elem:
                    list_price = parse_price_text(strike_price_elem.get_text())

                # Se dalla card non estraiamo dati completi, scarichiamo la scheda del prodotto
                if current_price == 0.0 or list_price == 0.0:
                    from amazon_tracker import fetch_amazon_product
                    p_details = fetch_amazon_product(asin)
                    if p_details:
                        current_price = p_details["price"]
                        # Cerca prezzo listino/consigliato nella pagina
                        # Se disponibile viene calcolato, altrimenti salviamo nel DB per rilevare ribassi
                        title = p_details["title"]
                        image_url = p_details["image_url"]
                        product_url = p_details["url"]
                    else:
                        continue
                else:
                    title_elem = card.find("img", alt=True) or card.find("span", {"class": "a-truncate-full"})
                    title = title_elem.get("alt") or title_elem.get_text() if title_elem else f"Prodotto Amazon {asin}"
                    image_elem = card.find("img", src=True)
                    image_url = image_elem["src"] if image_elem else ""
                    product_url = f"https://www.amazon.it/dp/{asin}"

                # Calcolo della percentuale di sconto reale
                discount_percent = 0.0
                if list_price > current_price and current_price > 0:
                    discount_percent = ((list_price - current_price) / list_price) * 100

                # Salva o aggiorna nel database locale
                res = db.add_or_update_product(
                    asin=asin,
                    title=title,
                    url=product_url,
                    image_url=image_url,
                    price=current_price
                )

                # Se abbiamo uno sconto di listino oppure un calo rilevato nel DB
                final_discount = max(discount_percent, res.get("discount_percent", 0.0))
                orig_price = list_price if list_price > current_price else res.get("previous_price", current_price)

                # Filtra SOLO i prodotti SUPER SCONTATI (es. >= min_discount_filter %)
                if final_discount >= min_discount_filter or (orig_price > current_price and orig_price - current_price >= 10.0):
                    deal_obj = {
                        "asin": asin,
                        "title": title,
                        "url": product_url,
                        "image_url": image_url,
                        "current_price": current_price,
                        "previous_price": orig_price,
                        "discount_percent": final_discount,
                        "price_drop": orig_price - current_price
                    }
                    found_deals.append(deal_obj)

                if len(found_deals) >= max_results:
                    break

        except Exception as e:
            logger.error(f"Errore durante la scansione delle super offerte: {e}")

    return found_deals
