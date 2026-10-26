param([string]$GamePath = 'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Add-Type -Path (Join-Path $repo 'work\tools\BepInEx_win_x86_5.4.23.2\BepInEx\core\Mono.Cecil.dll')
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $GamePath 'MonsterCon_Data\Managed\Assembly-CSharp.dll'))
try {
    $xml = $assembly.MainModule.Types | Where-Object FullName -eq 'BeautifulGlitch.CoreXmlSerializer'
    $generator = $xml.Methods | Where-Object Name -eq 'GenerateXMLFileStream'
    if (!($generator.Body.Instructions | Where-Object { $_.OpCode.Name -eq 'newobj' -and $_.Operand.DeclaringType.FullName -eq 'System.Text.ASCIIEncoding' })) { throw 'Original save encoding contract changed' }
    $type = $assembly.MainModule.Types | Where-Object FullName -eq 'BeautifulGlitch.CoreCheckpointXmlSerializer'
    $methods = @($type.Methods | Where-Object Name -eq 'SerializeCorePlayerData')
    if ($methods.Count -ne 1) { throw 'Expected one player serializer' }
    $writes = @($methods[0].Body.Instructions | Where-Object { $_.Operand.FullName -eq 'System.Void System.Xml.XmlWriter::WriteElementString(System.String,System.String)' })
    $names = @($methods[0].Body.Instructions | Where-Object { $_.OpCode.Name -eq 'ldstr' -and $_.Operand -ceq 'Name' })
    if ($writes.Count -eq 0 -or $names.Count -ne 1) { throw 'Original player-name writer contract changed' }
    Write-Output "PASS save-name contract: ASCII XML writer; one Name field; $($writes.Count) delegated string writes."
} finally { $assembly.Dispose() }
