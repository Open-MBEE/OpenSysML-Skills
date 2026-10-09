---
name: opensysml-wasm
description: Run OpenSysML as WebAssembly — build or download the wasip1 and js modules (sysml, sysml-lsp, sysml-grpc, sysml-engine, sysml-syntax, sysml-core, sysml-wasm), run them under Wasmtime or Node, embed the combined `sysml-wasm` module in Node or a browser through `connectWasm()` from @openmbee/opensysml, and know what a WebAssembly host cannot do (no processes, no sockets, no SMT, no PDF). Use when OpenSysML must run without a native binary or network service — in a browser, a sandbox, a serverless function — or when a WASM build refuses an operation.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# OpenSysML in WebAssembly

Every binary has two WebAssembly builds: `wasip1` (WASI preview 1, for Wasmtime/Wasmer/
wazero/WasmEdge and Node's WASI) and `js` (Go's `syscall/js` target, for browsers and Node
with `wasm_exec.js`). Releases attach them; a checkout builds them:

```bash
make build-wasm            # both targets → bin/wasm/{wasip1,js}/*.wasm
make build-wasm-wasip1     # or one
make build-wasm-js         # also copies bin/wasm/js/wasm_exec.js, the runtime a page includes
make build-wasm-prod       # smaller sysml-prod.wasm (-tags sysml_prod)
```

Modules: `sysml`, `sysml-lsp`, `sysml-grpc`, `sysml-engine`, `sysml-syntax`, `sysml-core`,
`sysml-wasm`. The module and `wasm_exec.js` must come from the same Go toolchain.

## Running the CLI/REPL/LSP as WASM

```bash
# WASI: mount the filesystem and tell the program its working directory
wasmtime run --dir=/ --env PWD="$PWD" bin/wasm/wasip1/sysml.wasm model.sysml -e 'Pkg::total'
"$(go env GOROOT)/lib/wasm/go_wasip1_wasm_exec" bin/wasm/wasip1/sysml.wasm -validate model.sysml   # Go's runner; GOWASIRUNTIME=wasmer|wazero|wasmedge

# js target under Node
node --stack-size=8192 --no-concurrent-sparkplug "$(go env GOROOT)/lib/wasm/wasm_exec_node.js" bin/wasm/js/sysml.wasm -version
```

`js` constraints: argv and environment share ~8 KiB (run with a small environment — `PATH`,
`HOME`, `TMPDIR`), the JS stack must be raised (`--stack-size=8192`), and
`--no-concurrent-sparkplug` avoids a Node shutdown deadlock. A `wasip1` program resolves
relative paths against `PWD`, so pass it. Node's WASI cannot block on an empty pipe, so feed
the REPL from a file rather than an interactive stream.

What works: `-validate`, `-e`, `-query`, `-convert`, `-render`, every document form except
PDF, `-engines`, the REPL reading a line at a time, `sysml-lsp --stdio`, and
`sysml-grpc -transport stdio` (Connect framing over stdin/stdout). The prompt is always
written because a WASM host cannot tell whether stdin is a terminal.

What is refused, with an explicit message: anything that starts a process (SMT solvers,
external engines, PDF converters, `-compile`), `sysml-grpc -transport grpc|connect`
(no sockets), outbound HTTP (Flexo repository commands), prompt history/completion/Ctrl-C.
A refusal names the operation; it is not a defect to report.

## The in-process modules

| Module | Serves | Use |
|---|---|---|
| `sysml-engine` | `ParseSources`, `Evaluate`, `Instantiate`, `ExecuteAction`, `ExecuteState`, `GetServerInfo` over JSON-RPC 2.0 with `Content-Length` frames | Execution without a service |
| `sysml-syntax` | `Parse`, `Format`, `Tokens` | Editors, highlighters, formatters |
| `sysml-core` | Parsing, diagnostics, symbol facts | Validation-only hosts |
| `sysml-wasm` | Union of core + engine: `ParseFile`, `ParseSources`, `GetDiagnostics`, `GetSymbol`, `Evaluate`, `Instantiate`, `ExecuteAction`, `ExecuteState`, `GetServerInfo` | What the Node/browser client embeds |

Exploration, verification, rendering, conversion, migration, queries and edits are **not**
served by these modules (`<Method> is not served by sysml-engine`); they need `sysml-grpc`
(`opensysml-service`) or the CLI.

## Node and browser through `@openmbee/opensysml`

```bash
npm install @openmbee/opensysml@<version> @openmbee/opensysml-wasm@<version>   # same version
```

```ts
import { connectWasm } from "@openmbee/opensysml";
await using connection = await connectWasm();                 // worker thread by default
const model = await connection.loads("package Demo { part def Car { attribute m : ScalarValues::Real = 1.0; } part c : Car; }");
console.log(model.ok, await model.eval("Demo::c.m"));
```

- Supply your own module with `connectWasm({ wasm: "./sysml-wasm.wasm", wasmExec: "/path/wasm_exec.js" })`.
- `thread: "inline"` runs Go on the calling thread (blocks it during calls; needed where
  workers are unavailable). Worker deadlines reject the call but cannot interrupt Go.
- Browser: `import { connectWasm } from "@openmbee/opensysml/browser"` and pass a module
  `Worker` built from the package's `browser/wasm-worker` entry, or omit it to run inline.
- The adapter is JSON-only (protobuf encoding is refused). Capability-gated operations not
  in the module's surface raise `MissingCapabilityError`; use `connect()` to a `sysml-grpc`
  for them (`opensysml-node`).
- Close the connection (`await using` / `close()`) to end the worker.

## Choosing WASM vs a service

Use WASM when there is no place to run a process or no network (browser-only tools,
sandboxes, edge functions) and the needed operations are parse/validate/evaluate/
instantiate/execute. Use `sysml-grpc` (native) for verification engines, conversion,
rendering, migration, SMT and anything that needs the filesystem or external tools.
