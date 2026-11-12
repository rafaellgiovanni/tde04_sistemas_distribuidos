FROM python:3.12-slim
WORKDIR /app
COPY app_server.py .
EXPOSE 8000
CMD ["python", "app_server.py"]
