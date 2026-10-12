# Gera a copia publica do relatorio para "Publicar na Web", que nao aceita modelo com RLS.
#
# Copia Olist.pbip, Olist.Report e Olist.SemanticModel (com o cache de dados .pbi/cache.abf,
# para abrir sem atualizar) e tira os papeis: a pasta definition/roles e as linhas
# "ref role" do model.tmdl. O original continua com RLS e OLS. A tabela seguranca_bi
# so tem e-mails ficticios e vai junto. Destino padrao: dashboards/powerbi/publico
# (no .gitignore).
#
# Uso:  powershell -ExecutionPolicy Bypass -File dashboards/powerbi/gerar_versao_publica.ps1
param([string]$Destino = (Join-Path $PSScriptRoot "publico"))

$ErrorActionPreference = "Stop"
$origem = $PSScriptRoot
$itens = @("Olist.pbip", "Olist.Report", "Olist.SemanticModel")
foreach ($item in $itens) {
    if (-not (Test-Path (Join-Path $origem $item))) { throw "Origem sem $item em $origem" }
}

# o destino nao pode ficar dentro do que esta sendo copiado
$destinoCheio = [IO.Path]::GetFullPath($Destino).TrimEnd('\', '/')
foreach ($pasta in @("Olist.Report", "Olist.SemanticModel")) {
    $cheio = [IO.Path]::GetFullPath((Join-Path $origem $pasta)).TrimEnd('\', '/')
    if ($destinoCheio.StartsWith($cheio, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Destino dentro de $pasta`: $destinoCheio"
    }
}
# nem igual a origem, nem uma pasta que a contenha (apagaria o projeto inteiro)
$origemCheia = [IO.Path]::GetFullPath($origem).TrimEnd('\', '/')
if (($origemCheia + [IO.Path]::DirectorySeparatorChar).StartsWith($destinoCheio + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw "Destino igual ou acima da origem: $destinoCheio"
}

# so apaga pasta vazia ou gerada por este script (marcador), nunca uma pasta qualquer
$marcador = ".gerado-por-gerar_versao_publica"
if (Test-Path $Destino) {
    $vazia = -not (Get-ChildItem -Force $Destino | Select-Object -First 1)
    if (-not $vazia -and -not (Test-Path (Join-Path $Destino $marcador))) {
        throw "Destino existe e nao foi gerado por este script: $destinoCheio"
    }
    Remove-Item -Recurse -Force $Destino
}
New-Item -ItemType Directory -Path $Destino | Out-Null
Set-Content -Path (Join-Path $Destino $marcador) -Value "Copia publica gerada por gerar_versao_publica.ps1; pode ser apagada e regerada."
foreach ($item in $itens) { Copy-Item -Recurse -Force (Join-Path $origem $item) $Destino }

$modelo = Join-Path $Destino "Olist.SemanticModel/definition"
$papeis = Join-Path $modelo "roles"
if (Test-Path $papeis) { Remove-Item -Recurse -Force $papeis }

# sem BOM e com a mesma quebra de linha do original
$arquivo = Join-Path $modelo "model.tmdl"
$texto = [IO.File]::ReadAllText($arquivo)
$quebra = if ($texto.Contains("`r`n")) { "`r`n" } else { "`n" }
$linhas = $texto -split "`r?`n" | Where-Object { $_ -notmatch '^ref role ' }
[IO.File]::WriteAllText($arquivo, ($linhas -join $quebra), (New-Object Text.UTF8Encoding($false)))

$cache = Join-Path $Destino "Olist.SemanticModel/.pbi/cache.abf"
if (-not (Test-Path $cache)) {
    Write-Warning "Sem .pbi/cache.abf: a copia abre sem dados e precisa atualizar a partir do Postgres local."
}
Write-Output "Copia publica em $Destino (sem papeis)."
