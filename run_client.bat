cd "C:\Python\Projects\networking"

set /a num=%RANDOM% %% 10

if %num%==0 set name=Shadow
if %num%==1 set name=Blaze
if %num%==2 set name=Vortex
if %num%==3 set name=Razor
if %num%==4 set name=Phantom
if %num%==5 set name=Nova123
if %num%==6 set name=Drift
if %num%==7 set name=Titan
if %num%==8 set name=Echo123
if %num%==9 set name=Fury123

python "client.py" %name% 127.0.0.1:5667
pause