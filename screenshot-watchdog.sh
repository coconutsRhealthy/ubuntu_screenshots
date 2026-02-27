#!/bin/bash

# --------------------------
# Screenshot Bot Watchdog
# --------------------------

IMAGE="screenshot-bot"
PREFIX="screenshot-bot"
PROJECT_DIR="/root/screenshot-bot"
VOLUME="$PROJECT_DIR/screenshots:/app/screenshots"

# Parameters
MAX_RESTARTS=8
WINDOW_SECONDS=180        # 3 minuten window voor rate-limit
COOLDOWN_SECONDS=600      # 10 minuten pauze bij te veel starts
MAX_RUNTIME=1800          # 30 minuten max runtime per container

echo "Watchdog gestart..."

LAST_RESTART=$(date +%s)

while true; do
  NOW=$(date +%s)
  ELAPSED=$(( NOW - LAST_RESTART ))

  #########################################
  # 1️⃣ Rate limit check
  #########################################

  RECENT_COUNT=0

  # Loop over alle containers met jouw prefix
  for CID in $(docker ps -a --filter "name=$PREFIX" --format "{{.ID}}"); do
    # Inspect creation timestamp (ISO 8601, versie-onafhankelijk)
    CREATED=$(docker inspect -f '{{.Created}}' $CID 2>/dev/null)
    if [ -n "$CREATED" ]; then
      CREATED_TS=$(date -d "$CREATED" +%s 2>/dev/null)
      if [ -n "$CREATED_TS" ]; then
        DIFF=$(( NOW - CREATED_TS ))
        if [ $DIFF -le $WINDOW_SECONDS ]; then
          RECENT_COUNT=$((RECENT_COUNT + 1))
        fi
      fi
    fi
  done

  if [ "$RECENT_COUNT" -gt "$MAX_RESTARTS" ]; then
    echo "[$(date)] $RECENT_COUNT containers gestart in de laatste 3 min. Cooldown $((COOLDOWN_SECONDS/60)) min..."
    sleep $COOLDOWN_SECONDS
    continue
  fi

  #########################################
  # 2️⃣ Oude gestopte containers opruimen (>10 min)
  #########################################

  docker container prune -f --filter "until=10m" > /dev/null

  #########################################
  # 3️⃣ Check actieve container(s)
  #########################################

  RUNNING=$(docker ps --filter "name=$PREFIX" --format "{{.Names}}")

  if [ -z "$RUNNING" ] || [ "$ELAPSED" -ge "$MAX_RUNTIME" ]; then

    if [ -n "$RUNNING" ]; then
      echo "[$(date)] Stoppen actieve container(s) na 30 min: $RUNNING"
      docker stop $RUNNING > /dev/null
    fi

    NEW_NAME="$PREFIX-$(date +%s)"

    echo "[$(date)] Starten nieuwe container: $NEW_NAME"

    docker run -d \
      --name "$NEW_NAME" \
      --cpus="0.7" \
      -v "$VOLUME" \
      "$IMAGE" > /dev/null

    echo "[$(date)] Container gestart."
    LAST_RESTART=$NOW
  fi

  sleep 10
done