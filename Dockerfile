FROM python:3.11-slim

WORKDIR /app

# System deps for newspaper3k
RUN apt-get update && apt-get install -y \
    gcc g++ libxml2-dev libxslt-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
