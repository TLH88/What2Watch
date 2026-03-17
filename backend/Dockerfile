FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/scripts/start-backend.sh

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["/app/scripts/start-backend.sh"]
