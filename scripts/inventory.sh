#!/usr/bin/env bash
# Record the environment and AWS resources used (evidence for the report).
# Usage: bash scripts/inventory.sh | tee evidence/outputs/01-environment.txt
set -uo pipefail
echo "== Identity ==";        aws sts get-caller-identity --output table
echo "== Host ==";            cat /etc/os-release | grep PRETTY_NAME; docker --version; aws --version
echo "== EC2 instances ==";   aws ec2 describe-instances --region us-east-1 \
  --query 'Reservations[].Instances[].{Name:Tags[?Key==`Name`]|[0].Value,Type:InstanceType,State:State.Name,PrivateIP:PrivateIpAddress,Subnet:SubnetId,SG:SecurityGroups[0].GroupId}' --output table
echo "== VPCs ==";            aws ec2 describe-vpcs --region us-east-1 \
  --query 'Vpcs[].{Name:Tags[?Key==`Name`]|[0].Value,Id:VpcId,Cidr:CidrBlock}' --output table
echo "== ECR repositories =="; aws ecr describe-repositories --region us-east-1 \
  --query 'repositories[].{Name:repositoryName,Uri:repositoryUri,Scan:imageScanningConfiguration.scanOnPush}' --output table
