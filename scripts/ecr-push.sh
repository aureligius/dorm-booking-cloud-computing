#!/usr/bin/env bash
# Create private ECR repositories (if missing) and push both images as v1.
# Usage: bash scripts/ecr-push.sh | tee evidence/outputs/05-ecr-push.txt
set -euo pipefail
REGION=us-east-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$REGISTRY"

for svc in room-service booking-service; do
  aws ecr describe-repositories --repository-names "dorm-booking/$svc" --region $REGION >/dev/null 2>&1 || \
    aws ecr create-repository --repository-name "dorm-booking/$svc" --region $REGION \
      --image-scanning-configuration scanOnPush=true --encryption-configuration encryptionType=AES256 \
      --query 'repository.repositoryUri' --output text
  docker tag "$svc:latest" "$REGISTRY/dorm-booking/$svc:v1"
  docker push "$REGISTRY/dorm-booking/$svc:v1"
done
aws ecr describe-images --repository-name dorm-booking/booking-service --region $REGION \
  --query 'imageDetails[].{tags:imageTags,pushed:imagePushedAt,sizeBytes:imageSizeInBytes}' --output table
