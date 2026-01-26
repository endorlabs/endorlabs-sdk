# Endor Cockpit Integration Tests

This directory contains integration tests for the Endor Cockpit SDK that use the real Endor Labs API.

## ⚠️ Important Notes

- **These tests create real objects** in the Endor Labs backend
- **Authentication required** - you need valid Endor Labs credentials
- **Cleanup is automatic** - tests clean up after themselves
- **Rate limiting** - tests include delays to respect API limits

## 🔧 Setup

### 1. Environment Variables

Set the following environment variables:

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
```

### 2. Install Dependencies

```bash
pip install -e .[dev]
```

### 3. Install endorctl (Optional)

For security scanning tests:

```bash
# Install endorctl (see Endor Labs documentation)
endorctl --version
```

## Running Integration Tests

### Quick Start

```bash
# Run all integration tests
python run_integration_tests.py

# Run with verbose output
python run_integration_tests.py -v

# Run specific test pattern
python run_integration_tests.py -k "test_create_namespace"

# Check environment only
python run_integration_tests.py --check-only
```

### Using pytest directly

```bash
# Run all integration tests
pytest tests/test_integration.py -m integration -v

# Run specific test
pytest tests/test_integration.py::TestEndorCockpitIntegration::test_create_namespace -v

# Run with cleanup disabled (for debugging)
pytest tests/test_integration.py -m integration -v --no-cleanup
```

## 📋 Test Categories

### Core Functionality Tests

- **`test_api_connection`** - Test basic API connection
- **`test_create_namespace`** - Test namespace creation
- **`test_list_namespaces`** - Test namespace listing
- **`test_get_namespace`** - Test namespace retrieval
- **`test_update_namespace`** - Test namespace updates
- **`test_delete_namespace`** - Test namespace deletion

### Advanced Tests

- **`test_namespace_hierarchy`** - Test parent-child namespace relationships
- **`test_error_handling`** - Test error conditions
- **`test_rate_limiting`** - Test API rate limiting behavior

### Security Tests

- **`test_security_scan_integration`** - Test endorctl security scanning
- **`test_security_scan_namespace`** - Test namespace security scanning

## 🏗️ Test Namespace

All tests use the namespace: **`endor-solutions-tgowan.tgowan-endor`**

Test objects are created with names like:
- `integration-test-create-{timestamp}`
- `integration-test-update-{timestamp}`
- `integration-test-delete-{timestamp}`

## 🧹 Cleanup

Tests automatically clean up after themselves:

1. **Namespace cleanup** - All test namespaces are deleted
2. **Hierarchy cleanup** - Child namespaces deleted before parents
3. **Error handling** - Cleanup continues even if tests fail
4. **Rate limiting** - Delays between operations to respect API limits

## 🔍 Debugging

### Check Environment

```bash
python run_integration_tests.py --check-only
```

### Run Without Cleanup

```bash
python run_integration_tests.py --no-cleanup
```

This leaves test objects in the backend for manual inspection.

### Verbose Output

```bash
python run_integration_tests.py -v
```

Shows detailed test output and API responses.

## ⚡ Performance

- **Rate limiting** - 1 second delays between operations
- **Timeouts** - 60 second timeouts for operations
- **Parallel execution** - Tests run sequentially to avoid conflicts
- **Cleanup delays** - Additional delays during cleanup

## 🚨 Troubleshooting

### Common Issues

1. **Authentication errors**
   - Check environment variables
   - Verify API credentials are valid
   - Ensure credentials have required permissions

2. **Permission errors**
   - Ensure credentials can create/delete namespaces
   - Check namespace permissions
   - Verify tenant namespace access

3. **Rate limiting**
   - Tests include delays, but API limits may still apply
   - Run tests with longer delays if needed

4. **endorctl not found**
   - Install endorctl for security scan tests
   - Security tests will be skipped if not available

### Debug Commands

```bash
# Check API connection
python -c "
from endor_cockpit.api_client import APIClient
client = APIClient()
print('API client created successfully')
"

# List namespaces manually
python -c "
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace
client = APIClient()
ns = namespace.list_namespaces(client, 'endor-solutions-tgowan.tgowan-endor')
print(f'Found {len(ns)} namespaces')
"
```

## Test Results

Successful test run output:

```
🧪 Endor Cockpit Integration Test Runner
==================================================
[OK] All required environment variables are set
[OK] endorctl is available: v1.0.0

[INFO] Running integration tests...
Command: python -m pytest tests/test_integration.py -q -m integration --tb=short --strict-markers --disable-warnings

[OK] All integration tests passed!
```

## 🔒 Security

- **No sensitive data** - Tests use dummy data
- **Automatic cleanup** - No persistent test data
- **Rate limiting** - Respects API limits
- **Error handling** - Graceful failure handling
