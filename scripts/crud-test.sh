#!/usr/bin/env bash
# Connectivity + CRUD test. Prints each request and its HTTP status.
# Usage: bash scripts/crud-test.sh | tee evidence/outputs/04-crud-test.txt
set -uo pipefail
R=${ROOM_URL:-http://localhost:8081}
B=${BOOKING_URL:-http://localhost:8082}

call() {  # method url [json]
  echo "### $1 $2 ${3:-}"
  if [ -n "${3:-}" ]; then
    curl -s -w '\nHTTP %{http_code}\n\n' -X "$1" "$2" -H 'Content-Type: application/json' -d "$3"
  else
    curl -s -w '\nHTTP %{http_code}\n\n' -X "$1" "$2"
  fi
}

echo "== Test run $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(hostname) =="
call GET  "$R/health"
call GET  "$B/health"
call GET  "$R/rooms?area=Pogung"

# CREATE (room-001 is a single room, capacity 1)
OUT=$(curl -s -w '
HTTP %{http_code}' -X POST "$B/bookings" -H 'Content-Type: application/json' \
  -d '{"roomId":"room-001","studentName":"Test Student","studentEmail":"student@example.com","checkInDate":"2027-01-15","durationMonths":6}')
echo "### POST $B/bookings (create)"; echo "$OUT"; echo
ID=$(echo "$OUT" | sed -n 's/.*"bookingId": *"\([^"]*\)".*/\1/p')

call GET    "$B/bookings/$ID"                                        # READ
call PUT    "$B/bookings/$ID" '{"status":"CONFIRMED"}'               # UPDATE
call POST   "$B/bookings" '{"roomId":"room-001","studentName":"Second Student","checkInDate":"2027-01-15"}'   # expect 409 full
call POST   "$B/bookings" '{"roomId":"room-999","studentName":"X","checkInDate":"2027-01-15"}'               # expect 404 room
call POST   "$B/bookings" '{"roomId":"room-002"}'                    # expect 400
call DELETE "$B/bookings/$ID"                                        # DELETE -> 204
call GET    "$B/bookings/$ID"                                        # expect 404
