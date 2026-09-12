# RESEAL-AIXMOS.ps1 - OWNER. Seal NEW content into VAULT/aixmos-work.xv under your
# EXISTING content key. Every drive you already issued keeps opening: same key, new content.
# Runs on the MASTER stick (the one holding _OWNER/issuer.bundle). Needs your issuer passphrase.
#
#   RESEAL-AIXMOS.ps1 -From C:\AIXMOS-RESALE\sealed
#
# NEW-ISSUER seals content once, when the identity is created. This is the "update the
# product" step that comes after it.
#
# Afterwards copy VAULT/aixmos-work.xv onto every issued drive: ISSUE-AIXMOS only copies
# it when the drive has none, so it will not refresh an older one.
param([Parameter(Mandatory=$true)][string]$From)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$Root/tools/xcrypto.ps1"

Write-Host '=== PROJECT X : RESEAL AIXMOS CONTENT ===' -ForegroundColor Cyan
if (-not (Test-Path "$Root/_OWNER/issuer.bundle")) { throw 'No issuer identity here. Run this on the master stick.' }
if (-not (Test-Path $From)) { throw "$From not found." }

# Protect-XFile seals in memory and .NET arrays stop at 2 GB. Models stay out of the
# vault; they are open-licensed and ship unsealed next to it.
$size = (Get-ChildItem $From -Recurse -File -Force | Measure-Object Length -Sum).Sum
if ($size -gt 1.5GB) { throw ('{0:N2} GB is too big to seal in one piece (limit 1.5 GB). Leave the AI models out.' -f ($size / 1GB)) }
Write-Host ('Sealing {0:N2} GB from {1}' -f ($size / 1GB), $From)

$sp   = Read-Host 'Issuer passphrase' -AsSecureString
$pass = [Runtime.InteropServices.Marshal]::PtrToStringUni([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sp))
$tmp  = "$Root/_OWNER/.u.tmp"
try {
    Unprotect-XFile "$Root/_OWNER/issuer.bundle" $tmp $pass
    $ckHex = (Get-Content $tmp -Raw | ConvertFrom-Json).ck
} finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
}
if (-not $ckHex) { throw 'issuer.bundle has no content key.' }

$zip   = Join-Path ([IO.Path]::GetTempPath()) ('aixmos-work-{0}.zip' -f [guid]::NewGuid())
$check = "$zip.check"
$out   = "$Root/VAULT/aixmos-work.xv"
try {
    Compress-Archive -Path (Join-Path $From '*') -DestinationPath $zip -CompressionLevel Optimal
    New-Item -ItemType Directory -Force "$Root/VAULT" | Out-Null
    Protect-XFile $zip "$out.new" $ckHex
    # Prove the new vault opens with the same key before it replaces the old one.
    Unprotect-XFile "$out.new" $check $ckHex
    if ((Get-FileHash $check).Hash -ne (Get-FileHash $zip).Hash) { throw 'Round-trip check failed. Vault NOT replaced.' }
    if (Test-Path $out) { Copy-Item $out "$out.prev" -Force }
    Move-Item "$out.new" $out -Force
} finally {
    foreach ($f in $zip, $check, "$out.new") { if (Test-Path $f) { Remove-Item $f -Force } }
}

Write-Host ''
Write-Host 'RESEALED. Existing licenses still open it.' -ForegroundColor Green
Write-Host '  Previous vault kept as VAULT/aixmos-work.xv.prev'
Write-Host '  Next: copy VAULT/aixmos-work.xv onto each issued drive (PROJECT-X/VAULT/).'
