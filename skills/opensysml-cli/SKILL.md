---
name: opensysml-cli
description: Drive the `sysml` command non-interactively — validate SysML v2/KerML files, evaluate expressions, instantiate parts, check constraints and requirements, run actions/states and analyses, emit machine-readable JSON, and interpret exit statuses 0/1/2. Use when scripting or CI needs to validate or question a model from the shell, when an agent must check its own edits to a .sysml file, or when a `sysml` invocation returns an unexpected status or "did not analyse cleanly".
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# Using the `sysml` CLI

`sysml [options] [file...]` loads every file named (`.sysml`, `.kerml`, directories, globs,
`.ipynb` notebooks, API element-form `.json`), then performs the operation the flags select.
With no operation flag and no stdin, it opens the REPL (see `opensysml-repl`). Every file is
loaded as its own document; nothing is implicitly imported across files, so name every file
the checked elements depend on. The standard library (`ScalarValues`, `ISQ`, `SI`, ...) is
bundled and always available to `import`.

Install first if `sysml -version` fails (see `opensysml-install`). `sysml -man` is the full
manual; `sysml -help` lists every flag.

## Exit status is the verdict

| Exit | Meaning |
|---|---|
| `0` | The model answered and the answer is positive (no errors, constraint holds, ...) |
| `1` | The model answered negatively (constraint false, requirement violated, ...) |
| `2` | No decision: parse/semantic errors, unbound subject, usage error, unresolved tool |

Diagnostics go to stderr as `file:line:col: error: message` followed by the source line and a
caret. The line `sysml: FILE did not analyse cleanly; no check was made` means the model has
errors and the requested operation did not run — fix the errors first; the exit is `2`, not
`1`. When piping through other tools remember the pipeline's exit is the last command's.

## Core operations

```bash
sysml -validate model.sysml                     # parse + name resolution + typing + constraints
sysml -validate -strict model.sysml             # strict OMG conformance: notation leniencies become errors
sysml -e 'Pkg::car.mass' -e '2 + 3 * 4' model.sysml   # evaluate expressions (repeatable -e)
sysml -instantiate Pkg::car model.sysml         # build an instance tree and report it
sysml -constraint Pkg::Car::massLimit model.sysml      # check one constraint; exit 0 holds / 1 fails
sysml -requirement Pkg::Car::MassReq model.sysml       # check a requirement (needs a bound subject)
sysml -satisfy=Pkg::massSatisfied model.sysml   # check a `satisfy ... by ...` assertion
sysml -calc 'Pkg::totalMass(3, 4)' model.sysml  # invoke a calculation with arguments
sysml -action 'Pkg::Drive Pkg::rover1' model.sysml   # run action Drive on object rover1
sysml -state 'Pkg::Mission Pkg::rover1' -advance 10 model.sysml  # run a state machine for 10 time units
sysml -analysis 'Pkg::rangeStudy()' model.sysml # run an analysis or verification case
sysml -query 'oslc.where=sysml:type="PartDefinition"' model.sysml   # OSLC query
sysml -validate=Pkg::car model.sysml            # validate an *instance* against its type
```

Names use `::` paths; quote names containing spaces or punctuation:
`-instantiate "Pkg::'SA-506'"`. Output lines start with `✓` (holds / done), `✗` (false),
`?` (undecided) and include a `standing:` line explaining how the verdict was reached
(for example `holds (observed: 1 run under reverse)`).

Add `-json` to get a single JSON object on stdout for scripting; it reports a *check*, so pair
it with `-validate`, `-constraint NAME`, `-requirement NAME`, etc.:

```bash
sysml -json -validate model.sysml
# {"status":"holds","exit":0,"checks":null,"diagnostics":null,"output":[...],"errors":null}
```
`status` is one of `holds`, `fails`, `unresolved`; `diagnostics` carries structured
`file/line/col/severity/message/code` entries when present.

## Behavior and verification controls

- `-schedule reverse|declared|seed:N|explore[:runs=N,depth=N]|replay:FILE` chooses how
  concurrent choices are ordered; `explore` runs many schedules and reports divergence.
- `-engine auto|run|explore|check|smt|sweep|solve|all` selects how a constraint or
  requirement is decided; `-engines [-probe]` lists engines and whether an SMT solver was
  found. Install `z3` or `cvc5` for `check`/`smt`/`solve` (see `opensysml-install`).
- `-check-property NAME`, `-check-diverge`, `-check-input`, `-check-assume`, `-check-witness`,
  `-check-depth N`, `-check-unroll N`, `-check-states`, `-check-timeout DUR` configure
  bounded model checking of actions/states; a counterexample witness is replayable with
  `-schedule replay:FILE`.
- `-sweep 'n=1..8:2'` (several ranges allowed) runs `-analysis`/`-calc` once per value,
  `-samples N -seed N` draws values instead; `-record-run CALL` runs an analysis and
  records it into the model as `AnalysisRecord`s; `-trace` prints execution steps; `-jobs N` parallelises independent work.
- Resource budgets come from `OPENSYSML_MAX_STEPS`, `OPENSYSML_MAX_ACTION_STEPS`,
  `OPENSYSML_MAX_EVENTS`, `OPENSYSML_MAX_ELEMENTS`, `OPENSYSML_MAX_CALC_DEPTH`,
  `OPENSYSML_MAX_SWEEP_RUNS`, `OPENSYSML_MAX_INTEGER_BITS`; a run that hits one exits `2`
  with a budget diagnostic rather than hanging.

## Other operations (each has its own skill)

- Conversion/export: `-convert sysml|ttl|api-json -o OUT` (`opensysml-convert-rdf`).
- SysML v1 migration: `-migrate sysml -o OUT model.xmi` (`opensysml-migrate-v1`).
- Documents and diagrams: `-render-document NAME -doc-form md|html|pdf`, `-render VIEW`,
  `-list [-list-kind KIND]` (`opensysml-documents`).
- Imports from tables: `-import data.csv -import-as values` (with `-import-map`,
  `-import-format`), then `-convert sysml -o OUT` writes the result; `-import-dry-run` previews.
- Code generation: `-compile Pkg::calc -target c|go -o OUT`.
- Flexo MMS sync: `-sync-diff`, `-sync-apply`, `-sync-state`.
- Lints: `-disable-lint NAME`, `-enable-lint NAME` (for example `rounded-real-literal`).
- Self-check of the model's own rules: `-self-check`, `-self-check-package PKG`.
- Diagnostics: `-debug`, `-quiet`, `-memstats`, `-cpuprofile FILE`, `-memprofile FILE`.

## Agent workflow for editing a model

1. Run `sysml -validate FILE` after every edit; stop on exit `2` and read the first
   diagnostic — later ones are often consequences of it.
2. Confirm values with `-e` before asserting constraints; `<undetermined>` means the
   expression depends on an unbound feature, `<unset>` means no value was given.
3. Use `-constraint`/`-requirement` with the *usage* or *definition* path the model declares;
   requirements need a subject (`subject c = part` in the model, or check via
   `-satisfy`), otherwise the result is `not covered` with exit `2`.
4. For reproducibility in CI, pin the binary version (`sysml -version`) and prefer `-json`.

## Pitfalls

- Passing a file that imports another package without passing that package's file yields
  `unresolved reference`; pass both files or a directory.
- `-e` on an unbound attribute of a *definition* returns its default, not an instance value;
  evaluate on the usage (`Pkg::car.mass`) for the configured value.
- `-json` without a check flag returns `status: unresolved` and exit `2` by design.
- Exit `0` printed after a pipe through `head` is `head`'s status, not `sysml`'s.
