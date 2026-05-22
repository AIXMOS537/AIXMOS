#Requires -Version 5.1
# Create 60TB NAS folder tree on mapped drive W: (or NAS_MOUNT_PATH)
param([string]$Root = $env:NAS_MOUNT_PATH)

if (-not $Root) {
    if (Test-Path "W:\") { $Root = "W:\" }
    elseif (Test-Path "Z:\") { $Root = "Z:\" }
    else { Write-Error "Map NAS first (net use W: \\UGREEN-NAS\AI-OPS). Or pass -Root W:\"; exit 1 }
}

$folders = @(
    "hot\knowledge", "hot\projects", "hot\voice-notes",
    "life\inbox", "life\inbox\processed", "life\inbox\voice\pending", "life\inbox\voice\approved",
    "life\tasks", "life\comms\drafts\pending", "life\comms\drafts\sent", "life\journal\recaps",
    "life\decisions", "life\meetings\transcripts", "life\meetings\actions",
    "life\comms\drafts", "life\relationships",
    "work\strategy", "work\tasks", "work\clients", "work\meetings", "work\projects",
    "knowledge\sops", "knowledge\policies", "knowledge\templates\comms", "knowledge\faq",
    "archive\life", "archive\work", "archive\media",
    "vault\exports", "backups\ai-ops", "models\ollama",
    "exports\open-webui", "exports\n8n",
    "locations\home\operators\brainiac-7\inbox",
    "locations\home\operators\brainiac-7\tasks",
    "locations\hq\operators\brainiac-6-hq-taha\inbox",
    "locations\hq\operators\brainiac-6-hq-taha\tasks",
    "locations\hq\operators\brainiac-5-hq-kayleigh\inbox",
    "locations\hq\operators\brainiac-5-hq-kayleigh\tasks",
    "locations\hq\operators\brainiac-5-hq-tahir\inbox",
    "locations\hq\operators\brainiac-4-hq-claryn",
    "locations\hq\operators\brainiac-4-hq-dominique",
    "locations\hq\operators\brainiac-4-hq-michael",
    "locations\hq\operators\brainiac-3-hq-dyson",
    "locations\hq\operators\brainiac-5-hq-tayyeba\inbox",
    "locations\hq\operators\brainiac-5-hq-tayyeba\tasks",
    "locations\hq\operators\brainiac-3-hq-nathan",
    "locations\hq\operators\brainiac-2-hq-shared",
    "locations\hq\exports", "locations\hq\escalations"
)

foreach ($f in $folders) {
    $p = Join-Path $Root $f
    New-Item -ItemType Directory -Force -Path $p | Out-Null
    Write-Host "[OK] $p"
}

$readme = @"
# AI-OPS NAS (60TB)
System of record for three executives: Oracle, Operator, Counsel.
See nas/folder-structure-60tb.md in the kit.
"@
Set-Content -Path (Join-Path $Root "README.md") -Value $readme
Write-Host "`nNAS layout ready at $Root"
