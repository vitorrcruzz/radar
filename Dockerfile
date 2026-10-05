FROM python:3.11-slim

WORKDIR /app

ENV TZ=America/Sao_Paulo

RUN apt-get update && apt-get install -y \
    libsnmp-dev \
    snmp \
    nmap \
    gcc \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY collector/ ./collector/

RUN mkdir -p /app/database /app/exports

EXPOSE 5000

CMD ["python", "backend/app.py"]