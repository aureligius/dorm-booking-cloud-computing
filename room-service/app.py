"""room-service: read-only catalog of dorm rooms near campus.

Runs on port 8081. Uses only the Python standard library so the Docker
image stays small and builds quickly.

Endpoints
  GET /health                         -> {"status": "ok"}
  GET /rooms?area=..&maxPrice=..      -> list rooms (optional filters)
  GET /rooms/{roomId}                 -> one room, 404 if unknown
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", "8081"))

# Seed catalog. In the implementation phase this moves to Amazon RDS (MySQL).
ROOMS = {
    "room-001": {"roomId": "room-001", "dormName": "Wisma Pogung Asri", "area": "Pogung",
                 "roomType": "single", "pricePerMonth": 1200000, "capacity": 1},
    "room-002": {"roomId": "room-002", "dormName": "Wisma Pogung Asri", "area": "Pogung",
                 "roomType": "shared", "pricePerMonth": 850000, "capacity": 2},
    "room-003": {"roomId": "room-003", "dormName": "Kos Karangmalang Indah", "area": "Karangmalang",
                 "roomType": "single", "pricePerMonth": 1500000, "capacity": 1},
    "room-004": {"roomId": "room-004", "dormName": "Asrama Sendowo", "area": "Sendowo",
                 "roomType": "shared", "pricePerMonth": 700000, "capacity": 3},
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        parts = [p for p in url.path.split("/") if p]

        if parts == ["health"]:
            return self._send(200, {"status": "ok", "service": "room-service"})

        if parts == ["rooms"]:
            q = parse_qs(url.query)
            rooms = list(ROOMS.values())
            if "area" in q:
                area = q["area"][0].lower()
                rooms = [r for r in rooms if r["area"].lower() == area]
            if "maxPrice" in q:
                try:
                    max_price = int(q["maxPrice"][0])
                except ValueError:
                    return self._send(400, {"error": "maxPrice must be an integer"})
                rooms = [r for r in rooms if r["pricePerMonth"] <= max_price]
            return self._send(200, rooms)

        if len(parts) == 2 and parts[0] == "rooms":
            room = ROOMS.get(parts[1])
            if room is None:
                return self._send(404, {"error": "room not found"})
            return self._send(200, room)

        return self._send(404, {"error": "route not found"})


if __name__ == "__main__":
    print(f"room-service listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
