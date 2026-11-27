# Deployment Plan

Region: `us-east-1` · Environment: AWS Academy *Microservices and CI/CD Pipeline Builder* lab (`LabVPC`).

## Phase 1: Week 12 (this submission) ✅
| Step | Resource | Result |
|---|---|---|
| 1 | AWS Cloud9 environment `dorm-booking-ide` (EC2 t3.small, Amazon Linux 2023, LabVPC / Public Subnet1, SSH) | Docker host + IDE |
| 2 | Clone this repo on the host | Starter code in place |
| 3 | `docker build` both services, run on Docker network `dorm-net` | 2 containers running |
| 4 | `scripts/crud-test.sh` over `localhost` | Connectivity + 4 CRUD operations verified |
| 5 | Private ECR repos `dorm-booking/room-service` and `dorm-booking/booking-service`, tag `v1` | Images published |

## Phase 2: Implementation (planned)
| Component | Plan | Why (cloud benefit) |
|---|---|---|
| **Amazon RDS for MySQL** | Store rooms and bookings in a private subnet. Only the service security group may reach port 3306. | Data survives container restarts. AWS manages backups and patching. |
| **Amazon ECS** | One ECS service per microservice, running the ECR images | Each service scales on its own (more booking-service tasks during the registration rush) |
| **Application Load Balancer** | Single public entry point across 2 AZs. `/rooms*` → room-service, `/bookings*` → booking-service. Health checks on `/health`. | High availability. Unhealthy containers are replaced automatically. |
| **CodePipeline + CodeDeploy** | On push: build the image → ECR → blue/green deployment to ECS | Zero-downtime updates |
| **CloudWatch Logs** | Container logs from both services | Monitoring and debugging |

## Security plan
- Only the ALB is public (HTTP 80). Service ports accept traffic **only from the ALB security group**.
- RDS is in a private subnet with no public access.
- IAM: use the lab-provided roles (`LabRole` for ECS task execution). No static access keys.

## Cost control (lab budget $40)
- Cloud9 auto-hibernates after 30 minutes idle.
- Small instance (t3.small). Small Alpine-based images (standard library only, no dependencies).
- Stop or delete the ECS services and ALB after each demo session.
