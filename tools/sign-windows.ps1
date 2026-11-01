# 给打包好的可执行文件签名（Windows）
#
# 用法：
#   .\sign-windows.ps1 -Exe build\dist\pojia-ce.exe -Pfx D:\certs\pojia-signing.pfx
#   .\sign-windows.ps1 -Exe build\dist\pojia-ce.exe -Pfx ... -Password 'xxx' -NoTimestamp
#
# 不传 -Password 就从 pfx 同目录的 pojia-signing-密码.txt 读。
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$Pfx,
    [string]$Password = "",
    [switch]$NoTimestamp
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Exe)) { throw "找不到 $Exe" }
if (-not (Test-Path -LiteralPath $Pfx)) { throw "找不到 $Pfx" }

if (-not $Password) {
    $side = Join-Path (Split-Path -Parent $Pfx) "pojia-signing-密码.txt"
    if (Test-Path -LiteralPath $side) {
        $Password = (Get-Content -LiteralPath $side -Raw).Trim()
    } else {
        throw "没给 -Password，同目录也没有 pojia-signing-密码.txt"
    }
}

# signtool 可能在 PATH 里，也可能在证书工具包里；两处都找一下。
$signtool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if (-not $signtool) {
    foreach ($p in @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "I:\Downloads\代码签名证书制作工具")) {
        if (Test-Path -LiteralPath $p) {
            $hit = Get-ChildItem -LiteralPath $p -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
                   Sort-Object FullName -Descending | Select-Object -First 1
            if ($hit) { $signtool = $hit.FullName; break }
        }
    }
}
if (-not $signtool) { throw "找不到 signtool.exe（装 Windows SDK，或把证书工具包里的那份加到 PATH）" }

$common = @("sign", "/f", $Pfx, "/p", $Password, "/fd", "sha256")
if (-not $NoTimestamp) {
    # 时间戳让签名在证书过期后仍然有效。自签证书照样能打 —— RFC 3161 的 TSA
    # 不校验签名者证书链。网络不通就退回不带时间戳，别让整条流水线卡死。
    & $signtool @common /tr "http://timestamp.digicert.com" /td sha256 $Exe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "时间戳失败（网络？），改为不带时间戳重签一次" -ForegroundColor Yellow
        & $signtool @common $Exe
    }
} else {
    & $signtool @common $Exe
}
if ($LASTEXITCODE -ne 0) { throw "签名失败（signtool 退出码 $LASTEXITCODE）" }

$sig = Get-AuthenticodeSignature -LiteralPath $Exe
Write-Host ""
Write-Host ("文件    : " + (Resolve-Path -LiteralPath $Exe).Path)
Write-Host ("签名类型: " + $sig.SignatureType)
Write-Host ("签名者  : " + $sig.SignerCertificate.Subject)
Write-Host ("状态    : " + $sig.Status)
if ($sig.Status -ne "Valid") {
    Write-Host "  状态不是 Valid 通常只是本机没信任这张自签根 —— 签名本身是好的。" -ForegroundColor Yellow
    Write-Host "  让本机信任：把 pojia-signing.cer 导入「受信任的根证书颁发机构」，或用 make-signing-cert.ps1 -Trust。" -ForegroundColor Yellow
}
