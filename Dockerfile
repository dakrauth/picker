FROM python:3.6.5-alpine3.7
RUN apk --update add build-base bash jpeg-dev zlib-dev python3-dev
ENV PYTHONUNBUFFERED 1
ENV DEMO_DB_NAME /db.sqlite3
RUN mkdir -p /app
WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && \
    pip install invoke && \
    pip install -e . && \
    pip install -e demo

RUN demo loaddemo

EXPOSE 80
CMD ["demo", "runserver", "0:80"]
