# Demostración de DeceptionNet desde ventanas externas

Esta guía muestra cómo iniciar cada interacción desde PowerShell o desde un navegador y observar en el panel los eventos y las alertas reales. Trabaja únicamente con los señuelos locales del proyecto. No hay botones que generen las pruebas en el panel.

## 1. Preparar las ventanas

1. Inicia Docker Desktop y espera a que esté listo.
2. Abre PowerShell y ejecuta:

   ```powershell
   cd 'C:\Users\BRUCE RODRIGUEZ\Desktop\BRUCE 7MO SEMESTRE\APLICACIONES DISTRIBUIDAS\PARCIAL 2\DeceptionNet_Dia1'
   docker compose up -d
   docker compose ps
   ```

3. Comprueba que `cowrie`, `canary-web`, `canary-bd`, sus colectores, `analyzer`, `gateway`, `controlador`, `api` y `panel` estén en ejecución. `postgres` y `redis` deben indicar `healthy`.
4. Abre [el panel](http://127.0.0.1:8081), entra con tu usuario **admin** y tu contraseña habitual, y selecciona **Monitoreo en vivo**.
5. Pulsa **Presentar**. Coloca el panel en una mitad de la pantalla y PowerShell en la otra. En Windows puedes usar la tecla de Windows junto con las flechas izquierda y derecha.
6. En **Del primer contacto a la respuesta**, sigue las etapas de origen, señuelo, análisis, alerta y respuesta. El selector permite volver a una alerta reciente; sus botones muestran el evento, la alerta y el historial MTD asociados.
7. En el panel observa las tres tarjetas: muestran el último evento y la última alerta **históricos**. Anota la hora o el número de la última alerta antes de comenzar. El aviso **Alerta nueva · En vivo** aparecerá cuando llegue una alerta nueva mientras el panel está conectado.

Las sesiones del panel duran diez minutos. Si caduca, vuelve a iniciar sesión. La etiqueta **En vivo** indica que el canal y las consultas están disponibles; ante una interrupción el panel puede consultar periódicamente y muestra su estado.

### Configurar cuándo se generan las alertas

En **Monitoreo en vivo → Configurar alertas**, el administrador del laboratorio puede definir, para SSH, Web y MySQL, la cantidad mínima y la ventana en segundos. Por ejemplo, establece Web y MySQL en **3 intentos en 300 segundos**, pulsa **Guardar reglas** y realiza cada intento manualmente. El contador agrupa por señuelo y origen: los eventos que ya estén dentro de la ventana pueden contar. La configuración guardada se aplica a los próximos eventos sin reiniciar el sistema. Tras una alerta, la misma regla y origen no producen otra alerta durante esa ventana; los eventos se siguen registrando. Para empezar la demostración desde cero, espera a que pasen la ventana configurada y la deduplicación de la alerta anterior. Los usuarios analistas pueden consultar las reglas, pero no modificarlas.

## 2. SSH: conexiones desde PowerShell

**Objetivo:** mostrar conexiones repetidas a Cowrie y la detección de un umbral.

1. Mantén abierto el panel en **Monitoreo en vivo** y usa la ventana de PowerShell abierta en la carpeta del proyecto.
2. Ejecuta una vez:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\pruebas\conexion_ssh.ps1
   ```

3. Verás `Conexion manual recibida: SSH-...`. Cada ejecución abre y cierra **una** conexión: no introduce contraseñas.
4. Para repetirla tú mismo, pulsa la flecha **↑** y luego **Enter**. Hazlo hasta completar la cantidad configurada de conexiones dentro de su ventana. El valor inicial es diez en 300 segundos. Espera a que termine cada ejecución antes de iniciar la siguiente.
5. Mira el panel: aparecerán eventos de conexión o cierre de sesión. Al alcanzarse el umbral configurado de conexiones del mismo origen, debería aparecer **Alerta nueva · Múltiples conexiones SSH**. La tarjeta SSH actualizará también su última alerta.
6. Pulsa **Ver alertas** o entra en **Actividad en vivo → Alertas**, filtra **SSH · Cowrie** y abre la alerta. Revisa el identificador, el origen, la cantidad y la ventana.
7. Abre **Defensa MTD** y busca la decisión por el mismo identificador de alerta. Si se creó una acción, espera su resultado y comprueba el puerto anterior y el nuevo. Una decisión puede quedar en enfriamiento o sin rotación; solo el estado **aplicada** confirma el cambio.

**Para repetir:** el detector agrupa por sensor, origen y procedencia, y evita otra alerta de la misma regla y origen durante la ventana. Si acabas de hacer la prueba, espera a que transcurra la ventana configurada antes de repetirla desde ese mismo origen. Los eventos de cierre pueden hacer que el número total de eventos suba más de diez.

**Límite de MTD:** las conexiones de la prueba entran directamente por el puerto local `2222`. MTD cambia el puerto del gateway entre `2201`, `2202` y `2203`; el puerto directo `2222` permanece disponible. Una rotación no implica que todo acceso al señuelo quede bloqueado.

### Opcional: enseñar comandos dentro de Cowrie

En PowerShell ejecuta:

```powershell
ssh -o UserKnownHostsFile=NUL -o StrictHostKeyChecking=no -p 2222 usuario_prueba@127.0.0.1
```

Si solicita contraseña, escribe una **inventada solo para esta prueba**. La configuración del señuelo puede aceptar o rechazarla; no uses credenciales reales. Si entra, escribe `whoami`, después `pwd` y finalmente `exit`. En **Actividad en vivo → Eventos**, filtra **SSH · Cowrie** y busca **Comando registrado: whoami** y **Comando registrado: pwd**. El panel muestra el comando registrado; la contraseña no se muestra en él.

## 3. Web: intento desde otra pestaña del navegador

**Objetivo:** mostrar que una visita y un intento de inicio de sesión son eventos distintos.

1. Mantén el panel visible y abre otra ventana o pestaña en [http://127.0.0.1:8088](http://127.0.0.1:8088).
2. La visita a la página señuelo puede generar eventos de solicitud o redirección. Una visita por sí sola no activa la nueva regla de intento de acceso.
3. En el formulario, escribe un usuario y una contraseña **ficticios** y pulsa el botón de acceso. Nunca uses tus credenciales reales: el honeypot puede guardar lo introducido en sus registros locales.
4. Repite el envío manualmente hasta alcanzar la cantidad de intentos Web configurada dentro de su ventana. Tras unos segundos debería aparecer **Alerta nueva · Intento de acceso web**, y la tarjeta Web mostrará el evento y la alerta correspondientes.
5. Abre **Ver alertas** en la tarjeta Web y después el detalle de la alerta. La regla dispara al alcanzar la cantidad configurada de intentos de acceso al formulario señuelo; requiere contexto y no demuestra por sí misma un ataque externo real.

Si necesitas una alternativa desde PowerShell, este comando envía **un** formulario con datos ficticios al mismo señuelo local:

```powershell
curl.exe -i -X POST --data "username=usuario_prueba&password=clave_ficticia" http://127.0.0.1:8088/index.html
```

Una repetición desde el mismo origen dentro de la ventana configurada registra el evento, pero puede no generar otra alerta debido a la deduplicación.

## 4. MySQL: intento desde PowerShell

**Objetivo:** hacer un intento ficticio de autenticación contra el servicio de base de datos simulado.

1. En la ventana de PowerShell, con la carpeta del proyecto como ubicación actual, ejecuta una vez:

   ```powershell
   python .\pruebas\intento_mysql_manual.py
   ```

2. El guion se conecta exclusivamente a `127.0.0.1:3307`, lee el saludo MySQL y envía un usuario ficticio **sin contraseña**. Debería mostrar que el acceso fue rechazado. Cada ejecución es un intento; no contiene un bucle automático.
3. Repite el comando manualmente hasta alcanzar la cantidad de intentos MySQL configurada dentro de su ventana. En el panel aparecerán los eventos y, al alcanzar el umbral, la **Alerta nueva · Intento de acceso MySQL**.
4. En la tarjeta MySQL pulsa **Ver alertas**, abre el detalle y muestra la hora, el origen y la regla. La regla genera una alerta al alcanzar la cantidad configurada de intentos de autenticación al señuelo; no se accede a una base de datos real.

Al igual que en Web, los intentos posteriores del mismo origen dentro de la ventana se registran, pero no necesariamente generan una nueva alerta. Espera a que pase la ventana configurada para repetir la alerta desde ese origen.

## 5. Cambiar el MTD: automático o manual

El MTD de este laboratorio cambia el puerto del **gateway SSH** entre `2201`, `2202` y `2203`. En **Defensa MTD** puedes ver la política configurada, el puerto actual, las decisiones y las acciones. El panel muestra el resultado registrado: **solicitada** o **en proceso** no equivalen a **aplicada**.

### Rotación automática

1. Entra como administrador al **Laboratorio local** y abre **Defensa MTD**. Comprueba que el modo configurado sea `adaptativa`.
2. Realiza manualmente las conexiones SSH necesarias para alcanzar el umbral configurado, como se explica en la sección 2. Cuando se genere la alerta, el controlador evaluará si corresponde una rotación; considera, entre otros factores, el sensor y el período de espera entre acciones.
3. Busca la decisión por el número de alerta. Si hay una acción, espera a que figure **aplicada** y muestra los puertos anterior y nuevo. También puedes seleccionar esa alerta en **Monitoreo en vivo** y seguir sus cinco etapas. Si indica **enfriamiento**, **sin acción**, **fallida** o **revertida**, explica ese resultado; no presentes el cambio como aplicado.
4. Si el modo no es `adaptativa`, antes de la exposición abre el archivo de configuración local:

   ```powershell
   notepad .env
   ```

   Busca `MTD_POLITICA` y deja la línea `MTD_POLITICA=adaptativa`; si no existe, añádela. Guarda y cierra el editor. El archivo contiene secretos, así que no lo proyectes ni compartas. Después aplica la configuración a ambos servicios:

   ```powershell
   docker compose up -d --force-recreate controlador api
   ```

   Espera a que arranquen, vuelve a cargar el panel y, si es necesario, inicia sesión otra vez. Las alertas Web y MySQL no rotan automáticamente sus servicios: esta política actúa sobre el gateway SSH.

### Rotación manual

1. Inicia sesión como administrador en **Laboratorio local** y entra en **Defensa MTD**.
2. En **Solicitar rotación manual**, elige uno de los puertos disponibles diferente del puerto actual, escribe un motivo de al menos cuatro caracteres y confirma la solicitud.
3. Consulta el historial y espera hasta ver **aplicada**. Comprueba que el puerto actual haya cambiado. Si figura otro estado, muestra ese estado y su detalle.

Puedes solicitar una rotación manual aunque `adaptativa` siga activa. Si quieres que durante la exposición las rotaciones sean **solo manuales**, cambia en `.env` la línea a `MTD_POLITICA=estatica` y vuelve a ejecutar `docker compose up -d --force-recreate controlador api`. Para reactivar las decisiones automáticas por alerta, vuelve a poner `adaptativa` y recrea ambos servicios del mismo modo. La interfaz no tiene un interruptor para cambiar esa política.

**Qué se bloquea:** una rotación aplicada deja de ofrecer el puerto anterior en el gateway y activa el nuevo. No establece un bloqueo general de la IP: el acceso directo a Cowrie por `2222` sigue disponible. Por eso no se debe afirmar que el atacante quedó bloqueado por completo.

## 6. Explicar el resultado

- El panel es el observador: las pruebas salen de ventanas externas y pasan por el señuelo, el colector, Redis, el analizador y PostgreSQL antes de llegar al panel.
- SSH usa una regla de conexiones repetidas; Web y MySQL alertan al alcanzar su cantidad configurada de intentos de autenticación al servicio señuelo. Una alerta es una señal para revisar, no una prueba automática de un ataque externo real.
- La respuesta MTD automática disponible es para el gateway SSH. Las alertas web y MySQL quedan registradas y su decisión no debe presentarse como un cambio automático de esos servicios.
- Registrar una empresa crea su espacio y credenciales, pero conectar un agente de una empresa nueva requiere configuración adicional fuera del panel.

## Si una alerta no aparece

1. Comprueba que estás en **Laboratorio local**, que el panel indica **En vivo** y que el intento se hizo contra el puerto correcto.
2. Espera unos segundos; los colectores leen sus registros de manera periódica. Usa **Actualizar datos** y revisa que los filtros correspondan al sensor.
3. Comprueba si ya hubo una alerta de la misma regla y origen durante la ventana configurada. Si es así, espera a que venza la ventana para repetir la alerta.
4. Revisa los servicios y sus registros, por ejemplo: `docker compose logs --tail 30 analyzer`, `docker compose logs --tail 30 collector-web` o `docker compose logs --tail 30 collector-bd`.
5. Para SSH, comprueba la cantidad de conexiones y consulta la decisión en **Defensa MTD**. Si la sesión del panel caducó, inicia sesión de nuevo.

Los resultados de las verificaciones anteriores y las capturas ya incorporadas se conservan en el documento Proyecto.docx. Las pruebas de la exposición se inician manualmente desde ventanas externas.
