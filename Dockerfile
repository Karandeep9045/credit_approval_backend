FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./credit_system/requirements.txt /app/

COPY ./credit_system /app/

RUN pip install -r requirements.txt