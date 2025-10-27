---
url: https://docs.endorlabs.com/endorctl/install-and-configure/
title: Install and configure endorctl | Endor Labs Docs
downloaded: 2025-10-27 12:57:23
---

Install and configure endorctl | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/install-and-configure/_print.html)



# Install and configure endorctl

Learn how to install, configure, and authenticate with Endor Labs

Perform software composition analysis, dependency management, or detect secrets in your code using Endor Labs.

## Download and install endorctl

Use one of the following methods to download and install endorctl on your local system. After you install endorctl, you must authenticate. Then you can start scanning your code.

### Install endorctl with Homebrew

Use Homebrew to efficiently install endorctl on macOS and Linux operating systems making it easy to manage dependencies, and track installed packages with their versions.

Install endorctl from the [Endor Labs tap](https://github.com/endorlabs/homebrew-tap) with Homebrew by running the following commands. The tap is updated regularly with the latest endorctl release.

```
brew tap endorlabs/tap
brew install endorctl
```

### Install endorctl with npm

Use npm to efficiently install endorctl on macOS, Linux, and Windows operating systems making it easy to manage dependencies, track and update installed packages and their versions.

1. Make sure that you have npm installed in your local environment and use the following command to install endorctl.

   ```
   npm install -g endorctl
   ```
2. Run the following command to get the npm global bin directory.

   ```
   npm config get prefix
   ```
3. Edit your shell configuration file and insert the path you obtained from the previous command.

   ```
   export PATH="/path/to/npm/global/bin:$PATH"
   ```
4. Reload your shell configuration and verify endorctl is installed.

   ```
   endorctl --version
   ```
5. To update your version of endorctl, run the following command.

   ```
   npm update -g endorctl
   ```

[endorctl](https://www.npmjs.com/package/endorctl) is available as an npm package and is updated regularly with the latest endorctl release.

### Download and install the endorctl binary directly

To download the endorctl binary directly use the following commands:

* Linux
* Mac OS
* Windows

```
## Download the latest CLI for Linux amd64
curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl

## Verify the checksum of the binary
echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c

## Modify the permissions of the binary to ensure it is executable
chmod +x ./endorctl

## Create an alias endorctl of the binary to ensure it is available in other directory
alias endorctl="$PWD/endorctl"
```

```
### Download the latest CLI for MacOS ARM64
curl https://api.endorlabs.com/download/latest/endorctl_macos_arm64 -o endorctl

### Verify the checksum of the binary
echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_macos_arm64)  endorctl" | shasum -a 256 -c

### Modify the permissions of the binary to ensure it is executable
chmod +x ./endorctl

### Create an alias endorctl of the binary to ensure it is available in other directory
alias endorctl="$PWD/endorctl"
```

```
## Download the latest CLI for Windows amd64
curl -O https://api.endorlabs.com/download/latest/endorctl_windows_amd64.exe
## Check the expected checksum of the binary file
curl https://api.endorlabs.com/sha/latest/endorctl_windows_amd64.exe
## Verify the expected checksum and the actual checksum of the binary match
certutil -hashfile .\endorctl_windows_amd64.exe SHA256
## Rename the binary file
ren endorctl_windows_amd64.exe endorctl.exe
```

You can also view these instructions via the Endor Labs application user interface:

1. Sign in to Endor Labs.
2. Select **Projects** from the left sidebar.
3. Click **Add Project**.
4. Choose **CLI**.
5. Follow the on-screen instructions to download and install the appropriate version and architecture of `endorctl` for your system.

You can keep track of endorctl release details by checking the [Endor Labs release notes](../../releasenotes/).

## Authenticate to Endor Labs

Users can authenticate to Endor Labs several ways:

1. [Using the init command](#login-with-the-init-command)
2. [With an API token](#login-with-an-api-key)

### Login with the init command

To log in with your supported authentication provider:

* Google
* GitHub
* GitLab
* Email
* SSO

```
endorctl init --auth-mode=google
```

```
endorctl init --auth-mode=github
```

```
endorctl init --auth-mode=gitlab
```

```
endorctl init --auth-email=<insert_email_address>
```

```
endorctl init --auth-mode=sso --auth-tenant=<insert-your-tenant>
```

To log in with your supported authentication provider in environments without a browser you can use headless mode:

* Google
* GitHub
* GitLab
* Email
* SSO

```
endorctl init --auth-mode=google --headless-mode
```

```
endorctl init --auth-mode=github --headless-mode
```

```
endorctl init --auth-mode=gitlab --headless-mode
```

```
endorctl init --auth-email=<insert_email_address> --headless-mode
```

```
endorctl init --auth-mode=sso --auth-tenant=<insert-your-tenant> --headless-mode
```

### Login with an API Key

To log in with an API key you’ll need to set the following environment variables:

* **ENDOR\_API\_CREDENTIALS\_KEY** - The API key used to authenticate against the Endor Labs API.
* **ENDOR\_API\_CREDENTIALS\_SECRET** - The API key secret used to authenticate against the Endor Labs API.
* **ENDOR\_NAMESPACE** - The Endor Labs namespace you would like to scan against. You can locate the namespace from the top left hand corner of the screen under the Endor Labs logo on the [Endor Labs application](https://app.endorlabs.com).

To get an API Key and secret for use with endorctl, see [Managing API Keys](../../administration/api-keys/).

To set your environment variables run the following commands and replace each example with the appropriate value.

```
export ENDOR_API_CREDENTIALS_KEY=<example-api-key>
export ENDOR_API_CREDENTIALS_SECRET=<example-api-key-secret>
export ENDOR_NAMESPACE=<example-tenant-namespace>
```

Once you’ve exported your environment variables you can test successful authentication by running the following command to list projects in your namespace.

```
endorctl api list -r Project --page-size=1
```

If you do not have any projects in your namespace you will get an empty json output, which means you are successfully authenticated.

### Print your access token

Once you have successfully initialized endorctl, you can print your access token with the following command.

```
endorctl auth --print-access-token
```

The token has an expiration time of 4 hours.

## Persistently set environment variables for endorctl

To persistently set an environment variable, append the environment variable and the value to `~/.endorctl/config.yaml`. This configuration file is for CLI usage.

For example, if your GitHub Enterprise Server URL was <https://api.github.com> you can set the variable to persist in your configuration using the following command.

```
echo "ENDOR_SCAN_SOURCE_GITHUB_API_URL: https://api.github.com" >> ~/.endorctl/config.yaml
```

See [endorctl commands for all supported commands and environment variables](../../endorctl/environment-variables/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
