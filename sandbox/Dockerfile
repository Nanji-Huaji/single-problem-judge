FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ coreutils bash python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
