# Dockerfile per il Bot Amazon Price Tracker
FROM python:3.11-slim

WORKDIR /app

# Copia i requisiti ed installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY . .

# Comando di avvio del bot
CMD ["python", "main.py"]
