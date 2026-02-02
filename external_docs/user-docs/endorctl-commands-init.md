---
url: https://docs.endorlabs.com/endorctl/commands/init/
title: init | Endor Labs Docs
downloaded: 2026-01-29 22:20:45
---

init | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/init/_print.html)



# init

Use the init command to authenticate to Endor Labs from a workstation with an external identity provider.

The command `endorctl init` allows you to quickly authenticate your client to Endor Labs using an external identity provider.

Supported authentication providers for `endorctl init` are:

* `google` - Used to create an API key and API key secret when you sign in with Google Workspaces as your external identity provider.
* `github` - Used to create an API key and API key secret when you sign in with GitHub Cloud as your external identity provider.
* `gitlab` - Used to create an API key and API key secret when you sign in with GitLab Cloud as your external identity provider.
* `email` - Used to create an API key and API key secret when you sign in with an email link.
* `sso` - Used to sign in with a Custom Enterprise Identity Provider, such as Okta.

## Usage

Run `endorctl init` and your browser window will open automatically. Select your authentication provider from the available options and complete the authentication process.

![Init authentication through browser](../../../images/init-auth-mode.png)

You can also specify your supported authentication provider manually:

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

To login with your supported authentication provider in environments without a browser you can use headless mode:

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

Once you’ve issued the command in headless mode please navigate to an internet/browser accessible computer and follow the instructions provided in your terminal.

## Options

The following flags and environment variables are available for the init command.

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `auth-mode` | `ENDOR_INIT_AUTH_MODE` | string | Set authentication method for the initialization process (`github`, `google`, `gitlab`, or `azureadv2`). |
| `headless-mode` | `ENDOR_INIT_HEADLESS_MODE` | boolean (default:false) | Run authentication and initialization without opening your browser. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
