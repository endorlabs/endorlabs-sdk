---
url: https://docs.endorlabs.com/integrations/package-manager/mtls-authentication/
title: Authenticate to private packages using mTLS | Endor Labs Docs
downloaded: 2025-10-23 23:25:30
---

Authenticate to private packages using mTLS | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/integrations/package-manager/mtls-authentication/_print.html)



# Authenticate to private packages using mTLS

Learn how to configure custom package repositories for dependency resolution using mTLS.

Mutual Transport Layer Security (mTLS) is a protocol that mandates both the sender and receiver to authenticate each other before establishing a secure connection. Each party verifies the other’s certificate, ensuring authenticity and trust. This establishes a secure connection between both the parties.

Use mutual TLS to securely authenticate to artifact repositories.

## Set up mTLS

Perform the following steps to set up a secure mTLS connection:

#### Note

If your certificate is in PKCS12 format, you can start with step 1. If you already have a PEM certificate, you can skip to step 2.

1. Generate client certificate and client key

   Run the following command to generate the client certificate in the Privacy Enhanced Mail (PEM) format. Replace `<pkcs12 file>` with the name of your `.p12` file.

   ```
   openssl pkcs12 -in <pkcs12 file>.p12 -clcerts -nokeys | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > client.crt
   ```

   Run the following command to generate the client key in the Privacy Enhanced Mail (PEM) format. Replace `<pkcs12 file>` with the name of your `.p12` file.

   ```
   openssl pkcs12 -in <pkcs12 file>.p12 -nocerts -nodes | sed -ne '/-BEGIN PRIVATE KEY-/,/-END PRIVATE KEY-/p' > client.key
   ```

   Ensure you have your PKCS12 certificate and its password ready. When prompted, enter the password.
2. Format the client certificate and client key as json

   Run the following command to format the client certificate as json:

   ```
   awk '{printf "%s\\n", $0}' client.crt
   ```

   Run the following command to format the client key as json:

   ```
   awk '{printf "%s\\n", $0}' client.key
   ```
3. Create a package manager resource after generating the client certificate and client key.

### Authenticate to Gradle repository

Run the following command to create a package manager resource and authenticate to Gradle artifact repository. Replace `namespace` with your namespace.

```
endorctl api create -n <namespace> -r packageManager -d '{
    "meta": {
        "name": "test mtls for npm creation",
        "description": "test mtls creation"
    },
    "spec": {
        "gradle": {
            "property_key_name": "ENDOR_MTLS_CONFIGURATION",
            "property_key_value": "any non empty value",
            "mtls": {
                "client_cert": "formatted pem client.crt",
                "client_key": "formatted pem client.key"
            }
        }
    }
}'
```

#### Note

The `property_key_name` must be set exactly as **ENDOR\_MTLS\_CONFIGURATION**.

### Authenticate to Maven repository

Run the following command to create a package manager resource and authenticate to Maven repository.

Replace:

* `namespace` with your namespace.
* `https://nexus.example.com/repository/public` with your Maven repository URL.

```
endorctl api create -n <namespace> -r packageManager -d '{
    "meta": {
        "name": "test mtls for npm creation",
        "description": "test mtls creation"
    },
    "spec": {
        "mvn": {
            "url": "https://nexus.example.com/repository/public",
            "mtls": {
                "client_cert": "formatted pem client.crt",
                "client_key": "formatted pem client.key"
            }
        }
    }
}'
```

### Authenticate to PyPI repository

Run the following command to create a package manager resource and authenticate to PyPI repository.

Replace:

* `namespace` with your namespace.
* `https://nexus.example.com/repository/pypi` with your PyPI repository URL.

```
endorctl api create -n <namespace> -r packageManager -d '{
    "meta": {
        "name": "test mtls for python creation",
        "description": "test mtls creation"
    },
    "spec": {
        "pypi": {
            "priority": 1,
            "url": "https://nexus.example.com/repository/pypi",
            "mtls": {
                "client_cert": "formatted pem client.crt",
                "client_key": "formatted pem client.key"
            }
        }
    }
}'
```

### Authenticate to npm registry

Run the following command to create a package manager resource and authenticate to npm registry.

Replace:

* `namespace` with your namespace.
* `https://nexus.example.com/repository/npm` with your npm registry URL.

```
endorctl api create -n <namespace> -r packageManager -d '{
    "meta": {
        "name": "test mtls for  npm creation",
        "description": "test mtls creation"
    },
    "spec": {
        "npm": {
            "url": "https://nexus.example.com/repository/npm",
            "mtls": {
                "client_cert": "formatted pem client.crt",
                "client_key": "formatted pem client.key"
            }
        }
    }
}'
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
