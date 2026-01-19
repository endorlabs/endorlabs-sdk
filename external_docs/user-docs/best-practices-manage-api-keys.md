---
url: https://docs.endorlabs.com/best-practices/manage-api-keys/
title: Best Practices: API key management | Endor Labs Docs
downloaded: 2026-01-16 09:48:24
---

Best Practices: API key management | Endor Labs Docs



* Type to search...

[Print entire section](/best-practices/manage-api-keys/_print.html)



# Best Practices: API key management

Learn how to manage API keys, check for expiring keys, and automate key rotation.

You can use API keys to engage with Endor Labs services programmatically to enable any automation or integration with other systems in your environment. See [Manage API keys](../../administration/api-keys/) for more information on how to create and delete API keys.

Ensure that you rotate API keys regularly to limit the window of opportunity for an API key to be compromised.

**Tip**

Instead of using API keys, you can use keyless authentication to authenticate with Endor Labs services. See [Keyless authentication](../../deployment/ci-scans/keyless-authentication/) for more information. Using keyless authentication eliminates the need to manage API keys and reduces the risk of API key compromise.

You can use the Endor Labs API to programmatically create scripts to manage API keys.

## Check for expiring API keys

API key expiry can cause interruptions in your workflows. It is a good practice to check for expiring API keys so that you can rotate them before they expire.

You can use the following script (`key-expiry.sh`) to check for expiring API keys. By default, the script checks for API keys that expire in the next day in the currently configured namespace. You can pass the `-d` flag with a number to check for API keys that expire in the next `n` days. You can also pass a namespace with the `-n` flag followed by the namespace name to check for expiring API keys in a specific namespace. The script uses [`jq`](https://jqlang.org/) to parse the json response and generate a formatted output. If you do not have `jq` installed, the script provides a json output.

```
#!/bin/bash

# Default values. You can update the values here or pass the values as flags to the script.
DAYS=1
NAMESPACE=""
NAMESPACE_FLAG=""

while getopts "n:d:" opt; do
  case $opt in
    n)
      NAMESPACE=$OPTARG
      NAMESPACE_FLAG="-n $NAMESPACE"
      ;;
    d)
      DAYS=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "Usage: $0 [-n namespace] [-d days]" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      echo "Usage: $0 [-n namespace] [-d days]" >&2
      exit 1
      ;;
  esac
done

TODAY=$(date +"%Y-%m-%d")

# Detect OS type and use appropriate date command
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    PLUS_DAYS=$(date -v+${DAYS}d +"%Y-%m-%d")
else
    # Other Unix systems
    PLUS_DAYS=$(date -d "+${DAYS} days" +"%Y-%m-%d")
fi

if [ -z "$NAMESPACE" ]; then
    echo "Searching for API keys expiring between $TODAY and $PLUS_DAYS ($DAYS days)"
else
    echo "Searching for API keys in namespace '$NAMESPACE' expiring between $TODAY and $PLUS_DAYS ($DAYS days)"
fi

# Check if jq is available
if command -v jq &> /dev/null; then
    # jq is available, use it for formatted output
    RESULT=$(endorctl api list $NAMESPACE_FLAG -r APIKey \
      --filter="spec.expiration_time >= date($TODAY) AND spec.expiration_time <= date($PLUS_DAYS)" \
      --field-mask "meta.name,spec.expiration_time,meta.created_by,spec.issuing_user.spec.email" -o json)

    if echo "$RESULT" | jq -e '.list.objects | length > 0' &>/dev/null; then
        echo "$RESULT" | jq '.list.objects[] | {name: .meta.name, expiration: .spec.expiration_time, user: .meta.created_by, email: .spec.issuing_user.spec.email}'
    else
        echo "No API keys found expiring in the specified date range."
    fi
else
    # jq is not available, use the regular output
    echo "Note: Install jq for better formatted output"
    endorctl api list $NAMESPACE_FLAG -r APIKey \
      --filter="spec.expiration_time >= date($TODAY) AND spec.expiration_time <= date($PLUS_DAYS)" \
      --field-mask "meta.name,spec.expiration_time"
fi
```

The script returns the API keys that are expiring in the specified days. The output contains the key name, expiry date, and the information about the user that created the key. You can inform the user that the API key is expiring in the specified days and ask them to rotate the API key. See [Create API keys](../../administration/api-keys/#create-an-api-key) for more information on how to create API keys.

### Create a cron job to check for expiring API keys

You can also create a cron job to run the script at a regular interval and fetch the details of the expiring API keys.

The following example shows a cron job script, `check_key_expiry_cron.sh`, that wraps the `key-expiry.sh` script, and sends an email to the specified email address if there are expiring API keys. You configure the script with the path to the script, the number of days to check for expiring API keys, the email address to send the report to, and the namespace to check for expiring API keys.

```
#!/bin/bash

# Configuration - Customize these values according to your needs
SCRIPT_PATH="/path/to/key-expiry.sh"
DAYS=1  # Days to check for expiring API keys
EMAIL="your-email@example.com"
NAMESPACE=""  # Namespace to check for expiring API keys

OUTPUT=$($SCRIPT_PATH -d $DAYS $([[ -n $NAMESPACE ]] && echo "-n $NAMESPACE"))

if [ $(echo "$OUTPUT" | wc -l) -gt 1 ]; then
    echo "$OUTPUT" | mail -s "API Keys Expiring in the Next $DAYS Days" $EMAIL
fi
```

Run the following command to create a cron job that runs the script at 8 AM every day if the script is located in the home directory.

```
0 8 * * * $HOME/check_key_expiry_cron.sh
```

## Check for API keys with long expiry

API keys with long expiry can be a security risk. The Endor Labs Create API key endpoint allows you to create API keys with expiry time of over 365 days. Such long expiry times may not be necessary and incompatible with your security policies.

You can use the following script (`check_long_expiry_keys.sh`) to check for API keys with long expiry. The script checks for API keys with expiry dates longer than 365 days by default on the currently configured namespace. You can pass the `-d` flag with a number to check for API keys with expiry days according to the number you pass. You can also choose to pass an Endor Labs namespace to search for long expiry API keys in a specific namespace with the `-n` flag followed by the namespace name. The script uses [`jq`](https://jqlang.org/) to parse the json response.

```
#!/bin/bash

# Default values
DAYS=365
NAMESPACE=""
NAMESPACE_FLAG=""

# Parse command line options
while getopts "n:d:" opt; do
  case $opt in
    n)
      NAMESPACE=$OPTARG
      NAMESPACE_FLAG="-n $NAMESPACE"
      ;;
    d)
      DAYS=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "Usage: $0 [-n namespace] [-d days]" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      echo "Usage: $0 [-n namespace] [-d days]" >&2
      exit 1
      ;;
  esac
done

# Calculate today's date in YYYY-MM-DD format
TODAY=$(date +"%Y-%m-%d")

# Detect OS type and use appropriate date command for calculating the future date
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    PLUS_DAYS=$(date -v+${DAYS}d +"%Y-%m-%d")
else
    # Linux
    PLUS_DAYS=$(date -d "+${DAYS} days" +"%Y-%m-%d")
fi

# Print info about the search
if [ -z "$NAMESPACE" ]; then
    echo "Searching for API keys with expiration dates longer than $DAYS days from today ($TODAY to $PLUS_DAYS)"
else
    echo "Searching for API keys in namespace '$NAMESPACE' with expiration dates longer than $DAYS days from today ($TODAY to $PLUS_DAYS)"
fi

# Check if jq is available
if command -v jq &> /dev/null; then
    # jq is available, use it for formatted output
    RESULT=$(endorctl api list $NAMESPACE_FLAG -r APIKey \
      --filter="spec.expiration_time > date($PLUS_DAYS)" \
      --field-mask "meta.name,spec.expiration_time,meta.created_by,spec.issuing_user.spec.email" -o json)

    # Check if list.objects exists and is not empty
    if echo "$RESULT" | jq -e '.list.objects | length > 0' &>/dev/null; then
        echo "$RESULT" | jq '.list.objects[] | {name: .meta.name, expiration: .spec.expiration_time, user: .meta.created_by, email: .spec.issuing_user.spec.email}'
    else
        echo "No API keys found with expiration dates longer than $DAYS days."
    fi
else
    # jq is not available, use the regular output
    echo "Note: Install jq for better formatted output"
    endorctl api list $NAMESPACE_FLAG -r APIKey \
      --filter="spec.expiration_time > date($PLUS_DAYS)" \
      --field-mask "meta.name,spec.expiration_time"
fi
```

The script returns the API keys with expiry dates longer than the number of days you passed with key name, expiry date, and the information about the user that created the key.

## Clean up expired API keys

You should regularly check for and delete expired API keys.

Keeping only active and necessary API keys can improve system performance by reducing the volume of data that needs to be processed during authentication checks. Regular cleanup makes it easier to manage and monitor active keys, allowing for better oversight of API access and usage patterns.

You can use the Endor Labs API to check for expired API keys and delete them.

The following script (`delete-expired-keys.sh`) checks for expired API keys and presents the options to delete them. You can choose to pass an Endor Labs namespace to search for expired API keys in a specific namespace. If you do not pass a namespace, the script checks for expired API keys in the currently configured namespace. The script uses [`jq`](https://jqlang.org/) to parse the json response.

```
#!/bin/bash
# Add a namespace to search for expired API keys in a specific namespace
NAMESPACE=""
NAMESPACE_FLAG=""
while getopts "n:" opt; do
  case $opt in
    n)
      NAMESPACE=$OPTARG
      NAMESPACE_FLAG="-n $NAMESPACE"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "Usage: $0 [-n namespace]" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      echo "Usage: $0 [-n namespace]" >&2
      exit 1
      ;;
  esac
done

TODAY=$(date +"%Y-%m-%d")
if [ -z "$NAMESPACE" ]; then
    echo "Searching for expired API keys (expiration date before $TODAY)"
else
    echo "Searching for expired API keys in namespace '$NAMESPACE' (expiration date before $TODAY)"
fi

check_jq() {
  if ! command -v jq &> /dev/null; then
    echo "Error: This script requires jq to be installed."
    echo "Please install jq and try again."
    exit 1
  fi
}
check_jq

# Get all expired API keys
RESULT=$(endorctl api list $NAMESPACE_FLAG -r APIKey \
  --filter="spec.expiration_time < date($TODAY)" \
  --field-mask "meta.name,spec.expiration_time,uuid" -o json)

# Check if there are any expired keys
if ! echo "$RESULT" | jq -e '.list.objects | length > 0' &>/dev/null; then
  echo "No expired API keys found."
  exit 0
fi

KEY_COUNT=$(echo "$RESULT" | jq '.list.objects | length')
echo "Found $KEY_COUNT expired API key(s)."

echo -e "\nExpired API Keys:"
echo "===================="
echo "$RESULT" | jq -r '.list.objects[] | "ID: \(.uuid)\nName: \(.meta.name)\nExpired: \(.spec.expiration_time)\n"'

echo -e "\nWould you like to delete these expired API keys?"
echo "1) Delete all expired keys"
echo "2) Select keys to delete individually"
echo "3) Exit without deleting"
read -p "Choose an option (1-3): " CHOICE

case $CHOICE in
  1)
    echo -e "\nDeleting all expired API keys..."
    for UUID in $(echo "$RESULT" | jq -r '.list.objects[].uuid'); do
      echo -n "Deleting key with UUID $UUID... "
      if endorctl api delete $NAMESPACE_FLAG -r APIKey --uuid=$UUID &> /dev/null; then
        echo "Success"
      else
        echo "Failed"
      fi
    done
    ;;

  2)
    echo -e "\nSelecting keys to delete individually:"
    for UUID in $(echo "$RESULT" | jq -r '.list.objects[].uuid'); do
      NAME=$(echo "$RESULT" | jq -r ".list.objects[] | select(.uuid == \"$UUID\") | .meta.name")
      EXPIRY=$(echo "$RESULT" | jq -r ".list.objects[] | select(.uuid == \"$UUID\") | .spec.expiration_time")

      echo -e "\nID: $UUID"
      echo "Name: $NAME"
      echo "Expired: $EXPIRY"

      read -p "Delete this key? (y/n): " DELETE
      if [[ $DELETE == "y" || $DELETE == "Y" ]]; then
        echo -n "Deleting... "
        if endorctl api delete $NAMESPACE_FLAG -r APIKey --uuid=$UUID &> /dev/null; then
          echo "Success"
        else
          echo "Failed"
        fi
      else
        echo "Skipped"
      fi
    done
    ;;

  3)
    echo "Exiting without deleting any keys."
    ;;

  *)
    echo "Invalid option. Exiting without deleting any keys."
    ;;
esac

echo -e "\nOperation completed."
```

### Create a cron job to check for expired API keys

You can also create a cron job to run the script at a regular interval.

The following example shows a cron job script, `check_expired_keys_cron.sh`, that wraps the `delete-expired-keys.sh` script. You configure the script with the option to run the script to delete or report expired API keys, the path to the script, the email address to send the report to, and the namespace to check for expired API keys.

```
#!/bin/bash

# Configuration - Customize these values according to you need
SCRIPT_PATH="/path/to/delete-expired-keys.sh"
EMAIL="your-email@example.com"
NAMESPACE=""  # Set the required namespace or leave empty to check API keys in the currently configured namespace
OPERATION="REPORT"  # Set that value as "DELETE" to delete expired API keys

# Create a temporary file for the report
TEMP_REPORT=$(mktemp)

# Function to send email with the report
send_email() {
  local subject="$1"
  cat $TEMP_REPORT | mail -s "$subject" $EMAIL
  echo "Email sent with expired API keys report."
}

if [ "$OPERATION" = "REPORT" ]; then
  if [ -z "$NAMESPACE" ]; then
    echo "3" | $SCRIPT_PATH > $TEMP_REPORT 2>&1
  else
    echo "3" | $SCRIPT_PATH -n $NAMESPACE > $TEMP_REPORT 2>&1
  fi

  if grep -q "Found [1-9][0-9]* expired API key" $TEMP_REPORT; then
    send_email "Expired API Keys Found - Action Required"
  else
    echo "No expired API keys found."
  fi

elif [ "$OPERATION" = "DELETE" ]; then
  if [ -z "$NAMESPACE" ]; then
    echo "1" | $SCRIPT_PATH > $TEMP_REPORT 2>&1
  else
    echo "1" | $SCRIPT_PATH -n $NAMESPACE > $TEMP_REPORT 2>&1
  fi

  if grep -q "Found [1-9][0-9]* expired API key" $TEMP_REPORT; then
    send_email "Expired API Keys Deleted - Action Taken"
  else
    echo "No expired API keys found."
  fi

else
  echo "Invalid OPERATION value: $OPERATION. Must be 'REPORT' or 'DELETE'." > $TEMP_REPORT
  send_email "ERROR: Invalid Expired API Keys Operation"
fi

rm $TEMP_REPORT
```

You can use the following command to create a cron job that runs the script at 8 AM every day.

```
0 8 * * * $HOME/check_expired_keys_cron.sh
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
