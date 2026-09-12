<#
  bootstick - one stick that carries everything TMMT and JARVIS need.

    aixmos bootstick stage           build or refresh the payload on C: (no stick needed)
    aixmos bootstick grab-boot       copy the Debian Live boot files off an attached master stick
    aixmos bootstick write E         copy the payload onto stick E: - additive, never deletes
    aixmos bootstick write E format  WIPE that USB stick into BOOT (FAT32) + DATA (exFAT), then write
    aixmos bootstick write E vault   also carry Personal-Brain into _VAULT (home-only sticks)
    aixmos bootstick check [E]       verify the stage or a stick: lanes, runtimes, models, no secrets

  Two ways to use the result:
    - plug it into any running Windows PC and run START-HERE.bat (nothing gets installed)
    - boot the Surface from it (Debian Live) with no Windows at all

  Bare words, not -Flags: aixmos.ps1 forwards its remaining arguments, and a
  leading -Flag gets eaten by its binder. "format" survives the trip.

  Every source path comes from kit.json or from where a tool is actually
  installed (Get-Command). Nothing here hardcodes a machine path.
#>
$ErrorActionPreference = 'Continue'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'lib\paths.ps1')

$words  = @($args | ForEach-Object { "$_".Trim().TrimStart('-').ToLower() } | Where-Object { $_ })
$Action = if ($words.Count) { $words[0] } else { 'help' }
$Drive  = $words | Select-Object -Skip 1 | Where-Object { $_ -match '^[a-z]:?\\?$' } | Select-Object -First 1
if ($Drive) { $Drive = $Drive.Substring(0, 1).ToUpper() }
$Format = $words -contains 'format'
$Vault  = ($words -contains 'vault') -or ($words -contains 'includevault')

$B     = $Kit.bootstick
$Stage = $B.stage -replace '/', '\'
$FAT32_MAX = 4294967295
$script:Failures = 0

function Hd($t)  { Write-Host ''; Write-Host "  $t" -ForegroundColor Cyan; Write-Host "  $('-' * $t.Length)" -ForegroundColor DarkGray }
function Ok($t)  { Write-Host '  [ OK ] ' -ForegroundColor Green  -NoNewline; Write-Host $t }
function Bad($t) { Write-Host '  [FAIL] ' -ForegroundColor Red    -NoNewline; Write-Host $t }
function Warn($t){ Write-Host '  [warn] ' -ForegroundColor Yellow -NoNewline; Write-Host $t }
function Note($k,$v){ Write-Host ('  {0,-14}' -f $k) -ForegroundColor DarkGray -NoNewline; Write-Host $v }
function Rel($p) { ($p -replace '/', '\') }

function Size-Bytes([string]$Path) {
    if (-not (Test-Path $Path)) { return 0 }
    $s = (Get-ChildItem $Path -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if ($s) { [int64]$s } else { 0 }
}
function GB($bytes) { '{0:N2} GB' -f ($bytes / 1GB) }

function Copy-Tree([string]$Src, [string]$Dst, [string[]]$Xd = @(), [string[]]$Xf = @(), [string[]]$More = @()) {
    # /E copy everything incl. empty dirs · /XO skip what is already current ·
    # /XJ never follow junctions (Documents\My Music loops back on itself).
    # Copy, never mirror: a stick is the backup of last resort.
    $a  = @($Src, $Dst, '/E', '/XO', '/XJ', '/R:1', '/W:1', '/NP', '/NFL', '/NDL', '/NJH', '/NJS')
    $Xd = @($Xd | Where-Object { $_ }); $Xf = @($Xf | Where-Object { $_ })
    if ($Xd.Count) { $a += '/XD'; $a += $Xd }
    if ($Xf.Count) { $a += '/XF'; $a += $Xf }
    $a += @($More | Where-Object { $_ })
    & robocopy @a | Out-Null
    $c = $LASTEXITCODE
    if ($c -ge 8) { Bad "$Src -> $Dst  (robocopy exit $c)"; $script:Failures++ }
    else          { Ok ('{0,-52} {1}' -f $Dst, (GB (Size-Bytes $Dst))) }
}

function Test-Admin {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Lanes that go on the stick: everything except private ones, and not lanes that
# already ride inside another (tmmt-os lives inside CommandCenter).
function Get-StickLanes {
    $names = @(Get-KitLanes | Where-Object { -not $Kit.lanes.$_.private })
    foreach ($n in $names) {
        $l = $Kit.lanes.$n
        $outer = @($names | Where-Object { $_ -ne $n -and $l.local.StartsWith($Kit.lanes.$_.local + '/') })
        if (-not $outer.Count) { $n }
    }
}

# ---------------------------------------------------------------- stage
function Do-Stage {
    if ($KitMode -ne 'local') { Bad 'stage runs from the installed kit on the machine that has the work, not from a stick.'; return }
    Hd "STAGE -> $Stage"
    New-Item -ItemType Directory -Force $Stage | Out-Null
    $xdBase = @($B.exclude_dirs)
    $xfBase = @($B.exclude_files)

    Write-Host '  lanes' -ForegroundColor White
    foreach ($n in Get-StickLanes) {
        $l   = $Kit.lanes.$n
        $src = Get-KitLane $n
        if (-not (Test-Path $src)) { Warn "$n - source missing: $src"; continue }
        $xd = $xdBase + @(@($B.exclude_dirs_extra.$n) | Where-Object { $_ } | ForEach-Object { Join-Path $src (Rel $_) })
        $xf = $xfBase + @(@($B.exclude_files_extra.$n) | Where-Object { $_ })
        Copy-Tree $src (Join-Path $Stage (Rel $l.drive)) $xd $xf
    }

    Write-Host ''
    Write-Host '  extras' -ForegroundColor White
    foreach ($e in $B.extras) {
        $src = Join-Path $Workspace (Rel $e.local)
        if (-not (Test-Path $src)) { Warn "$($e.local) - not here, skipped"; continue }
        Copy-Tree $src (Join-Path $Stage (Rel $e.drive)) $xdBase $xfBase
    }

    Write-Host ''
    Write-Host '  runtimes (Windows: copied from what is installed here; Linux ollama: official release, unpacked by extract-linux-ollama.py)' -ForegroundColor White
    foreach ($p in $B.runtimes.PSObject.Properties) {
        $r   = $p.Value
        $cmd = Get-Command $r.find -CommandType Application -ErrorAction SilentlyContinue |
               Where-Object { $_.Source -notlike '*\WindowsApps\*' } | Select-Object -First 1
        if (-not $cmd) { Warn "$($p.Name) - not installed on this machine, not carried"; continue }
        $dir = Split-Path $cmd.Source -Parent
        for ($i = 0; $i -lt [int]$r.up; $i++) { $dir = Split-Path $dir -Parent }
        $dst = Join-Path $Stage (Rel $r.drive)
        if ($r.only) {
            New-Item -ItemType Directory -Force $dst | Out-Null
            & robocopy $dir $dst @($r.only) /XO /R:1 /W:1 /NP /NFL /NDL /NJH /NJS | Out-Null
            if ($LASTEXITCODE -ge 8) { Bad "$($p.Name) copy failed"; $script:Failures++ } else { Ok ('{0,-52} {1}' -f $dst, (GB (Size-Bytes $dst))) }
        } else {
            Copy-Tree $dir $dst @($r.xd) @($r.xf)
        }
    }

    $lo = Join-Path $Workspace (Rel $B.linux_ollama.local)
    if (Test-Path (Join-Path $lo (Rel $B.linux_ollama.exe))) { Copy-Tree $lo (Join-Path $Stage (Rel $B.linux_ollama.drive)) }
    else { Warn "linux ollama not at $lo - the booted side will have no brain" }

    Write-Host ''
    Write-Host '  offline brain (ollama models)' -ForegroundColor White
    Copy-Tree (Join-Path $Workspace (Rel $Kit.local_ai.store)) (Join-Path $Stage (Rel $B.models))

    Write-Host ''
    Write-Host '  launchers' -ForegroundColor White
    Copy-Tree (Join-Path $KitRoot 'payload\stick') $Stage

    # Belt and braces: anything that must never ride, removed from the stage
    # even if a future copy rule lets it through.
    foreach ($s in $B.strip) {
        $f = Join-Path $Stage (Rel $s)
        if (Test-Path $f) { Remove-Item $f -Force; Ok "stripped $s" }
    }

    if (Test-Path (Join-Path $Stage '_BOOT\live')) { Ok 'boot payload already staged (_BOOT)' }
    else { Warn 'no boot payload yet - plug in AIXMOS02 or CYBORG and run: aixmos bootstick grab-boot' }

    Write-Manifest $Stage
    Do-Check $Stage
}

function Write-Manifest([string]$Root) {
    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine('AIXMOS BOOT STICK - MANIFEST')
    [void]$sb.AppendLine("built   $(Get-Date -Format 'yyyy-MM-dd HH:mm') on $env:COMPUTERNAME  (kit $($Kit.version))")
    [void]$sb.AppendLine('')
    foreach ($d in Get-ChildItem $Root -Directory -Force) {
        [void]$sb.AppendLine(('{0,-16} {1}' -f $d.Name, (GB (Size-Bytes $d.FullName))))
    }
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('NOT on this stick, on purpose:')
    [void]$sb.AppendLine('  - live production keys (tmmt-os .env.local, TMMT-canon .env, JARVIS settings.json)')
    [void]$sb.AppendLine('  - node_modules / .next (npm ci restores them)')
    [void]$sb.AppendLine('  - Personal-Brain, unless the stick was written with "vault"')
    [void]$sb.AppendLine('  - the live Supabase database (it lives online; the stick carries code + history)')
    $sb.ToString() | Out-File -Encoding utf8 (Join-Path $Root 'STICK-MANIFEST.txt')
}

# ---------------------------------------------------------------- grab-boot
function Do-GrabBoot {
    $cands = @(Get-Volume | Where-Object { $_.DriveLetter -and "$($_.DriveLetter)" -ne 'C' } |
               Where-Object { Test-Path "$($_.DriveLetter):\live\filesystem.squashfs" })
    if ($Drive) { $cands = @($cands | Where-Object { "$($_.DriveLetter)" -eq $Drive }) }
    if (-not $cands.Count) {
        Bad 'No attached drive carries a Debian Live boot (live\filesystem.squashfs).'
        Write-Host '  Plug in AIXMOS02 or CYBORG (both are bootable masters) and run this again.' -ForegroundColor DarkGray
        return
    }
    $v   = $cands[0]
    $src = "$($v.DriveLetter):\"
    $dst = Join-Path $Stage '_BOOT'
    Hd "GRAB BOOT  $src ($($v.FileSystemLabel)) -> $dst"
    foreach ($d in $B.boot_dirs) {
        if (Test-Path (Join-Path $src $d)) { Copy-Tree (Join-Path $src $d) (Join-Path $dst $d) }
    }
    $files = @($B.boot_files | Where-Object { Test-Path (Join-Path $src $_) })
    if ($files.Count) { & robocopy $src $dst @files /XO /R:1 /W:1 /NP /NFL /NDL /NJH /NJS | Out-Null }

    Write-Host '  verifying the live image (SHA-256)...' -ForegroundColor DarkGray
    $a = (Get-FileHash (Join-Path $src 'live\filesystem.squashfs') -Algorithm SHA256).Hash
    $b = (Get-FileHash (Join-Path $dst 'live\filesystem.squashfs') -Algorithm SHA256).Hash
    if ($a -eq $b) { Ok "filesystem.squashfs verified  $($a.Substring(0,16))..." }
    else           { Bad 'squashfs hash mismatch - delete _BOOT and grab again'; $script:Failures++ }
}

# ---------------------------------------------------------------- write
function Do-Write {
    if (-not $Drive) { Bad 'which stick?  aixmos bootstick write E'; Show-Drives; return }
    if ($Drive -eq 'C') { Bad 'C: is this machine. Refusing.'; return }
    if (-not (Test-Path (Join-Path $Stage 'AIXMOS-KIT\kit.json'))) { Bad "nothing staged at $Stage - run: aixmos bootstick stage"; return }

    $part = Get-Partition -DriveLetter $Drive -ErrorAction SilentlyContinue
    if (-not $part) { Bad "$Drive`: is not attached"; return }
    $disk = $part | Get-Disk
    if ($disk.IsSystem -or $disk.IsBoot) { Bad "$Drive`: is on the system disk. Refusing."; return }
    if ("$($disk.BusType)" -ne 'USB') { Bad "$Drive`: is a $($disk.BusType) disk, not USB. Refusing."; return }

    $bootRoot = $null; $dataRoot = $null
    if ($Format) {
        if (-not (Test-Path (Join-Path $Stage '_BOOT\live\filesystem.squashfs'))) {
            Bad 'format makes a BOOTABLE stick, and no boot payload is staged yet.'
            Write-Host '  Plug in AIXMOS02 or CYBORG and run: aixmos bootstick grab-boot' -ForegroundColor DarkGray
            return
        }
        if (-not (Test-Admin)) { Bad 'formatting needs an elevated PowerShell (Run as administrator).'; return }
        $gb = [math]::Round($disk.Size / 1GB, 1)
        Hd "FORMAT  disk $($disk.Number): $($disk.FriendlyName)  $gb GB"
        Write-Host '  EVERYTHING on this stick will be erased:' -ForegroundColor Red
        Get-Partition -DiskNumber $disk.Number | Where-Object DriveLetter | Get-Volume |
            ForEach-Object { Write-Host ("    {0}:  {1}  [{2}]  {3} used" -f $_.DriveLetter, $_.FileSystemLabel, $_.FileSystem, (GB ($_.Size - $_.SizeRemaining))) -ForegroundColor Red }
        $typed = Read-Host "  Type  WIPE $Drive  to continue"
        if ($typed -cne "WIPE $Drive") { Warn 'cancelled - nothing touched'; return }

        $bootGB = [math]::Max(4, [math]::Ceiling((Size-Bytes (Join-Path $Stage '_BOOT')) / 1GB) + 1)
        Clear-Disk -Number $disk.Number -RemoveData -RemoveOEM -Confirm:$false
        Initialize-Disk -Number $disk.Number -PartitionStyle GPT
        # UEFI firmware (the Surface included) only boots from FAT32, so the boot
        # side is a small FAT32 partition. The data side is exFAT so the 4.4 GB
        # 7B model - bigger than FAT32's 4 GB file limit - still fits.
        $p1 = New-Partition -DiskNumber $disk.Number -Size ([int64]$bootGB * 1GB) -AssignDriveLetter
        $p1 | Format-Volume -FileSystem FAT32 -NewFileSystemLabel $B.boot_label -Confirm:$false | Out-Null
        $p2 = New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
        $p2 | Format-Volume -FileSystem exFAT -NewFileSystemLabel $B.data_label -Confirm:$false | Out-Null
        Start-Sleep 2
        $bootRoot = "$((Get-Partition -DiskNumber $disk.Number -PartitionNumber $p1.PartitionNumber).DriveLetter):\"
        $dataRoot = "$((Get-Partition -DiskNumber $disk.Number -PartitionNumber $p2.PartitionNumber).DriveLetter):\"
        Ok "BOOT $bootRoot ($bootGB GB FAT32)   DATA $dataRoot (exFAT)"
    } else {
        # A stick written with "format" earlier has both halves - find them by label.
        $vols = @(Get-Partition -DiskNumber $disk.Number | Where-Object DriveLetter | Get-Volume)
        $bv = $vols | Where-Object { $_.FileSystemLabel -eq $B.boot_label } | Select-Object -First 1
        $dv = $vols | Where-Object { $_.FileSystemLabel -eq $B.data_label } | Select-Object -First 1
        if ($bv -and $dv) { $bootRoot = "$($bv.DriveLetter):\"; $dataRoot = "$($dv.DriveLetter):\" }
        else              { $bootRoot = "$Drive`:\";           $dataRoot = "$Drive`:\" }
    }

    $dataVol = Get-Volume -DriveLetter $dataRoot.Substring(0,1)
    $bootVol = Get-Volume -DriveLetter $bootRoot.Substring(0,1)
    $dataFat = "$($dataVol.FileSystem)" -eq 'FAT32'
    Hd "WRITE  $Stage  ->  $dataRoot  [$($dataVol.FileSystem)]"

    # FAT32 cannot hold a file over 4 GB. Leave those off, and leave off the model
    # manifests that point at them so Ollama never lists a model it cannot load.
    $more = @('/FFT')
    $xfBig = @()
    if ($dataFat) {
        $more += "/MAX:$FAT32_MAX"
        $mroot = Join-Path $Stage (Rel $B.models)
        foreach ($m in Get-ChildItem (Join-Path $mroot 'manifests') -Recurse -File -ErrorAction SilentlyContinue) {
            $j = Get-Content $m.FullName -Raw | ConvertFrom-Json
            $big = @(@($j.layers) + @($j.config) | Where-Object { $_.size -gt $FAT32_MAX })
            if ($big.Count) { $xfBig += $m.FullName; Warn "$($m.Directory.Name):$($m.Name) left off - its $(GB $big[0].size) file will not fit on FAT32 (use 'format' for exFAT)" }
        }
    }

    $need = (Size-Bytes $Stage) - (Size-Bytes (Join-Path $Stage '_BOOT'))
    if ($dataFat) { $need -= (Get-ChildItem $Stage -Recurse -File -Force | Where-Object Length -gt $FAT32_MAX | Measure-Object Length -Sum).Sum }
    $have = (Get-Volume -DriveLetter $dataRoot.Substring(0,1)).SizeRemaining
    Note 'needs' "up to $(GB $need) (less if some is already there)"
    Note 'free'  (GB $have)
    $existing = Size-Bytes (Join-Path $dataRoot 'TMMT-WORK')
    if ($need - $existing -gt $have) { Bad 'not enough room on the stick. Use a bigger stick, or free space on it first.'; return }

    Copy-Tree $Stage $dataRoot @((Join-Path $Stage '_BOOT')) $xfBig $more

    if ($Vault) {
        $src = Get-KitLane vault
        if (Test-Path $src) { Copy-Tree $src (Join-Path $dataRoot (Rel $Kit.lanes.vault.drive)) @() @() @('/FFT') }
        else { Warn 'vault requested but Personal-Brain is not on this machine' }
    }

    # Boot side. Never overwrite a boot that is already there.
    $bootFat = "$($bootVol.FileSystem)" -eq 'FAT32'
    if (Test-Path (Join-Path $bootRoot 'live\filesystem.squashfs')) {
        Ok "$bootRoot already boots - boot files left as they are"
    } elseif (-not $bootFat) {
        Warn "$bootRoot is $($bootVol.FileSystem): it runs as a plug-in stick, but cannot BOOT a Surface (UEFI needs FAT32)."
        Write-Host "  To make it bootable: aixmos bootstick write $Drive format   (erases the stick)" -ForegroundColor DarkGray
    } elseif (-not (Test-Path (Join-Path $Stage '_BOOT\live'))) {
        Warn 'no boot payload staged - plug-in use only for now. Run: aixmos bootstick grab-boot'
    } else {
        Copy-Tree (Join-Path $Stage '_BOOT') $bootRoot @() @() @('/FFT')
    }
    if ($bootRoot -ne $dataRoot) {
        # So the booted side can find its launcher and the instructions.
        & robocopy $Stage $bootRoot 'READ-ME-FIRST.txt' 'BOOTED-START-JARVIS.sh' /FFT /R:1 /W:1 /NP /NFL /NDL /NJH /NJS | Out-Null
    }

    Do-Check $dataRoot
}

# ---------------------------------------------------------------- check
function Do-Check([string]$Root) {
    Hd "CHECK  $Root"
    $bad = 0

    Write-Host '  lanes' -ForegroundColor White
    foreach ($n in Get-StickLanes) {
        $p = Join-Path $Root (Rel $Kit.lanes.$n.drive)
        if (Test-Path $p) { Ok $n } else { Bad "$n missing ($p)"; $bad++ }
    }
    $vp = Join-Path $Root (Rel $Kit.lanes.vault.drive)
    if (Test-Path $vp) { Warn 'vault present - this stick carries PERSONAL material, keep it home' }

    Write-Host ''
    Write-Host '  runtimes' -ForegroundColor White
    foreach ($p in $B.runtimes.PSObject.Properties) {
        $exe = Join-Path (Join-Path $Root (Rel $p.Value.drive)) (Rel $p.Value.exe)
        if (Test-Path $exe) { Ok $p.Name } else { Bad "$($p.Name) missing ($exe)"; $bad++ }
    }
    $lx = Join-Path (Join-Path $Root (Rel $B.linux_ollama.drive)) (Rel $B.linux_ollama.exe)
    if (Test-Path $lx) { Ok "ollama (linux $($B.linux_ollama.release), for the booted side)" }
    else { Warn 'no linux ollama - booted JARVIS would have no brain' }

    Write-Host ''
    Write-Host '  JARVIS' -ForegroundColor White
    $j = Join-Path (Join-Path $Root (Rel $Kit.lanes.automation.drive)) 'project-aixmos'
    foreach ($f in 'project_aixmos_server.py', 'vendor\requests', 'aixmos', 'memory\kit', 'whisper\models') {
        if (Test-Path (Join-Path $j $f)) { Ok $f } else { Bad "$f missing"; $bad++ }
    }
    foreach ($k in 'windows', 'mac_linux', 'readme') {
        $f = Join-Path $Root (Rel $B.installer.$k)
        if (Test-Path $f) { Ok "installer $k  $(Split-Path $f -Leaf)" } else { Warn "installer $k missing ($f)" }
    }

    Write-Host ''
    Write-Host '  offline brain' -ForegroundColor White
    $mroot = Join-Path $Root (Rel $B.models)
    $mans  = @(Get-ChildItem (Join-Path $mroot 'manifests') -Recurse -File -ErrorAction SilentlyContinue)
    if (-not $mans.Count) { Bad 'no models'; $bad++ }
    foreach ($m in $mans) {
        $jm   = Get-Content $m.FullName -Raw | ConvertFrom-Json
        $digs = @(@($jm.config) + @($jm.layers) | ForEach-Object { $_.digest } | Where-Object { $_ })
        $miss = @($digs | Where-Object { -not (Test-Path (Join-Path $mroot ('blobs\' + ($_ -replace ':', '-')))) })
        $name = "$($m.Directory.Name):$($m.Name)"
        if ($miss.Count) { Bad "$name - $($miss.Count) file(s) missing"; $bad++ } else { Ok $name }
    }

    Write-Host ''
    Write-Host '  boot' -ForegroundColor White
    $bootHere = $false
    if ($Root.TrimEnd('\') -eq $Stage) {
        $bootHere = Test-Path (Join-Path $Stage '_BOOT\live\filesystem.squashfs')
    } else {
        $d = Get-Partition -DriveLetter $Root.Substring(0,1) -ErrorAction SilentlyContinue | Get-Disk
        if ($d) {
            foreach ($v in Get-Partition -DiskNumber $d.Number | Where-Object DriveLetter | Get-Volume) {
                $r = "$($v.DriveLetter):\"
                if ("$($v.FileSystem)" -eq 'FAT32' -and (Test-Path (Join-Path $r 'live\filesystem.squashfs')) -and (Test-Path (Join-Path $r 'EFI\BOOT'))) { $bootHere = $true }
            }
        }
    }
    if ($bootHere) { Ok 'Debian Live boot present' } else { Warn 'not bootable yet (plug-in use still works)' }

    Write-Host ''
    Write-Host '  secrets (must be none)' -ForegroundColor White
    $skip = '\\(\.git|node_modules|_RUNTIME|_BOOT|_INSTALLERS|vendor|whisper)\\'
    $envs = @(Get-ChildItem $Root -Recurse -Force -File -Filter '.env*' -ErrorAction SilentlyContinue |
              Where-Object { $_.FullName -notmatch $skip -and $_.Name -notmatch '\.(example|sample|template|public)$' })
    $jset = Join-Path $j 'memory\settings.json'
    $pat  = 'sb_secret_[A-Za-z0-9_\-]{12,}|SUPABASE_SERVICE_ROLE_KEY\s*=\s*["'']?[A-Za-z0-9_\-\.]{20,}|GHL_API_KEY\s*=\s*["'']?[A-Za-z0-9_\-]{20,}|\bsk-(proj-|ant-)?[A-Za-z0-9_\-]{24,}'
    $text = Get-ChildItem $Root -Recurse -Force -File -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch $skip -and $_.Length -lt 1MB -and $_.Extension -match '^(\.(env.*|json|txt|md|ps1|psm1|bat|cmd|sh|ts|tsx|js|mjs|cjs|py|toml|ya?ml|ini|cfg|conf))?$' }
    # Docs and templates are full of "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key".
    # Flag a match only when its value does not read as placeholder text.
    $placeholder = '(?i)your|paste|here|xxx|placeholder|example|changeme|<|\.\.\.'
    $hits = @($text | Select-String -Pattern $pat -AllMatches -ErrorAction SilentlyContinue |
              Where-Object { @($_.Matches | Where-Object { ($_.Value -replace '^[A-Z_]+\s*=\s*["'']?', '') -notmatch $placeholder }).Count } |
              Select-Object -ExpandProperty Path -Unique)
    $found = @($envs | ForEach-Object FullName) + @($hits)
    if (Test-Path $jset) { $found += $jset }
    $found = @($found | Where-Object { $_ } | Sort-Object -Unique)
    if ($found.Count) { foreach ($f in $found) { Bad "possible secret: $f" }; $bad += $found.Count }
    else { Ok 'no .env files, no live keys, no JARVIS settings.json' }

    Write-Host ''
    Note 'total' (GB (Size-Bytes $Root))
    if ($bad -eq 0 -and $script:Failures -eq 0) { Ok 'ready' } else { Warn "$($bad + $script:Failures) thing(s) want attention" }
    Write-Host ''
}

function Show-Drives {
    Write-Host ''
    Write-Host '  Attached drives:' -ForegroundColor White
    $vols = @(Get-Volume | Where-Object { $_.DriveLetter -and "$($_.DriveLetter)" -ne 'C' })
    if ($vols.Count) { $vols | ForEach-Object { Write-Host ("    {0}:  {1,-12} [{2}]  {3} free" -f $_.DriveLetter, $_.FileSystemLabel, $_.FileSystem, (GB $_.SizeRemaining)) } }
    else { Write-Host '    (none attached)' -ForegroundColor DarkGray }
    Write-Host ''
}

function Do-Help {
    Hd 'BOOTSTICK - TMMT + JARVIS ON ONE DRIVE'
    $rows = [ordered]@{
        'aixmos bootstick stage'          = "build/refresh the payload at $Stage"
        'aixmos bootstick grab-boot'      = 'pull the Debian Live boot off AIXMOS02 / CYBORG'
        'aixmos bootstick write E'        = 'copy onto stick E: (additive, never deletes)'
        'aixmos bootstick write E format' = 'ERASE a USB stick into BOOT + DATA, then write'
        'aixmos bootstick write E vault'  = 'also carry Personal-Brain (home-only sticks)'
        'aixmos bootstick check [E]'      = 'verify: lanes, runtimes, models, boot, no secrets'
    }
    foreach ($k in $rows.Keys) { Write-Host ('  {0,-34}' -f $k) -ForegroundColor White -NoNewline; Write-Host $rows[$k] -ForegroundColor Gray }
    Show-Drives
}

switch -Regex ($Action) {
    '^stage$'            { Do-Stage }
    '^grab-?boot$'       { Do-GrabBoot }
    '^write$'            { Do-Write }
    '^check$'            { if ($Drive) { Do-Check "$Drive`:\" } else { Do-Check $Stage } }
    default              { Do-Help }
}
