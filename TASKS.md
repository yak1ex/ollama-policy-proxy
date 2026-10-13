# TASKS.md

## Project objective

Build a small, maintainable, Ollama-compatible HTTP proxy that applies YAML-configured inference defaults by global, model, and named profile scope while preserving explicit request parameters and transparent upstream behavior.

## Scope and constraints

- In scope: native Ollama API proxying; policy processing for `/api/chat` and `/api/generate`; fixed upstream routing; incremental streaming; configuration validation; mock-upstream automated tests; concise operations and integration documentation.
- Out of scope: API translation, multiple providers, load balancing, authentication, billing, web UI, request history, caching, model lifecycle management, prompt rewriting, and deployment infrastructure.
- Deployment target: a `uv`-managed Python service on a trusted local network, bound to loopback by default.
- Important constraints: explicit request values win even when false, zero, or null; `options` merge by key; request and response compatibility must be preserved; dependencies require prior approval; no Git commits without explicit authorization.

## Current status

The MVP is implemented and verified with mock Ollama upstreams. Configuration, policy precedence, transparent pass-through, incremental streaming, cancellation cleanup, timeout/error mapping, packaging, and documentation checks pass. Real-Ollama integration was not performed and is explicitly documented as optional manual verification.

## Current plan

No implementation work remains in the accepted MVP plan.

- Selection basis: all accepted tasks are complete; real-Ollama testing remains a documented optional manual check rather than an automated completion dependency.
- Last reviewed: 2026-10-13

## Active work

- Task: `none`
- Current step: None.
- Waiting on: `none`
- Required action: None.

## Tasks

### T001 — Instantiate development process templates

- Status: completed
- Objective: Establish the required self-contained operating, task-management, provenance, and Python/uv instructions.
- Scope:
  - Inspect the upstream README, customization guide, base templates, Python/uv appendix, release, and exact Git revision.
  - Instantiate and adapt `AGENTS.md`, `TASKS.md`, and `.agentic-template.yml` without unresolved placeholders.
- Acceptance criteria:
  - Required files exist, contain project-specific content, and record exact upstream provenance.
- Implemented:
  - Instantiated all three required files and incorporated the Python/uv appendix into `AGENTS.md`.
  - Recorded release `2026-09-27` and revision `b68d62c7a62bf7428144fb64f76700f403c7e26b`.
- Verification:
  - Upstream files were read from the pinned revision on 2026-10-13.
  - Placeholder scan and `git diff --check` passed on 2026-10-13.
- Remaining:
  - None.
- Notes:
  - No Git commit was created.

### T002 — Select architecture and dependencies

- Status: completed
- Objective: Establish an Ollama-compatible forwarding design and an approved minimal dependency set grounded in current official API documentation.
- Scope:
  - Verify `/api/chat`, `/api/generate`, `/api/tags`, and `/api/show` request behavior.
  - Evaluate asynchronous server/client, YAML, validation, and test options.
  - Record policy precedence, header handling, and pass-through decisions.
- Acceptance criteria:
  - Proposed dependencies include alternatives and impacts, and receive user approval before any manifest or lockfile mutation.
- Implemented:
  - Chose `X-Ollama-Profile` as the MVP selection mechanism and fixed configured upstream routing.
  - Deferred virtual model aliases because they would alter model identity and compatibility semantics.
  - Verified that chat and generate accept `think`, `options`, and `stream`; Ollama's documented `ThinkValue` supports Boolean, null, and model-defined string levels.
  - Verified that chat/generate stream `application/x-ndjson` by default, `/api/tags` is `GET`, and `/api/show` is a JSON `POST` that advertises model thinking controls.
  - Proposed `aiohttp` and `PyYAML` at runtime, `uv_build` for packaging, and `pytest`, `pytest-asyncio`, and `ruff` for development.
  - User approved the proposed dependency set on 2026-10-13; `pyproject.toml` and `uv.lock` record the resolved environment.
- Verification:
  - Inspected current official Ollama API pages for chat, generate, tags, show, streaming, errors, and thinking on 2026-10-13.
  - Inspected official documentation for aiohttp, PyYAML, pytest, pytest-asyncio, and Ruff on 2026-10-13.
- Remaining:
  - None.
- Notes:
  - No additional dependency was introduced beyond the approved set.
  - Standard-library HTTP servers and clients would require substantial custom asynchronous streaming, cancellation, connection pooling, and backpressure code. `aiohttp` supplies both sides with one dependency family.
  - JSON-only configuration would avoid a parser but would not satisfy the requested YAML configuration. `PyYAML.safe_load` supplies mature YAML parsing; schema validation will remain small explicit project code rather than add Pydantic.
  - `unittest.IsolatedAsyncioTestCase` could avoid pytest plugins, but pytest plus pytest-asyncio provides concise async fixtures for multiple live mock servers and cancellation tests. Ruff supplies both lint and format checks in one tool.

### T003 — Implement configuration and policy processing

- Status: completed
- Objective: Start the proxy from validated YAML and transform eligible JSON requests with the required precedence.
- Scope:
  - Create the `uv` package and CLI.
  - Implement actionable startup validation, global/model/profile resolution, and key-wise `options` merging.
- Acceptance criteria:
  - Missing fields receive defaults; explicit false, zero, and null values remain unchanged; unrelated fields remain unchanged.
- Implemented:
  - Created the Python 3.11 `uv` package and `ollama-policy-proxy` CLI entry point.
  - Added safe YAML loading with path-specific validation for upstream, server, global, model, and profile configuration.
  - Implemented precedence-aware request transformation with key-wise `options` merging and presence-aware false, zero, and null handling.
- Verification:
  - Policy and configuration tests passed as part of the 24-test suite on 2026-10-13.
  - `config.example.yml` loaded successfully through the production loader.
- Remaining:
  - None.
- Notes:
  - Begins after `T002` approval.

### T004 — Implement transparent asynchronous proxying

- Status: completed
- Objective: Forward transformed and pass-through traffic while preserving HTTP and streaming semantics.
- Scope:
  - Strip hop-by-hop, host, framing, and internal profile headers as appropriate.
  - Stream responses incrementally with backpressure, cancellation cleanup, timeouts, and upstream failure mapping.
  - Pass non-policy endpoints and non-JSON bodies through without unnecessary buffering.
- Acceptance criteria:
  - Status, bodies, relevant headers, streamed chunks, cancellation, cleanup, and errors behave as documented and tested.
- Implemented:
  - Added one fixed-upstream asynchronous forwarding path with incremental pass-through request and response bodies.
  - Added hop-by-hop, host, framing, and profile-header filtering without response reconstruction.
  - Added structured invalid-request and profile errors, transparent upstream HTTP errors, `502` connection failures, and `504` upstream read timeouts.
  - Added cleanup paths for client cancellation, downstream reset, timeout, and upstream disconnection.
- Verification:
  - Mock-upstream tests verified pass-through bytes and query strings, incremental first-chunk delivery, final chunks, upstream disconnection, timeout, HTTP errors, client cancellation, and upstream cleanup on 2026-10-13.
- Remaining:
  - None.
- Notes:
  - Administrative pass-through risks must be documented.

### T005 — Complete automated verification and documentation

- Status: completed
- Objective: Provide a reproducible mock-upstream test suite and complete operator documentation.
- Scope:
  - Cover all requested policy, pass-through, streaming, timeout, error, cancellation, and cleanup cases with representative fixtures.
  - Document installation, configuration, operation, curl examples, precedence, limitations, troubleshooting, and manual integration.
- Acceptance criteria:
  - Relevant automated checks pass and the README supports first-time setup and use.
- Implemented:
  - Added representative multimodal/tool/structured-output chat and NDJSON stream fixtures.
  - Added configuration, policy, HTTP integration, streaming, failure, and cancellation tests.
  - Documented installation, schema, precedence, profiles, examples, endpoint behavior, security, limitations, troubleshooting, and manual integration.
- Verification:
  - `uv run pytest -q`: 24 passed on 2026-10-13.
  - `uv run ruff check .`: passed on 2026-10-13.
  - `uv run ruff format --check .`: passed on 2026-10-13.
  - `uv sync --locked`: passed on 2026-10-13.
  - `uv build`: source distribution and wheel built successfully on 2026-10-13.
  - `uv run ollama-policy-proxy --help`: passed on 2026-10-13.
  - Started the packaged CLI with `config.example.yml`; `/api/tags` returned the expected `502` while no Ollama server was listening, then the proxy was stopped cleanly on 2026-10-13.
- Remaining:
  - None.
- Notes:
  - Real Ollama is not required for standard tests.

### T006 — Verify real Ollama integration

- Status: completed
- Objective: Clearly separate automated compatibility evidence from optional verification against a real Ollama server.
- Scope:
  - Provide concrete manual commands for streaming and non-streaming chat/generate requests, profile selection, and explicit thinking overrides.
  - Run them only if a suitable Ollama installation and model are available.
- Acceptance criteria:
  - Manual steps are documented; any executed checks record environment and observed results without overstating coverage.
- Implemented:
  - Added manual steps for tags, show, default thinking, explicit reasoning, streaming completion, and client cancellation against a real Ollama server.
- Verification:
  - Documentation consistency reviewed on 2026-10-13.
  - Real Ollama checks were not run because no suitable server and installed model were established in this environment.
- Remaining:
  - Optional user execution against the intended Ollama version and models; this is not claimed as verified.
- Notes:
  - This task may remain in progress awaiting user verification if no real environment is available.

## Decisions

### D001 — Use a request header for profile selection

- Date: 2026-10-13
- Status: accepted
- Decision: Select named profiles with the optional `X-Ollama-Profile` request header and strip it before forwarding upstream.
- Rationale: This leaves Ollama JSON schemas and model names unchanged and is simple for configurable clients and reverse proxies to set.
- Consequences:
  - Clients unable to add headers receive global and model defaults only.
  - Unknown profile names produce a client error before any upstream request.
- Related tasks: `T002`, `T003`, `T004`

### D002 — Defer virtual model aliases

- Date: 2026-10-13
- Status: accepted
- Decision: Do not implement virtual model names in the MVP.
- Rationale: Rewriting model identity can affect model lookup, response identity, lifecycle endpoints, client caches, and compatibility while the header meets the stated MVP need.
- Consequences:
  - Profile-aware clients or an adjacent reverse proxy must set the custom header.
- Related tasks: `T002`

### D003 — Forward to one configured upstream

- Date: 2026-10-13
- Status: accepted
- Decision: Resolve all requests against one startup-configured Ollama base URL and never accept a client-supplied destination.
- Rationale: This prevents open-proxy behavior and matches the single-upstream MVP scope.
- Consequences:
  - Changing upstream requires configuration and restart.
- Related tasks: `T003`, `T004`

### D004 — Use one aiohttp server/client stack

- Date: 2026-10-13
- Status: accepted
- Decision: Use `aiohttp` for both inbound serving and upstream requests, `PyYAML.safe_load` plus explicit validation for configuration, and the approved pytest/Ruff toolchain.
- Rationale: A shared asynchronous HTTP stack provides incremental I/O, backpressure, cancellation, connection pooling, and cleanup without introducing a gateway framework; explicit validation preserves presence-sensitive policy semantics.
- Consequences:
  - Runtime dependencies are `aiohttp` and `PyYAML`; resolved transitive dependencies are recorded in `uv.lock`.
  - Configuration schema changes require corresponding explicit validation and tests.
- Related tasks: `T002`, `T003`, `T004`, `T005`

## Blocked items

- None.

## Cancelled items

- None.

## Candidate items

### C001 — Restrict administrative pass-through endpoints

- Origin: Security review of the requested preference for transparent forwarding of other Ollama endpoints.
- Question: Should a later release add an allowlist or denylist for model lifecycle and administrative endpoints?
- Possible relationship: separate work after `T005`
- Disposition: awaiting triage
- Notes:
  - The MVP will document that exposing unrestricted pass-through to untrusted clients grants access to upstream Ollama capabilities.
