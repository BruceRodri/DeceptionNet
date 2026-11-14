
# UTILIZAR PYTHON COMO BASE DEL CONTENEDOR.
FROM python:3.12-slim
# EVITAR ARCHIVOS TEMPORALES DE PYTHON Y MOSTRAR LOGS EN TIEMPO REAL.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# DEFINIR LA CARPETA DE TRABAJO.
WORKDIR /app
# INSTALAR LAS LIBRERIAS DEL PROYECTO.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# CREAR UN USUARIO SIN PRIVILEGIOS DE ADMINISTRADOR.
RUN groupadd -g 10001 appuser \
    && useradd -u 10001 -g 10001 --no-create-home appuser \
    && mkdir -p /estado \
    && chown appuser:appuser /estado
# COPIAR EL PROGRAMA COLECTOR.
COPY --chown=appuser:appuser main.py adaptadores.py /app/
# EJECUTAR EL PROGRAMA CON PERMISOS LIMITADOS.
USER appuser
# INICIAR EL COLECTOR AUTOMATICAMENTE.
CMD ["python", "/app/main.py"]
