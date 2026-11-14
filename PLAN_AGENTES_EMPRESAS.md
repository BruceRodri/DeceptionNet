# Conexión de empresas y agentes

## Situación actual

El administrador puede registrar una empresa y crear su cuenta. El ingreso TLS existente reconoce únicamente los agentes A y B preconfigurados; no autentica agentes de las organizaciones creadas desde el panel. Los tres señuelos locales pertenecen al laboratorio y no deben atribuirse a una empresa distinta sin conectar sus propios sensores.

## Fases de implementación

1. **Identidad y aislamiento.** Asociar cada agente a una empresa y preparar el almacenamiento de credenciales como huellas, con vencimiento y revocación. Una credencial no puede pertenecer a un agente de otra empresa. Esta fase prepara los datos; todavía no conecta agentes.
2. **Registro desde el panel.** Permitir que un administrador autorizado registre un agente, genere su credencial una sola vez, consulte su estado y la revoque. Validar permisos y guardar auditoría sin registrar la credencial.
3. **Ingreso y envío seguro.** Adaptar el ingreso TLS para identificar la empresa desde la credencial del agente, validar sus sensores y recibir eventos sin aceptar que el remitente elija otra empresa. Manejar reconexión y duplicados.
4. **Instalación y observación.** Preparar instrucciones y configuración para desplegar el agente con los señuelos soportados. Mostrar conexión, última comunicación, sensores y errores en el panel sin afirmar que un agente está conectado antes de recibir una señal real.
5. **Pruebas de extremo a extremo.** Comprobar con dos empresas que cada una recibe únicamente sus eventos, que las credenciales revocadas o inválidas no funcionan y que los eventos sobreviven a interrupciones. Verificar alertas y la experiencia de demostración manual.
6. **MTD remoto, si se necesita.** Ampliar las órdenes y su confirmación únicamente después de que los agentes y el aislamiento funcionen; el mecanismo actual de órdenes remotas también está limitado a A/B.

## Avance de la fase 1

La migración `024_identidad_agentes.sql` crea la tabla de credenciales vinculada al identificador de la empresa y al agente existente. Solo almacena una huella de 32 bytes y admite vencimiento y revocación. Todavía no hay una pantalla de emisión, un cliente instalable general ni autenticación de estas credenciales en el ingreso TLS. El acceso se habilitará de forma restringida en las fases siguientes, junto con sus validaciones.
