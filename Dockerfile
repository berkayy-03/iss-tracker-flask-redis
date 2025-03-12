FROM python:3.8-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir requests flask pytz

CMD ["python", "iss_tracker.py"]
