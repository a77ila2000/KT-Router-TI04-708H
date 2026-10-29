# Windows x86 PowerShell + signed WCH DLL from AsProgrammer 2.1.2.
param(
 [ValidateSet('SelfTest','Probe','Read','WriteEnv')][string]$Mode='SelfTest',
 [string]$DllPath,
 [string]$OutputDirectory,
 [string]$Source,[string]$Read2,[string]$Read3,[string]$Candidate,
 [string]$Python='python',
 [switch]$BoardUnpoweredAndOtherCablesRemoved
)
$ErrorActionPreference='Stop'
$readSource=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ch341\Ch341Read.cs'))
$writeSource=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ch341\Ch341Env.cs'))
Add-Type -TypeDefinition ($readSource+"`n"+$writeSource)
if($Mode -eq 'SelfTest'){
 [Ti04EnvSector]::SelfTest()
 [Ti04NorReadOnly]::CheckFrame([byte[]]@(0x9F,255,255,255))
 [Ti04NorReadOnly]::CheckFrame([Ti04NorReadOnly]::ReadFrame(2095104,2048))
 Write-Host 'SELFTEST PASS; no DLL loaded, no hardware access.'
 exit
}
if([IntPtr]::Size -ne 4){throw 'Use C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe (x86 DLL)'}
if(-not $BoardUnpoweredAndOtherCablesRemoved){throw 'Confirm physical isolation with -BoardUnpoweredAndOtherCablesRemoved'}
$dll=(Resolve-Path -LiteralPath $DllPath).Path
if((Split-Path -Leaf $dll) -ine 'CH341DLL.DLL' -or
 (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash -ne '935F5D2EA6A40D47FCBB4892127670E09633374CA524B8739615B30A02C4D178' -or
 (Get-AuthenticodeSignature -LiteralPath $dll).Status -ne 'Valid'){throw 'Unsupported DLL version/hash/signature'}
if(Get-Process -Name AsProgrammer -ErrorAction SilentlyContinue){throw 'Close AsProgrammer first'}
$devices=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB\VID_1A86&PID_5512*'})
if($devices.Count -ne 1 -or $devices[0].Status -ne 'OK'){throw 'Exactly one healthy CH341A SPI programmer required'}
if($Mode -in @('Read','WriteEnv')){
 if(-not [IO.Path]::IsPathRooted($OutputDirectory) -or (Test-Path -LiteralPath $OutputDirectory)){throw 'New absolute output directory required'}
}
if($Mode -eq 'WriteEnv'){
 foreach($file in @($Source,$Read2,$Read3,$Candidate)){if(-not $file){throw 'Source, Read2, Read3 and Candidate required'}}
 & $Python (Join-Path $PSScriptRoot 'patch_nor_env.py') --source $Source --read2 $Read2 --read3 $Read3 --check-candidate $Candidate
 if($LASTEXITCODE -ne 0){throw 'Offline candidate validation failed; no hardware access'}
 $before=[IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Source).Path)
 $after=[IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Candidate).Path)
 [Ti04EnvSector]::BeforeHash=[Ti04EnvSector]::Hash($before)
 [Ti04EnvSector]::CandidateHash=[Ti04EnvSector]::Hash($after)
}
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Ti04DllLoader {
 [DllImport("kernel32",CharSet=CharSet.Unicode,SetLastError=true)]
 public static extern IntPtr LoadLibraryEx(string name,IntPtr reserved,uint flags);
}
'@
if([Ti04DllLoader]::LoadLibraryEx($dll,[IntPtr]::Zero,8) -eq [IntPtr]::Zero){throw 'Could not load verified DLL'}
$mutex=[Threading.Mutex]::new($false,'Local\TI04_CH341_ENV_SECTOR')
$owned=$false
try{
 try{$owned=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$owned=$true}
 if(-not $owned){throw 'Another CH341 operation is active'}
 if($Mode -eq 'WriteEnv'){
  [void][IO.Directory]::CreateDirectory($OutputDirectory)
  [Ti04EnvSector]::Apply($before,$after,$OutputDirectory)
  if([Ti04EnvSector]::VerifiedHash -ne [Ti04EnvSector]::CandidateHash){throw 'Full readback did not pass'}
  Write-Host 'PASS: full 2MiB equals own candidate. Reopen/read independently before power-on.'
 }else{
  [Ti04NorReadOnly]::Open()
  if([Ti04NorReadOnly]::Jedec() -ne 'C84015'){throw 'Unexpected JEDEC; stop without retry/unprotect'}
  if($Mode -eq 'Probe'){Write-Host 'JEDEC C84015 confirmed; no array data read';return}
  [void][IO.Directory]::CreateDirectory($OutputDirectory)
  $firstHash=''
  foreach($n in 1..3){
   if([Ti04NorReadOnly]::Jedec() -ne 'C84015'){throw 'JEDEC changed'}
   $data=New-Object byte[] 2097152
   for($offset=0;$offset -lt $data.Length;$offset+=2048){
    $part=[Ti04NorReadOnly]::ReadBlock($offset,2048)
    [Array]::Copy($part,0,$data,$offset,2048)
   }
   $path=Join-Path $OutputDirectory ('nor-read'+$n+'.bin')
   [IO.File]::WriteAllBytes($path,$data)
   if([Ti04NorReadOnly]::All($data,0) -or [Ti04NorReadOnly]::All($data,255)){throw 'Blank read'}
   $hash=[Ti04EnvSector]::Hash($data)
   if($n -eq 1){$firstHash=$hash}elseif($hash -ne $firstHash){throw 'Independent reads differ'}
   Write-Host ('Read '+$n+'/3 PASS: '+$hash)
  }
 }
}finally{
 [Ti04NorReadOnly]::Close()
 if($owned){$mutex.ReleaseMutex()};$mutex.Dispose()
}
