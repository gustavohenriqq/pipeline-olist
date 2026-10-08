<#
Confere o modelo do Power BI contra o SQL.

Consulta por DAX o modelo aberto no Power BI Desktop (o motor local que o
Desktop sobe) e compara cada caso de casos.json com o valor de esperado.sql,
calculado direto nas marts do Postgres local.

Uso (com o Olist.pbip aberto e atualizado no Desktop):
  .\conferir.ps1                                   # modelo e medidas
  .\conferir.ps1 -Grupos modelo                    # so contagens de linhas
  .\conferir.ps1 -Papel Vendedor -Usuario vendedor.a@exemplo.com.br

Com -Papel e -Usuario, a conexao entra no modelo como aquele papel e aquele
usuario (Roles e EffectiveUserName), e confere o que o RLS deixa ver. No papel
Vendedor tambem confere o OLS: as colunas de identificacao do cliente devem
falhar. Sai com 1 se algum caso falhar.
#>
param(
    [string[]]$Grupos = @("modelo", "medidas"),
    [string]$Papel,
    [string]$Usuario
)

$ErrorActionPreference = "Stop"
$Pasta = $PSScriptRoot
$Raiz = (Resolve-Path (Join-Path $Pasta "..\..\..")).Path

# --- Motor local do Power BI Desktop -----------------------------------------
$espacos = Join-Path $env:LOCALAPPDATA "Packages\Microsoft.MicrosoftPowerBIDesktop_8wekyb3d8bbwe\LocalState\AnalysisServicesWorkspaces"
$portas = @()
if (Test-Path $espacos) {
    $portas = Get-ChildItem $espacos -Directory |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object { Join-Path $_.FullName "Data\msmdsrv.port.txt" } |
        Where-Object { Test-Path $_ }
}
if (-not $portas -or -not (Get-Process msmdsrv -ErrorAction SilentlyContinue)) {
    Write-Host "Power BI Desktop nao esta aberto com o modelo (motor local nao encontrado)."
    exit 1
}
$porta = (Get-Content $portas[0] -Encoding Unicode | Select-Object -First 1).Trim()

$instalacao = (Get-AppxPackage -Name "Microsoft.MicrosoftPowerBIDesktop").InstallLocation
Add-Type -Path (Join-Path $instalacao "bin\Microsoft.PowerBI.AdomdClient.dll")

# --- Valores esperados (SQL) ---------------------------------------------------
Push-Location $Raiz
try {
    $linhas = Get-Content (Join-Path $Pasta "esperado.sql") -Raw |
        docker compose exec -T postgres psql -U olist -d olist -At -F "|"
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) { Write-Host "Falha ao calcular os valores esperados no Postgres."; exit 1 }
$esperado = @{}
foreach ($linha in $linhas) {
    $partes = $linha -split "\|", 2
    if ($partes.Count -eq 2) { $esperado[$partes[0]] = $partes[1] }
}

# --- Casos ---------------------------------------------------------------------
$todos = Get-Content (Join-Path $Pasta "casos.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$casos = @()
if ($Usuario) {
    foreach ($c in $todos.seguranca) {
        $casos += [pscustomobject]@{ caso = $c.caso.Replace("{usuario}", $Usuario); dax = $c.dax; erro = $false }
    }
    if ($Papel -eq "Vendedor") {
        foreach ($c in $todos.ols_vendedor) {
            $casos += [pscustomobject]@{ caso = $c.caso; dax = $c.dax; erro = $true }
        }
    }
} else {
    foreach ($g in $Grupos) {
        foreach ($c in $todos.$g) {
            $casos += [pscustomobject]@{ caso = $c.caso; dax = $c.dax; erro = $false }
        }
    }
}

# --- Conexao e conferencia -------------------------------------------------------
$conexao = "Data Source=localhost:$porta"
if ($Papel) { $conexao += ";Roles=$Papel" }
if ($Usuario) { $conexao += ";EffectiveUserName=$Usuario" }
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($conexao)
$conn.Open()

$cultura = [System.Globalization.CultureInfo]::InvariantCulture
$falhas = 0
foreach ($c in $casos) {
    $valor = $null
    $erroMsg = $null
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $c.dax
        $leitor = $cmd.ExecuteReader()
        if ($leitor.Read()) { $valor = $leitor.GetValue(0) }
        $leitor.Close()
    } catch {
        $erroMsg = $_.Exception.Message
    }

    if ($c.erro) {
        $ok = [bool]$erroMsg
        $mostrar = if ($ok) { "bloqueado" } else { "retornou $valor" }
        $alvo = "erro de permissao"
    } elseif ($erroMsg) {
        $ok = $false
        $mostrar = "ERRO: " + $erroMsg.Split([Environment]::NewLine)[0]
        $alvo = $esperado[$c.caso]
    } else {
        $alvo = $esperado[$c.caso]
        if ($null -eq $alvo) {
            $ok = $false
            $mostrar = "sem valor esperado em esperado.sql"
        } elseif ($alvo -eq "vazio") {
            $ok = ($null -eq $valor) -or ($valor -is [System.DBNull])
            $mostrar = if ($ok) { "vazio" } else { [string]$valor }
        } else {
            $e = [double]::Parse($alvo, $cultura)
            if (($null -eq $valor) -or ($valor -is [System.DBNull])) {
                $a = 0.0
                $ok = ($e -eq 0)
                $mostrar = "vazio"
            } else {
                $a = [double]$valor
                $ok = [Math]::Abs($a - $e) -le (1e-6 * [Math]::Max(1.0, [Math]::Abs($e)) + 0.005)
                $mostrar = $a.ToString("0.######", $cultura)
            }
        }
    }
    $estado = if ($ok) { "OK     " } else { "FALHOU " }
    if (-not $ok) { $falhas++ }
    Write-Host ("{0} {1,-40} modelo={2,-22} esperado={3}" -f $estado, $c.caso, $mostrar, $alvo)
}
$conn.Close()

$contexto = if ($Usuario) { " (papel $Papel, usuario $Usuario)" } else { "" }
if ($falhas -gt 0) {
    Write-Host "$falhas caso(s) falharam$contexto."
    exit 1
}
Write-Host "Todos os $($casos.Count) casos conferem$contexto."
exit 0
