#!/usr/bin/env bash
# Build both images and run them on a private Docker network.
# Usage (from repo root, on the Cloud9 EC2 host): bash scripts/build-run.sh
set -euo pipefail
docker network create dorm-net 2>/dev/null || true
docker rm -f room-service booking-service 2>/dev/null || true

docker build -t room-service:latest ./room-service
docker build -t booking-service:latest ./booking-service

docker run -d --name room-service --network dorm-net -p 8081:8081 room-service:latest
docker run -d --name booking-service --network dorm-net -p 8082:8082 \
  -e ROOM_SERVICE_URL=http://room-service:8081 booking-service:latest

sleep 2
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
