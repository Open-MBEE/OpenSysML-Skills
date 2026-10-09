---
name: opensysml-repl
description: Use the interactive `sysml` REPL — load models, search and print elements, instantiate objects, evaluate expressions, check constraints/requirements, step actions and drive state machines with signals and simulated time, run analyses and sweeps, render views, and record/replay runs — including how to script it non-interactively from stdin. Use when a task needs stateful exploration of a SysML model (objects that persist between questions), when sending events to a running state machine, or when a `%` command is reported unknown.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# The `sysml` REPL

`sysml` with no operation flag (and files optionally named on the command line) opens the
REPL:

```text
SysML v2 REPL — %help for commands, Ctrl-D to exit
Lines starting with % are commands; anything else is SysML notation.
```

Anything you type that does not start with `%` is parsed as SysML and added to the live
model, so you can declare a `package` or a `part` and immediately question it. Objects you
instantiate persist for the session — the main reason to prefer the REPL over repeated
`sysml -e` calls (see `opensysml-cli`). `sysml -man` and `%help` describe every command;
`%help <command>` gives one.

## Scripting it

Pipe commands on stdin; the REPL exits at EOF and its status is `0` unless a command
failed. Prefer this to expecting a TTY:

```bash
printf '%%load vehicle.sysml\n%%instantiate Vehicles::myCar\n%%eval myCar.mass\n%%constraint Vehicles::Car::massLimit\n' | sysml
```

Pass `-strict` to load under strict conformance; the banner goes to stderr.

## Session and model commands

| Command | Effect |
|---|---|
| `%load [--cells SEL] PATH...` | Load files/dirs (`.sysml`, `.kerml`, `.ipynb`, `.json`) |
| `%print [NAME]` | Pretty-print the model or one element in SysML notation |
| `%search SUBSTRING` | Find elements by name |
| `%list`, `%documents`, `%views` | Catalog documents/views/diagrams in the model |
| `%builtins` | List the bundled standard-library packages |
| `%save FILE` | Write the live model (`.sysml`, `.ttl`, `.json` by extension) |
| `%clear` | Drop the model and all objects |
| `%strict [on\|off]`, `%lint CODE on\|off`, `%verbosity N`, `%trace on\|off` | Session settings |
| `%query OSLC` | OSLC query; `%run-query NAME [p=expr...]` runs a model-defined query |
| `%repo [PATH]`, `%projects`, `%publish` | Flexo MMS repository workflow |
| `%quit` | Exit |

## Objects and values

```text
%instantiate Vehicles::myCar          # object #1 of the usage (or of a definition)
%instances                            # list live objects with their ids
%features myCar [all|depth N]         # feature values of an object
%eval myCar.mass                      # expression in the model scope
%eval in myCar : mass * 2.0           # expression evaluated inside an object
%invoke myCar <op> [<expr>...]        # call an operation on an object
%validate myCar                       # validate an object against its type and multiplicities
```

`%eval` reports `<undetermined>` for values that depend on unbound features and `<unset>`
for features without a value (see `opensysml-sysml-authoring`).

## Checking

```text
%constraint Vehicles::Car::massLimit  # ✓ holds / ✗ false / ? undecided, with a `standing:` line
%requirement Vehicles::massReq        # evaluates the requirement and its verification cases
%satisfy [name]                       # all `satisfy ... by ...` assertions, or one
%check NAME                           # bounded model checking (needs an SMT solver)
%explain NAME                         # why a verdict came out as it did
%solve NAME | %configure NAME [v=variant...] | %optimize NAME   # SMT-backed
%engines [probe] | %engine NAME|auto|all                        # choose analysis engine
%check-property NAME | %check-diverge | %check-input | %check-assume | %check-witness DIR | %check-bounds depth=N states=N unroll=N
%replay WITNESS                       # replay a counterexample from %check-witness
```

## Running behavior

```text
%action Drive rover1                  # run an action to completion on an object
%step | %continue | %tokens | %break NODE | %stop     # single-step an action
%state Modes rover1                   # start a state machine on an object
%current                              # current state(s)
%send Go to rover1                    # queue a signal; %send Go(speed=2.0) to rover1 passes attributes
                                      # then %step or %advance T dispatches it
%events                               # pending events
%advance 5                            # advance the shared simulated clock
%schedule reverse|declared|seed:N|explore  # choice-point policy; %seed N fixes draws
%draws POLICY | %clock-step SECONDS | %budget | %jobs N
```

Behavior commands take the *definition or usage name* followed by the object to run on. A
state machine stays alive between commands, so `%send` / `%advance` / `%current` form a
conversation with it.

## Analyses, sweeps, rendering

```text
%calc Range 50.0                      # calculation with positional arguments
%analysis rangeStudy(10) rover1       # analysis or verification case on an object
%record rangeStudy(10) rover1 into Pkg    # run and record AnalysisRecords into the model
%sweep rangeStudy() rover1 n=1..8:2   # one run per value; %samples N SEED name draws instead
%runs 20 [seed] Drive                 # repeat an action under different schedules
%tool case|action(args) [object]      # run via an external engine (OPENSYSML_TOOLS)
%import data.csv [map map.json]       # set feature values from a table
%view NAME | %graphs NAME | %render NAME [form [palette]] | %viz [--view=V] [--style=S] [form]
%render-document NAME [mermaid|dot|plantuml|d2 [pilot|cameo]]
%render-run timeline|sequence [form]  # diagram of the last run
```

Rendering to images and documents can need external tools; see `opensysml-documents`.

## Failure modes

- `unknown command %foo`: check `%help`; commands are lowercase with hyphens
  (`%check-property`, `%render-document`).
- `no instance of X (use %instantiate first)`: behavior and object commands need an object;
  `%instantiate X` first, then refer to it by name or `#id`.
- A `%send` is ignored: the signal type must be one a transition `accept`s and the state
  machine must have been started with `%state`; check `%current` and `%events`.
- Infinite-looking `%action`: budgets (`%budget`, `OPENSYSML_MAX_ACTION_STEPS`) stop it and
  report a budget diagnostic; lower them while exploring.
