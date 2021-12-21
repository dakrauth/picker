FROM python:3.7.4-alpine3.9
RUN apk --update add build-base bash jpeg-dev zlib-dev python3-dev
ENV PYTHONUNBUFFERED 1
ENV DEMO_DB_NAME /db.sqlite3
RUN mkdir -p /app
WORKDIR /app

RUN pip install pillow

COPY . .
RUN pip install django_extensions && \
    pip install -e . && \
    pip install -e demo

RUN demo migrate --no-input && \
    demo loaddata demo/demo/fixtures/users.json && \
    demo loaddata demo/demo/fixtures/picker.json && \
    demo import_picks tests/nfl2019.json


EXPOSE 80
RUN echo Load at http://localhost:8080
CMD ["demo", "runserver", "0:80"]
