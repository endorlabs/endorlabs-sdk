# Fix CI Issues for PR #7

## Overview

PR #7 has multiple CI failures that need to be addressed:
1. **Linting failures** - 250 ruff errors (mostly whitespace and line length issues)
2. **Test failures** - Missing required secrets for integration tests
3. **Unicode encoding issues** - Some files have Unicode characters causing encoding problems

## Issues Identified

### 1. Linting Issues (250 errors)
- **W293**: Blank lines contain whitespace (206 instances)
- **E501**: Line too long (117 > 88 characters) 
- **F541**: f-string without placeholders
- **Files affected**: `workflow/init_vector_db.py`, `workflow/test_vector_db.py`

### 2. Test Failures
- **Secret vs Variable mismatch**: CI workflow checks for `ENDOR_API` and `ENDOR_NAMESPACE` as **secrets**, but they're configured as **environment variables**
- **Integration tests**: Cannot run without proper API credentials
- **All Python versions**: 3.12, 3.13, 3.14 failing for same reason

### 3. Unicode Issues
- **Encoding problems**: Some files contain Unicode characters causing `charmap` codec errors
- **Cross-platform**: Windows compatibility issues with Unicode emojis

## Fix Plan

### Phase 1: Fix Linting Issues (High Priority)
1. **Run ruff auto-fix** to resolve fixable issues
2. **Manual fixes** for remaining issues:
   - Remove whitespace from blank lines
   - Break long lines (E501 errors)
   - Remove unnecessary f-string prefixes
3. **Test locally** before pushing

### Phase 2: Handle Test Failures (Medium Priority)
1. **Fix secret vs variable mismatch**: Update CI workflow to check for `ENDOR_API` and `ENDOR_NAMESPACE` as **variables** instead of **secrets**
2. **Update environment variable references** in the workflow
3. **Test the fix** to ensure integration tests can run

### Phase 3: Fix Unicode Issues (Medium Priority)
1. **Remove Unicode characters** from all files
2. **Use ASCII alternatives** for status indicators
3. **Test cross-platform compatibility**

### Phase 4: Clean Up (Low Priority)
1. **Remove unnecessary files** (__pycache__, .gitignore issues)
2. **Update .gitignore** to exclude build artifacts
3. **Verify all changes** work correctly

## Implementation Steps

### Step 1: Fix Linting Issues
```bash
# Run ruff auto-fix
uv run ruff check . --fix

# Check remaining issues
uv run ruff check .

# Fix remaining issues manually
```

### Step 2: Handle Test Failures
```bash
# Fix CI workflow to check for variables instead of secrets
# Update .github/workflows/ci.yml lines 114-122
# Change from secrets.ENDOR_API to vars.ENDOR_API
# Change from secrets.ENDOR_NAMESPACE to vars.ENDOR_NAMESPACE
```

### Step 3: Fix Unicode Issues
```bash
# Remove Unicode characters from all files
# Replace with ASCII alternatives
```

### Step 4: Clean Up
```bash
# Remove __pycache__ directories
# Update .gitignore
# Test locally
```

## Success Criteria

- [x] **Phase 1 Complete**: Fixed 200+ linting errors (whitespace, line length, unused imports)
- [x] **Phase 2 Complete**: Fixed CI workflow to check variables instead of secrets
- [ ] Remaining 15 linting errors in tool_schema.py and workflow files
- [ ] Tests pass (unit tests at minimum)
- [ ] No Unicode encoding issues
- [ ] CI pipeline passes
- [ ] PR ready for review

## Files to Fix

### High Priority
- `workflow/init_vector_db.py` - 200+ linting errors
- `workflow/test_vector_db.py` - 50+ linting errors

### Medium Priority
- `.github/workflows/ci.yml` - Update to handle missing secrets
- `tests/test_integration.py` - Add conditional logic

### Low Priority
- Remove `__pycache__/` directories
- Update `.gitignore`
- Clean up temporary files

## Estimated Time

- **Phase 1**: 30 minutes (auto-fix + manual cleanup)
- **Phase 2**: 15 minutes (CI workflow updates)
- **Phase 3**: 15 minutes (Unicode cleanup)
- **Phase 4**: 10 minutes (cleanup)
- **Total**: ~70 minutes

## Notes

- Focus on Phase 1 first (linting issues)
- Test changes locally before pushing
- Consider creating a separate branch for fixes
- Ensure all changes maintain functionality
