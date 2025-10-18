#!/bin/bash
# Shell script to set up environment variables for Endor Cockpit integration tests
# Run this script before running integration tests

echo "Setting up Endor Cockpit environment variables..."

# Set the environment variables
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key-here"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret-here"

echo "Environment variables set:"
echo "  ENDOR_API = $ENDOR_API"
echo "  ENDOR_API_CREDENTIALS_KEY = $ENDOR_API_CREDENTIALS_KEY"
echo "  ENDOR_API_CREDENTIALS_SECRET = [HIDDEN]"

echo ""
echo "To run integration tests:"
echo "  python run_integration_tests.py"

echo ""
echo "To check environment:"
echo "  python test_integration_setup.py"
