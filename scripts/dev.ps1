param(
    [int]$Port = 8001,
    [switch]$NoServer
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $localSettings = @{}
    foreach ($fileName in @('.env', '.env.local')) {
        $filePath = Join-Path $projectRoot $fileName
        if (!(Test-Path $filePath)) { continue }
        foreach ($line in Get-Content $filePath -Encoding UTF8) {
            if ($line -notmatch '^\s*(DEMO_STUDENT_A_PASSWORD|DEMO_STUDENT_B_PASSWORD|DEMO_TEACHER_PASSWORD)\s*=\s*(.*)$') { continue }
            $value = $Matches[2].Trim()
            if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $localSettings[$Matches[1]] = $value
        }
    }

    $studentA = $localSettings['DEMO_STUDENT_A_PASSWORD']
    $studentB = $localSettings['DEMO_STUDENT_B_PASSWORD']
    if (!$studentA -or !$studentB) {
        throw 'Укажите разные DEMO_STUDENT_A_PASSWORD и DEMO_STUDENT_B_PASSWORD в .env или .env.local.'
    }
    if ($studentA -eq $studentB) { throw 'Пароли двух студентов должны различаться.' }

    $env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
    $env:DEMO_STUDENT_A_PASSWORD = $studentA
    $env:DEMO_STUDENT_B_PASSWORD = $studentB
    if ($localSettings['DEMO_TEACHER_PASSWORD']) {
        $env:DEMO_TEACHER_PASSWORD = $localSettings['DEMO_TEACHER_PASSWORD']
    } else {
        Remove-Item Env:DEMO_TEACHER_PASSWORD -ErrorAction SilentlyContinue
    }

    $python = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (!(Test-Path $python)) {
        py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать окружение. Установите Python 3.12 с Python Launcher.' }
    }

    $requirements = Join-Path $projectRoot 'requirements.txt'
    $stamp = Join-Path $projectRoot '.venv\requirements.sha256'
    $checksum = (Get-FileHash $requirements -Algorithm SHA256).Hash
    if (!(Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $checksum) {
        & $python -m pip install -r $requirements
        if ($LASTEXITCODE -ne 0) { throw 'Установка зависимостей завершилась с ошибкой.' }
        Set-Content $stamp $checksum -Encoding ASCII
    }

    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Миграции не применились.' }
    & $python manage.py seed_demo
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось подготовить демоаккаунты.' }

    if (!$NoServer) {
        Write-Host "Откройте http://127.0.0.1:$Port/login/"
        & $python manage.py runserver "127.0.0.1:$Port"
    }
} finally {
    Pop-Location
}
