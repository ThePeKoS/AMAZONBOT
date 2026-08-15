import sqlite3
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "amazon_tracker.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Crea la tabella prodotti e la tabella dello storico prezzi se non esistono."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    asin TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    image_url TEXT,
                    current_price REAL,
                    previous_price REAL,
                    lowest_price REAL,
                    highest_price REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asin TEXT NOT NULL,
                    price REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (asin) REFERENCES products (asin)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sent_deals (
                    asin TEXT PRIMARY KEY,
                    last_sent_price REAL NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("Database inizializzato con successo.")

    def is_deal_already_sent(self, asin: str, current_price: float = 0.0) -> bool:
        """Verifica se l'offerta per questo ASIN è già stata inviata sul canale."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_sent_price FROM sent_deals WHERE asin = ?", (asin,))
            row = cursor.fetchone()
            if row is not None:
                # Se è già stato inviato sul canale, non reinviare mai più a meno che il prezzo non sia calato ulteriormente
                last_sent_price = row[0]
                if current_price >= last_sent_price or current_price == 0.0 or current_price == 999999.0:
                    return True
            return False

    def mark_deal_as_sent(self, asin: str, current_price: float):
        """Registra l'offerta come inviata nel canale."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sent_deals (asin, last_sent_price)
                VALUES (?, ?)
                ON CONFLICT(asin) DO UPDATE SET
                    last_sent_price = excluded.last_sent_price,
                    sent_at = CURRENT_TIMESTAMP
            """, (asin, current_price))
            conn.commit()


    def add_or_update_product(
        self,
        asin: str,
        title: str,
        url: str,
        image_url: str,
        price: float
    ) -> Dict[str, Any]:
        """
        Inserisce o aggiorna un prodotto.
        Ritorna un dizionario contenente i dettagli ed eventuali variazioni di prezzo.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT current_price, lowest_price, highest_price FROM products WHERE asin = ?", (asin,))
            row = cursor.fetchone()

            is_new = False
            price_drop = 0.0
            discount_percent = 0.0
            previous_price = price

            if row is None:
                is_new = True
                lowest_price = price
                highest_price = price
                previous_price = price
                cursor.execute("""
                    INSERT INTO products (asin, title, url, image_url, current_price, previous_price, lowest_price, highest_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (asin, title, url, image_url, price, price, lowest_price, highest_price))
            else:
                old_current, lowest_price, highest_price = row
                previous_price = old_current
                
                if price < old_current:
                    price_drop = old_current - price
                    discount_percent = (price_drop / old_current) * 100

                new_lowest = min(lowest_price, price)
                new_highest = max(highest_price, price)

                cursor.execute("""
                    UPDATE products
                    SET title = ?,
                        url = ?,
                        image_url = ?,
                        previous_price = ?,
                        current_price = ?,
                        lowest_price = ?,
                        highest_price = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE asin = ?
                """, (title, url, image_url, old_current, price, new_lowest, new_highest, asin))

            # Inserisci nella cronologia prezzi
            cursor.execute("INSERT INTO price_history (asin, price) VALUES (?, ?)", (asin, price))
            conn.commit()

            return {
                "asin": asin,
                "title": title,
                "url": url,
                "image_url": image_url,
                "current_price": price,
                "previous_price": previous_price,
                "price_drop": price_drop,
                "discount_percent": discount_percent,
                "is_new": is_new,
                "lowest_price": min(lowest_price if not is_new else price, price)
            }

    def get_all_products(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def remove_product(self, asin: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_history WHERE asin = ?", (asin,))
            cursor.execute("DELETE FROM products WHERE asin = ?", (asin,))
            conn.commit()
            return cursor.rowcount > 0
