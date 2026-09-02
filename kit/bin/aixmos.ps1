<#
  aixmos - one command surface. Same commands on C:, on a stick, on the Mac.

    aixmos              where am I, what is up, what is broken
    aixmos lanes        every lane and whether it is here
    aixmos doctor       find drift before it bites
    aixmos ai "q"       ask the offline brain
    aixmos online       what the live side looks like
    aixmos manifest     rewrite MANIFEST.md from what is actually here
    aixmos replicate X: stage this kit onto a drive

  Nothing here hardcodes a path. Every lane comes from kit.json.
#>
param([Parameter(Position=0)][string]$Command = 'status',
      [Parameter(Position=1, ValueFromRemainingArguments=$true)][string[]]$Rest)

. (Join-Path (Split-Path $PSScriptRoot -Parent) 'lib\paths.ps1')

function Hd($t)  { Write-Host ''; Write-Host "  $t" -ForegroundColor Cyan; Write-Host "  $('-' * $t.Length)" -ForegroundColor DarkGray }
function Ok($t)  { Write-Host '  [ OK ] ' -ForegroundColor Green  -NoNewline; Write-Host $t }
function Bad($t) { Write-Host '  [FAIL] ' -ForegroundColor Red    -NoNewline; Write-Host $t }
function Warn($t){ Write-Host '  [warn] ' -ForegroundColor Yellow -NoNewline; Write-Host $t }
function Note($k,$v){ Write-Host ('  {0,-14}' -f $k) -ForegroundColor DarkGray -NoNewline; Write-Host $v }

function Test-Ollama {
    try { (Invoke-WebRequest "$($Kit.local_ai.endpoint)/api/tags" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { $false }
}
function Test-Online {
    try { (Invoke-WebRequest 'https://api.github.com' -UseBasicParsing -TimeoutSec 4).StatusCode -lt 500 } catch { $false }
}
function Get-OllamaModels {
    @((ollama list 2>$null | Select-Object -Skip 1) | ForEach-Object { ($_ -split '\s+')[0] } | Where-Object { $_ })
}

function Cmd-Status {
    $i = Get-KitInfo
    Hd 'AIXMOS KIT'
    Note 'Kit'          "$($i.Version)  ($($i.Mode))"
    Note 'Running from' $i.KitRoot
    Note 'Workspace'    $i.Workspace
    Note 'Machine'      $env:COMPUTERNAME

    Hd 'LANES'
    foreach ($n in Get-KitLanes) {
        $p = Get-KitLane $n
        if (Test-Path $p) { Ok ('{0,-14} {1}' -f $n, $p) }
        else              { Warn ('{0,-14} not here: {1}' -f $n, $p) }
    }

    Hd 'OFFLINE BRAIN'
    if (Test-Ollama) { Ok "ollama up - $((Get-OllamaModels) -join ', ')" }
    else             { Bad "ollama not answering on $($Kit.local_ai.endpoint)" }

    Hd 'LIVE SIDE'
    if (Test-Online) { Ok 'internet reachable' } else { Warn 'offline - local lanes still work' }
    Note 'supabase' $Kit.online.supabase.project_ref
    Note 'vercel'   "$($Kit.online.vercel.team)  ($($Kit.online.vercel.projects.Count) projects)"

    Write-Host ''
    Write-Host '  aixmos doctor   find drift before it bites' -ForegroundColor DarkGray
    Write-Host ''
}

function Cmd-Lanes {
    Hd 'LANES (from kit.json)'
    foreach ($n in Get-KitLanes) {
        $l = $Kit.lanes.$n
        $p = Get-KitLane $n
        $tag = @()
        if ($l.private) { $tag += 'PRIVATE' }
        if ($l.secrets) { $tag += 'SECRETS' }
        if ($l.app)     { $tag += 'APP' }
        Write-Host ('  {0,-14} ' -f $n) -ForegroundColor White -NoNewline
        Write-Host $l.role -ForegroundColor Gray
        Write-Host ('  {0,-14} {1}' -f '', $p) -ForegroundColor DarkGray -NoNewline
        if ($tag) { Write-Host ("   [$($tag -join ' ')]") -ForegroundColor Yellow } else { Write-Host '' }
    }
    Hd 'RETIRED - do not point anything here'
    foreach ($r in Get-KitRetired) {
        Write-Host "  $($r.Path)" -ForegroundColor DarkGray -NoNewline
        if (Test-Path $r.Path) { Write-Host '   (still on disk)' -ForegroundColor Yellow }
        else                   { Write-Host '   (gone)' -ForegroundColor DarkGray }
        Write-Host "      -> use lane '$($r.ReplacedBy)'" -ForegroundColor DarkGray
    }
    Write-Host ''
}

function Cmd-Doctor {
    $problems = 0
    Hd 'DOCTOR'

    # 1. Anything still pointing at a retired path. This is the check that would
    #    have caught eight broken scripts on 2026-09-01 the day they broke,
    #    instead of weeks later when a command quietly did nothing.
    Write-Host '  scripts pointing at retired lanes' -ForegroundColor White
    $scanRoots = @(
        @($Kit.scan_lanes) | ForEach-Object { Get-KitLane $_ }
        @($Kit.scan_extra) | ForEach-Object { Join-Path $Workspace $_ }
    ) | Where-Object { $_ -and (Test-Path $_) }
    $retired = @(Get-KitRetired)
    $hits = 0
    foreach ($root in $scanRoots) {
        $files = Get-ChildItem $root -Recurse -File -Include *.ps1,*.bat,*.cmd,*.vbs,*.sh -ErrorAction SilentlyContinue |
                 Where-Object { $_.FullName -notlike '*\node_modules\*' -and $_.FullName -notlike '*\.git\*' }
        foreach ($f in $files) {
            $txt = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
            if (-not $txt) { continue }
            foreach ($r in $retired) {
                if (-not $txt.Contains($r.Path)) { continue }
                # TMMT-canon also contains the string "TMMT" - only flag a hit
                # where the retired path is not the prefix of a longer name.
                # Skip comments. A note explaining that a path is dead is the
                # opposite of a script still pointing at it.
                $bad = @($txt -split "`n" | Where-Object {
                    $_.Contains($r.Path) -and
                    $_ -notmatch ([regex]::Escape($r.Path) + '[-\w]') -and
                    $_.TrimStart() -notlike '#*'
                })
                if ($bad) {
                    Bad ("{0}  ->  {1}" -f $f.FullName.Replace($Workspace, '~'), $r.Path)
                    $hits++; $problems++
                }
            }
        }
    }
    if (-not $hits) { Ok 'none - every script resolves through kit.json' }

    # 2. Lanes that should be here and are not.
    Write-Host ''
    Write-Host '  lanes present' -ForegroundColor White
    $missing = 0
    foreach ($n in Get-KitLanes) {
        if (-not (Test-KitLane $n)) { Warn "$n missing at $(Get-KitLane $n)"; $missing++; $problems++ }
    }
    if (-not $missing) { Ok 'all lanes accounted for' }

    # 3. Uncommitted work is work that exists on exactly one machine.
    Write-Host ''
    Write-Host '  repos' -ForegroundColor White
    foreach ($n in Get-KitLanes) {
        $p = Get-KitLane $n
        if (-not (Test-Path (Join-Path $p '.git'))) { continue }
        Push-Location $p
        $dirty = @(git status --porcelain 2>$null).Count
        $br    = git rev-parse --abbrev-ref HEAD 2>$null
        $ahead = git rev-list --count '@{u}..HEAD' 2>$null
        Pop-Location
        $unpushed = 0
        if ($ahead) { [int]::TryParse($ahead, [ref]$unpushed) | Out-Null }
        if ($dirty -gt 0 -or $unpushed -gt 0) {
            Warn ('{0,-14} {1}  {2} uncommitted, {3} unpushed' -f $n, $br, $dirty, $unpushed)
            $problems++
        } else {
            Ok ('{0,-14} {1}  clean' -f $n, $br)
        }
    }

    # 4. Offline brain - the whole point of booting from a stick with no wifi.
    Write-Host ''
    Write-Host '  offline brain' -ForegroundColor White
    if (Test-Ollama) {
        $have = Get-OllamaModels
        foreach ($m in $Kit.local_ai.models) {
            if ($have -contains $m.name) { Ok $m.name }
            else { Warn "$($m.name) missing - pull or rebuild it"; $problems++ }
        }
    } else { Bad 'ollama down - the kit cannot answer offline'; $problems++ }

    # 5. Schema drift. The repo is what you can rebuild from; the live DB is
    #    what pays. When they disagree, the repo is the one that is lying.
    Write-Host ''
    Write-Host '  schema drift (repo vs live)' -ForegroundColor White
    $mig = Join-Path (Get-KitLane canon) 'supabase\migrations'
    if (Test-Path $mig) {
        $repoCount = @(Get-ChildItem $mig -Filter *.sql -File -ErrorAction SilentlyContinue).Count
        $live      = [int]$Kit.online.supabase.live_migrations
        if ($repoCount -lt $live) {
            Bad "repo has $repoCount migrations, live has $live - $($live - $repoCount) went straight to prod"
            $problems++
        } else { Ok "repo $repoCount / live $live" }
    } else { Warn 'no migrations folder in canon'; $problems++ }

    Write-Host ''
    if ($problems -eq 0) { Ok 'clean' } else { Warn "$problems thing(s) want attention" }
    Write-Host ''
}

function Cmd-Ai {
    $q = ($Rest -join ' ').Trim()
    if (-not $q) { Bad 'aixmos ai "your question"'; return }
    if (-not (Test-Ollama)) { Bad 'offline brain is down - start Ollama'; return }
    $model = $Kit.local_ai.models[0].name
    Hd "OFFLINE BRAIN ($model)"
    $body = @{ model = $model; prompt = $q; stream = $false } | ConvertTo-Json
    try {
        $r = Invoke-RestMethod "$($Kit.local_ai.endpoint)/api/generate" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 300
        Write-Host ''
        ($r.response -split "`n") | ForEach-Object { Write-Host "  $_" }
    } catch { Bad "failed: $($_.Exception.Message)" }
    Write-Host ''
}

function Cmd-Online {
    Hd 'LIVE SIDE'
    if (-not (Test-Online)) { Warn 'no internet right now - this is the last known map' }
    $s = $Kit.online.supabase
    Note 'supabase'   "$($s.project_ref)  pg$($s.postgres)  $($s.region)"
    Note 'migrations' "live $($s.live_migrations)  /  repo $($s.repo_migrations)"
    Note 'serves'     ($s.serves -join ', ')
    Write-Host ''
    Note 'vercel team' $Kit.online.vercel.team
    foreach ($p in $Kit.online.vercel.projects) { Write-Host "                 $p" -ForegroundColor DarkGray }
    Warn $Kit.online.vercel.deploy
    Write-Host ''
    Note 'mesh core' ($Kit.online.mesh.core -join ', ')
    if (Get-Command tailscale -ErrorAction SilentlyContinue) {
        if (tailscale status 2>$null) { Ok 'tailscale up' } else { Warn 'tailscale not running' }
    }
    Hd 'GATES'
    foreach ($g in $Kit.gates.PSObject.Properties) {
        Write-Host ('  {0,-9} {1}' -f $g.Name, $g.Value) -ForegroundColor Yellow
    }
    Write-Host ''
}

function Cmd-Manifest {
    $out = Join-Path $KitRoot 'MANIFEST.md'
    $i   = Get-KitInfo
    $sb  = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine('# AIXMOS KIT - MANIFEST')
    [void]$sb.AppendLine("_generated $(Get-Date -Format 'yyyy-MM-dd HH:mm') on $env:COMPUTERNAME - kit $($i.Version) ($($i.Mode))_")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("Workspace: ``$($i.Workspace)``")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('| lane | path | here | git | role |')
    [void]$sb.AppendLine('|---|---|---|---|---|')
    foreach ($n in Get-KitLanes) {
        $p    = Get-KitLane $n
        $here = if (Test-Path $p) { 'yes' } else { 'no' }
        $g    = ''
        if (Test-Path (Join-Path $p '.git')) {
            Push-Location $p
            $g = "$(git rev-parse --abbrev-ref HEAD 2>$null) - $(@(git status --porcelain 2>$null).Count) dirty"
            Pop-Location
        }
        [void]$sb.AppendLine("| $n | ``$p`` | $here | $g | $($Kit.lanes.$n.role) |")
    }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Offline brain')
    if (Test-Ollama) {
        foreach ($l in ((ollama list 2>$null) | Select-Object -Skip 1)) { if ($l) { [void]$sb.AppendLine("- ``$l``") } }
    } else { [void]$sb.AppendLine('- ollama was not running at scan time') }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Retired - never point a script here')
    foreach ($r in Get-KitRetired) {
        [void]$sb.AppendLine("- ``$($r.Path)`` -> lane ``$($r.ReplacedBy)``. $($r.Reason)")
    }
    $sb.ToString() | Out-File -Encoding utf8 $out
    Ok "wrote $out"
}

function Cmd-Replicate {
    $target = ($Rest | Select-Object -First 1)
    if (-not $target) {
        Hd 'REPLICATE'
        Write-Host '  aixmos replicate E:      stage the kit onto that drive' -ForegroundColor Gray
        Write-Host ''
        Write-Host '  Attached drives:' -ForegroundColor White
        $vols = @(Get-Volume | Where-Object { $_.DriveLetter -and "$($_.DriveLetter)" -ne 'C' })
        if ($vols) { $vols | ForEach-Object { Write-Host ("    {0}:  {1}" -f $_.DriveLetter, $_.FileSystemLabel) } }
        else { Write-Host '    (none attached)' -ForegroundColor DarkGray }
        Write-Host ''
        return
    }
    $letter = ($target -replace '[:\\]', '').Substring(0,1)
    $root   = "${letter}:\"
    if (-not (Test-Path $root)) { Bad "$root is not attached"; return }
    $dest = Join-Path $root 'AIXMOS-KIT'
    Hd "REPLICATE -> $dest"
    # Copy, never mirror. A stick is the backup of last resort, and deleting on
    # it to match this machine is the one failure worth engineering out.
    robocopy $KitRoot $dest /E /XD payload /R:1 /W:1 /NP /NFL /NDL /NJH /NJS | Out-Null
    if (Test-Path (Join-Path $dest 'bin\aixmos.ps1')) {
        Ok "kit staged at $dest"
        Write-Host "  On that machine:  powershell -ExecutionPolicy Bypass -File $dest\bin\aixmos.ps1" -ForegroundColor DarkGray
    } else { Bad 'copy did not land' }
    Write-Host ''
}

function Cmd-Help {
    Hd 'AIXMOS - ONE COMMAND SURFACE, EVERY MACHINE'
    $rows = [ordered]@{
        'aixmos'              = 'where am I, what is up, what is missing'
        'aixmos lanes'        = 'every lane, where it resolves, what is retired'
        'aixmos doctor'       = 'find drift: dead paths, dirty repos, schema gap'
        'aixmos ai "q"'       = 'ask the offline brain (no internet needed)'
        'aixmos online'       = 'the live side + the owner gates'
        'aixmos manifest'     = 'rewrite MANIFEST.md from what is actually here'
        'aixmos replicate E:' = 'stage this kit onto a drive'
        'aixmos help'         = 'this'
    }
    foreach ($k in $rows.Keys) {
        Write-Host ('  {0,-22}' -f $k) -ForegroundColor White -NoNewline
        Write-Host $rows[$k] -ForegroundColor Gray
    }
    Write-Host ''
    Write-Host '  Every path comes from kit.json. Change a lane there, not in a script.' -ForegroundColor DarkGray
    Write-Host ''
}

switch -Regex ($Command.ToLower()) {
    '^(status|)$'           { Cmd-Status }
    '^lanes?$'              { Cmd-Lanes }
    '^doctor$'              { Cmd-Doctor }
    '^(ai|ask)$'            { Cmd-Ai }
    '^online$'              { Cmd-Online }
    '^manifest$'            { Cmd-Manifest }
    '^replicate$'           { Cmd-Replicate }
    '^(help|-h|--help|\?)$' { Cmd-Help }
    default { Bad "unknown: $Command"; Cmd-Help }
}
