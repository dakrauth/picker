FROM python:3.12.7-alpine
RUN apk --update add build-base bash jpeg-dev zlib-dev python3-dev

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DEMO_DB_NAME /db.sqlite3
RUN pip install django-extensions

RUN mkdir -p /app
WORKDIR /app

COPY setup.py README.rst /app
COPY picker /app/picker
COPY demo /app/demo
COPY tests /app/tests

RUN pip install -e /app
RUN pip install -e /app/demo/
RUN demo migrate --no-input && \
    demo loaddata demo/demo/fixtures/users.json && \
    demo loaddata demo/demo/fixtures/picker.json && \
    demo import_picks tests/nfl2024.json

EXPOSE 8080
RUN echo Load at http://localhost:8008
CMD ["demo", "runserver", "0:8008"]
