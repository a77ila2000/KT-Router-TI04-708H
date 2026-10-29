# Read-only vendor U-Boot backup. Close other serial owners first.
param(
 [Parameter(Mandatory=$true)][ValidatePattern('^COM[0-9]+$')][string]$Port,
 [Parameter(Mandatory=$true)][ipaddress]$ServerIP,
 [Parameter(Mandatory=$true)][ipaddress]$RouterIP,
 [Parameter(Mandatory=$true)][string]$Chunks,
 [ValidateRange(512,1468)][int]$BlockSize=1468
)
$ErrorActionPreference='Stop'
if($BlockSize -notin @(512,1468)){throw 'BlockSize must be 512 or 1468'}
if($ServerIP.AddressFamily -ne 'InterNetwork' -or $RouterIP.AddressFamily -ne 'InterNetwork'){throw 'IPv4 required'}
$directory=(Resolve-Path -LiteralPath $Chunks).Path
$evidence=Join-Path $directory 'uboot-crc.json'
if(Test-Path -LiteralPath $evidence){throw 'Use a fresh backup directory; evidence exists'}
$serial=[IO.Ports.SerialPort]::new($Port,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$serial.Handshake=[IO.Ports.Handshake]::None
$serial.DtrEnable=$false; $serial.RtsEnable=$false; $serial.WriteTimeout=1000
$records=[Collections.Generic.List[object]]::new()
function Command([string]$line,[int]$timeout=90){
 $wire=[Text.Encoding]::ASCII.GetBytes($line+"`r")
 for($offset=0;$offset -lt $wire.Length;$offset+=16){
  $count=[Math]::Min(16,$wire.Length-$offset)
  $serial.Write($wire,$offset,$count); Start-Sleep -Milliseconds 20
 }
 $answer=[Text.StringBuilder]::new(); $deadline=[DateTime]::UtcNow.AddSeconds($timeout)
 do {
  if($serial.BytesToRead -gt 0){[void]$answer.Append($serial.ReadExisting())}
  $s=$answer.ToString()
  if($s -match '(?m)^\(IPQ40xx\) #\s*$'){return $s}
  Start-Sleep -Milliseconds 20
 }while([DateTime]::UtcNow -lt $deadline)
 throw 'U-Boot response timeout; backup stopped. No Ctrl+C/reset sent.'
}
try {
 $serial.Open()
 $serial.DiscardInBuffer()
 [void](Command '')
 $v=Command 'version'
 if($v -notmatch 'TI04-708H' -or $v -notmatch 'U-Boot 2012.07'){throw 'Wrong model/bootloader'}
 [void](Command 'setenv debug_mode on')
 $device=Command 'nand device'
 if($device -notmatch 'Device 1: nand1' -or $device -notmatch 'Page size\s+2048 b' -or $device -notmatch 'OOB size\s+64 b' -or $device -notmatch 'Erase size\s+131072 b'){throw 'Unsupported NAND device/geometry'}
 $bad=Command 'nand bad'
 if($bad -notmatch 'Device 1 bad blocks:' -or $bad -match '(?im)^\s*(?:0x)?[0-9a-f]{8}\s*$'){throw 'Bad-block layout needs separate handling'}
 $unexpected=@((($bad -replace "`r",'') -split "`n") | Where-Object {$_.Trim() -and $_.Trim() -ne 'nand bad' -and $_.Trim() -ne 'Device 1 bad blocks:' -and $_.Trim() -ne '(IPQ40xx) #'})
 if($unexpected.Count -gt 0){throw 'Unexpected nand bad response; do not assume zero bad blocks'}
 [void](Command ('setenv ipaddr '+$RouterIP.IPAddressToString))
 [void](Command ('setenv serverip '+$ServerIP.IPAddressToString))
 [void](Command 'setenv netmask 255.255.255.0')
 [void](Command ('setenv tftpblocksize '+$BlockSize))
 foreach($kind in @('main','raw')){
  for($n=0;$n -lt 128;$n++){
   $offset=$n*0x100000; $hex='{0:x8}' -f $offset
   $file='nand-'+$kind+'-'+$hex+'.bin'
   $path=Join-Path $directory $file
   if(Test-Path -LiteralPath $path){throw ('Refusing to overwrite chunk '+$file)}
   if($kind -eq 'main'){$read='nand read 84000000 '+$hex+' 100000';$size=1048576;$sizeHex='100000'}
   else{$read='nand read.raw 84000000 '+$hex+' 200';$size=1081344;$sizeHex='108000'}
   $reply=Command $read
   if($reply -notmatch 'bytes read: OK' -or $reply -match '(?i)ERROR|failed|bad block|Skipping'){throw ('Read failed/skipped: '+$file)}
   $crc=Command ('crc32 84000000 '+$sizeHex)
   if($crc -notmatch '(?im)^CRC32[^\r\n]*==>\s*([0-9a-f]{8})\s*$'){throw 'Missing CRC32 response'}
   $expectedCRC=$Matches[1].ToLower()
   $sent=Command ('tftpput 84000000 '+$sizeHex+' '+$file)
   if($sent -notmatch ('Bytes transferred = '+$size+'\b')){throw 'TFTP transfer not confirmed'}
   $deadline=[DateTime]::UtcNow.AddSeconds(10)
   while(-not(Test-Path -LiteralPath $path) -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Milliseconds 100}
   if(-not(Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -ne $size){throw 'Received chunk missing/wrong size'}
   $records.Add([pscustomobject]@{file=$file;offset=$offset;bytes=$size;crc32=$expectedCRC;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()})
   [IO.File]::WriteAllText($evidence,(@($records.ToArray())|ConvertTo-Json -Depth 3),[Text.UTF8Encoding]::new($false))
   Write-Host ($kind+' '+($n+1)+'/128 saved')
  }
 }
 Write-Host '256 chunks saved. Run verify_backups.py before proceeding. This does not prove restoration.'
}finally{$serial.Dispose()}
