# Arquitectura de DeceptionNet en el laboratorio

La interfaz vigente se describe en `GUIA_PRESENTACION_EXTERNA.md`. El panel solo observa las pruebas iniciadas en PowerShell o en el navegador; la antigua ruta de generación de conexiones fue retirada. La API entrega métricas por identidad RLS. Eventos, alertas, decisiones y acciones MTD notifican a Socket.IO después del commit. Los intentos de acceso a los señuelos web y MySQL locales tienen reglas específicas; la rotación MTD automática sigue limitada al gateway SSH. El ingreso de agentes A/B mantiene su configuración anterior; registrar una organización no provisiona su agente.

Los diagramas describen los archivos `compose.yaml`, `compose.override.yaml`, `agentes/empresa_a/compose.yaml` y `agentes/empresa_b/compose.yaml`. A y B son empresas ficticias.

## Componentes

```mermaid
flowchart LR
  A[Señuelo de A] --> AA[Agente A y cola SQLite]
  B[Señuelo de B] --> AB[Agente B y cola SQLite]
  AA -->|HTTPS TLS| ING[Ingreso de agentes]
  AB -->|HTTPS TLS| ING
  ING --> R[Redis Streams]
  C[Cowrie] --> COL[Colector local] --> R
  R --> AN[Analizador]
  AN --> P[(PostgreSQL y RLS)]
  P -->|NOTIFY| API[API y Socket.IO]
  API --> UI[Panel local]
  P --> CTRL[Controlador MTD local] --> G[Gateway SSH local] --> C
```

## Secuencia de un evento remoto

```mermaid
sequenceDiagram
  participant H as Señuelo simulado
  participant A as Agente y SQLite
  participant I as Ingreso TLS
  participant R as Redis Streams
  participant N as Analizador
  participant D as PostgreSQL
  participant P as API y panel
  H->>A: Registro local de interacción
  A->>A: Encolar con ID único
  A->>I: Lote autenticado
  I->>R: XADD idempotente
  I-->>A: ACK de eventos aceptados
  R->>N: Mensaje del grupo de consumidores
  N->>D: Guardar evento y posible alerta
  N->>R: XACK tras confirmar transacción
  D-->>P: NOTIFY de alerta confirmada
  P-->>P: Emitir a la sala del tenant
```

## Redes Docker

```mermaid
flowchart TB
  subgraph Red_A[Red interna de Empresa A]
    HA[Señuelo A] --- AG[Agente A]
  end
  subgraph Red_B[Red interna de Empresa B]
    HB[Señuelo B] --- BG[Agente B]
  end
  subgraph Transporte[Red interna deceptionnet_agentes]
    AG --- IN[Ingreso TLS]
    BG --- IN
  end
  subgraph Gestion[Red interna deceptionnet_gestion]
    IN --- REDIS[(Redis)]
    REDIS --- ANA[Analizador]
    ANA --- PG[(PostgreSQL)]
    PG --- API[API]
  end
  API --- INTERFAZ[Red de interfaz y panel en localhost]
```

## Orden MTD remota

```mermaid
sequenceDiagram
  participant U as Administrador autenticado
  participant P as API central
  participant D as PostgreSQL
  participant I as Ingreso TLS
  participant A as Agente de la empresa
  participant G as Gateway de su señuelo
  U->>P: Solicitar puerto permitido e idempotencia
  P->>D: Registrar orden y vencimiento por tenant
  A->>I: Consultar órdenes con credencial propia
  I->>D: Seleccionar orden del tenant
  I-->>A: Orden firmada y con vencimiento
  A->>A: Verificar firma, tenant, sensor y plazo
  A->>G: Abrir candidato y comprobar salud
  alt Verificación correcta
    G-->>A: Cambio aplicado
  else Fallo
    G-->>A: Conservar puerto anterior
  end
  A->>I: ACK persistente con resultado
  I->>D: Actualizar estado e historial
```
