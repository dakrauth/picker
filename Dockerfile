FROM python:3.12.7-alpine
RUN apk --update add build-base bash jpeg-dev zlib-dev python3-dev

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DEMO_DB_NAME /db.sqlite3

RUN mkdir -p /app
WORKDIR /app

COPY . .
RUN pip install . && pip install demo/ && pip install django-extensions
RUN demo migrate --no-input && \
    demo loaddata demo/demo/fixtures/users.json && \
    demo loaddata demo/demo/fixtures/picker.json && \
    demo import_picks tests/nfl2024.json

EXPOSE 80
RUN echo Load at http://localhost:8080
CMD ["demo", "runserver", "0:80"]
