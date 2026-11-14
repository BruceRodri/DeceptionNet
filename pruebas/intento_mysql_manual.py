"""Enviar un intento MySQL ficticio al señuelo local, sin contraseña."""
import socket
import struct

HOST, PORT = '127.0.0.1', 3307

def recibir_exacto(sock, cantidad):
    datos = bytearray()
    while len(datos) < cantidad:
        parte = sock.recv(cantidad - len(datos))
        if not parte:
            raise ConnectionError('El señuelo cerró la conexión antes de completar la respuesta.')
        datos.extend(parte)
    return bytes(datos)

def recibir_paquete(sock):
    cabecera = recibir_exacto(sock, 4)
    longitud = int.from_bytes(cabecera[:3], 'little')
    if longitud > 4096:
        raise ValueError('Respuesta del señuelo demasiado grande.')
    return recibir_exacto(sock, longitud)

with socket.create_connection((HOST, PORT), timeout=5) as sock:
    saludo = recibir_paquete(sock)
    if not saludo or saludo[0] != 10:
        raise ValueError('El servicio no devolvió el saludo MySQL esperado.')
    version = saludo[1:].split(b'\x00', 1)[0].decode('ascii', 'replace')
    print('Saludo del senuelo:', version)
    # HandshakeResponse41, usuario ficticio y respuesta de autenticación vacía.
    # El destino y la identidad están fijados para este laboratorio.
    contenido = struct.pack('<IIB', 0x00008200, 16777216, 33) + bytes(23) + b'usuario_prueba\x00\x00'
    sock.sendall(len(contenido).to_bytes(3, 'little') + b'\x01' + contenido)
    respuesta = recibir_paquete(sock)
    if not respuesta or respuesta[0] != 0xff:
        raise ValueError('La respuesta no fue el rechazo esperado del señuelo.')
    print('Intento ficticio enviado sin contrasena: acceso rechazado por el senuelo.')
    print('Abre Actividad en vivo y busca: Intento de acceso MySQL.')
