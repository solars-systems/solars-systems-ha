@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SolarPro - Scriere Firmware ESP32 pe USB (Flash Tool)
color 0B

echo ==============================================================
echo        SOLARPRO - SCRIERE FIRMWARE PE ESP32 PRIN USB          
echo ==============================================================
echo.

:: 1. DETECTARE AUTOMATA ESPTOOL (FUNCTIONEAZA PE ORICE PC)
set "ESPTOOL_CMD="

:: Pas 1: Cauta in Arduino15 (orice versiune de ESP32 Core si orice utilizator)
if exist "%LOCALAPPDATA%\Arduino15\packages\esp32\tools\esptool_py" (
    for /d %%v in ("%LOCALAPPDATA%\Arduino15\packages\esp32\tools\esptool_py\*") do (
        if exist "%%v\esptool.exe" (
            set ESPTOOL_CMD="%%v\esptool.exe"
            goto :ESPTOOL_FOUND
        )
    )
)

:: Pas 2: Cauta in PlatformIO (VS Code pe orice utilizator)
if exist "%USERPROFILE%\.platformio\penv\Scripts\python.exe" (
    if exist "%USERPROFILE%\.platformio\packages\tool-esptoolpy\esptool.py" (
        set ESPTOOL_CMD="%USERPROFILE%\.platformio\penv\Scripts\python.exe" "%USERPROFILE%\.platformio\packages\tool-esptoolpy\esptool.py"
        goto :ESPTOOL_FOUND
    )
)

:: Pas 3: Cauta in PATH (daca utilizatorul a instalat esptool ca executabil global)
where esptool.exe >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%p in ('where esptool.exe') do (
        set ESPTOOL_CMD="%%p"
        goto :ESPTOOL_FOUND
    )
)

:: Pas 4: Cauta in mediul Python global
where python.exe >nul 2>&1
if %errorlevel% equ 0 (
    python -m esptool version >nul 2>&1
    if %errorlevel% equ 0 (
        set ESPTOOL_CMD=python -m esptool
        goto :ESPTOOL_FOUND
    )
)

:ESPTOOL_FOUND
if not defined ESPTOOL_CMD (
    color 0C
    echo [EROARE CRITICA] Nu s-a gasit esptool pe acest calculator!
    echo Asigura-te ca ai instalat Arduino IDE cu suport ESP32 sau PlatformIO in VS Code.
    echo.
    goto END
)

:: 2. DETERMINARE DIRECTOR PROIECT (ADAPTAT PENTRU ORICE PC)
set "REPO_DIR=%~dp0"
if not exist "%REPO_DIR%solars-pcb-platformio" (
    if exist "D:\Programdata\Arduino\esp32-solars-firmware\solars-pcb-platformio" (
        set "REPO_DIR=D:\Programdata\Arduino\esp32-solars-firmware\"
    )
)

:: 3. SELECTIE FISIER .BIN (DRAG-AND-DROP SAU AUTO-DETECTIE)
set "BIN_FILE=%~1"

if "%BIN_FILE%"=="" (
    if exist "%REPO_DIR%solars-pcb-platformio\.pio\build\pcb_v1_2\firmware.bin" (
        set "BIN_FILE=%REPO_DIR%solars-pcb-platformio\.pio\build\pcb_v1_2\firmware.bin"
        echo [AUTO] Gasit binar PlatformIO PCB: solars-pcb-platformio
    ) else if exist "%REPO_DIR%solars-systems-platformio\.pio\build\esp32_standard\firmware.bin" (
        set "BIN_FILE=%REPO_DIR%solars-systems-platformio\.pio\build\esp32_standard\firmware.bin"
        echo [AUTO] Gasit binar PlatformIO Standard: solars-systems-platformio
    ) else if exist "%REPO_DIR%noulsolars-systemspcbV1.2\firmware_pcb.bin" (
        set "BIN_FILE=%REPO_DIR%noulsolars-systemspcbV1.2\firmware_pcb.bin"
        echo [AUTO] Gasit binar Arduino IDE PCB: firmware_pcb.bin
    )
)

if "%BIN_FILE%"=="" (
    echo Nu s-a gasit automat un binar compilat in folderul proiectului.
    echo Poti trage cu mouse-ul fisierul .bin direct peste acest script sau tasteaza calea lui:
    set /p "BIN_FILE=Cale fisier .bin: "
)

set "BIN_FILE=%BIN_FILE:"=%"

if not exist "!BIN_FILE!" (
    echo.
    echo [EROARE] Fisierul "!BIN_FILE!" nu exista!
    goto END
)

echo -> Fisier tinta: "!BIN_FILE!"
echo.

:: 4. DETECTARE AUTOMATA PORT COM
echo Cautare port COM ESP32 pe acest PC...
set "DETECTED_PORT="
for /f "tokens=*" %%p in ('powershell -NoProfile -Command "Get-CimInstance Win32_SerialPort | Where-Object { $_.Description -match 'CH340|CP210|USB|Serial' -or $_.Name -match 'CH340|CP210|USB|Serial' } | Select-Object -ExpandProperty DeviceID | Select-Object -First 1"') do (
    set "DETECTED_PORT=%%p"
)

if "!DETECTED_PORT!"=="" (
    set "DETECTED_PORT=COM3"
)

echo -> Port detectat: !DETECTED_PORT!
set "TARGET_PORT="
set /p "TARGET_PORT=Apasa ENTER pentru [!DETECTED_PORT!] sau tasteaza alt port (ex: COM5): "
if "!TARGET_PORT!"=="" set "TARGET_PORT=!DETECTED_PORT!"

echo.
echo ==============================================================
echo  Conectare la: !TARGET_PORT! (921600 baud)...
echo  Daca apar puncte "Connecting.....", TINE APASAT butonul BOOT!
echo ==============================================================
echo.

!ESPTOOL_CMD! --chip esp32 --port !TARGET_PORT! --baud 921600 --before default-reset --after hard-reset write-flash -z --flash-mode keep --flash-freq 40m --flash-size detect 0x10000 "!BIN_FILE!"

echo.
if %errorlevel% equ 0 (
    color 0A
    echo ==============================================================
    echo  [SUCCES] Firmware-ul a fost scris cu succes pe ESP32!
    echo ==============================================================
) else (
    color 0C
    echo ==============================================================
    echo  [EROARE] Scrierea a esuat!
    echo  - Daca a dat "Access Denied", deconecteaza si reconecteaza cablul USB si inchide Serial Monitor.
    echo  - Daca a dat "Failed to connect", tine apasat butonul BOOT cand reincerci.
    echo ==============================================================
)

:END
echo.
pause
