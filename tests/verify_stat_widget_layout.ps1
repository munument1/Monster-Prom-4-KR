# Read-only IL contract check; never loads Unity or starts the game.
param([string]$GamePath = 'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Add-Type -Path (Join-Path $repo 'work\tools\BepInEx_win_x86_5.4.23.2\BepInEx\core\Mono.Cecil.dll')
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $GamePath 'MonsterCon_Data\Managed\Assembly-CSharp.dll'))
try {
    $widget = $assembly.MainModule.Types | Where-Object FullName -eq 'Game.StatWidget'
    $methods = @($widget.Methods | Where-Object Name -eq 'AwakeMe')
    if ($methods.Count -ne 2) { throw 'Expected two AwakeMe overloads' }
    foreach ($method in $methods) {
        $setters = @($method.Body.Instructions | Where-Object { $_.OpCode.Name -eq 'callvirt' -and $_.Operand.FullName -eq 'System.Void UILabel::set_text(System.String)' })
        if ($setters.Count -ne 1) { throw "Unexpected text assignments: $method" }
        $setter = $setters[0]
        if ($setter.Previous.Operand.FullName -ne 'System.String System.Object::ToString()') { throw 'Stat label no longer comes directly from enum.ToString()' }
        $clones = @($method.Body.Instructions | Where-Object { $_.Operand.FullName -eq 'System.Void Game.StatWidget::InstantiateAuxLabels()' })
        if ($clones.Count -ne 1 -or $clones[0].Offset -le $setter.Offset) { throw 'Auxiliary label clone order changed' }
        if ($method.Body.ExceptionHandlers.Count -ne 0) { throw 'Unexpected exception block layout' }
        Write-Output "PASS stat-name insertion contract: $($method.FullName)"
    }
} finally { $assembly.Dispose() }
