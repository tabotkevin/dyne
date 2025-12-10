Here is a **clean, professional, production-ready `CONTRIBUTING.md`** for Dyne — modeled after FastAPI, Starlette, Django, and SQLAlchemy contributing guides.
You can copy/paste this directly into the root of the repository.

---

# 🧩 **CONTRIBUTING.md for Dyne**

# Contributing to Dyne

First off — thank you for thinking about contributing to **Dyne**!
Dyne is an open-source, batteries-included async Python web framework, and contributions of all kinds are welcome:

- 🚀 new features
- 🐛 bug fixes
- 🧪 test improvements
- 📚 documentation improvements
- 🛠 refactors and cleanups
- 💡 ideas, discussions, and feedback

This guide describes how to contribute effectively and consistently.

---

# 📌 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Submit an Issue](#how-to-submit-an-issue)
3. [Development Setup](#development-setup)
4. [Branching and Workflow](#branching-and-workflow)
5. [Code Style](#code-style)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Guidelines](#pull-request-guidelines)
9. [Release Process](#release-process)

---

# 📜 Code of Conduct

By contributing, you agree to follow the project’s **Code of Conduct**.
Be respectful, constructive, and kind.

---

# 🐞 How to Submit an Issue

Before opening an issue:

1. Search existing issues to avoid duplicates
2. Use the built-in issue templates:

   - **Bug Report**
   - **Feature Request**
   - **Refactor Request**

A good issue includes:

- A clear summary
- Steps to reproduce (if a bug)
- Motivation (if a feature)
- Code samples when possible
- Environment info

---

# 🛠 Development Setup

Install `Rye` from `https://rye.astral.sh/guide/installation/`

Clone the repository:

```bash
git clone https://github.com/<your-user>/dyne.git
cd dyne
```

Create a virtual environment and install development dependencies:

```bash
rye sync
```

This installs:

- pytest
- pytest-mock
- httpx

---

# 🌿 Branching and Workflow

Dyne follows a simple, clean **Issue → Branch → PR** workflow.

## 1. Create an issue

Every change starts with an issue.

## 2. Create a branch named after the issue

Example:

```
issue-123-add-pydantic-output-backend
issue-98-fix-router-path-matching
issue-77-refactor-startup-signals
```

## 3. Make commits referencing the issue

Use **conventional commits**:

```
feat(output): add plugin-based backends (#123)
fix(router): normalize slashes in paths (#98)
refactor(core): simplify middleware chain (#77)
```

---

# 🎨 Code Style

Dyne uses:

- **Ruff** for linting
- **Black** formatting (via Ruff rules)
- **PEP8 + modern Python** idioms
- **Async-first** architecture

Run lint:

```bash
rye lint
```

---

# 🧪 Running Tests

Tests use pytest:

```bash
rye test
```

With coverage:

```bash
coverage run -m pytest
coverage report -m
```

Contributions must include tests when they affect behavior.

---

# 📚 Documentation

Documentation contributions are welcome!

If changing user-facing behavior, add or update docs.

Examples:

- New decorators
- New Response types
- Changes in request handling
- New GraphQL backends
- Output serialization plugins

Documentation style: clear, concise, example-driven.

---

# 🔀 Pull Request Guidelines

Before submitting a pull request:

### ✔ 1. Your PR **must** reference an issue

Include:

```
Closes #123
```

### ✔ 2. Your PR should have a clear title

Using conventional commits:

```
feat(graphql): add ariadne backend (#140)
fix(output): handle marshmallow nested fields (#155)
docs: update quickstart (#112)
```

### ✔ 3. Run all checks locally

- `rye lint`
- `rye test`

### ✔ 4. Keep PRs focused

Prefer smaller PRs to giant ones when possible.

### ✔ 5. Add tests

If your code changes behavior, you must include or update tests.

---

# 🚀 Release Process (Maintainers)

Releases follow semantic versioning:

- **MAJOR** — breaking changes
- **MINOR** — new functionality
- **PATCH** — bug fixes

Dyne uses **Release Drafter** to automatically build release notes.

Maintainers create a release from the GitHub “Draft Release” page.

Optional automatic version tagging is supported via `auto-tag.yml`.

---

# ❤️ Thank You

Your contributions help make **Dyne** better for everyone.
We appreciate your time, your ideas, and your effort.

If you need help, open a discussion or tag maintainers on GitHub.

Happy hacking! 🚀
