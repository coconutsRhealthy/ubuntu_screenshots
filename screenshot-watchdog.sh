#!/bin/bash

IMAGE="screenshot-bot"
PREFIX="screenshot-bot"
PROJECT_DIR="/root/screenshot-bot"
VOLUME="$PROJECT_DIR/screenshots:/app/screenshots"

echo "Watchdog gestart..."

while true; do
  RUNNING=$(docker ps --filter "name=$PREFIX" --format "{{.Names}}")

  if [ -z "$RUNNING" ]; then
    echo "[$(date)] Geen actieve container gevonden."

    # Oude containers opruimen
    OLD=$(docker ps -a --filter "name=$PREFIX" --format "{{.Names}}")
    for c in $OLD; do
      echo "[$(date)] Verwijderen oude container: $c"
      docker rm -f $c
    done

    # Nieuwe container starten
    TIMESTAMP=$(date +%s)
    NEW_NAME="$PREFIX-$TIMESTAMP"

    echo "[$(date)] Starten nieuwe container: $NEW_NAME"

    docker run -d \
      --name $NEW_NAME \
      -v $VOLUME \
      $IMAGE

    echo "[$(date)] Container gestart."
  fi

  sleep 10
done