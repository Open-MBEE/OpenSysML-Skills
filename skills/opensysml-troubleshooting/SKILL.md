---
name: opensysml-troubleshooting
description: Diagnose OpenSysML problems — read `standing:` lines and ✓/✗/? verdicts, tell "false" from "undecided" from "not covered", fix unresolved references and multi-file loading, tune the OPENSYSML_* environment variables (resource budgets, SMT solver, external engines, library path, parallelism), and recover from client/service version mismatches. Use when `sysml` exits 2 unexpectedly, a check is `?`/undecided, a run hits a step/element/event budget, a solver or external tool is not found, or a language client raises a provisioning, checksum, stale-service or missing-capability error.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# Troubleshooting OpenSysML

Work top-down: (1) does the model analyse cleanly? (2) did the check decide? (3) was the
decision what you expected? Each layer has its own signal.

## 1. The model did not analyse cleanly (exit 2)

`sysml: FILE did not analyse cleanly; no check was made` — nothing downstream ran. Read the
*first* diagnostic (`file:line:col: error: ...`); later ones are often consequences.

| Diagnostic | Usual cause / fix |
|---|---|
| `unresolved reference: X — did you mean ...` | Missing `import` (stdlib names need `private import ScalarValues::*;` etc.), typo, or the file that declares `X` was not passed to `sysml`. Pass every file or the directory. |
| `cannot override the binding value ... write it as default =` | Definition used `= value`; change to `default = value` so usages can redefine. |
| `satisfy target must be a requirement usage` / `Must be an accessible feature` | `satisfy` needs a `requirement r : Def;` usage visible from the `satisfy`, not a def or a nested path. |
| `expected ... got ...` (syntax) | Missing `;` or `}`; OpenSysML never fails to parse but reports the error node. Under `-strict`, notation outside the OMG grammar is an error too. |
| multiplicity / type mismatch on `-validate=OBJ` | Instance disagrees with its type; fix the usage, or the `[n..m]`. |

`sysml -validate` on every edit is the cheapest guard; `-json -validate` gives the same
structured.

## 2. The check did not decide (`?`, exit 2)

The `standing:` line says why:

- `not covered (requirement r: c subject is unbound ...)` — bind the subject
  (`satisfy r by part;` and check with `-satisfy`, or `subject c = part;`).
- `not covered (no instance of "X" (use %instantiate first))` — add `-instantiate X` to the
  command, or `%instantiate` in the REPL before `%action`/`%state`.
- `undecided` with `<undetermined>` values — an attribute in the expression has neither a
  value nor a default; give one or evaluate on a usage that binds it.
- `undecided (no engine could decide ...)` — the `run` engine needs concrete values; the
  `check`/`smt`/`solve` engines need a solver. `sysml -engines -probe` reports each engine's
  status; install `z3`/`cvc5` and set `OPENSYSML_SMT=/path/to/z3` if it is not on PATH.
  `OPENSYSML_SMT_TIMEOUT` (duration, e.g. `30s`) bounds solver time.
- `budget exhausted` — see §4.

## 3. The check decided, but wrongly

- `✗` with `standing: fails (observed: 1 run under reverse)`: the verdict is a real
  evaluation under the default `reverse` schedule. Try `-schedule declared`,
  `-schedule seed:N`, or `-schedule explore` to see whether ordering matters
  (`-check-diverge` reports divergence between schedules).
- A constraint on a *definition* evaluated with defaults rather than the usage's values:
  check the usage (`-instantiate Pkg::car -constraint Pkg::Car::massLimit`).
- Float surprises: `1500` is an `Integer`; `rounded-real-literal` lint (opt-in) flags
  inexact decimal literals.
- Stdlib behaving unexpectedly: `OPENSYSML_LIBRARY_PATH` overrides the bundled library — unset
  it unless you mean to.

## 4. Resource budgets and performance

Every budget is an environment variable read by `sysml`, `sysml-lsp`, `sysml-grpc` (and
therefore by every language client's private service). Exceeding one produces a budget
diagnostic and exit `2`, never a hang.

| Variable | Governs |
|---|---|
| `OPENSYSML_MAX_STEPS` | Total execution steps per run |
| `OPENSYSML_MAX_ACTION_STEPS` | Steps for one action execution |
| `OPENSYSML_MAX_DO_STEPS` | Steps inside a state's `do` behavior |
| `OPENSYSML_MAX_EVENTS` | Queued/dispatched events for a state machine |
| `OPENSYSML_MAX_ELEMENTS` | Elements created by instantiation |
| `OPENSYSML_MAX_CALC_DEPTH` | Recursion depth of calculations |
| `OPENSYSML_MAX_SWEEP_RUNS` | Runs of one `-sweep` |
| `OPENSYSML_MAX_INTEGER_BITS` | Size of big integers before refusing |
| `OPENSYSML_JOBS` | Default for `-jobs`: concurrent runs/files |
| `OPENSYSML_SMT`, `OPENSYSML_SMT_TIMEOUT` | Solver binary and per-call timeout |
| `OPENSYSML_TOOLS`, `OPENSYSML_ENGINES`, `OPENSYSML_TOOL_TIMEOUT`, `OPENSYSML_TOOL_MAX_OUTPUT` | External analysis tools/engines, their timeout and output cap |
| `OPENSYSML_GRPC_MAX_HELD_OBJECTS`, `OPENSYSML_GRPC_INDEX_POOL` | Service-side instance and parse-cache limits |
| `OPENSYSML_WEASYPRINT`, `OPENSYSML_PANDOC`, `OPENSYSML_MMDC`, `OPENSYSML_MMDC_PUPPETEER` | PDF/diagram toolchain for `-render-document` |

Set them where the *process doing the work* runs: for a Python/Node client that spawns a
private `sysml-grpc`, that is the client's environment; for a shared service, the
service's. Use `-memstats`, `-cpuprofile FILE`, `-trace` to see where time goes; `-jobs N`
parallelises independent checks and file loads. The full list is
`docs/reference/environment.md` in the OpenSysML repository and `sysml -man`.

## 5. Clients and services

| Symptom | Fix |
|---|---|
| `BinaryNotFoundError` / cannot provision `sysml-grpc` | Install it (`opensysml-install`) and set `OPENSYSML_GRPC_BINARY`, or allow the client's verified download (needs network). |
| `ChecksumMismatchError` | Corrupt or wrong download; delete `~/.opensysml/bin/sysml-grpc*` and retry; never bypass the check. |
| Unpinned-download refusal | A development build of the client; set `OPENSYSML_ALLOW_UNPINNED_DOWNLOAD=1` only for local development, or pin a release binary. |
| `StaleServiceError` / version mismatch | Service older than the client; upgrade the binary or `OPENSYSML_GRPC_BINARY`. |
| `MissingCapabilityError` | The service lacks that feature; check `server_info()` / `GetServerInfo.capabilities` and upgrade or avoid the call (`opensysml-service`). |
| `connection refused` on `OPENSYSML_SERVICE` | Service not running on that address; start `sysml-grpc -port N` and check `/health`. |
| Browser: CORS or mixed-content error | `sysml-grpc -cors-allowed-origins <origin>` and TLS (`-tls-cert/-tls-key`) for non-localhost. |
| Instances disappear between calls | Objects are held by the service; reuse the same `Connection`/model handle and keep it open. |

## 6. Getting help

`sysml -version` identifies the build (include commit and Go version in reports);
`sysml -debug` prints internal diagnostics. Issues: https://github.com/Open-MBEE/OpenSysML/issues.
Documentation: `docs/guide/10-troubleshooting.md`, `docs/reference/environment.md`.
