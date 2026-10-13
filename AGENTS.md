# AGENTS.md

Operating instructions for coding agents working in `ollama-policy-proxy`. Read this file and `TASKS.md` before changing the repository.

## 1. Non-negotiable rules

1. Do not fabricate repository facts, file paths, APIs, commands, test results, or completion claims. Inspect or run them.
2. Make the smallest change that satisfies the requested outcome. Do not perform unrelated cleanup, refactoring, reformatting, or feature work.
3. Match existing repository structure, conventions, and patterns unless the task explicitly changes them.
4. Do not add, remove, replace, or upgrade dependencies without prior user approval.
5. Do not create commits, rewrite history, push, or publish unless the user explicitly authorizes it.
6. Keep `TASKS.md` synchronized with meaningful implementation progress in the same work cycle.
7. Do not expose, copy, log, or commit credentials, secrets, private keys, tokens, personal data, or prompt contents.

## 2. Project context

- Project: `ollama-policy-proxy`
- Objective: Provide a thin Ollama-compatible HTTP proxy that applies configurable global, model, and profile inference defaults while preserving explicit request values and transparent streaming.
- Primary language(s): Python and YAML
- Framework(s): To be selected after dependency approval
- Runtime and deployment target: Local-network asynchronous HTTP service managed with `uv`
- Supported host platforms: Windows, macOS, and Linux where the selected Python dependencies are supported
- External runtime requirements: Python, `uv`, and an Ollama server for optional manual integration testing

## 3. Repository orientation

Before editing:

1. Read `TASKS.md`; identify the active work, current plan, and relevant mainline task.
2. Inspect the files to be changed and their callers, tests, configuration, and adjacent conventions.
3. Inspect manifests and lockfiles before choosing tool commands or proposing dependencies.
4. Check the working tree and preserve unrelated user changes.
5. State a brief plan and verifiable success criteria for non-trivial work.
6. Resolve ambiguity from repository evidence when possible. Ask only when materially different interpretations remain.

Repository layout:

- Source: `src/ollama_policy_proxy/`
- Tests: `tests/`
- Configuration: `pyproject.toml`, `uv.lock`, and user-supplied YAML policy files
- Generated or vendored paths not to edit manually: `uv.lock`, `.venv/`, build outputs, and caches; update `uv.lock` only through `uv`

## 4. Implementation policy

- Implement only requested behavior and work required to make it correct.
- Prefer direct, readable code over speculative abstraction or configurability.
- Reuse existing utilities and patterns before introducing new ones.
- Handle realistic failure modes at system boundaries; do not hide errors or suppress diagnostics without justification.
- Remove imports, variables, functions, files, and configuration made obsolete by the current change, but do not delete unrelated pre-existing code.
- Preserve public APIs, request bodies, response bodies, streaming, headers, and compatibility unless the task explicitly changes them.
- Update documentation and examples when the change makes them inaccurate.
- Keep the upstream URL fixed by configuration; never accept a client-selected destination.
- Never log request or response bodies by default.

## 5. Dependency policy

Prefer the standard library and existing dependencies. A new dependency is acceptable only when it materially simplifies the implementation or avoids unreliable custom code.

Prior user approval is required before adding, removing, replacing, upgrading, or materially reconfiguring a dependency or package source. Before requesting approval, explain the need, alternatives, operational impact, and files that will change. Installing or synchronizing already declared dependencies is allowed. After an approved dependency change, update both `pyproject.toml` and `uv.lock` and run relevant checks.

## 6. Verification policy

Define success as observable behavior and verification, not a plausible diff.

- Run every relevant check configured by the repository.
- During iteration, prefer focused tests; run the broader relevant suite before finalizing.
- Add a practical reproducer for bug fixes where possible.
- Read command output and report failures accurately.
- Establish a minimal testing and static-check baseline appropriate to this service.
- Objective non-UI work may be marked `completed` after relevant automated checks pass.
- Real Ollama compatibility remains unverified until the documented manual integration procedure is performed against a real server.

## 7. Task management

`TASKS.md` is authoritative. Classify newly requested or discovered work as part of the current task, another existing task, a new accepted `T###` task, a candidate `C###` item, or no action. Candidate items are not authorization to implement.

Task IDs provide stable identity only. `Current plan` defines execution order. Continue actionable active work first; otherwise choose the first actionable planned task, skipping blocked or user-waiting work without silently reordering it. Do not renumber or reuse IDs. Allowed statuses are exactly `pending`, `in progress`, `blocked`, `completed`, and `cancelled`.

Keep `Active work` consistent: its task must exist and cannot be completed or cancelled; user or external waits require a concrete action; `Waiting on: none` requires `Required action: None.` Update affected task evidence, plan, and active work together after each meaningful step.

`.agentic-template.yml` is the authoritative provenance record. Review future upstream changes from `last_reviewed_revision` and merge applicable updates without overwriting project-specific instructions.

## 8. Git and workspace safety

- Inspect the working tree before and after work.
- Do not discard, overwrite, stage, or modify unrelated user changes.
- Avoid destructive Git commands unless explicitly requested and the consequences are clear.
- Do not commit, push, or publish by default.
- If commits are authorized, use concise imperative commit subjects and include only task-related changes.
- Do not add AI attribution unless explicitly required.

## 9. Commands

- Install or synchronize: `uv sync`
- Run locally: `uv run ollama-policy-proxy --config config.yml`
- Build: `uv build`
- Test all: `uv run pytest`
- Test focused: `uv run pytest tests/<test_file>.py -k <test_name>`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type or static check: `N/A` (no static type checker is declared)
- Package or release check: `uv build`

Commands naming undeclared tools are planned commands until their dependencies are approved and declared.

## 10. Repository-specific constraints

- Process policies only for `POST /api/chat` and `POST /api/generate`; pass other paths through without body transformation.
- Strip the profile-selection header and hop-by-hop headers before forwarding; recompute framing after transformed requests.
- Preserve streamed upstream bytes incrementally, status codes, meaningful headers, and upstream error bodies without reconstructing responses.
- Treat missing values differently from explicit `false`, `0`, and `null`; merge `options` one key at a time.
- Bind to loopback by default and document that pass-through administrative endpoints are unsafe for untrusted exposure.

## 11. Stack-specific instructions

- Treat `pyproject.toml` and `uv.lock` as the normal project and resolution sources.
- Use the Python version declared by `.python-version` or `requires-python`; do not silently broaden compatibility claims.
- Synchronize declared dependencies with `uv sync` and run project commands through `uv run`.
- Add dependencies only after approval using `uv add`; update manifest and lockfile together.
- Prefer importable modules and package entry points over path-dependent scripts.
- Run configured tests, lint, format, type, and package checks. Do not assume tools that are not declared.
- Do not use `uv pip install` as the normal way to mutate this managed project.

## 12. Project learnings

- None yet.

## 13. User handoff and action requests

Use exactly one outcome: `No user action required`, `Permission required`, `Decision required`, `User verification required`, or `Blocked`. When action is required, end the response with a clearly labelled `User action required` section that distinguishes the user's action from the agent's next action.

## 14. Final response checklist

Review changed files, run relevant verification, synchronize `TASKS.md`, distinguish verified behavior from unverified claims, mention blockers and manual verification, and state whether user action is required.
