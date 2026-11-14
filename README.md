# DeceptionNet

DeceptionNet es un laboratorio académico que registra interacciones con señuelos SSH, web y MySQL y muestra eventos, alertas y decisiones MTD en un panel local.

## Uso diario

1. Abre Docker Desktop.
2. Desde esta carpeta ejecuta `docker compose up -d`.
3. Abre [el panel](http://127.0.0.1:8081) e inicia sesión con tus credenciales existentes.
4. Sigue la [guía de presentación desde ventanas externas](GUIA_PRESENTACION_EXTERNA.md): las interacciones se ejecutan manualmente en PowerShell o en un navegador y el panel las muestra en vivo.

## Documentación

- [Instalación y arranque](INICIO_Y_DEMO.md): requisitos, preparación inicial y servicios.
- [Arquitectura](ARQUITECTURA.md): componentes, redes y agentes.
- `Proyecto.docx`, ubicado en la carpeta superior: informe con resultados y capturas incrustadas.

Las contraseñas, certificados y configuraciones locales se conservan en `.env` y `.secrets`. PostgreSQL y Redis guardan sus datos en volúmenes Docker. La aplicación es un prototipo académico local: registrar una empresa no instala automáticamente su agente y la rotación MTD afecta al gateway SSH, mientras el puerto directo 2222 permanece disponible.
