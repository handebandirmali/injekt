@echo off
setlocal

set IDS_ROOT=C:\Program Files\IDS\ids_peak
set INCLUDE_DIR=%IDS_ROOT%\comfort_sdk\api\include
set LIB_DIR=%IDS_ROOT%\comfort_sdk\api\lib\x86_64

if not exist "%INCLUDE_DIR%\ids_peak_comfort_c\ids_peak_comfort_c.h" (
    echo Header bulunamadi:
    echo %INCLUDE_DIR%\ids_peak_comfort_c\ids_peak_comfort_c.h
    exit /b 1
)

if not exist "%LIB_DIR%\ids_peak_comfort_c.lib" (
    echo Lib bulunamadi:
    echo %LIB_DIR%\ids_peak_comfort_c.lib
    exit /b 1
)

cl /EHsc /std:c++17 /I "%INCLUDE_DIR%" ids_cset_exporter.cpp /link /LIBPATH:"%LIB_DIR%" ids_peak_comfort_c.lib /OUT:ids_cset_exporter.exe

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Build OK: ids_cset_exporter.exe
endlocal