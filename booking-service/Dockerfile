# Base image from Amazon ECR Public (avoids Docker Hub pull rate limits on EC2)
FROM public.ecr.aws/docker/library/python:3.12-alpine
WORKDIR /app
COPY app.py .
ENV PORT=8082 PYTHONUNBUFFERED=1
EXPOSE 8082
# Run as a non-root user
RUN adduser -D appuser
USER appuser
CMD ["python", "app.py"]
