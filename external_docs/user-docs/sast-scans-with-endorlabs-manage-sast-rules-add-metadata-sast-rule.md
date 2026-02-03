---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/manage-sast-rules/add-metadata-sast-rule/
title: Add metadata to a SAST rule | Endor Labs Docs
downloaded: 2026-02-03 00:50:10
---

Add metadata to a SAST rule | Endor Labs Docs



* Type to search...

[Print entire section](/sast-scans-with-endorlabs/manage-sast-rules/add-metadata-sast-rule/_print.html)



# Add metadata to a SAST rule

You can add metadata to the custom SAST rule that you create or when you clone an existing Endor Labs rule in the metadata section.

The following example shows the SAST rule template with the metadata section.

```
rules:
- id: <lang>-<rulename>
  languages:
  - < java | js | py >

  < patterns, mode, options >

  message: < Rule message that provides details about the matched pattern and informs about how to mitigate any related issues, and can be shown in our UI. >
  severity: < INFO | WARNING | ERROR >
  metadata:
    version: 1.0.0
    description: A customer visible description for this rule.
    explanation: |
        An explanation of the issue.
    remediation: |
        Possible remediation steps you can take to fix the issue.
    cwe:
    - "CWE-xxx: <cwe title from https://cwe.mitre.org/data/definitions/xxx.html>"
    likelihood: < HIGH | MEDIUM | LOW >
    impact: < HIGH | MEDIUM | LOW >
    confidence: < HIGH | MEDIUM | LOW >
```

You can add the following metadata information to the rule:

* `explanation`: An explanation of the issue.
* `remediation`: Possible remediation steps you can take to fix the issue.
* `cwe`: The CWE ID of the issue. The OWASP or SANS-25 category of the CWE ID will automatically appear under **Rule Tags** in **Findings** if such a mapping can be established.

  The following image shows an example where the CWE-22 is automatically mapped to the appropriate category.

  ![Finding details](../../../images/SASTRuleCWEID.png)
* `impact`: The impact of the issue. Impact is one of the factors that determines the severity of the issue. See [SAST severity matrix](../../../sast-scans-with-endorlabs/#sast-severity-matrix) for more information.
* `confidence`: The confidence level that the issue is real. Confidence is one of the factors that determines the severity of the issue. See [SAST severity matrix](../../../sast-scans-with-endorlabs/#sast-severity-matrix) for more information.

For example:

```
rules:
  - id: python_ssl_rule-ssl-no-version
    .
    .
    .
    metadata:
      explanation: |
        The application was found calling an SSL module with SSL or TLS protocols that have known deficiencies. It is strongly recommended that newer applications use TLS 1.2 or 1.3 and `SSLContext.wrap_socket`.
      remediation: |
        If using the `pyOpenSSL` module, please note that it has been deprecated and the Python Cryptographic Authority strongly suggests moving to use the [pyca/cryptography](https://github.com/pyca/cryptography) module instead. To remediate this issue for the `ssl` module, create a new TLS context and pass in `ssl.PROTOCOL_TLS_CLIENT` for clients or `ssl.PROTOCOL_TLS_SERVER` for servers to the `ssl.SSLContext(...)` `protocol=` argument. When converting the socket to a TLS socket, use the new `SSLContext.wrap_socket` method instead.
    .
    .
    .
```

When Endor Labs generates a finding based on this rule, the explanation and remediation sections appear in the finding details.

![Finding details](../../../images/metadata-sast-rule.png)

The metadata information also appears in the SARIF output.

```
{
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": {
          "uri": "samples/3p/gitlab/python/ssl/rule-ssl-with-bad-version.py"
        },
        "region": {
          "startLine": 9
        }
      }
    }
  ],
  "message": {
    "text": "Problem:\nThe application was found calling an SSL module with SSL or TLS protocols that have known deficiencies. It is strongly\nrecommended that newer applications use TLS 1.2 or 1.3 and `SSLContext.wrap_socket`.\n\nSolution:\nIf using the `pyOpenSSL` module, please note that it has been deprecated and the Python Cryptographic Authority strongly\nsuggests moving to use the [pyca/cryptography](https://github.com/pyca/cryptography) module instead.\nTo remediate this issue for the `ssl` module, create a new TLS context and pass in `ssl.PROTOCOL_TLS_CLIENT` for clients\nor `ssl.PROTOCOL_TLS_SERVER` for servers to the `ssl.SSLContext(...)` `protocol=` argument. When converting the socket\nto a TLS socket, use the new `SSLContext.wrap_socket` method instead.\n\nExample creating a TLS 1.3 client socket connection by using a newer version of Python (3.11.4) and the SSL module:\n```\nimport ssl\nimport socket\n\n# Create our initial socket\nwith socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:\n    # Connect the socket\n    sock.connect(('www.example.org', 443))\n\n    # Create a new SSLContext with protocol set to ssl.PROTOCOL_TLS_CLIENT\n    # This will auto-select the highest grade TLS protocol version (1.3)\n    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)\n    # Load our a certificates for server certificate authentication\n    context.load_verify_locations('cert.pem')\n    # Create our TLS socket, and validate the server hostname matches\n    with context.wrap_socket(sock, server_hostname=\"www.example.org\") as tls_sock:\n        # Send some bytes over the socket (HTTP request in this case)\\\n        data = bytes('GET / HTTP/1.1\\r\\nHost: example.org\\r\\n\\r\\n', 'utf-8')\n        sent_bytes = tls_sock.send(data)\n        # Validate number of sent bytes\n        # ...\n        # Read the response\n        resp = tls_sock.recv()\n        # Work with the response\n        # ...\n```\n\nFor more information on the ssl module see:\n- https://docs.python.org/3/library/ssl.html\n\nFor more information on pyca/cryptography and openssl see:\n- https://cryptography.io/en/latest/openssl/\n"
  },
  "properties": {
    "explanation": "The application was found calling an SSL module with SSL or TLS protocols that have known deficiencies. It is strongly recommended that newer applications use TLS 1.2 or 1.3 and `SSLContext.wrap_socket`.\n",
    "remediation": "If using the `pyOpenSSL` module, please note that it has been deprecated and the Python Cryptographic Authority strongly suggests moving to use the [pyca/cryptography](https://github.com/pyca/cryptography) module instead. To remediate this issue for the `ssl` module, create a new TLS context and pass in `ssl.PROTOCOL_TLS_CLIENT` for clients or `ssl.PROTOCOL_TLS_SERVER` for servers to the `ssl.SSLContext(...)` `protocol=` argument. When converting the socket to a TLS socket, use the new `SSLContext.wrap_socket` method instead.\n",
    "tags": [
      "A02:2021",
      "Cryptographic-Failures",
      "OWASP-Top-10"
    ]
  }
}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
