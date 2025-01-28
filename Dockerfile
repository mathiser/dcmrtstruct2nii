FROM python:3.10

RUN mkdir -p /opt/app
COPY . /opt/app/
RUN pip install -e /opt/app/

