"""booking-service: CRUD for the Booking entity.

Runs on port 8082. Before creating a booking it asks room-service for the
room (does it exist? what is its capacity and price?) and refuses the
booking if the room is already full, so a room can never be overbooked.

Endpoints
  GET    /health
  POST   /bookings              create   -> 201 | 400 | 404 room | 409 full | 503 room-service down
  GET    /bookings              list all -> 200
  GET    /bookings/{bookingId}  read     -> 200 | 404
  PUT    /bookings/{bookingId}  update   -> 200 | 400 | 404 | 409
  DELETE /bookings/{bookingId}  delete   -> 204 | 404
"""
import json
import os
import threading
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8082"))
ROOM_SERVICE_URL = os.environ.get("ROOM_SERVICE_URL", "http://room-service:8081")

STATUSES = {"PENDING", "CONFIRMED", "CANCELLED"}
ACTIVE = {"PENDING", "CONFIRMED"}  # bookings that occupy a bed

# In-memory store for week 12. Planned: Amazon RDS (MySQL).
BOOKINGS = {}
LOCK = threading.Lock()  # one booking decision at a time -> no double booking


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RoomServiceDown(Exception):
    pass


def fetch_room(room_id):
    """Return the room dict, None if it does not exist, or raise RoomServiceDown."""
    try:
        with urllib.request.urlopen(f"{ROOM_SERVICE_URL}/rooms/{room_id}", timeout=3) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RoomServiceDown() from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RoomServiceDown() from e


def occupied(room_id, exclude=None):
    return sum(1 for b in BOOKINGS.values()
               if b["roomId"] == room_id and b["status"] in ACTIVE and b["bookingId"] != exclude)


def valid_date(s):
    try:
        date.fromisoformat(s)
        return True
    except (TypeError, ValueError):
        return False


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=None):
        data = b"" if body is None else json.dumps(body).encode()
        self.send_response(code)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return None
        return body if isinstance(body, dict) else None

    def _parts(self):
        return [p for p in self.path.split("?")[0].split("/") if p]

    # ---------- READ ----------
    def do_GET(self):
        parts = self._parts()
        if parts == ["health"]:
            return self._send(200, {"status": "ok", "service": "booking-service"})
        if parts == ["bookings"]:
            return self._send(200, list(BOOKINGS.values()))
        if len(parts) == 2 and parts[0] == "bookings":
            b = BOOKINGS.get(parts[1])
            return self._send(200, b) if b else self._send(404, {"error": "booking not found"})
        return self._send(404, {"error": "route not found"})

    # ---------- CREATE ----------
    def do_POST(self):
        if self._parts() != ["bookings"]:
            return self._send(404, {"error": "route not found"})
        body = self._json()
        if body is None:
            return self._send(400, {"error": "invalid JSON"})

        missing = [f for f in ("roomId", "studentName", "checkInDate") if not body.get(f)]
        if missing:
            return self._send(400, {"error": f"missing fields: {', '.join(missing)}"})
        if not valid_date(body["checkInDate"]):
            return self._send(400, {"error": "checkInDate must be YYYY-MM-DD"})
        months = body.get("durationMonths", 1)
        if not isinstance(months, int) or isinstance(months, bool) or not 1 <= months <= 12:
            return self._send(400, {"error": "durationMonths must be an integer 1-12"})

        try:
            room = fetch_room(body["roomId"])
        except RoomServiceDown:
            return self._send(503, {"error": "room-service unavailable"})
        if room is None:
            return self._send(404, {"error": "room not found"})

        with LOCK:
            if occupied(room["roomId"]) >= room["capacity"]:
                return self._send(409, {"error": "room is full"})
            ts = now()
            booking = {
                "bookingId": "bkg-" + uuid.uuid4().hex[:8],
                "roomId": room["roomId"],
                "dormName": room["dormName"],
                "studentName": body["studentName"],
                "studentEmail": body.get("studentEmail", ""),
                "checkInDate": body["checkInDate"],
                "durationMonths": months,
                "totalPrice": room["pricePerMonth"] * months,
                "status": "PENDING",
                "createdAt": ts,
                "updatedAt": ts,
            }
            BOOKINGS[booking["bookingId"]] = booking
        return self._send(201, booking)

    # ---------- UPDATE ----------
    def do_PUT(self):
        parts = self._parts()
        if not (len(parts) == 2 and parts[0] == "bookings"):
            return self._send(404, {"error": "route not found"})
        body = self._json()
        if body is None:
            return self._send(400, {"error": "invalid JSON"})

        with LOCK:
            b = BOOKINGS.get(parts[1])
            if b is None:
                return self._send(404, {"error": "booking not found"})
            if "status" in body and body["status"] not in STATUSES:
                return self._send(400, {"error": f"status must be one of {sorted(STATUSES)}"})
            if "checkInDate" in body and not valid_date(body["checkInDate"]):
                return self._send(400, {"error": "checkInDate must be YYYY-MM-DD"})
            # Re-activating a cancelled booking must not overbook the room.
            if b["status"] == "CANCELLED" and body.get("status") in ACTIVE:
                try:
                    room = fetch_room(b["roomId"])
                except RoomServiceDown:
                    return self._send(503, {"error": "room-service unavailable"})
                if room is None or occupied(b["roomId"]) >= room["capacity"]:
                    return self._send(409, {"error": "room is full"})
            for f in ("status", "studentName", "studentEmail", "checkInDate"):
                if f in body:
                    b[f] = body[f]
            b["updatedAt"] = now()
            return self._send(200, b)

    # ---------- DELETE ----------
    def do_DELETE(self):
        parts = self._parts()
        if not (len(parts) == 2 and parts[0] == "bookings"):
            return self._send(404, {"error": "route not found"})
        with LOCK:
            if BOOKINGS.pop(parts[1], None) is None:
                return self._send(404, {"error": "booking not found"})
        return self._send(204)


if __name__ == "__main__":
    print(f"booking-service listening on :{PORT} (room-service at {ROOM_SERVICE_URL})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
