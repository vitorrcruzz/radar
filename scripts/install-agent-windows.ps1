#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,
    [string]$ProjectPath = (Split-Path -Parent $PSScriptRoot),
    [string]$PythonPath,
    [string]$CaBundle,
    [ValidateRange(60, 86400)]
    [int]$IntervalSeconds = 60,
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

function Invoke-NativeCaptured {
    param(
        [Parameter(Mandatory = $true)] [string]$FilePath,
        [Parameter(Mandatory = $true)] [string[]]$Arguments
    )

    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell can turn native stderr into a terminating error
        # when ErrorActionPreference is Stop. Capture it without aborting the
        # installer (e.g. py.exe reports this when no runtime is installed).
        $ErrorActionPreference = 'Continue'
        $output = @(& $FilePath @Arguments 2>$null)
        $exitCode = $LASTEXITCODE
    }
    catch {
        $output = @()
        $exitCode = 1
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    return [pscustomobject]@{ Output = $output; ExitCode = $exitCode }
}

function Resolve-CompatiblePython {
    param([string]$RequestedPath)

    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($RequestedPath) {
        # An explicit path is supplied by the administrator. Validate that
        # it exists, then let `python -m venv` perform the real execution
        # check. This avoids false negatives from native stdout handling in
        # Windows PowerShell 5.1 when Python's version probe is captured.
        if (Test-Path -LiteralPath $RequestedPath -PathType Leaf) {
            return (Resolve-Path -LiteralPath $RequestedPath).Path
        }
        return $null
    }
    else {
        foreach ($commandName in @('python.exe')) {
            Get-Command $commandName -All -ErrorAction SilentlyContinue |
                ForEach-Object { if ($_.Source) { $candidates.Add($_.Source) } }
        }

        $pathValues = @(
            [Environment]::GetEnvironmentVariable('Path', 'Machine'),
            [Environment]::GetEnvironmentVariable('Path', 'User'),
            $env:Path
        )
        foreach ($directory in (($pathValues -join ';') -split ';' | Select-Object -Unique)) {
            $directory = $directory.Trim().Trim('"')
            if ($directory) {
                $candidates.Add((Join-Path $directory 'python.exe'))
            }
        }

        if ($env:ProgramFiles) {
            $candidates.Add((Join-Path $env:ProgramFiles 'Python314\python.exe'))
            $candidates.Add((Join-Path $env:ProgramFiles 'Python 3.14\python.exe'))
            $candidates.Add((Join-Path $env:ProgramFiles 'Python312\python.exe'))
            $candidates.Add((Join-Path $env:ProgramFiles 'Python 3.12\python.exe'))
        }
        # Look up registered CPython installs directly instead of relying
        # only on PATH or the Python launcher.
        foreach ($registryPath in @(
            'HKLM:\SOFTWARE\Python\PythonCore',
            'HKLM:\SOFTWARE\WOW6432Node\Python\PythonCore',
            'HKCU:\SOFTWARE\Python\PythonCore'
        )) {
            if (Test-Path -LiteralPath $registryPath) {
                Get-ChildItem -LiteralPath $registryPath -ErrorAction SilentlyContinue |
                    ForEach-Object {
                        $installKey = Join-Path $_.PSPath 'InstallPath'
                        if (Test-Path -LiteralPath $installKey) {
                            $registeredDir = (Get-Item -LiteralPath $installKey).GetValue('')
                            if ($registeredDir) {
                                $candidates.Add((Join-Path $registeredDir 'python.exe'))
                            }
                        }
                    }
            }
        }
        if ($env:LocalAppData) {
            $userPythonRoot = Join-Path $env:LocalAppData 'Programs\Python'
            if (Test-Path -LiteralPath $userPythonRoot -PathType Container) {
                Get-ChildItem -LiteralPath $userPythonRoot -Directory -ErrorAction SilentlyContinue |
                    ForEach-Object { $candidates.Add((Join-Path $_.FullName 'python.exe')) }
            }
        }

        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            foreach ($minorVersion in @('3.14', '3.13', '3.12', '3.11', '3.10')) {
                $probe = Invoke-NativeCaptured -FilePath $launcher.Source -Arguments @(
                    "-$minorVersion", '-c', 'import sys; print(sys.executable)'
                )
                if ($probe.ExitCode -eq 0 -and $probe.Output) {
                    $candidates.Add(($probe.Output | Select-Object -First 1).ToString().Trim())
                }
            }
        }
    }

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            # Invoke the interpreter directly for this check. The generic
            # native-output wrapper can represent stdout differently across
            # Windows PowerShell 5.1 and PowerShell 7, causing a valid Python
            # executable to be rejected even though --version works.
            $versionOutput = @(& $candidate -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>&1)
            $pythonExitCode = $LASTEXITCODE
            if ($pythonExitCode -ne 0 -or -not $versionOutput) { continue }
            $versionText = ($versionOutput | Select-Object -First 1).ToString().Trim()
            $version = [version]$versionText
            if ($version -ge [version]'3.10') {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        }
        catch {
            continue
        }
    }
    return $null
}

$resolvedPython = Resolve-CompatiblePython -RequestedPath $PythonPath
if (-not $resolvedPython -and $PythonPath) {
    throw "PythonPath nao aponta para um Python 3.10 ou superior valido: $PythonPath"
}

if (-not $resolvedPython) {
    throw 'Python 3.10+ nao encontrado. Instale o Python manualmente e execute novamente, informando o caminho completo do python.exe com -PythonPath (por exemplo: -PythonPath "C:\Program Files\Python314\python.exe"). O instalador RADAR nao baixa nem instala o Python.'
}
$PythonPath = $resolvedPython
Write-Host "Python selecionado: $PythonPath"

if (-not (Test-Path (Join-Path $ProjectPath 'agent\client.py')) -or
    -not (Test-Path (Join-Path $ProjectPath 'collector\host_inventory.py')) -or
    -not (Test-Path (Join-Path $ProjectPath 'agent-requirements.txt'))) {
    throw "ProjectPath nao aponta para a raiz do repositorio RADAR: $ProjectPath"
}
if ($ServerUrl -notmatch '^https://') {
    if (-not $AllowInsecureHttp -or $ServerUrl -notmatch '^http://') {
        throw 'Use HTTPS. HTTP somente é aceito no laboratório com -AllowInsecureHttp.'
    }
    Write-Warning 'HTTP esta sem criptografia. Use esta opçao somente no laboratorio domestico isolado.'
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
    -Principal $principal -Settings $settings -Description 'Coleta local de inventario pelo RADAR.' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "Agente instalado e iniciado. Tarefa: $taskName"
Write-Host "Estado protegido: $stateFile"
Write-Host "Log: $logFile"
Write-Host 'A tarefa executa como SYSTEM; nenhuma senha de usuario e armazenada.'
