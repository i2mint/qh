# qh

Quick HTTP: expose Python functions as a FastAPI web service with one call.
`mk_app` normalizes a function, list of functions, or dict of route configs into
a FastAPI app; type hints drive request validation and the OpenAPI document, a
convention layer infers RESTful paths/methods, and a rule chain + type registry
decide where each parameter lives in the request and how it (de)serializes.

## Module map (`qh/`)

**Three generations of app-building coexist** — `app.py` is current/primary;
`base.py` and `core.py` are earlier, still-present takes:
- `app.py` — **primary entry point**: `mk_app`, `inspect_routes`, `print_routes`.
- `base.py` — a lighter, config-free predecessor with a dict-based route config
  and a store dispatcher.
- `core.py` — an early, self-contained take built on `i2.wrapper.Wrap`
  (`mk_fastapi_app`).

**Supporting the primary path:**
- `config.py` — `RouteConfig` / `AppConfig`: per-route and app-wide configuration.
- `conventions.py` — convention-based routing (infers paths/methods from names).
- `rules.py` — the transformation rule system deciding parameter placement/(de)serialization.
- `types.py` — type registry: automatic (de)serialization for custom types.
- `endpoint.py` — endpoint creation using `i2.Wrap` to transform functions into routes.
- `async_tasks.py` / `async_endpoints.py` — `TaskConfig` background execution for
  functions named in `async_funcs`, and the task-management endpoints for them.
- `au_integration.py` — integration layer between `qh` and `au`.
- `openapi.py` — OpenAPI document generation, incl. JSON Schema from type hints.
- `client.py` / `jsclient.py` — Python / JS+TS client generation from OpenAPI specs.
- `testing.py` — `test_app`, `quick_test`, `service_running`/`run_app`/`AppRunner`:
  in-process and live (real-port) testing.
- `stores_qh.py` — a FastAPI service for operating on `dol`-style store objects.

## Tests & lint (verified)

```bash
uv venv .venv && uv pip install -e . pytest ruff
.venv/bin/pytest -q   # testpaths = qh/tests (examples/scrap/misc excluded)
.venv/bin/ruff check .
```
CI (`.github/workflows/ci.yml`) calls the `i2mint/wads` reusable workflow, but
**this repo's `pyproject.toml` has no `[tool.wads.ci]` section at all** — CI runs
on the reusable workflow's built-in defaults, not repo-specific config. Worth
adding one deliberately rather than relying on defaults staying right.

**Gotcha found verifying:** `qh/tests/test_service_running.py::test_service_running_with_app`
and `::test_service_info_return_value` fail together (both locally and run
standalone) — the second test to bind port 8102 in the file sees
`was_already_running=True` and `thread=None` because a prior test's server is
still up. Order-dependent test pollution in that file, not caused by this change.

## Docs

- `misc/docs/` — API_REFERENCE, FEATURES, GETTING_STARTED, IMPLEMENTATION_STATUS,
  PHASE_2_SUMMARY, TESTING, qh_development_plan.
- `misc/CODEBASE_OVERVIEW.md`, `misc/QUICK_REFERENCE.md`.

## Dependents

`identidots` and `uf` import this package — check their tests before changing
`mk_app`'s signature, `RouteConfig`/`AppConfig`, or the OpenAPI output shape.
