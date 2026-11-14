# DeceptionNet: instalación y demostración local

El proyecto es un laboratorio académico. Las empresas A y B, sus agentes y sus señuelos son simulados. El panel y los puertos históricos del laboratorio se publican únicamente en localhost; los dos señuelos remotos funcionan dentro de redes internas de Docker.

## Requisitos

Windows, Docker Desktop con Compose, Python 3 y Node.js. Para crear el certificado local se requiere `python -m pip install -r agentes/requirements-tools.txt`. Los paquetes del panel y la API se instalan durante la construcción de las imágenes. Los paquetes del panel y la API se instalan durante la construcción de las imágenes; el asistente de cuentas usa módulos nativos de Node.

## Puesta en marcha de un laboratorio nuevo

Trabajar desde la carpeta raíz. Estos pasos son para una instalación nueva: no reemplazar un `.env` existente ni borrar volúmenes de una instalación anterior.

1. Copiar `.env.example` a `.env` únicamente si no existe y establecer una contraseña local propia de PostgreSQL.
2. Iniciar la infraestructura y dejar que el analizador prepare las tablas iniciales:

   ```powershell
   docker compose up -d --build redis postgres analyzer
   ```

3. Preparar roles y migraciones en este orden. Los guiones guardan secretos en `.secrets`, fuera del control de versiones. Esperar a que PostgreSQL y el analizador estén activos antes de ejecutarlos:

   ```powershell
   python api/provisionar.py
   python api/provisionar_auth.py
   python api/provisionar_mtd.py
   python api/provisionar_controlador.py
   Get-Content migraciones/015_multicliente.sql -Raw | docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
   python api/provisionar_rls.py
   Get-Content migraciones/017_agentes.sql -Raw | docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
   python api/provisionar_remoto.py
   python api/provisionar_panel.py
   python agentes/preparar_secretos.py
   ```

4. Iniciar la plataforma central y los dos despliegues independientes:

   ```powershell
   docker compose up -d --build
   docker compose -f agentes/empresa_a/compose.yaml up -d --build
   docker compose -f agentes/empresa_b/compose.yaml up -d --build
   ```

5. Abrir `http://127.0.0.1:8081`. Si se trata de una instalación nueva, abrir localmente `.secrets/bootstrap_token` y configurar las contraseñas diferentes de `admin` y `analista`. No compartir el código ni los archivos de `.secrets`.

El panel permite registrar organizaciones y sus credenciales desde **Empresas**, con la cuenta administradora del laboratorio. El alta crea el espacio aislado; conectar agentes y sensores sigue siendo una configuración del despliegue fuera del panel. Las cuentas temporales de A y B usadas por los guiones se desactivan al finalizar. Para exponer el proyecto usando los nuevos controles, consulta **GUIA_PRESENTACION_EXTERNA.md**.

## Comprobar los servicios y preparar la exposición

```powershell
docker compose ps
docker compose -f agentes/empresa_a/compose.yaml ps
docker compose -f agentes/empresa_b/compose.yaml ps
```

Para demostrar las conexiones y alertas de los tres señuelos desde ventanas separadas, sigue [GUIA_PRESENTACION_EXTERNA.md](GUIA_PRESENTACION_EXTERNA.md). Cada conexión o intento se inicia manualmente.

Para acceder de forma opcional a las empresas simuladas A y B con usuarios propios, inicia sus despliegues y ejecuta `pwsh -NoProfile -File .\api\crear_usuarios_demo.ps1`. El asistente solicita contraseñas diferentes sin mostrarlas y presenta los nombres de usuario. Para desactivarlos después, ejecuta `node api/usuarios_demo.mjs desactivar USUARIO_A USUARIO_B`, sustituyendo los nombres por los que recibiste.

## Límites técnicos

RLS protege las lecturas de los roles específicos; el proceso API tiene acceso a las credenciales de todos ellos y el propietario de las tablas puede eludir RLS. El ingreso de agentes aplica la identidad y el alcance de las órdenes en el servidor; no sustituye una revisión de seguridad integral. TLS usa un certificado autofirmado local y tokens estáticos de laboratorio. Las órdenes entregadas cuyo resultado no se conozca permanecen en estado entregado hasta recibir confirmación o revisión: no se presume que hayan fallado. El planificador periódico solo existe dentro del experimento. El puerto directo 2222 de Cowrie sigue publicado y un nuevo escaneo puede hallar el puerto activo del gateway. El prototipo no está preparado para Internet ni para clientes reales.
