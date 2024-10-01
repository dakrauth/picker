FROM python:3.10.15-alpine3.20
RUN apk --update add build-base bash jpeg-dev zlib-dev python3-dev
ENV PYTHONUNBUFFERED 1
ENV DEMO_DB_NAME /db.sqlite3
RUN mkdir -p /app
WORKDIR /app

RUN pip install \
    pillow \
    "Django<5.0" \
    "django-bootstrap3>=12.0.1" \
    "python-dateutil>=2.8.1" \
    django_extensions

COPY . .
RUN pip install . demo/ && \
    demo migrate --no-input && \
    demo loaddata demo/demo/fixtures/users.json && \
    demo loaddata demo/demo/fixtures/picker.json && \
    demo import_picks tests/nfl2019.json

EXPOSE 80
RUN echo Load at http://localhost:8080
CMD ["demo", "runserver", "0:80"]
