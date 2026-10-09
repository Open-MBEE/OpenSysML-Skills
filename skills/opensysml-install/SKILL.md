---
name: opensysml-install
description: Install the OpenSysML REDK binaries (sysml, sysml-lsp, sysml-grpc, sysml-jupyter-kernel) with the release install script, Homebrew, go install, or a source build, pin a release or the nightly, verify checksums, and locate the binaries the language clients auto-download. Use when a task needs the `sysml` command or a `sysml-grpc` service and it is not yet on PATH, when choosing a release version, or when a client reports it cannot find or verify a binary.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# Installing OpenSysML

OpenSysML ships four executables from one release:

| Binary | Purpose |
|---|---|
| `sysml` | CLI, REPL, validator, execution runtime, document generator |
| `sysml-lsp` | Language Server Protocol server for editors |
| `sysml-grpc` | Service process the Python/Node/Java/Rust/Julia/MATLAB clients talk to |
| `sysml-jupyter-kernel` | Jupyter kernel backed by the REPL |

Releases live at https://github.com/Open-MBEE/OpenSysML/releases. The tag `nightly` is a
rolling snapshot of `develop`; `latest` is the newest tagged release. Each release carries a
`SHA256SUMS.txt` manifest, and the install paths below verify downloads against it.

## Pick a route

1. **Release install script (recommended).** No root required; verifies checksums.
   ```bash
   curl -fsSL https://opensysml.org/install.sh | sh
   ```
   Installs to `/usr/local/bin` when writable, else `~/.local/bin`, with man pages under
   `share/man/man1`. It never edits a shell profile; add the directory to `PATH` if told to.
   Options go after `sh -s --` (environment variable equivalents in parentheses):
   - `--version v0.9.2 | latest | nightly` (`OPENSYSML_VERSION`)
   - `--tools sysml,sysml-lsp,sysml-grpc,sysml-jupyter-kernel | all` (`OPENSYSML_TOOLS`)
   - `--prefix DIR` / `--bin-dir DIR` (`OPENSYSML_PREFIX`, `OPENSYSML_BIN_DIR`)
   - `--base-url URL` for a release mirror (`OPENSYSML_DOWNLOAD_BASE`)
   - `--dry-run` shows what would be installed; `--verify-signature` also checks the
     manifest's cosign signature (needs `cosign` on PATH)
   - `--os`/`--arch` stage another platform's build without running it
   ```bash
   # just the language server, nightly, into ~/bin
   curl -fsSL https://opensysml.org/install.sh | sh -s -- --tools sysml-lsp --bin-dir ~/bin --version nightly
   ```
   Windows (PowerShell 5.1+, no admin): `irm https://opensysml.org/install.ps1 | iex`, with
   `-Version`, `-Tools`, `-InstallDir`, `-NoPath`, `-DryRun` parameters. Installs to
   `%LOCALAPPDATA%\Programs\OpenSysML` and adds it to the user PATH.

2. **Homebrew (macOS/Linux).**
   ```bash
   brew install Open-MBEE/tap/opensysml
   ```

3. **Go toolchain (Go 1.23+).** Builds from source, so no checksum manifest applies.
   ```bash
   go install github.com/Open-MBEE/OpenSysML/cmd/sysml@latest
   go install github.com/Open-MBEE/OpenSysML/cmd/sysml-lsp@latest
   go install github.com/Open-MBEE/OpenSysML/cmd/sysml-grpc@latest
   ```

4. **From a checkout.**
   ```bash
   git clone https://github.com/Open-MBEE/OpenSysML && cd OpenSysML
   make build            # bin/sysml, bin/sysml-lsp, bin/sysml-grpc with version ldflags
   make build-wasm       # optional: bin/wasm/{wasip1,js}
   ```
   `cmd/` also holds `sysml-jupyter-kernel`, `sysml-core`, `sysml-engine`, `sysml-syntax`,
   `sysml-wasm`; build any with `go build -o bin/<name> ./cmd/<name>`.

Confirm with `sysml -version` (prints version, commit, build time, Go version) and
`sysml -man` for the manual page.

## Binaries the language clients download for themselves

The Python, Node, Java and Rust clients start a private `sysml-grpc` and resolve it in this
order: an explicit path (`OPENSYSML_GRPC_BINARY`, or a constructor argument), the shared cache
`~/.opensysml/bin/`, a verified release download matching the client's pinned version, then
`PATH`. Downloads are checked against SHA-256 digests baked into the client package; a
mismatch raises a `ChecksumMismatchError` rather than running the binary. Development
(unpinned) client builds refuse to download unless `OPENSYSML_ALLOW_UNPINNED_DOWNLOAD=1`.
Julia and MATLAB look at `OPENSYSML_GRPC_BINARY`, then the cache, then `PATH`, and do not
download.

To avoid any download in CI or offline, install `sysml-grpc` by one of the routes above and
export `OPENSYSML_GRPC_BINARY=/path/to/sysml-grpc`, or point every client at a shared running
service with `OPENSYSML_SERVICE=host:port` (see `opensysml-service`).

## Optional components

- **SMT solver** for `-check*`, `%solve`, `%configure`, `%optimize`: install `z3` or `cvc5`
  and, if not on PATH, set `OPENSYSML_SMT=/path/to/z3`. `sysml -engines -probe` reports
  whether a solver was found.
- **Document rendering to PDF/HTML** needs external tools (WeasyPrint, pandoc, mermaid-cli,
  KaTeX, Graphviz, PlantUML, D2); see `opensysml-documents`.
- **Standard library**: bundled into the binary. `OPENSYSML_LIBRARY_PATH` overrides it with
  a directory of `.kerml`/`.sysml` library files.

## Failure modes

- `sysml: command not found` after the script: the install directory is not on `PATH`; the
  script printed the directory. Re-run with `--bin-dir` or export `PATH`.
- macOS Gatekeeper blocks a hand-downloaded archive: the script's `curl` download does not
  trigger it; for manual downloads use `xattr -d com.apple.quarantine <binary>`.
- Checksum mismatch: the download is corrupt or a mirror is stale; retry without
  `--base-url`, or pin `--version` to a tag that exists.
- A client complains the cached binary is stale (`StaleServiceError` or a version mismatch):
  delete `~/.opensysml/bin/sysml-grpc*` and let it re-download, or set
  `OPENSYSML_GRPC_BINARY` to a binary built from the same release as the client.
