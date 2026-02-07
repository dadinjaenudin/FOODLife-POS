@echo off
echo ========================================
echo   Building Tailwind CSS for Production
echo   (Offline Mode)
echo ========================================
echo.

cd static\css

if not exist "node_modules" (
    echo Installing Tailwind CSS...
    call npm install
    echo.
)

echo Building Tailwind CSS...
call npx tailwindcss -i input.css -o output.css --minify

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo Output file: static\css\output.css
echo.
echo The application is now ready for offline use.
echo All CSS and JavaScript files are local.
echo.
pause
