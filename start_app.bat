@echo off
echo.
echo ==========================================
echo   Name Card Extractor - Streamlit App
echo ==========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

:: Check if required files exist
if not exist "streamlit_app.py" (
    echo Error: streamlit_app.py not found
    echo Please run this batch file from the project directory
    pause
    exit /b 1
)

if not exist "Name_Card_Extract.py" (
    echo Error: Name_Card_Extract.py not found
    echo Please ensure the core extraction module is present
    pause
    exit /b 1
)

:: Check if virtual environment should be used
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: Install requirements if they don't exist
echo Checking requirements...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error installing requirements
        pause
        exit /b 1
    )
)

:: Check environment file
if not exist ".env" (
    echo.
    echo Warning: .env file not found
    echo Please create a .env file with your IBM Watson credentials:
    echo.
    echo WATSONX_API_KEY=your_api_key_here
    echo WATSONX_PROJECT_ID=your_project_id_here
    echo WATSONX_API_URL=https://us-south.ml.cloud.ibm.com
    echo.
    echo Press any key to continue anyway...
    pause >nul
)

:: Start the application
echo.
echo Starting Name Card Extractor...
echo.
echo The application will open in your default web browser
echo URL: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo ==========================================
echo.

python -m streamlit run streamlit_app.py --server.headless false --server.port 8501 --browser.gatherUsageStats false

echo.
echo Application stopped.
pause
