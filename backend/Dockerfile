FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" pelgo \
    && chown -R pelgo:pelgo /app
USER pelgo

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
