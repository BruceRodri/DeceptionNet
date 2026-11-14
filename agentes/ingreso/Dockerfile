FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir redis==5.2.1 psycopg[binary]==3.2.6 && groupadd -g 10001 agente && useradd -u 10001 -g 10001 -M agente
COPY main.py /app/main.py
USER 10001:10001
CMD ["python","-u","/app/main.py"]
