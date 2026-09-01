FROM python:3.14-slim

WORKDIR /app
ARG WEBFLUID_VERSION=1.0.0rc1

RUN apt update && apt install -y --no-install-recommends git \
        && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir webfluid==${WEBFLUID_VERSION}
RUN wf create project dummy -sd && rm -rf dummy

ENTRYPOINT ["wf", "run"]