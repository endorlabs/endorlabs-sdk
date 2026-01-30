# Endorctl Version Check Scripts

Fast, lightweight scripts to check for endorctl updates via the public Endor Labs API.

## Quick Start

The fastest way to check for updates is using the public API endpoint:

```bash
curl -s https://api.endorlabs.com/meta/version | jq .ClientVersion
```

This returns the latest version (e.g., `"v1.6.322"`) without requiring authentication.

## Scripts

### Python Version (`check_endorctl_version.py`)

Full-featured version with proper version comparison and error handling.

```bash
# Simple check (just print latest version)
python .github/scripts/check_endorctl_version.py

# Check with state file (tracks last known version)
python .github/scripts/check_endorctl_version.py --state-file /tmp/endorctl_version.state

# Check and notify if update available
python .github/scripts/check_endorctl_version.py --state-file /tmp/endorctl_version.state --notify
```

**Exit codes:**
- `0` - No update available (or first run)
- `1` - Update available
- `2` - Error querying API

### Shell Version (`check_endorctl_version.sh`)

Lightweight shell script - fastest option for cron jobs.

```bash
# Simple check
./scripts/check_endorctl_version.sh

# Check with state file
./scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state

# Check and notify
./scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --notify
```

**Exit codes:** Same as Python version

## Cron Job Examples

### Check every 6 hours

```bash
# Python version
0 */6 * * * /usr/bin/python3 /path/to/.github/scripts/check_endorctl_version.py --state-file /tmp/endorctl_version.state --notify

# Shell version (faster)
0 */6 * * * /path/to/scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --notify
```

### Check daily at 9 AM

```bash
0 9 * * * /path/to/scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --notify
```

### Check hourly (quiet mode, only exit code)

```bash
0 * * * * /path/to/.github/scripts/check_endorctl_version.py --state-file /tmp/endorctl_version.state --quiet
```

## Integration Examples

### With Email Notification

```bash
#!/bin/bash
/path/to/scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --notify | \
    mail -s "endorctl Update Available" admin@example.com
```

### With Webhook Notification

```bash
#!/bin/bash
if /path/to/scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --quiet; then
    curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
        -d '{"text":"endorctl update available!"}'
fi
```

### With Logging

```bash
0 */6 * * * /path/to/scripts/check_endorctl_version.sh --state-file /tmp/endorctl_version.state --notify >> /var/log/endorctl_updates.log 2>&1
```

## API Endpoint Details

**Endpoint:** `https://api.endorlabs.com/meta/version`

**Method:** GET

**Authentication:** None required (public endpoint)

**Response Format:**
```json
{
  "ClientVersion": "v1.6.322",
  "Version": "v1.6.322"
}
```

**Fields:**
- `ClientVersion` - Latest endorctl version (recommended)
- `Version` - Alternative field name (same value)

## Performance

- **API Response Time:** Typically < 100ms
- **Script Execution:** < 200ms (Python) or < 50ms (Shell)
- **Network Overhead:** Minimal (single HTTP GET request)
- **Resource Usage:** Negligible (suitable for frequent cron jobs)

## Error Handling

Both scripts handle:
- Network timeouts (5 second timeout)
- API errors (non-200 responses)
- Missing state files (first run)
- Invalid version formats (graceful degradation)

## State File Format

The state file stores a single version string (e.g., `1.6.322`). The file is created automatically on first run and updated when a new version is detected.

**Location:** User-specified (recommended: `/tmp/endorctl_version.state` or `~/.endorctl_version.state`)

## Version Comparison

Versions are compared using semantic versioning rules:
- `1.6.322` < `1.6.323` (patch increment)
- `1.6.322` < `1.7.0` (minor increment)
- `1.6.322` < `2.0.0` (major increment)

The Python version uses proper version tuple comparison. The shell version uses `sort -V` when available, with fallback to string comparison.

## References

- [Endor Labs API Versions Documentation](https://docs.endorlabs.com/rest-api/about/versions/)
- [endorctl Installation Guide](https://docs.endorlabs.com/endorctl/install-and-configure/)

