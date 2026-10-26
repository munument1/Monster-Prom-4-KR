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
    $manager = $assembly.MainModule.Types | Where-Object FullName -eq 'Game.MainGameEventManager'
    $parser = @($manager.Methods | Where-Object Name -eq 'ProcessStatPatterns')
    if ($parser.Count -ne 1) { throw 'Expected one ProcessStatPatterns method' }
    $format = @($parser[0].Body.Instructions | Where-Object { $_.OpCode.Name -eq 'ldstr' -and $_.Operand -ceq '{0}{1}{2}{3}{4}[-]' })
    $changes = @($parser[0].Body.Instructions | Where-Object { $_.OpCode.Name -eq 'newobj' -and $_.Operand.DeclaringType.FullName -eq 'BeautifulGlitch.StatChange' })
    if ($format.Count -ne 1 -or $changes.Count -ne 1 -or $changes[0].Offset -ge $format[0].Offset) { throw 'Stat changes must be constructed before display formatting' }
    $slot = @($parser[0].Body.Instructions | Where-Object {
        $_.Offset -gt $format[0].Offset -and $_.OpCode.Name -eq 'ldc.i4.4' -and
        $_.Next.OpCode.Name -eq 'ldloc.s' -and $_.Next.Operand.Index -eq 13 -and
        $_.Next.Next.OpCode.Name -eq 'stelem.ref'
    })
    if ($slot.Count -ne 1) { throw 'Expected one formatted display-name slot after numeric stat parsing' }
    Write-Output 'PASS dialogue stat contract: numeric StatChange construction precedes the unique display-name formatting slot.'
} finally { $assembly.Dispose() }
