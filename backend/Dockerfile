FROM python:3.10-slim

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install gunicorn==20.1.0

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--forwarded-allow-ips=*", "foodgram_backend.wsgi"] 