---
name: opensysml-rust
description: Use the `opensysml` Rust crate (crates.io, blocking API) to load, validate, evaluate, verify, execute, convert and edit SysML v2 models from Rust — `Connection::private()` for a child `sysml-grpc`, `Connection::external(host, port)` or OPENSYSML_SERVICE for a shared one, binary provisioning variables, capability negotiation and the typed `Value`/error surface. Use when writing Rust tools, tests or build scripts on top of OpenSysML.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# OpenSysML from Rust

```toml
[dependencies]
opensysml = "0.9"                # crates.io release, pinned to the matching sysml-grpc release
# development against a checkout:
# opensysml = { path = "../OpenSysML/client/rust/opensysml" }
# opensysml = { git = "https://github.com/Open-MBEE/OpenSysML.git", branch = "main" }
```

The API is **blocking** (no async runtime required; wrap in `spawn_blocking` from Tokio if
needed) and speaks Connect/protobuf to `sysml-grpc`; JSON is only a debugging encoding.

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let model = opensysml::load("vehicle.sysml")?;          // private service, parse
    if !model.ok() {
        for diagnostic in model.diagnostics() { eprintln!("{diagnostic}"); }
        return Err("The model has errors.".into());
    }
    let result = model.evaluate(
        "mass",
        &opensysml::EvalOptions { subject: Some("Vehicles::myCar".into()), ..Default::default() },
    )?;
    if let opensysml::Value::Real(mass) = result.result { println!("{mass:.1}"); }  // 1300.0
    Ok(())
}
```

`opensysml::loads(source)` parses text. For several models, hold a `Connection`:

```rust
let conn = opensysml::Connection::connect()?;       // $OPENSYSML_SERVICE if set, else private child
let a = conn.load("a.sysml")?;
let b = conn.loads("package B { part def X; }")?;
drop(conn);                                         // stops a private child; external ones keep running
```

## Service lifecycle

- `Connection::private()` starts one `sysml-grpc` child per parent process
  (`-port 0 -exit-with-parent`); every `Connection` in the process shares it and its parse
  cache; the last drop stops it.
- `Connection::external(host, port)` connects to a service someone else runs and never
  stops it. `Connection::connect()` chooses based on `OPENSYSML_SERVICE`.
- Binary for the private child: `OPENSYSML_GRPC_BINARY` → `~/.opensysml/bin/sysml-grpc` →
  download of `OPENSYSML_GRPC_VERSION` (default: the crate's pinned release; `latest`
  allowed) from `OPENSYSML_GITHUB_REPO` (default `Open-MBEE/OpenSysML`) → `PATH`. SHA-256
  of the archive is checked against the release manifest; an unpinned (git/path) build
  refuses to download unless `OPENSYSML_ALLOW_UNPINNED_DOWNLOAD=1` (`opensysml-install`).
- Capabilities: the connection reads `GetServerInfo` once (`conn.capabilities()`); options the
  service does not advertise are refused client-side with `Error::MissingCapability` rather
  than failing inside the RPC.

## Typed surface

`Model` methods mirror the service (`opensysml-service`): `ok`, `diagnostics`, `errors`,
`hash`, `root`/`roots`, `get`, `find`, `lookup`, `contains`, `evaluate(expr, &EvalOptions)`,
`instantiate`, `verify_constraint`/`verify_requirement`/`verify_satisfaction`/`satisfied`/
`validate_instance` (`&VerifyOptions`/`&SatisfyOptions`; verdicts carry `holds` and a
standing), `calc(&CalcOptions)`, `run_analysis(&AnalysisOptions)`, `run_sweep(&SweepOptions)`,
`execute_action(&ActionOptions)`, `explore_action`/`explore_analysis`, `query`/`query_oslc`,
`render_document`, `render_view`/`render_view_with_ports`, `export_graphs`,
`convert(&ConvertOptions)`/`to_turtle`/`to_api_json`/`to_sysml`/`save`, `edit()` →
`Editor::apply()`. On `Connection`: `parse_file`, `parse_content`, `model_by_hash`,
`diagnostics(hash)`, `apply_edits`, `list_engines`, `capabilities`, `server_info`,
`private_service_pid`; migration lives in the `migration` module (`MigrateOptions`).
`load_with`/`loads_with` take `ParseOptions` (strict, conformance, language).

`Value` is an enum — `Real(f64)`, `Integer(i64)`, `BigInteger`, `Rational`, `Complex`,
`Boolean`, `Text`, `EnumLiteral`, `Quantity`, `VectorQuantity`, `TensorQuantity`,
`MeasurementRef`, `Array`, `Vector`, `Sequence`, `Set`, `InstanceRef`, `Metaobject`,
`Function`, `Infinity`, `Null`, `Unset`, `Undetermined` — `match` on it;
`Unset`/`Undetermined` are answers, not `Err`. `opensysml::Error` is one enum:
`Transport`, `Service(Status)` (canonical code), `ServiceStart`, `BinaryNotFound`,
`UnsupportedPlatform`, `BinaryDownload`, `ChecksumMismatch`, `UnpinnedRelease`,
`MissingCapability`, `Decode`, `Model`, `ModelErrors`, `InvalidRequest`, `SymbolNotFound`,
`UnsupportedValue`, `WrongKind`, `Execution`, `AnalysisRun`, `Conversion`, `Migration`,
`Unwritable`, `Edit`, `Query`, `Io`. A false verdict, a model with diagnostics or a failed
run is `Ok` with that result.

## Patterns

```rust
#[test]
fn requirements_hold() {
    let model = opensysml::load("model/vehicle.sysml").unwrap();
    assert!(model.ok(), "{:?}", model.diagnostics());
    assert!(model.satisfied(&Default::default()).unwrap());
}
```

Set `OPENSYSML_GRPC_BINARY` in CI to skip downloads; put budgets/solver variables
(`OPENSYSML_MAX_*`, `OPENSYSML_SMT`) in the environment of the process that spawns the
child or of the shared service (`opensysml-troubleshooting`). `client/rust/README.md` has
the conformance runner and release procedure; `cargo doc --open -p opensysml` for exact
signatures.
