# Dorm Booking — Microservices on AWS (Track B)

A student housing booking system for dorms and boarding rooms near campus, built as
**two Docker microservices** and deployed on AWS (Cloud9 EC2 host and Amazon ECR) in the
AWS Academy *Microservices and CI/CD Pipeline Builder* lab (`us-east-1`).

## Why microservices?
Housing traffic is **spiky**. Thousands of students book in the first days of a new semester,
then traffic drops to almost nothing. Browsing rooms (reads) and booking rooms (writes) behave
differently, so they are split up:

| Service | Port | Responsibility | Scales on |
|---|---|---|---|
| `room-service` | 8081 | Read-only catalog of dorm rooms (area, price, capacity) | Browsing traffic |
| `booking-service` | 8082 | CRUD for **Booking**. Validates the room and blocks overbooking. | Registration rush |

If `booking-service` fails, students can still browse rooms. Each service is its own image in
ECR and can be deployed and scaled on its own.

## Data entity: `Booking`
| Field | Type | Rule |
|---|---|---|
| bookingId | string | Primary key, `bkg-` + 8 hex chars (generated) |
| roomId | string | **Required**, must exist in room-service |
| dormName | string | Copied from room-service at creation |
| studentName | string | **Required** |
| studentEmail | string | Optional |
| checkInDate | string | **Required**, `YYYY-MM-DD` |
| durationMonths | integer | 1–12, default 1 |
| totalPrice | integer | `pricePerMonth × durationMonths` (IDR) |
| status | string | `PENDING` at creation → `CONFIRMED` / `CANCELLED` |
| createdAt / updatedAt | string | ISO 8601 UTC |

## API
### booking-service (`:8082`)
| Operation | Method & path | Success | Errors |
|---|---|---|---|
| Create | `POST /bookings` | 201 + Booking | 400 invalid input · 404 room not found · **409 room full** · 503 room-service down |
| Read | `GET /bookings/{bookingId}` (list: `GET /bookings`) | 200 | 404 |
| Update | `PUT /bookings/{bookingId}` (status, studentName, studentEmail, checkInDate) | 200 | 400 · 404 · 409 |
| Delete | `DELETE /bookings/{bookingId}` | 204 | 404 |

### room-service (`:8081`)
`GET /health` · `GET /rooms?area=Pogung&maxPrice=1000000` · `GET /rooms/{roomId}`

## Repository layout
```
room-service/      app.py + Dockerfile (Python 3.12 Alpine, standard library only)
booking-service/   app.py + Dockerfile
scripts/           build-run.sh · crud-test.sh · ecr-push.sh · inventory.sh
docs/              deployment-plan.md
evidence/          outputs/ (command logs) · screenshots/ (AWS console)
```

## Run it (on the Cloud9 EC2 host)
```bash
git clone https://github.com/aureligius/dorm-booking-cloud-computing.git
cd dorm-booking-cloud-computing
bash scripts/inventory.sh  | tee evidence/outputs/01-environment.txt   # identity, VPC, EC2
bash scripts/build-run.sh  | tee evidence/outputs/02-build-run.txt     # build + run both containers
bash scripts/crud-test.sh  | tee evidence/outputs/04-crud-test.txt     # connectivity + CRUD test
bash scripts/ecr-push.sh   | tee evidence/outputs/05-ecr-push.txt      # push images to ECR (tag v1)
```
Run locally without Docker:
`python room-service/app.py` and `ROOM_SERVICE_URL=http://localhost:8081 python booking-service/app.py`.

## Security notes
- No AWS keys in this repo. Cloud9 uses temporary credentials from the lab role (`voclabs`).
- ECR repositories are private, with AES-256 encryption and scan-on-push enabled.
- Ports 8081/8082 are **not** opened to the internet in week 12. Tests run via `localhost`.
- Containers run as a non-root user.

See [docs/deployment-plan.md](docs/deployment-plan.md) for the next phases.
