# Una ejecución = una conexión SSH al señuelo local; no envía contraseñas.
$conexion = [System.Net.Sockets.TcpClient]::new()
try {
    $conexion.ReceiveTimeout = 5000
    $conexion.Connect('127.0.0.1', 2222)
    $buffer = [byte[]]::new(256)
    $cantidad = $conexion.GetStream().Read($buffer, 0, $buffer.Length)
    if ($cantidad -le 0) { throw 'El señuelo cerró la conexión sin enviar un saludo.' }
    $saludo = [Text.Encoding]::ASCII.GetString($buffer, 0, $cantidad).Trim()
    if (-not $saludo.StartsWith('SSH-')) { throw 'La respuesta no es un saludo SSH.' }
    Write-Host "Conexion manual recibida: $saludo"
} finally {
    $conexion.Dispose()
}
