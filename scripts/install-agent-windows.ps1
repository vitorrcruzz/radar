#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,
    [string]$ProjectPath = (Split-Path -Parent $PSScriptRoot),
    [string]$PythonPath,
    [string]$CaBundle,
    [ValidateRange(60, 86400)]
    [int]$IntervalSeconds = 900,
    [switch]$AllowInsecureHttp
)

$ErrorActionPreference = 'Stop'
$taskName = 'RADAR Agent'
$installRoot = Join-Path $env:ProgramFiles 'RADAR'
$sourceRoot = Join-Path $installRoot 'src'
$stateRoot = Join-Path $env:ProgramData 'RADAR'
$stateFile = Join-Path $stateRoot 'agent.json'
$logFile = Join-Path $stateRoot 'agent.log'
$venvPython = Join-Path $installRoot 'venv\Scripts\python.exe'

if (-not $PythonPath) {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { throw 'Python não encontrado. Instale Python 3.10+ ou informe -PythonPath.' }
    $PythonPath = $python.Source
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw "Executável Python não encontrado: $PythonPath" }
if (-not (Test-Path (Join-Path $ProjectPath 'agent\client.py')) -or
    -not (Test-Path (Join-Path $ProjectPath 'collector\host_inventory.py'))) {
    throw "ProjectPath não aponta para a raiz do repositório RADAR: $ProjectPath"
}
if ($ServerUrl -notmatch '^https://') {
    if (-not $AllowInsecureHttp -or $ServerUrl -notmatch '^http://') {
        throw 'Use HTTPS. HTTP somente é aceito no laboratório com -AllowInsecureHttp.'
    }
    Write-Warning 'HTTP está sem criptografia. Use esta opção somente no laboratório doméstico isolado.'
}

New-Item -ItemType Directory -Force -Path $installRoot, $sourceRoot, $stateRoot | Out-Null
Copy-Item -Path (Join-Path $ProjectPath 'agent'), (Join-Path $ProjectPath 'collector') -Destination $sourceRoot -Recurse -Force

if (-not (Test-Path $venvPython)) {
    & $PythonPath -m venv (Join-Path $installRoot 'venv')
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o ambiente virtual do agente.' }
}
& $venvPython -m pip install -r (Join-Path $ProjectPath 'agent-requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências do agente.' }

# O estado contém o token individual. Somente SYSTEM e Administradores podem acessá-lo.
& icacls.exe $stateRoot /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível restringir as permissões de ProgramData\RADAR.' }

$caPath = $null
if ($CaBundle) {
    if (-not (Test-Path -LiteralPath $CaBundle -PathType Leaf)) { throw "CA não encontrada: $CaBundle" }
    $caPath = Join-Path $stateRoot 'radar-ca.pem'
    Copy-Item -LiteralPath $CaBundle -Destination $caPath -Force
}

$registerArgs = @('-m', 'agent.client', '--register', '--server-url', $ServerUrl, '--state-file', $stateFile)
if ($caPath) { $registerArgs += @('--ca-bundle', $caPath) }
if ($AllowInsecureHttp) { $registerArgs += '--allow-insecure-http' }

# Lê o token sem ecoá-lo e mantém o valor apenas no ambiente do processo de registro.
$secureToken = Read-Host 'Token de registro RADAR (bootstrap)' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $env:RADAR_AGENT_ENROLLMENT_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    Push-Location $sourceRoot
    try {
        & $venvPython @registerArgs
        if ($LASTEXITCODE -ne 0) { throw 'O servidor recusou o registro do agente.' }
    }
    finally { Pop-Location }
}
finally {
    Remove-Item Env:\RADAR_AGENT_ENROLLMENT_TOKEN -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    $secureToken.Dispose()
}

$arguments = "-m agent.client --interval $IntervalSeconds --state-file `"$stateFile`" --log-file `"$logFile`""
if ($AllowInsecureHttp) { $arguments += ' --allow-insecure-http' }
$action = New-ScheduledTaskAction -Execute $venvPython -Argument $arguments -WorkingDirectory $sourceRoot
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Description 'Coleta local de inventário pelo RADAR.' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "Agente instalado e iniciado. Tarefa: $taskName"
Write-Host "Estado protegido: $stateFile"
Write-Host "Log: $logFile"
Write-Host 'A tarefa executa como SYSTEM; nenhuma senha de usuário é armazenada.'
