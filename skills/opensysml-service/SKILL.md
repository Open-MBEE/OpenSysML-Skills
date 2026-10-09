---
name: opensysml-service
description: Run and talk to the `sysml-grpc` service that backs every OpenSysML language client — start it on a port, check `/health`, negotiate capabilities with GetServerInfo, call methods over Connect JSON with curl, gRPC, or gRPC-Web, configure CORS/TLS for browsers, and share one service between several clients via OPENSYSML_SERVICE. Use when a client cannot connect, when exposing OpenSysML to a browser or another machine, when debugging requests with curl, or when choosing between a private per-process service and a shared one.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# The `sysml-grpc` service

`sysml-grpc` is one process serving gRPC, gRPC-Web, Connect (protobuf and JSON), server
reflection and `GET /health` on a single port (default `50051`). The Python, Node, Java,
Rust, Julia and MATLAB clients are thin wrappers over it; anything they can do is one RPC
on `sysml.SysMLService`. The contract is `api/proto/sysml.proto` in the OpenSysML
repository, documented in `docs/reference/service-transports.md` and
`docs/reference/wire-contract.md`.

## Start it

```bash
sysml-grpc                                  # :50051, logs to stderr
sysml-grpc -port 0 -report-address          # pick a free port and print it on stdout
sysml-grpc -port 50051 -health-port 0 -log-level warn
sysml-grpc -exit-with-parent                # die with the process that spawned it
sysml-grpc -transport stdio                 # Connect over stdin/stdout for embedding
sysml-grpc -cors-allowed-origins https://app.example.org -tls-cert cert.pem -tls-key key.pem
```

Flags: `-port`, `-health-port` (deprecated separate listener; `0` disables it), `-log-level`,
`-report-address`, `-exit-with-parent`, `-transport grpc|stdio`, `-cors-allowed-origins`
(exact origins, comma-separated; browsers need this), `-tls-cert`/`-tls-key`,
`-cache-size`, `-serve-external-engines`, `-version`, `-man`.

Clients start a **private** service by default (a child process on a free port, closed
with the connection). Point them at a **shared** service instead with
`OPENSYSML_SERVICE=host:port` (Node, Julia, MATLAB honour it directly; Python
`opensysml.connect(host=, port=)`, Rust `Connection::external(addr)`, Java
`Connection.open(address)`). A shared service holds parsed models by `modelHash`, so
several clients can reuse one parse.

## Probe it with curl (Connect JSON)

```bash
curl -s http://127.0.0.1:50051/health
# {"service":"sysml-grpc","status":"ok","version":"v0.9.2"}

curl -s -X POST http://127.0.0.1:50051/sysml.SysMLService/GetServerInfo \
     -H 'Content-Type: application/json' -d '{}'
# {"version":"v0.9.2","capabilities":["type_facts","convert","verification","query", ...]}

curl -s -X POST http://127.0.0.1:50051/sysml.SysMLService/ParseFile \
     -H 'Content-Type: application/json' \
     -d '{"content":"package P { part def A { attribute x : Nope; } }"}'
# {"modelHash":"52e2...","root":{"kind":"RootNamespace","childIds":["P"]},
#  "diagnostics":[{"severity":"error","message":"unresolved reference: Nope — did you mean ...",
#                  "span":{"file":"<content>","startLine":1,"startCol":40,"endLine":1,"endCol":44},
#                  "code":"unresolved"}]}
```

Unary Connect paths are `/sysml.SysMLService/<Method>`; `Content-Type: application/json`
selects JSON, `application/proto` protobuf. The 25 RPCs are `GetServerInfo`, `ParseFile`,
`ParseSources`, `GetSymbol`, `GetDiagnostics`, `Evaluate`, `Instantiate`, `ExecuteAction`,
`ExecuteState`, `Convert`, `Migrate`, `ApplyEdits`, `VerifyConstraint`, `VerifyRequirement`,
`VerifySatisfaction`, `ValidateInstance`, `EvaluateCalc`, `RunAnalysis`, `RunSweep`,
`ListEngines`, `Query`, `RunDocumentQuery`, `RenderDocument`, `RenderView`, `ExportGraphs`.
Request/response field names come from the proto (`model_hash` is `modelHash` in JSON);
`grpcurl -plaintext 127.0.0.1:50051 describe sysml.SysMLService` lists them via reflection.

Most calls after `ParseFile` take the returned `modelHash`, e.g.
`{"modelHash":"...","expression":"P::a.x"}` for `Evaluate` (optional `contextSymbolId`,
`subjectSymbolId` scope the evaluation).

## Rules every caller must follow

- **Negotiate capabilities.** `GetServerInfo.capabilities` is a list of names such as
  `convert`, `verification`, `oslc_query`, `apply_edits`, `render_document_html`,
  `big_int_values`, `rational_values`, `parse_sources`. Check for the name before using
  an optional method or reading an optional response field; older services omit both.
  The official clients raise `MissingCapabilityError` for you.
- **JSON follows proto3 rules.** 64-bit integers are JSON *strings*; absent fields mean
  default values; enums are names. Use protobuf for large responses (instance trees,
  Turtle conversions) — JSON is for debugging and `curl`.
- **Errors** arrive as an HTTP status plus `{"code":"not_found","message":"..."}`
  (Connect error codes: `invalid_argument`, `not_found`, `failed_precondition`,
  `unimplemented`, `resource_exhausted`, `deadline_exceeded`, ...). A model with
  diagnostics is *not* an error — `ParseFile` succeeds and reports them in `diagnostics`.
- **Held objects.** Instances created by `Instantiate` live in the service;
  `OPENSYSML_GRPC_MAX_HELD_OBJECTS` caps them and `OPENSYSML_GRPC_INDEX_POOL` sizes the
  parse cache. Close connections (or let private services exit) to release them.
- **Browsers** need the exact page origin in `-cors-allowed-origins` and, for anything
  other than `localhost`, TLS (`-tls-cert`/`-tls-key`). Private services cannot be
  spawned from a browser; run `sysml-grpc` yourself or use the WASM transport
  (`opensysml-wasm`).

## Troubleshooting

- `connection refused`: the service is not listening on that port; run with
  `-report-address` to learn the chosen port, and check nothing else holds `50051`.
- Client says the service is stale (`StaleServiceError`): the binary predates the
  client's pinned version; upgrade the service or set `OPENSYSML_GRPC_BINARY` to a
  matching build (`opensysml-install`).
- Verification calls hang or exit with `resource_exhausted`: raise/lower the
  `OPENSYSML_MAX_*` budgets in the *service's* environment, not the client's.
- SMT-backed calls report no solver: `OPENSYSML_SMT` must be set where `sysml-grpc` runs.
- `health_port=8081` warning at startup: the separate health listener is deprecated; pass
  `-health-port 0` and use `/health` on the main port.
