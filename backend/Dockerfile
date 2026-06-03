FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-bq.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-bq.txt
COPY app ./app
ENV PORT=8080 USE_BQ=true
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
