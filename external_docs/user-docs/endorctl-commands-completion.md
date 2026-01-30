---
url: https://docs.endorlabs.com/endorctl/commands/completion/
title: completion | Endor Labs Docs
downloaded: 2026-01-26 10:05:41
---

completion | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/completion/_print.html)



# completion

Use the completion command to get a command completion script for a specified command shell

The `completion` command for endorctl outputs a completion script that may be added to your local environment. Once run this script will enable tab autocompletion for endorctl.

Supported command completion environments are Zsh, PowerShell, bash and fish.

## Command completion for Zsh shells

To enable command completion for a macOS based Zsh environment.

```
echo "source $(endorctl completion zsh)" >> ~/.zshrc
source ~/.zshrc
```

You will need to start a new shell for this setup to take effect.

## Command completion for bash shells

To enable command completion for a Linux bash based shell.

```
echo "source $(endorctl completion zsh)" >> ~/.bashrc
source ~/.bashrc
```

You will need to start a new shell for this setup to take effect.

## Command completion for PowerShell

To load completions in your current shell session.

```
endorctl completion powershell | Out-String | Invoke-Expression
```

To load completions for every new session, add the output of the above command
to your PowerShell profile.

## Command completion for Fish shells

To load completions in your current shell session.

```
endorctl completion fish | source
```

To load completions for every new session, execute once.

```
endorctl completion fish > ~/.config/fish/completions/endorctl.fish
```

You will need to start a new shell for this setup to take effect.

## Usage

There are no flags that apply to endorctl completion.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
