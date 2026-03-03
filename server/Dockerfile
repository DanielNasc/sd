FROM python:3.12-slim

WORKDIR /app

COPY app.py /app/app.py
COPY business /app/business
COPY persistence /app/persistence
COPY domain /app/domain

EXPOSE 9000

CMD ["python", "app.py"]
