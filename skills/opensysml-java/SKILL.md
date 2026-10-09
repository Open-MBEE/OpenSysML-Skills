---
name: opensysml-java
description: Use the Java client `org.openmbee:opensysml` (JDK 17+) to drive OpenSysML from Java, Kotlin or Scala — build it from the OpenSysML checkout, open a private `sysml-grpc` or connect to a shared one, load models, read diagnostics, evaluate typed values, verify, execute, convert and edit, with unchecked exceptions and capability negotiation. Use when integrating OpenSysML into JVM tooling (Maven/Gradle builds, Cameo/Papyrus plugins, servers).
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# OpenSysML from Java

```xml
<dependency>
  <groupId>org.openmbee</groupId>
  <artifactId>opensysml</artifactId>
  <version>0.9.2</version>
</dependency>
```

The artifact is built from the checkout, not fetched from Maven Central:

```bash
git clone https://github.com/Open-MBEE/OpenSysML && cd OpenSysML
make build-grpc                      # bin/sysml-grpc the tests and private connections use
mvn -f client/java/pom.xml install   # installs org.openmbee:opensysml (+ sources, javadoc) into ~/.m2
```

`maven.compiler.release` is 17; the client uses protobuf bodies over Connect by default and
has a small dependency footprint (no gRPC-java runtime).

```java
import org.openmbee.opensysml.*;

try (Connection connection = Connection.open()) {          // private sysml-grpc child
  Model model = connection.load(Path.of("vehicle.sysml"));
  if (!model.ok()) {
    model.diagnostics().forEach(System.err::println);
    throw new IllegalStateException("The model has errors.");
  }
  Value value = model.evalWithSubject("mass", "Vehicles::myCar");
  System.out.printf("%.1f%n", ((Value.RealValue) value).value());   // 1300.0
}
```

## Connections

- `Connection.open()` starts a **private child** (`sysml-grpc -port 0 -exit-with-parent`)
  and stops it on `close()`; no orphans survive a parent crash.
- `Connection.open(ConnectionOptions.builder().service("host", 50051).build())`,
  `OPENSYSML_SERVICE=host:port`, or `.autoStart(false)` connect to a service someone else
  runs and never stop it.
- `ConnectionOptions.Builder`: `service(host, port)`, `autoStart`, `binaryPath(Path)`,
  `downloadVersion(tag)` (default the client's own, else `OPENSYSML_GRPC_VERSION`),
  `requireCapabilities(...)` (refused at open, not at first use), `requestTimeout`,
  `startupTimeout`, `encoding(Encoding)` (protobuf default, JSON for debugging),
  `isolatedService(true)` for a child this connection alone owns, `githubRepo`,
  `allowUnpinnedDownload`.
- Binary resolution for the private child: `binaryPath`, `OPENSYSML_GRPC_BINARY`,
  `~/.opensysml/bin/`, a SHA-256-verified download of the pinned release (15 s request
  timeout; `OPENSYSML_GITHUB_REPO` to mirror), then `PATH`. An unpinned (snapshot) client
  refuses to download unless `OPENSYSML_ALLOW_UNPINNED_DOWNLOAD=1` (`opensysml-install`).
- `Connection` is thread-safe; `Model`s belong to their connection.

## `Model` operations

Same surface as the other clients, in Java naming: `ok`, `errors`, `diagnostics`,
`requireNoErrors`, `root`/`roots`, `get`, `find`, `lookup`, `symbol`, `contains`,
`eval`/`evalWithSubject`/`evalInContext`, `evaluateCalc`, `instantiate`, `verifyConstraint`,
`verifyRequirement`, `verifySatisfaction`, `validateInstance`, `runAnalysis`, `runSweep`,
`executeAction`, `executeState`, `exploreAction`/`exploreState`/`exploreAnalysis`, `query`,
`queryOslc`, `runDocumentQuery`, `documents`, `renderDocument`, `renderView`,
`exportGraphs`, `convert`/`save`, `withEngine(name)` (a model view that routes verification
to one engine), `edit()` → `Editor` collecting operations for one `applyEdits`, plus
`connection.migrate(...)`/`migrateFile(...)`, `connection.convert(...)`/`convertFile(...)`,
`connection.capabilities()`, `connection.listEngines()`, `connection.address()`,
`connection.ownsService()`.

`Value` is a sealed interface of records — `RealValue`, `IntegerValue`, `BigIntegerValue`,
`RationalValue`, `ComplexValue`, `BooleanValue`, `StringValue`, `EnumerationValue`,
`QuantityValue`, `MeasurementRefValue`, `ArrayValue`, `Sequence`, `InstanceReference`,
`MetaobjectValue`, `FunctionValue`, `InfinityValue`, `NullValue`, `UnsetValue`,
`UndeterminedValue` — so pattern-match in a `switch`; `unset`/`undetermined` are answers,
not exceptions. `Verdict` exposes `holds()`, `decided()`, `violated()` and a `Standing`;
`verifySatisfaction()` returns a `Satisfaction` (`holds()`, `violated()`, `undecided()`,
`verificationsOf(...)`).

## Exceptions

All unchecked, rooted at `OpenSysMLException`. The distinction that matters: a model with
diagnostics, a false verdict or a failed run is a **result** (`model.ok()`, `verdict.holds()`,
`Outcome`/`FailureReason` objects); an exception means the call itself could not be made or
was refused — `TransportException`, `ServiceException`, `ServiceStartException`,
`StaleServiceException` (version mismatch), `CapabilityException`,
`ChecksumMismatchException`, `ManifestSignatureException`, `UnsignedReleaseException`,
`UnpinnedReleaseException`, `ModelException`, `ModelFileNotFoundException`,
`ModelNotFoundException`, `SymbolNotFoundException`, `AnalysisException`,
`ConversionException`, `MigrationException`, `EditException`. Catch the root to log,
specific types to recover.

## Patterns

```java
// JUnit gate, one service per class
static Connection connection;
@BeforeAll static void open() { connection = Connection.open(); }
@AfterAll  static void close() { connection.close(); }
@Test void requirementsHold() {
  Model model = connection.load(Path.of("model/vehicle.sysml"));
  model.requireNoErrors();
  assertTrue(model.verifySatisfaction().holds());   // Satisfaction: holds(), violated(), undecided()
}
```

Gradle: add `mavenLocal()` after `mvn install`, or publish the artifact to your own
repository. Budgets/solver variables (`OPENSYSML_MAX_*`, `OPENSYSML_SMT`) go in the JVM's
environment for a private child or in the shared service's (`opensysml-troubleshooting`).
`client/java/README.md` documents conformance tests, publishing and limitations (no
in-process engine; FMI runner is a separate program).
