@echo off
REM ============================================
REM Git Commit & Push Script
REM Safe workflow for committing changes
REM ============================================

echo.
echo ========================================
echo     Git Commit Helper
echo ========================================
echo.

REM Check if we're in a git repository
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Not a git repository!
    echo Please run this from project root.
    pause
    exit /b 1
)

REM Show current status
echo [1/5] Checking git status...
echo.
git status
echo.

REM Ask for confirmation
set /p CONFIRM="Continue with commit? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

REM Add all changes
echo.
echo [2/5] Adding all changes...
git add .
echo Done!

REM Show what will be committed
echo.
echo [3/5] Files to be committed:
git diff --cached --name-status
echo.

REM Get commit message
set /p COMMIT_MSG="[4/5] Enter commit message: "
if "%COMMIT_MSG%"=="" (
    echo [ERROR] Commit message cannot be empty!
    pause
    exit /b 1
)

REM Commit
echo.
echo [5/5] Committing...
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo [ERROR] Commit failed!
    pause
    exit /b 1
)
echo Done!

REM Ask if want to push
echo.
set /p PUSH="Push to remote? (Y/N): "
if /i "%PUSH%"=="Y" (
    echo.
    echo Pushing to remote...
    
    REM Get current branch
    for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
    
    echo Branch: %BRANCH%
    git push origin %BRANCH%
    
    if errorlevel 1 (
        echo [ERROR] Push failed!
        echo You may need to pull changes first or resolve conflicts.
        pause
        exit /b 1
    )
    
    echo.
    echo ========================================
    echo   SUCCESS! Changes pushed to remote.
    echo ========================================
) else (
    echo.
    echo ========================================
    echo   Committed locally (not pushed)
    echo   Run 'git push' to push later.
    echo ========================================
)

echo.
pause
