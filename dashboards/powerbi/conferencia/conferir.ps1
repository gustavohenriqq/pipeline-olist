<#
Confere o modelo do Power BI contra o SQL.

Consulta por DAX o modelo aberto no Power BI Desktop (o motor local que o
Desktop sobe) e compara cada caso de casos.json com o valor de esperado.sql,
calculado direto nas marts do Postgres local.

Uso (com o Olist.pbip aberto e atualizado no Desktop):
  .\conferir.ps1                                   # modelo e medidas
  .\conferir.ps1 -Grupos modelo                    # so contagens de linhas
  .\conferir.ps1 -Papel Vendedor                   # RLS e OLS do papel

Com -Papel, a conexao entra no modelo como aquele papel (Roles). O motor local
do Desktop nao aceita EffectiveUserName com um e-mail que nao seja conta do
Windows, entao USERPRINCIPALNAME() devolve o usuario do Windows, que nao esta em
seguranca_bi: nos papeis Gerente regional e Vendedor ele deve ver zero (o caso
"fora do seed"); na Diretoria, tudo. No papel Vendedor tambem confere o OLS: as
colunas de identificacao do cliente devem falhar. Os numeros de cada usuario do
seed sao conferidos pelo "Exibir como" do Desktop (ver README.md desta pasta).
Sai com 1 se algum caso falhar.
#>
param(
    [string[]]$Grupos = @("modelo", "medidas"),
    [string]$Papel
)

$ErrorActionPreference = "Stop"
$Pasta = $PSScriptRoot
$Raiz = (Resolve-Path (Join-Path $Pasta "..\..\..")).Path

# --- Motor local do Power BI Desktop -----------------------------------------
# A pasta de trabalho do motor muda entre a versao da loja e a instalada; o
# caminho certo esta na linha de comando do msmdsrv (-s "<pasta>\Data").
$portas = @()
$motores = @()
foreach ($p in Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'") {
    if ($p.CommandLine -match '-s\s+"([^"]+)"') {
        $arquivo = Join-Path $Matches[1] "msmdsrv.port.txt"
        if (Test-Path $arquivo) { $portas += $arquivo; $motores += $p.ExecutablePath }
    }
}
if (-not $portas) {
    Write-Host "Power BI Desktop nao esta aberto com o modelo (motor local nao encontrado)."
    exit 1
}
if ($portas.Count -gt 1) {
    Write-Host "Mais de um Power BI Desktop aberto; feche os outros e deixe so o Olist.pbip."
    exit 1
}
$porta = (Get-Content $portas[0] -Encoding Unicode | Select-Object -First 1).Trim()

# A biblioteca de cliente fica na mesma pasta bin do msmdsrv, nas duas instalacoes.
Add-Type -Path (Join-Path (Split-Path $motores[0]) "Microsoft.PowerBI.AdomdClient.dll")

# --- Valores esperados (SQL) ---------------------------------------------------
Push-Location $Raiz
try {
    $linhas = Get-Content (Join-Path $Pasta "esperado.sql") -Raw |
        docker compose exec -T postgres psql -U olist -d olist -At -F "|" -v ON_ERROR_STOP=1
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) { Write-Host "Falha ao calcular os valores esperados no Postgres."; exit 1 }
$esperado = @{}
foreach ($linha in $linhas) {
    $partes = $linha -split "\|", 2
    # Valor nulo no SQL (ex.: soma sem linhas) conta como medida em branco.
    if ($partes.Count -eq 2) {
        $esperado[$partes[0]] = if ($partes[1] -eq "") { "vazio" } else { $partes[1] }
    }
}

# --- Casos ---------------------------------------------------------------------
$todos = Get-Content (Join-Path $Pasta "casos.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$casos = @()
if ($Papel) {
    # Diretoria nao filtra; nos outros papeis o usuario do Windows fica de fora.
    $Usuario = if ($Papel -eq "Diretoria") { "diretoria@exemplo.com.br" } else { "fora@exemplo.com.br" }
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
if ($Papel) {
    # Com Roles o motor exige o catalogo explicito.
    $conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($conexao)
    $conn.Open()
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = 'SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS'
    $leitor = $cmd.ExecuteReader()
    $leitor.Read() | Out-Null
    $catalogo = $leitor.GetValue(0)
    $leitor.Close()
    $conn.Close()
    $conexao += ";Initial Catalog=$catalogo;Roles=$Papel"
}
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($conexao)
$conn.Open()
# Conexao de controle, sem papel: o caso de OLS so vale se a mesma consulta
# funciona fora do papel (senao um erro de digitacao passaria por bloqueio).
$controle = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$porta")
$controle.Open()

function Consultar($conexaoAberta, [string]$dax) {
    $r = @{ valor = $null; erro = $null }
    $leitor = $null
    try {
        $cmd = $conexaoAberta.CreateCommand()
        $cmd.CommandText = $dax
        $leitor = $cmd.ExecuteReader()
        if ($leitor.Read()) { $r.valor = $leitor.GetValue(0) }
    } catch {
        $r.erro = $_.Exception.Message
    } finally {
        if ($leitor) { $leitor.Close() }
    }
    return $r
}

$cultura = [System.Globalization.CultureInfo]::InvariantCulture
$falhas = 0
foreach ($c in $casos) {
    $r = Consultar $conn $c.dax
    $valor = $r.valor
    $erroMsg = $r.erro

    if ($c.erro) {
        $base = Consultar $controle $c.dax
        $alvo = "erro de permissao"
        if ($base.erro) {
            $ok = $false
            $mostrar = "consulta falha ate sem papel"
        } else {
            $ok = [bool]$erroMsg
            $mostrar = if ($ok) { "bloqueado" } else { "retornou $valor" }
        }
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
                # Medidas de dinheiro sao decimais fixos (somas exatas); as razoes
                # vem em double. A folga cobre so o arredondamento do double.
                $ok = [Math]::Abs($a - $e) -le (1e-6 + 1e-12 * [Math]::Abs($e))
                $mostrar = $a.ToString("0.######", $cultura)
            }
        }
    }
    $estado = if ($ok) { "OK     " } else { "FALHOU " }
    if (-not $ok) { $falhas++ }
    Write-Host ("{0} {1,-40} modelo={2,-22} esperado={3}" -f $estado, $c.caso, $mostrar, $alvo)
}
$conn.Close()
$controle.Close()

$contexto = if ($Papel) { " (papel $Papel, esperado como $Usuario)" } else { "" }
if ($falhas -gt 0) {
    Write-Host "$falhas caso(s) falharam$contexto."
    exit 1
}
Write-Host "Todos os $($casos.Count) casos conferem$contexto."
exit 0
