@echo off
echo ========================================
echo   INICIAR OLLAMA PARA LINCEUS
echo ========================================
echo.

echo [1/2] Verificando si Ollama esta corriendo...
curl -s http://localhost:11434/api/tags >nul 2>&1

if %ERRORLEVEL% == 0 (
    echo ✓ Ollama ya esta corriendo
) else (
    echo ✗ Ollama no esta corriendo
    echo.
    echo Iniciando Ollama server...
    start "Ollama Server" ollama serve
    timeout /t 3 /nobreak >nul
)

echo.
echo [2/3] Verificando modelo llama3.2:3b...
ollama list | findstr "llama3.2:3b" >nul 2>&1

if %ERRORLEVEL% == 0 (
    echo ✓ Modelo llama3.2:3b ya esta descargado
) else (
    echo ✗ Descargando modelo llama3.2:3b (esto puede tardar unos minutos)...
    ollama pull llama3.2:3b
)

echo.
echo [3/3] Pre-cargando modelo llama3.2:3b en memoria...
ollama run llama3.2:3b "Hola, di OK" --verbose

echo.
echo ========================================
echo ✓ Ollama listo para usar
echo ========================================
echo.
echo Ahora puedes iniciar Rasa con:
echo    rasa run actions
echo.
pause
