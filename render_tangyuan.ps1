$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$rp = "C:\project\generate\article\ex\4-2\render_multiview.py"
$base = "C:\project\generate\article\ex\4-2\tangyuan\washingmachine"
$wm = "C:\project\generate\article\ex\4-2\wm_in"
$AZS = "0,18,36,54,72,90,108,126,144,162,180,198,216,234,252,270,288,306,324,342"
New-Item -ItemType Directory -Force $base | Out-Null
$log = "$base\render.log"
$items = @(
 @{n='articraft_closed';g='wm_articraft_closed.glb';u='y'},
 @{n='aa_closed';g='wm_articulate_anything_closed.glb';u='auto'},
 @{n='aa_open';g='wm_articulate_anything_open.glb';u='auto'},
 @{n='urdfplus_closed';g='wm_urdf_anything_plus_closed.glb';u='auto'},
 @{n='urdfplus_open';g='wm_urdf_anything_plus_open.glb';u='auto'},
 @{n='spark_closed';g='wm_spark_closed.glb';u='auto'},
 @{n='spark_open';g='wm_spark_open.glb';u='auto'}
)
"START $(Get-Date -Format HH:mm:ss)" | Out-File $log -Encoding utf8
foreach($it in $items){
 $out = Join-Path $base $it.n
 New-Item -ItemType Directory -Force $out | Out-Null
 for($try=1; $try -le 3; $try++){
  $c = (Get-ChildItem "$out\*.png" -ErrorAction SilentlyContinue | Measure-Object).Count
  if($c -ge 20){break}
  "RENDER $($it.n) try$try up=$($it.u) $(Get-Date -Format HH:mm:ss)" | Add-Content $log
  Get-Process blender -ErrorAction SilentlyContinue | Stop-Process -Force
  $a = @('-b','-P',$rp,'--','--glb',(Join-Path $wm $it.g),'--outdir',$out,'--azs',$AZS,'--el','18','--res','800','--vc','1','--floor','1','--up',$it.u)
  Start-Process -FilePath $blender -ArgumentList $a -WindowStyle Hidden -Wait
 }
 $c = (Get-ChildItem "$out\*.png" -ErrorAction SilentlyContinue | Measure-Object).Count
 "DONE $($it.n) pngs=$c $(Get-Date -Format HH:mm:ss)" | Add-Content $log
}
"ALLDONE $(Get-Date -Format HH:mm:ss)" | Add-Content $log
