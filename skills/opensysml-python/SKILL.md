---
name: opensysml-python
description: Use the `opensysml` Python package (PyPI) to load, validate, evaluate, instantiate, verify, execute, analyse, render, convert and edit SysML v2 models from Python — including how it provisions and starts a private `sysml-grpc`, connects to a shared service, checks capabilities, and raises typed errors. Use when writing Python scripts, tests, pipelines or notebooks against OpenSysML, or when the package reports ConnectionError, ChecksumMismatchError, StaleServiceError or MissingCapabilityError.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# OpenSysML from Python

`pip install opensysml` (Python 3.9+). The package is a client for the `sysml-grpc` service
(`opensysml-service`): on first use it starts a **private** service on a free port, finding
the binary via `OPENSYSML_GRPC_BINARY`, then `~/.opensysml/bin/`, then a SHA-256-verified
download of the release pinned in the package, then `PATH`. Set `OPENSYSML_GRPC_BINARY` in
CI/offline environments (`opensysml-install`). If `OPENSYSML_SERVICE=host:port` is set, or
`host`/`port` are given, the package connects to that shared service instead of spawning one.

```python
import opensysml

model = opensysml.load("vehicle.sysml")          # private service, parse, return Model
if not model.ok:
    for d in model.diagnostics:                   # Diagnostic(severity, message, span, code)
        print(d)
    raise SystemExit(2)
print(model.eval("mass", subject="Vehicles::myCar"))   # 1300.0 (plain Python value)
```

- `opensysml.load(path, host="localhost", port=None, strict=False, strict_conformance=False)`
- `opensysml.loads(content, ..., language=None)` for source text (`language="kerml"` for KerML)
- `opensysml.connect(host="localhost", port=None, auto_start=True, version=None, require_capabilities=None)`
  returns a `Connection`; with no address and `OPENSYSML_SERVICE` unset it starts a private
  service; `opensysml.connect("localhost:50051")` or `connect("localhost", 50051)` connects to
  an existing one that the client does not manage.
  `conn.load(path)`, `conn.load_from_content(text)`, `conn.parse_sources({...})` return
  `Model`s that share the service; `conn.close()` (or a `with` block) stops a private service.
- `model.raise_for_errors()` raises on error diagnostics; `model.errors` filters them.

## `Model` operations

| Need | Call |
|---|---|
| Value of an expression | `model.eval(expr, context_symbol_id=None, subject=None)` |
| Element lookup | `model.get("Pkg::part")`, `model.find("name")`, `model.root`, `model.roots` |
| Object | `model.instantiate("Pkg::usage")` → object handle for `subject=` arguments |
| Constraint / requirement / satisfy | `model.verify_constraint(id, subject=None, engine=None)` and `model.verify_requirement(...)` → `Verdict` (`.holds`, `.kind`, `.engine`, `.explain`, `.diagnostics`, `.error`); `model.verify_satisfaction(id=None)` → list of `Verdict`s, `model.satisfied()` → bool |
| Instance vs type | `model.validate_instance(id)` |
| Calculation / analysis / sweep | `model.calc(id, arguments=[...])`, `model.run_analysis(id, subject=, arguments=, named_arguments=, schedule=, engine=)`, `model.run_sweep(id, ranges={"n": "1..8:2"}, samples=0, seed=0)` |
| Behavior | `model.execute_action(id, inputs=, schedule=, performer=)`, `model.execute_state(id, events=[...], trace=False)`; `explore_action`/`explore_state`/`explore_analysis` run many schedules |
| Queries | `model.query(where=..., select=..., scope=...)`, `model.run_document_query(query_id, bindings=)` |
| Rendering | `model.render_view(name, ports="minimal")`, `model.render_document(doc_id, form="markdown")`, `model.export_graphs(subject)`, `model.documents` |
| Conversion | `model.to_turtle()`, `model.to_api_json()`, `model.to_sysml()`, `model.convert("ttl")`, `model.save("out.ttl")` |
| Editing | `e = model.edit(); e.set_value(...); e.rename(...); e.add_attribute(...); result = e.apply()` — operations are collected and applied in one `ApplyEdits` call that rewrites only the edited spans |
| Migration | `conn.migrate("sysml", file_path="Model.mdzip", report=True)` |

Symbol ids are qualified names (`"Vehicles::Car::massLimit"`). Values come back as Python
types: `float`, `int`, `bool`, `str`, `Array`, `EnumLiteral`, `ElementRef`; big integers and
rationals need the `big_int_values` / `rational_values` capabilities.

## Capabilities and errors

```python
info = conn.server_info()                 # .version, .capabilities
if opensysml.CAPABILITY_CONVERT_DOCUMENTS not in info.capabilities: ...
conn = opensysml.connect(require_capabilities=[opensysml.CAPABILITY_RATIONAL_VALUES])
```

Typed exceptions: `ConnectionError` (service unreachable or binary not provisioned),
`ChecksumMismatchError`, `UnpinnedReleaseError`, `UnsignedReleaseError`,
`SigstoreUnavailableError`, `StaleServiceError`, `ServiceError`, `ServiceTimeoutError`,
`MissingCapabilityError`, `ExecutionError`, `AnalysisRunError`,
`ConversionError`, `DocumentQueryError`, `EditError` (+ `EditTargetError`,
`EditResultError`, `DeleteReferencedError`), and `ExperimentalFeatureWarning` on RDF/
migration paths. Model *diagnostics* are data, not exceptions — check `model.ok`.

## Patterns

```python
# pytest gate
def test_mass_requirement():
    model = opensysml.load("model/vehicle.sysml"); model.raise_for_errors()
    assert all(v.holds for v in model.verify_satisfaction())

# one service for many files
with opensysml.connect() as conn:
    models = [conn.load(p) for p in paths]

# shared service started elsewhere (sysml-grpc -port 50051)
conn = opensysml.connect("localhost", 50051)
```

Budgets and solver variables (`OPENSYSML_MAX_*`, `OPENSYSML_SMT`) must be in the
environment of the Python process that spawns the private service, or of the shared
service (`opensysml-troubleshooting`). Pin `opensysml==X.Y.Z`; the package version is the
service version it provisions. Jupyter users: prefer the kernel (`opensysml-jupyter`) for
exploration and this package for pipelines.
