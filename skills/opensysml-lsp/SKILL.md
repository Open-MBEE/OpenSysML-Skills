---
name: opensysml-lsp
description: Wire the `sysml-lsp` language server into editors and coding agents — VS Code (opensysml-sysml.vsix), OpenCode, Neovim or any LSP client — over stdio, configure strict conformance and lint settings, and understand the experimental methods (rendering, document rendering, stdlib content, model edits, debugging). Use when setting up SysML v2 editing support, when an agent harness should get live diagnostics for .sysml/.kerml files, or when the server starts but reports nothing.
license: Apache-2.0
metadata:
  project: OpenSysML
  upstream: https://github.com/Open-MBEE/OpenSysML
---

# `sysml-lsp` and editors

`sysml-lsp` is a Language Server Protocol server for `.sysml` and `.kerml` files: diagnostics
(the same checks `sysml -validate` runs), completion, hover, go-to-definition, references,
rename, document symbols, semantic tokens, formatting and code actions. It serves one
workspace and resolves names across all its files, so cross-file references work in the
editor even though the CLI loads only the files named.

Install it with any route in `opensysml-install` (`--tools sysml-lsp`); the Go route is
`go install github.com/Open-MBEE/OpenSysML/cmd/sysml-lsp@latest`.

## Command line

```bash
sysml-lsp --stdio                 # the only transport; clients spawn it and talk JSON-RPC on stdio
sysml-lsp --stdio -strict         # strict OMG conformance for every document
sysml-lsp --stdio -no-record-cache
sysml-lsp -version
```

## Settings (sent by the client, `sysml` section)

| Setting | Effect |
|---|---|
| `sysml.strictConformance` (bool) | Same as `-strict`; `nonstandard-notation` becomes an error |
| `sysml.disabledLints` (string[]) | Lint codes to drop, e.g. `["undeclared-signal"]` |
| `sysml.enabledLints` (string[]) | Opt-in lints to report, e.g. `["rounded-real-literal"]` |

Environment variables apply as for the CLI (`OPENSYSML_LIBRARY_PATH`, budgets; see
`opensysml-troubleshooting`).

## VS Code

The extension lives in `editors/vscode` of the OpenSysML repository and is published as a
VSIX on the nightly release, not on the Marketplace:

```bash
curl -fsSLO https://github.com/Open-MBEE/OpenSysML/releases/download/nightly/opensysml-sysml.vsix
code --install-extension opensysml-sysml.vsix
```

or build it: `cd editors/vscode && npm install && npm run package`. It finds `sysml-lsp`
on `PATH`; pin a specific binary with `.vscode/settings.json`:

```json
{
  "opensysml.server.path": "/absolute/path/to/sysml-lsp",
  "opensysml.server.args": ["-strict"],
  "opensysml.diagram.autoOpen": false
}
```

Extension settings use the `opensysml.*` prefix (`server.path`, `server.args`,
`server.enabled`, `trace.server`, `diagram.autoOpen`, `diagram.style`); the server's own
settings keep the `sysml.*` prefix above and are passed through unchanged.

Beyond LSP it adds a diagram panel (renders views via the server), a standard-library
browser, and "run this element" commands that shell out to `sysml`.
`editors/vscode/README.md` documents every setting.

## OpenCode and other agent harnesses

Any harness that forwards LSP diagnostics to its agent gets `sysml -validate`-grade feedback
on every edit. OpenCode: add to `opencode.json` in the project (or
`~/.config/opencode/opencode.json` for all projects):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "sysml": {
      "command": ["sysml-lsp", "--stdio"],
      "extensions": [".sysml", ".kerml"]
    }
  }
}
```

The server must be on `PATH` when the harness starts (`PATH="$PWD/bin:$PATH" opencode`
after `make build` in a checkout).

## Neovim (`nvim-lspconfig` style)

```lua
vim.filetype.add({ extension = { sysml = "sysml", kerml = "kerml" } })
vim.lsp.config("sysml_lsp", {
  cmd = { "sysml-lsp", "--stdio" },
  filetypes = { "sysml", "kerml" },
  root_markers = { ".git" },
  settings = { sysml = { strictConformance = false } },
})
vim.lsp.enable("sysml_lsp")
```

Any client that can run a stdio server works the same way (Helix, Emacs `eglot`, Zed, Sublime
LSP): command `sysml-lsp --stdio`, language ids `sysml` and `kerml`.

## Experimental methods (`$/sysml/...`)

The server exposes extensions for tooling — rendering a view or document to
Markdown/Mermaid/HTML, serving standard-library source for navigation, applying model
edits, debugging actions/states (stepping, events), cross-document layout, palettes,
forms, styles and port display. They are documented with request/response shapes in
`docs/reference/lsp.md` of the OpenSysML repository and are used by the VS Code extension;
treat them as unstable and check the server version (`sysml-lsp -version`) before relying
on one.

## Troubleshooting

- No diagnostics at all: the file is not recognised as `sysml`/`kerml` by the client, or the
  server exited at startup — run `sysml-lsp --stdio < /dev/null` to see a clean exit, and
  check the client's LSP log.
- Unresolved references that the CLI resolves: the LSP resolves across the *workspace root*;
  open the folder containing all files, not a single file.
- Different verdicts from the CLI: strict mode or lint settings differ; align
  `sysml.strictConformance` with `-strict`.
- Stale results after installing a new binary: restart the server (the client caches the
  process); `-no-record-cache` disables the on-disk record cache if it looks corrupt.
