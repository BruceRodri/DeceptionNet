FROM python:3.12-slim
RUN groupadd -g 10001 agente && useradd -u 10001 -g 10001 -M agente && mkdir /estado /registros && chown 10001:10001 /estado /registros
WORKDIR /app
COPY agente.py senuelo.py gateway.py protocolo.py /app/
USER 10001:10001
CMD ["python","-u","/app/agente.py"]
