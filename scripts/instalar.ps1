# Instalador do "Minhas Finanças" (Windows)
# 1) verifica o Python (oferece instalar pelo winget se faltar)
# 2) instala as dependências (Flask)
# 3) cria o atalho "Minhas Finanças" na Área de Trabalho
param([switch]$SemPerguntas)  # -SemPerguntas: instala sem perguntar (não abre o app no final)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Escrever-Passo($n, $texto) { Write-Host ""; Write-Host "[$n/3] $texto" -ForegroundColor Cyan }
function Escrever-Ok($texto) { Write-Host "  OK  $texto" -ForegroundColor Green }
function Escrever-Erro($texto) { Write-Host "  ERRO  $texto" -ForegroundColor Red }

Write-Host "=============================================" -ForegroundColor Blue
Write-Host "   Minhas Finanças - instalação" -ForegroundColor Blue
Write-Host "=============================================" -ForegroundColor Blue

# ---------- 1. Python ----------
Escrever-Passo 1 "Verificando o Python (3.10 ou mais novo)"
function Achar-Python {
    foreach ($cmd in @("python", "py")) {
        try {
            $v = & $cmd -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v) {
                $partes = $v.Trim().Split(".")
                if ([int]$partes[0] -ge 3 -and [int]$partes[1] -ge 10) { return @{ cmd = $cmd; versao = $v.Trim() } }
            }
        } catch {}
    }
    return $null
}
$py = Achar-Python
if (-not $py) {
    Escrever-Erro "Python 3.10+ não encontrado."
    $temWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
    if ($temWinget) {
        $resp = if ($SemPerguntas) { "s" } else { Read-Host "  Quer instalar o Python 3.12 agora pelo winget (gerenciador oficial do Windows)? [S/n]" }
        if ($resp -eq "" -or $resp -match "^[sSyY]") {
            winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
            # recarrega o PATH desta janela para enxergar o Python recém-instalado
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
            $py = Achar-Python
        }
    }
    if (-not $py) {
        Write-Host "  Instale o Python em https://www.python.org/downloads/ (marque 'Add python.exe to PATH')" -ForegroundColor Yellow
        Write-Host "  e depois rode o install.bat de novo." -ForegroundColor Yellow
        exit 1
    }
}
Escrever-Ok "Python $($py.versao) ($($py.cmd))"

# ---------- 2. Dependências ----------
Escrever-Passo 2 "Instalando as dependências (requirements.txt)"
& $py.cmd -m pip install --disable-pip-version-check -q -r (Join-Path $raiz "requirements.txt")
if ($LASTEXITCODE -ne 0) { Escrever-Erro "Falha ao instalar as dependências."; exit 1 }
& $py.cmd -c "from importlib.metadata import version; print(version('flask'))" | ForEach-Object { Escrever-Ok "Flask $_ instalado" }

# ---------- 3. Atalho ----------
Escrever-Passo 3 "Criando o atalho na Área de Trabalho"
$desktop = [Environment]::GetFolderPath("Desktop")   # funciona também com Área de Trabalho no OneDrive
$atalho = Join-Path $desktop "Minhas Finanças.lnk"
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($atalho)
$lnk.TargetPath = Join-Path $raiz "iniciar.bat"
$lnk.WorkingDirectory = $raiz
$lnk.IconLocation = (Join-Path $raiz "static\icon.ico") + ",0"
$lnk.Description = "Minhas Finanças - controle financeiro pessoal"
$lnk.WindowStyle = 7   # janela do servidor minimizada
$lnk.Save()
Escrever-Ok "Atalho criado: $atalho"

Write-Host ""
Write-Host "Tudo pronto! Para usar, dê dois cliques no atalho 'Minhas Finanças' na Área de Trabalho." -ForegroundColor Green
Write-Host "O navegador abre em http://localhost:5050 (a janela do servidor fica minimizada na barra de tarefas)."
if ($SemPerguntas) { exit 0 }
$abrir = Read-Host "Abrir o aplicativo agora? [S/n]"
if ($abrir -eq "" -or $abrir -match "^[sSyY]") { Start-Process $atalho }