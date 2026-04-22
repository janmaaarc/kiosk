FROM python:3.11-slim

WORKDIR /app

RUN addgroup --system kiosk && adduser --system --ingroup kiosk kiosk

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs static/uploads static/files static/images/announcements \
    && chown -R kiosk:kiosk /app

USER kiosk

ENV FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "60", "app:app"]
