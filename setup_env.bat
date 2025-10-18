@echo off
REM Batch script to set up environment variables for Endor Cockpit integration tests
REM Run this script before running integration tests

echo Setting up Endor Cockpit environment variables...

REM Set the environment variables
set ENDOR_API=https://api.endorlabs.com
set ENDOR_API_CREDENTIALS_KEY=your-api-key-here
set ENDOR_API_CREDENTIALS_SECRET=your-api-secret-here

echo Environment variables set:
echo   ENDOR_API = %ENDOR_API%
echo   ENDOR_API_CREDENTIALS_KEY = %ENDOR_API_CREDENTIALS_KEY%
echo   ENDOR_API_CREDENTIALS_SECRET = [HIDDEN]

echo.
echo To run integration tests:
echo   python run_integration_tests.py

echo.
echo To check environment:
echo   python test_integration_setup.py
