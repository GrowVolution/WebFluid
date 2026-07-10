FROM python:3.14-slim

WORKDIR /app

RUN apt update && apt install -y --no-install-recommends git \
        && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir webfluid==1.0.0b1
RUN wf create project dummy -sd && rm -rf dummy

ENTRYPOINT ["wf", "run"]