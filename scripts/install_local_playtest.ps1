# Installs the verified Roadtrip Korean preview into the user's current game.
# All originals are preserved. Every new file is recorded for reversible removal.
param(
    [string]$GamePath = 'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$game = (Resolve-Path -LiteralPath $GamePath -ErrorAction Stop).Path
$data = Join-Path $game 'MonsterCon_Data'
if (!(Test-Path -LiteralPath (Join-Path $game 'MonsterCon.exe')) -or
    !(Test-Path -LiteralPath (Join-Path $data 'Managed\Assembly-CSharp.dll'))) {
    throw "Not a recognizable Monster Roadtrip install: $game"
}
if (Get-Process -Name 'MonsterCon' -ErrorAction SilentlyContinue) {
    throw 'MonsterCon.exe is running. Exit the game before installation; process was NOT stopped.'
}

$state = Join-Path $repo 'work\install\installed_files.json'
if (Test-Path -LiteralPath $state) {
    throw "Prior installation manifest exists. For safety, run uninstall_local_playtest.ps1 first: $state"
}
$bepinex = Join-Path $repo 'work\tools\BepInEx_win_x86_5.4.23.2'
$bridge = Join-Path $repo 'src\MonsterConKoreanBridge\bin\Release\MonsterConKoreanBridge.dll'
$events = Join-Path $repo 'build\playtest\game_assets\texts'
$metatext = Join-Path $repo 'build\preview\english_metatexts.txt'
$fonts = Join-Path $repo 'work\fonts'
$roadtripFontBundle = Join-Path $repo 'build\fonts\monstercon_korean_fonts.bundle'
foreach ($file in @($bridge, $metatext,
    (Join-Path $bepinex 'winhttp.dll'), (Join-Path $bepinex 'doorstop_config.ini'))) {
    if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing build input: $file" }
}
if (!(Test-Path -LiteralPath $roadtripFontBundle -PathType Leaf)) { throw 'Prepare OFL font bundle first.' }

$entries = New-Object 'System.Collections.Generic.List[object]'
foreach ($name in @('winhttp.dll','doorstop_config.ini','.doorstop_version')) {
    $entries.Add([pscustomobject]@{source = (Join-Path $bepinex $name); relative = $name})
}
$bepinexRoot = Join-Path $bepinex 'BepInEx'
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build_mono_corlib_fix.ps1') -GamePath $game
if ($LASTEXITCODE -ne 0) { throw 'The game-specific MonoMod compatibility build failed; no installation performed.' }
$fixedUtils = Join-Path $repo 'build\runtime_compat\MonoMod.Utils.dll'
foreach ($src in Get-ChildItem -LiteralPath $bepinexRoot -Recurse -File) {
    $relative = 'BepInEx\' + $src.FullName.Substring($bepinexRoot.Length).TrimStart('\')
    $sourceForInstall = if ($src.Name -eq 'MonoMod.Utils.dll') { $fixedUtils } else { $src.FullName }
    $entries.Add([pscustomobject]@{source = $sourceForInstall; relative = $relative})
}
$pluginRelative = 'BepInEx\plugins\MonsterConKoreanBridge'
$entries.Add([pscustomobject]@{source = $bridge; relative = ($pluginRelative + '\MonsterConKoreanBridge.dll')})
$entries.Add([pscustomobject]@{source = $metatext; relative = ($pluginRelative + '\english_metatexts.txt')})
$entries.Add([pscustomobject]@{source = $roadtripFontBundle; relative = ($pluginRelative + '\monstercon_korean_fonts.bundle')})
foreach ($license in @('Jua-OFL.txt','GamjaFlower-OFL.txt','PROVENANCE.json')) {
    $entries.Add([pscustomobject]@{source = (Join-Path $repo ('build\fonts\' + $license)); relative = ($pluginRelative + '\' + $license)})
}
foreach ($src in Get-ChildItem -LiteralPath $events -Filter 'english_*.txt' -File) {
    $entries.Add([pscustomobject]@{source = $src.FullName; relative = ('MonsterCon_Data\StreamingAssets\game_assets\texts\' + $src.Name)})
}
# Conflict gate before any modification. This release never overwrites an existing file.
foreach ($item in $entries) {
    $dest = Join-Path $game $item.relative
    if (Test-Path -LiteralPath $dest) {
        throw "Refusing to overwrite existing game/mod file: $dest"
    }
}

$original = @{
    'Assembly-CSharp.dll' = (Get-FileHash -LiteralPath (Join-Path $data 'Managed\Assembly-CSharp.dll') -Algorithm SHA256).Hash
    'texts_assets_all.bundle' = (Get-FileHash -LiteralPath (Join-Path $data 'StreamingAssets\aa\StandaloneWindows\texts_assets_all.bundle') -Algorithm SHA256).Hash
}
$installed = New-Object 'System.Collections.Generic.List[object]'
try {
    foreach ($item in $entries) {
        $dest = Join-Path $game $item.relative
        $dir = Split-Path -Parent $dest
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Copy-Item -LiteralPath $item.source -Destination $dest -ErrorAction Stop
        $expected = (Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash
        $actual = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
        if ($actual -ne $expected) { throw "Copy integrity mismatch: $dest" }
        $installed.Add([pscustomobject]@{relative = $item.relative; sha256 = $actual})
    }
    $manifest = [ordered]@{
        schema = 1
        game = $game
        installed_at = (Get-Date).ToString('o')
        repository_commit = (git -C $repo rev-parse --verify HEAD 2>$null)
        original_file_hashes = $original
        files = @($installed.ToArray())
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $state) -Force | Out-Null
    $manifest | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $state -Encoding UTF8
    Write-Output "INSTALLED $($installed.Count) new files to: $game"
    Write-Output "ROLLBACK_MANIFEST=$state"
    Write-Output "FONT_SOURCES=$fonts"
    Write-Output "METATEXT_SOURCE=$metatext"
    Write-Output "UNINSTALL_COMMAND=powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\uninstall_local_playtest.ps1`""
} catch {
    Write-Warning "Install failed, removing newly copied files: $_"
    foreach ($item in @($installed.ToArray())) {
        $dest = Join-Path $game $item.relative
        if (Test-Path -LiteralPath $dest -PathType Leaf) { Remove-Item -LiteralPath $dest -Force }
    }
    throw
}
