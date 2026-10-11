# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/base:bookworm

RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*