#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$ProjectPath
)

$ErrorActionPreference = 'Stop'
if (-not $ProjectPath) {
    $scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectPath = Split-Path -Parent $scriptDirectory
}

$taskName = 'RADAR Agent'
$installRoot = Join-Path $env:ProgramFiles 'RADAR'
$sourceAgent = Join-Path $ProjectPath 'agent'
$sourceCollector = Join-Path $ProjectPath 'collector'
$sourceRoot = Join-Path $installRoot 'src'
$venvPython = Join-Path $installRoot 'venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath (Join-Path $sourceAgent 'client.py') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $sourceCollector 'host_inventory.py') -PathType Leaf)) {
    throw "Código atualizado do agente não encontrado em $ProjectPath. Informe a raiz do projeto com -ProjectPath."
}
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container) -or
    -not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw "Agente RADAR não encontrado em $installRoot. Instale o agente antes de atualizá-lo."
}
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    throw "A tarefa '$taskName' não foi encontrada. Verifique se o agente está instalado."
}

if ($task.State -eq 'Running') {
    Stop-ScheduledTask -TaskName $taskName
    $limite = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $task = Get-ScheduledTask -TaskName $taskName
    } while ($task.State -eq 'Running' -and (Get-Date) -lt $limite)
    if ($task.State -eq 'Running') {
        throw "A tarefa '$taskName' não parou dentro de 20 segundos."
    }
}

try {
    Copy-Item -Path $sourceAgent, $sourceCollector -Destination $sourceRoot -Recurse -Force
}
finally {
    # Reativa a coleta mesmo se a cópia falhar.
    Start-ScheduledTask -TaskName $taskName
}

Write-Host 'Agente RADAR atualizado e reiniciado.'
Write-Host "Código atualizado em: $sourceRoot"
Write-Host 'Identidade e token do agente preservados em ProgramData\RADAR.'
Write-Host "Tarefa: $taskName"
