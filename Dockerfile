FROM python:3.13-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    COLORTERM=truecolor

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        mpv \
        libmpv2 \
        nodejs \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN echo "--js-runtimes node" > /etc/yt-dlp.conf

RUN useradd -m -u 1000 app \
    && mkdir -p /home/app/.cache/terminal-youtube \
    && chown -R app:app /home/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY terminal_youtube ./terminal_youtube

USER app

CMD ["python", "-m", "terminal_youtube"]
