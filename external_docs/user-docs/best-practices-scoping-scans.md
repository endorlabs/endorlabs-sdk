---
url: https://docs.endorlabs.com/best-practices/scoping-scans/
title: Best Practices: Scoping scans | Endor Labs Docs
downloaded: 2025-11-20 11:49:47
---

Best Practices: Scoping scans | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/best-practices/scoping-scans/_print.html)



# Best Practices: Scoping scans

Learn how to effectively scope your scans with Endor Labs inclusion and exclusion patterns.

Exclude and include filters help your team to focus their attention on the open source packages that matter most and to improve scan performance. Use inclusion patterns when you have many packages that you want to scan separately and exclusion patterns when you want to filter out packages that are not important to you.

You can include or exclude packages using the following standard patterns:

1. Include or exclude specific packages.
2. Include or exclude specific directories.
3. Include or exclude with a Glob style expressions.
4. Use include and exclude patterns together to exclude specific directories such as a test directory from a scan.
5. Use multiple include and exclude patterns together to exclude or include specific directories or file paths.

## Scoping scans with endorctl

To include or exclude a package based on its file name when you scan with endorctl.

* Include path
* Exclude path

```
endorctl scan --include-path="path/to/your/manifest/file/package.json"
```

```
endorctl scan --exclude-path="path/to/your/manifest/file/package.json"
```

To include or exclude a package based on its directory

* Include Directory
* Exclude Directory

```
endorctl scan --include-path="directory/path/**"
```

```
endorctl scan --include-path="src/java/**"
```

```
endorctl scan --exclude-path="path/to/your/directory/**"
```

```
endorctl scan --exclude-path="src/ruby/**"
```

## Examples of scoping scan

The following examples show how you can use scoping scans.

Use `--exclude-path="src/java/**"` to exclude all files under src/java, including all its subdirectories.

```
endorctl scan --exclude-path="src/java/**"
```

Use `--exclude-path="src/java/**"` to only exclude the files under src/java, but not its subdirectories.

```
endorctl scan --exclude-path="src/java/**"
```

Use `--include-path` and `--exclude-path` together to exclude specific directories such as test directories.

```
endorctl scan --include-path="src/java/**" --exclude-path="src/java/test/**"
```

Use multiple inclusion patterns together.

```
endorctl scan --quick-scan --include-path="src/java/**" --include-path="src/dotnet/**"
```

* Use multiple exclusion patterns together.

```
endorctl scan --include-path="src/java/**" --exclude-path="src/java/gradle/**" --exclude-path="src/java/maven/**"
```

## Best practices of scoping scans

Here are a few best practices of using scoping scans:

* Ensure that you enclose your exclude pattern in double quotes to avoid shell expansion issues. For example, do not use `--exclude-path=src/test/**`, instead, use `--exclude-path="src/test/**"`.
* Inclusion patterns are not designed for documentation or example directories. You cannot explicitly include documentation or example directories:
  + `docs/`
  + `documentation/`
  + `groovydoc/`
  + `javadoc`
  + `man/`
  + `examples/`
  + `demos/`
  + `inst/doc/`
  + `samples/`
* The specified paths must be relative to the root of the directory.
* If you are using **JavaScript** workspaces, Endor Labs automatically detects workspace roots and their lock files:
  + You can scan individual workspace packages without explicitly including the root package. The scanner automatically detects the workspace root and locates the lock file.
  + For example, to scan only a specific workspace package: `endorctl scan --include-path="packages/utils/**"` - the scanner automatically finds and uses the lock file at the workspace root.
  + You can still exclude specific child packages from your scan while the workspace root is automatically detected.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
