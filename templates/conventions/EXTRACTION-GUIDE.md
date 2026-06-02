# Convention Extraction Guide

Use this guide before asking Qoder, Cursor, Codex, or another AI coding tool to
write `.codebrain/conventions/*.md` files from a framework or business codebase.

## Goal

Extract rules that developers should follow while writing application code.
Do not extract framework internals, implementation mechanisms, private helper
details, or facts that are only useful when maintaining the framework itself.

## Required Inputs

- Read application source files for usage patterns.
- Read test files and extract how the project expects tests to be written.
- Prefer public APIs, project-level conventions, error handling, validation,
  routing, dependency injection, security, data access, and testing patterns.

## Do

- Write short, actionable rules.
- Include when the rule applies.
- Prefer "do this / avoid that" language.
- Keep each convention under 500 words.
- Mention concrete APIs only when application developers should call or avoid them.
- Create a dedicated `testing.md` when tests reveal project-specific patterns.

## Do Not

- Do not turn framework internals into team conventions.
- Do not write rules about metaclass machinery, dependency solver internals,
  field registration internals, private attributes, or generated counters.
- Do not copy long explanations from source files.
- Do not include production secrets, customer data, logs, or credentials.
- Do not write a convention unless it changes how an application developer should work.

## Low-Signal Keywords

Treat these as warning signs. If a generated convention contains them, rewrite it
as a developer-facing rule or drop it:

- Django: `creation_counter`, `contribute_to_class`, `from_queryset`, `_meta`, `Options`
- FastAPI: `solve_dependencies`, `get_flat_dependant`, `ModelField`, `lenient_issubclass`

## Output Format

Each file should use YAML frontmatter:

```markdown
---
module: auth
title: Token refresh error handling
tags: [auth, errors]
---

Keep token refresh validation inside the auth module. Return an explicit
AuthError for invalid refresh tokens instead of catching broad Exception.
```

## Final Check

Before saving a convention file, answer:

- Is this a rule an application developer should follow?
- Is it shorter than 500 words?
- Did I extract at least one testing convention if the project has tests?
- Did I avoid framework internals unless they are directly developer-facing?
