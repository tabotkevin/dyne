
# Semantic Commit Rules

Dyne follows the **Conventional Commits** specification to ensure clear, predictable versioning and automatic changelog generation.

This document describes the full commit message format, allowed types, rules, and examples.

## Commit Message Format

A commit message must follow this structure::

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

## Commit Types

The following commit `type` keywords are allowed:

* **feat** — A new feature
* **fix** — A bug fix
* **docs** — Documentation-only changes
* **style** — Code style changes (formatting, whitespace, no logic changes)
* **refactor** — Code changes that are not fixes or new features
* **perf** — Performance improvements
* **test** — Adding or improving tests
* **build** — Build system changes (Poetry, setuptools, CI)
* **ci** — CI-related changes (GitHub Actions, pipelines)
* **chore** — Routine tasks that do not affect production code
* **revert** — Reverting a previous commit

## Scopes

Scopes help clarify what part of Dyne is affected. Examples::

```
feat(core): add async request parser
fix(graphql): resolve Strawberry context issue
docs(api): update Response documentation
```

Scopes should be lowercase and short.

## Breaking Changes

To mark a breaking change, add `!` after the type or scope::

```
feat!: rewrite routing engine
refactor(core)!: remove deprecated middleware API
```

Also include a footer::

```
BREAKING CHANGE: Old middleware signature removed.
```

## Commit Description

Write a short, imperative sentence:

* Good: `add new async router`
* Bad: `added new async router` or `adds async router`

Keep it clear and concise.

## Body Section (Optional)

Use the body to explain *why* the change was made::

```
feat(validation): add pydantic v2 validators

Adds support for new pydantic V2 style validators and
improves error formatting for input validation.
```

Wrap lines at ~80 chars.

## Footer (Optional)

The footer is used for:

* **BREAKING CHANGE:** descriptions
* Issue references (`Fixes #15`, `Closes #22`)

Example::

```
fix(sqlalchemy): correct session cleanup

Fixes #42.
```

## Examples

### Feature

::

```
feat(graphql): add Strawberry integration interface
```

### Bug Fix

::

```
fix(router): resolve parameter matching bug
```

### Documentation

::

```
docs(contributing): expand PR guidelines
```

### Breaking Change

::

```
refactor(response)!: remove sync fallback API

BREAKING CHANGE: synchronous Response APIs removed.
```

## Why We Use Semantic Commits

Semantic commits enable:

* Automatic changelog generation
* Automatic version bumping (major/minor/patch)
* Clear history for maintainers and users
* Cleaner release notes

These rules are required for all pull requests submitted to Dyne.
