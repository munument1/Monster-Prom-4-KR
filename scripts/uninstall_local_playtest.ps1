# Removes only the files created by scripts/install_local_playtest.ps1.
# Leaves the game's original DLLs/AssetBundles, saves, logs, and unknown files intact.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$state = Join-Path $repo 'work\install\installed_files.json'
if (!(Test-Path -LiteralPath $state)) { throw "No installation manifest: $state" }
$manifest = Get-Content -LiteralPath $state -Raw -Encoding UTF8 | ConvertFrom-Json
$game = (Resolve-Path -LiteralPath $manifest.game -ErrorAction Stop).Path
if (!(Test-Path -LiteralPath (Join-Path $game 'MonsterCon.exe'))) {
    throw "Manifest does not resolve to a Monster Con install: $game"
}
if (Get-Process -Name MonsterCon -ErrorAction SilentlyContinue) {
    throw 'Exit Monster Con before removal; the game will not be terminated.'
}

# Scan first: never delete if an installed file was externally edited/replaced.
foreach ($item in $manifest.files) {
    $file = Join-Path $game $item.relative
    if (Test-Path -LiteralPath $file -PathType Leaf) {
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if ($hash -ne $item.sha256) {
            throw "Installed file changed since installation; refusing to delete: $file"
        }
    }
}
$removed = 0
foreach ($item in $manifest.files) {
    $file = Join-Path $game $item.relative
    if (Test-Path -LiteralPath $file -PathType Leaf) {
        Remove-Item -LiteralPath $file -Force
        $removed++
    }
}

# Remove only empty directories that were part of this test installation.
foreach ($relative in @('BepInEx\plugins\MonsterConKoreanBridge',
        'BepInEx\plugins', 'BepInEx\core',
        'MonsterCon_Data\StreamingAssets\game_assets\texts',
        'MonsterCon_Data\StreamingAssets\game_assets', 'BepInEx')) {
    $dir = Join-Path $game $relative
    if ((Test-Path -LiteralPath $dir -PathType Container) -and
        @(Get-ChildItem -LiteralPath $dir -Force).Count -eq 0) {
        Remove-Item -LiteralPath $dir
    }
}
Remove-Item -LiteralPath $state -Force
Write-Output "REMOVED $removed installed test files. Existing game files and save data preserved."
