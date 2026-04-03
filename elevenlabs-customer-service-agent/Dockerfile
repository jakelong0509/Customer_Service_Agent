# Container config
FROM python:3.12-slim

WORKDIR /root

# Repo root is /app; Python imports `api` and `src` from the inner app package dir (/app/app).
ENV PYTHONPATH=/root:/root/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
