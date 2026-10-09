---
name: opensysml-go
description: Use the Go API `github.com/Open-MBEE/OpenSysML/client/opensysml` — embed the OpenSysML engine in-process with `opensysml.New()`, or reach a `sysml-grpc` service with `opensysml.Dial(address)` through the identical `Client` interface; parse files and sources, read diagnostics, evaluate typed values, instantiate, verify, execute, run analyses, query, render, convert, migrate and apply edits, and use `OpenSession` for stateful stepping. Use when writing Go programs, tests or tools (CI gates, build plugins, services) on top of OpenSysML.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# OpenSysML from Go

```bash
go get github.com/Open-MBEE/OpenSysML@latest        # Go 1.23+; module root, package client/opensysml
```

The Go client is the only one that can run the engine **in-process** — no `sysml-grpc`,
no binary download. `New()` and `Dial(address)` return the same `Client` interface and are
held to identical behavior by the conformance suite, so code written against one works
against the other.

```go
import (
    "context"
    "fmt"
    "github.com/Open-MBEE/OpenSysML/client/opensysml"
)

func check(ctx context.Context) error {
    client, err := opensysml.New()                 // in-process; or opensysml.Dial("localhost:50051")
    if err != nil { return err }
    defer client.Close()

    model, err := client.ParseFile(ctx, "vehicle.sysml")
    if err != nil { return err }                   // I/O or transport failure
    if errs := model.Errors(); len(errs) != 0 {    // model diagnostics are data, not errors
        return fmt.Errorf("model diagnostics: %v", errs)
    }
    mass, err := client.Evaluate(ctx, model, "mass", opensysml.WithSubject("Vehicles::myCar"))
    if err != nil { return err }
    fmt.Println(mass)                              // typed Value; prints as SysML notation: 1300.0
    return nil
}
```

## Parsing

- `ParseFile(ctx, path, opts...)`, `ParseSource(ctx, content, opts...)`,
  `ParseFiles(ctx, paths...)` (one model, imports resolve across files),
  `ParseDocuments(ctx, docs...)` mixing `opensysml.File(path)` and `opensysml.Source(name, text)`.
- Options: `WithStrict()`, `WithStrictConformance()`, `WithLanguage(opensysml.LanguageKerML)`.
  Formats: `FormatSysML`, `FormatTurtle`, `FormatAPIJSON`.
- `model.OK()`, `model.Errors()`, `model.Diagnostics()` (severity, message, span, code),
  `client.Diagnostics(ctx, model)`, `client.LookupSymbol(ctx, model, "Pkg::x")`.
- A syntax error is a diagnostic, not an `error`; a missing file is an `error`.

## Operations on `Client`

| Need | Method |
|---|---|
| Values | `Evaluate(ctx, model, expr, WithSubject(id), WithContextSymbol(id))`, `EvaluateCalc(ctx, model, id, CalcArguments(...), CalcEngine(name))` |
| Objects | `Instantiate(ctx, model, id)`; refer to held objects with `ObjectByID(n)` / `ObjectByPath(path)`, run behavior on one with `PerformedBy(path)` |
| Verification | `VerifyConstraint`, `VerifyRequirement` (with `Subject(id)`, `Engine(name)`, `Asking(question)`), `VerifySatisfaction`, `ValidateInstance` → verdicts carrying their standing |
| Execution | `ExecuteAction(ctx, model, id, Arguments(...), Schedule(policy), PerformedBy(path))`, `ExecuteState(ctx, model, id, ..., WithTrace())`, `ExploreAction/ExploreState/ExploreAnalysis` for every outcome under exploring schedules |
| Analysis | `RunAnalysis(ctx, model, id, Argument(...), Subject(...), Engine(...))`, `ListEngines(ctx)` |
| Query/documents | `Query(ctx, model, ...)`, `QueryOSLC(ctx, model, text)`, `RunDocumentQuery(ctx, model, id, Bind(...))`, `RenderDocument(ctx, model, id, form)`, `RenderView(ctx, model, name, WithFullPorts())`, `ExportGraphs(ctx, model, subject)` |
| Conversion | `Convert(ctx, model, opensysml.FormatTurtle)`, `ConvertFile(ctx, path, format, WithFromFormat(...))`, `ConvertSource(...)`, `WithTolerateSyntaxErrors()` |
| Migration | `MigrateFile(ctx, path, format, WithMigrationReport(), WithMigrationResults(), WithLayoutFile(...), WithImageBaseURL(...))`, `MigrateSource` |
| Editing | `ApplyEdits(ctx, model, ops...)`, `ApplyDocumentEdits(...)` — all-or-nothing, refusals name the referrers |
| Service | `ServerInfo(ctx)` (version, capabilities), `Close()` |

Values are a typed sum (`Value` with Real/Integer/Boolean/String/Enum/Quantity/Array/
Set/Instance/Metaobject/Function/Complex/Undetermined/Unset…); construct inputs with
`NewInteger(*big.Int)`, `NewRational(*big.Rat)`; compare with `opensysml.Equal`. Predicates
for document queries: `Equals`, `Greater`, `Less`, `All`, `Any`, `Against`.

## In-process vs `Dial`

- `New(opts...)` embeds `internal/frontend/grpc.Service` directly: no process, no port,
  same budgets via `OPENSYSML_MAX_*`; `WithCacheSize(n)` sizes the parse cache. Prefer it
  for CLIs, tests and build tooling.
- `Dial(address, opts...)` talks Connect/protobuf to a running `sysml-grpc`
  (`WithJSONBody()` for JSON, `WithHTTPClient(c)` for TLS/proxies). The service's
  capability list gates optional features; the client omits a field or refuses an
  option the service does not advertise, so check `ServerInfo` when behavior differs.
- `OpenSession(client, model)` is **in-process only**: a stateful session that holds
  an object, performs actions turn by turn, sets features, changes schedule, dispatches
  events and reports transitions — what the REPL's `%step`/`%send` do. A `Dial`ed client
  cannot open one.

Every call takes a `context.Context`; a cancelled context refuses the call, an expired
deadline is `DeadlineExceeded`. `Client` is safe for concurrent use; after `Close()` every
operation is refused.

## Errors

Transport and refusal errors carry a canonical code (`invalid_argument`, `not_found`,
`failed_precondition`, `unimplemented`, `unavailable`, `deadline_exceeded`) you can match
with `errors.As`; a verdict of false, a failed run, or a model with diagnostics is an
*answer*, returned without error. Read the result's standing/outcome instead.

Reference: `client/opensysml/README.md` (stability policy: `Client`, `New`, `Dial` and the
option functions are stable) and `go doc github.com/Open-MBEE/OpenSysML/client/opensysml`.
