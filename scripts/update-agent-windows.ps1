#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$ProjectPath = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$taskName = 'RADAR Agent'
$installRoot = Join-Path $env:ProgramFiles 'RADAR'
$sourceFile = Join-Path $ProjectPath 'collector\host_inventory.py'
$targetDirectory = Join-Path $installRoot 'src\collector'
$targetFile = Join-Path $targetDirectory 'host_inventory.py'

if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
    throw "Coletor atualizado não encontrado: $sourceFile. Informe a raiz do projeto com -ProjectPath."
}
if (-not (Test-Path -LiteralPath $targetDirectory -PathType Container)) {
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
    Copy-Item -LiteralPath $sourceFile -Destination $targetFile -Force
}
finally {
    # Reativa a coleta mesmo se a cópia falhar.
    Start-ScheduledTask -TaskName $taskName
}

Write-Host 'Agente RADAR atualizado e reiniciado.'
Write-Host "Arquivo atualizado: $targetFile"
Write-Host "Tarefa: $taskName"
