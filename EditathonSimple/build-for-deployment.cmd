@echo off
REM Build and package EditathonSimple for cPanel deployment
REM Run this script from the EditathonSimple directory

echo ========================================
echo EditathonSimple Deployment Builder
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "package.json" (
    echo ERROR: package.json not found!
    echo Please run this script from the EditathonSimple directory.
    pause
    exit /b 1
)

echo Step 1: Installing dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Building React application...
call npm run build
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo Step 3: Creating deployment package...

REM Create deployment directory
if exist "deployment-package" rmdir /s /q deployment-package
mkdir deployment-package

REM Copy necessary files
echo Copying dist folder...
xcopy /E /I /Y dist deployment-package\dist

echo Copying server file...
copy server-postgres.js deployment-package\

echo Copying package.json...
copy package.json deployment-package\

echo Creating .env.local template...
(
echo DB_HOST=localhost
echo DB_NAME=editathon_db
echo DB_USER=editathon_user
echo DB_PASSWORD=YOUR_PASSWORD_HERE
echo DB_PORT=5432
echo PORT=3000
) > deployment-package\.env.local.template

echo Creating README...
(
echo DEPLOYMENT PACKAGE
echo ==================
echo.
echo This package contains:
echo - dist/              Built React application
echo - server-postgres.js Node.js server
echo - package.json       Dependencies
echo - .env.local.template Environment variables template
echo.
echo IMPORTANT: 
echo 1. Rename .env.local.template to .env.local
echo 2. Edit .env.local and add your database password
echo 3. Upload all files to your cPanel directory
echo 4. Run 'npm install' in cPanel Node.js app
echo 5. Set server-postgres.js as startup file
echo 6. Restart the application
echo.
echo See DEPLOYMENT_CHECKLIST.md for detailed instructions.
) > deployment-package\README.txt

echo.
echo Step 4: Creating ZIP file...
powershell Compress-Archive -Path deployment-package\* -DestinationPath editathon-deployment.zip -Force

echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo.
echo Deployment package created: editathon-deployment.zip
echo.
echo NEXT STEPS:
echo 1. Upload editathon-deployment.zip to your cPanel File Manager
echo 2. Extract the zip file in your app directory
echo 3. Rename .env.local.template to .env.local
echo 4. Edit .env.local with your database credentials
echo 5. In cPanel Node.js App, click "Run NPM Install"
echo 6. Restart the application
echo.
echo See DEPLOYMENT_CHECKLIST.md for detailed instructions.
echo.
pause
