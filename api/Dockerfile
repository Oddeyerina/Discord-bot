FROM python:3.12-slim
WORKDIR /app
RUN groupadd -g 10001 app && useradd -u 10001 -g app -m app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data && chown -R app:app /app
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
