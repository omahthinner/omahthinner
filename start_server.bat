@echo off
title Omah Thinner & Cat - Server Lokal Fullstack
cd /d "%~dp0"

echo ==============================================================
echo    OMAH THINNER & CAT - BY AJID PAINTING (LOCAL FULLSTACK)
echo ==============================================================
echo    Menyiapkan koneksi server lokal...

:: Cek dan bersihkan port 8080 jika ada proses python yang menggantung
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 ^| findstr LISTENING') do (
    if not "%%a"=="" (
        echo Membersihkan proses lama pada port 8080 (PID: %%a)...
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo    Website      : http://localhost:8080
echo    Upload Folder: %~dp0uploads
echo ==============================================================

:: Buka browser secara otomatis
start http://localhost:8080/

:: Jalankan server backend
python server.py
pause
