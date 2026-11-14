FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd -g 10001 appuser \
    && useradd -u 10001 -g 10001 --no-create-home appuser
COPY main.py normalizador.py detector.py repositorio.py schema.sql /app/
USER appuser
CMD ["python", "/app/main.py"]
