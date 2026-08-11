FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings_production

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        lib32gcc-s1 \
        openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system rat-race \
    && useradd --system --gid rat-race --create-home rat-race \
    && mkdir -p /app /home/rat-race/steamcmd \
    && curl --fail --location --silent --show-error \
        https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz \
        | tar -xz -C /home/rat-race/steamcmd \
    && chown -R rat-race:rat-race /app /home/rat-race

WORKDIR /app

COPY apps/website/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --requirement /tmp/requirements.txt

COPY --chown=rat-race:rat-race apps/website/ /app/

USER rat-race

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
