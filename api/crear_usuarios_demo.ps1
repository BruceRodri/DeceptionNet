# SOLICITAR LAS CLAVES EN LA TERMINAL SIN MOSTRARLAS NI GUARDARLAS EN ARCHIVOS.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$secureA = $null
$secureB = $null
$payload = $null
try {
    $secureA = Read-Host 'Contraseña temporal para Empresa A (mínimo 12 caracteres)' -AsSecureString
    $secureB = Read-Host 'Contraseña temporal diferente para Empresa B (mínimo 12 caracteres)' -AsSecureString
    $passwordA = [System.Net.NetworkCredential]::new('', $secureA).Password
    $passwordB = [System.Net.NetworkCredential]::new('', $secureB).Password
    $payload = @{passwordA=$passwordA; passwordB=$passwordB} | ConvertTo-Json -Compress
    $payload | node api/usuarios_demo.mjs crear
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron crear las cuentas de demostración.' }
} finally {
    $passwordA = $null; $passwordB = $null; $payload = $null
    if ($secureA) { $secureA.Dispose() }
    if ($secureB) { $secureB.Dispose() }
}
