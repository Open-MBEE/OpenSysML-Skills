---
name: opensysml-matlab
description: Use the MATLAB/Octave client under client/matlab (`+opensysml` package, no toolboxes) to parse, validate, evaluate, verify, execute, analyse, convert and edit SysML v2 models — `opensysml.connect`, `opensysml.external`, `opensysml.private`, parseFile/parseSource, values, errors, and the Octave+curl path. Use when calling OpenSysML from MATLAB scripts, Simulink callbacks, or Octave in CI.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# OpenSysML from MATLAB / Octave

```matlab
addpath('/path/to/OpenSysML/client/matlab');     % the +opensysml package; no toolboxes required
```

MATLAB uses `matlab.net.http`; Octave shells out to `curl` (the path CI exercises). The
transport is Connect **JSON**, so answers compare directly with `curl` against
`sysml-grpc` (`opensysml-service`).

```matlab
conn = opensysml.connect();                       % OPENSYSML_SERVICE, otherwise a private child
cleanup = onCleanup(@() conn.close());
model = opensysml.parseFile(conn, 'vehicle.sysml');
if ~model.ok()
    disp(opensysml.diagnostics(model))
    error('The model has errors.')
end
mass = opensysml.evaluate(model, 'mass', 'subject', 'Vehicles::myCar');
fprintf('%.1f\n', mass);                          % 1300.0
```

## Connections

```matlab
conn = opensysml.connect();                                    % env-driven
conn = opensysml.external('localhost:50051');                  % service someone else runs; close() only disconnects
conn = opensysml.private('binary', '/path/to/sysml-grpc', 'timeout', 30);   % explicit child
```

- `opensysml.private` needs Java (MATLAB's process control); MATLAB without Java and Octave
  configurations that cannot spawn should use `opensysml.external` or `OPENSYSML_SERVICE`.
- Binary resolution for a private child: the `'binary'` argument, `OPENSYSML_GRPC_BINARY`,
  `~/.opensysml/bin/sysml-grpc`, then `PATH`. The MATLAB client does **not** download
  releases — install the binary first (`opensysml-install`).
- `opensysml.capabilities(conn)` reports what the service advertises; `opensysml.lastError()`
  returns the last service error struct.

## Parsing and models

`opensysml.parseFile(conn, path)`, `opensysml.parseSource(conn, text)`,
`opensysml.parseSources(conn, docs)` (`opensysml.SourceDocument`s); `model.ok()`,
`opensysml.diagnostics(model)` (struct array with `severity`, `message`, `span`, `code`),
`model.hash`, `opensysml.getSymbol(model, 'Pkg::x')` → `opensysml.Symbol`.

## Operations

Name/value pairs for options: `opensysml.evaluate(model, expr, 'subject', id)`,
`opensysml.instantiate(model, id)`, `opensysml.verifyConstraint(model, id, 'subject', id)`,
`opensysml.verifyRequirement`, `opensysml.verifySatisfaction(model)`,
`opensysml.validateInstance`, `opensysml.calc(model, id, args)`,
`opensysml.runAnalysis(model, id, 'subject', ..., 'engine', ...)`,
`opensysml.runSweep(model, id, ranges)`, `opensysml.executeAction(model, id, 'inputs', ...)`,
`opensysml.executeState(model, id, 'events', {...}, 'trace', true)`,
`opensysml.query(model, 'where', ...)`, `opensysml.runDocumentQuery`,
`opensysml.renderDocument(model, id, 'form', 'markdown')`, `opensysml.renderView`,
`opensysml.exportGraphs`, `opensysml.convert(model, opensysml.FORMAT_TURTLE)` (also
`FORMAT_SYSML`, `FORMAT_API_JSON`; result is an `opensysml.Conversion`),
`opensysml.migrate(conn, 'Model.mdzip', ...)` → `opensysml.Migration` (`opensysml.isV1(path)`
tells whether a file needs migration), `opensysml.listEngines(conn)`.

Values: reals/ints become `double` (64-bit ints beyond `flintmax` are returned as `int64`
or strings per capability), booleans `logical`, strings `char`, arrays cell/numeric
arrays; enum literals, quantities, instance references and the unset/undetermined answers
come back as typed values built by `opensysml.quantity`, `opensysml.enumLiteral`,
`opensysml.instanceRef`, `opensysml.infinity`, `opensysml.metaobject`, `opensysml.functionRef`
(use the same constructors to pass inputs) — check the class before arithmetic.
`opensysml.Verdict` has `holds`, `standing`, `engine`, `explain`.

## Authoring edits

`opensysml.setValue(model, id, value)` is the one-shot form; for several operations build an
`opensysml.Editor`, add operations, and send them with `opensysml.applyEdits(...)` — one
`ApplyEdits` call returning an `opensysml.EditResult`; refusals report the referrers.

## Errors

Errors use identifiers under `opensysml:` — `opensysml:transport`, `opensysml:staleService`,
`opensysml:missingCapability`, `opensysml:unsupported`, `opensysml:argument`,
`opensysml:featureValue`, `opensysml:encode`/`opensysml:decode`, `opensysml:experimental`
(RDF/migration warnings) — catch with `try … catch err, switch err.identifier`; service
refusals carry the canonical code in `opensysml.lastError()`. Diagnostics and false
verdicts are return values (`opensysml.Verdict`, `opensysml.Standing`).

Not available in MATLAB/Octave: in-process execution, protobuf transport, release download,
typed stub generation (see `client/matlab/README.md`). CI pattern:

```bash
sysml-grpc -port 50051 &                                  # or OPENSYSML_SERVICE=localhost:50051
octave --no-gui --eval "addpath('client/matlab'); run_tests"
```
