#!/bin/bash

IMAGE="screenshot-bot"
PREFIX="screenshot-bot"
PROJECT_DIR="/root/screenshot-bot"
VOLUME="$PROJECT_DIR/screenshots:/app/screenshots"

echo "Watchdog gestart..."

# Timestamp van laatste restart initialiseren
LAST_RESTART=$(date +%s)

while true; do
  NOW=$(date +%s)
  ELAPSED=$(( NOW - LAST_RESTART ))

  # Check of er een container draait
  RUNNING=$(docker ps --filter "name=$PREFIX" --format "{{.Names}}")

  # Als er geen container is of als 30 minuten voorbij zijn
  if [ -z "$RUNNING" ] || [ $ELAPSED -ge 1800 ]; then
    if [ ! -z "$RUNNING" ]; then
      echo "[$(date)] Stoppen actieve container(s) na 30 min: $RUNNING"
      docker rm -f $RUNNING
    fi

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
      --cpus="0.7" \
      -v $VOLUME \
      $IMAGE

    echo "[$(date)] Container gestart."
    LAST_RESTART=$NOW
  fi

  sleep 10
done