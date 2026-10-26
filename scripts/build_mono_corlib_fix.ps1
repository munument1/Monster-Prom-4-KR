# Build a local, fingerprint-gated MonoMod correction. Never edits the game.
param([string]$GamePath = 'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stock = Join-Path $root 'work\tools\BepInEx_win_x86_5.4.23.2\BepInEx\core'
$mono = Join-Path $GamePath 'MonoBleedingEdge\EmbedRuntime\mono-2.0-bdwgc.dll'
$source = Join-Path $stock 'MonoMod.Utils.dll'
if ((Get-FileHash -LiteralPath $mono).Hash -ne 'C012E79F0ABBF5CD969C430BF1272FEFC93E234DF2C0FD823C05A23607160ACA') {
    throw 'Unsupported Mono build. Inspect its native MonoAssembly layout before building a correction.'
}
if ((Get-FileHash -LiteralPath $source).Hash -ne '9D1495F147AC93C4F81F84538C1A326E8F8A6AEFC78D6289D798F3CE1162C5E9') {
    throw 'Unexpected stock MonoMod.Utils input; do not apply this correction to another version.'
}
Add-Type -Path (Join-Path $stock 'Mono.Cecil.dll')
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($source)
$type = $assembly.MainModule.Types | Where-Object FullName -eq 'MonoMod.Utils.Extensions'
$method = $type.Methods | Where-Object Name -eq 'SetMonoCorlibInternal'
$target = @($method.Body.Instructions | Where-Object {
    $_.OpCode.Name -eq 'stloc.s' -and $_.Operand -eq $method.Body.Variables[4]
})
if ($target.Count -ne 1 -or $target[0].Offset -ne 0x1d1) { throw 'Unexpected method body layout' }
# On this exact x86 Unity Mono, corlib_internal is +0x53, not the +0x4F
# calculated by legacy MonoMod. +0x4F belongs to the high byte of a pointer.
$il = $method.Body.GetILProcessor()
$il.InsertBefore($target[0], [Mono.Cecil.Cil.Instruction]::Create([Mono.Cecil.Cil.OpCodes]::Ldc_I4_4))
$il.InsertBefore($target[0], [Mono.Cecil.Cil.Instruction]::Create([Mono.Cecil.Cil.OpCodes]::Add))
$out = Join-Path $root 'build\runtime_compat'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$dest = Join-Path $out 'MonoMod.Utils.dll'
$assembly.Write($dest)
$assembly.Dispose()
Write-Output "BUILT local x86 MonoMod compatibility correction: $dest"
Write-Output ('SHA256=' + (Get-FileHash -LiteralPath $dest).Hash)
