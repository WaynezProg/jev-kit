# Native integrations

Jev Kit shares one runtime and five judgment tools across hosts. Native packaging
changes installation and discovery; it does not automatically intercept actions,
prune context, lower reasoning effort, or enable the experimental browser loop.

## Install, migrate, update, remove

```sh
./jev install --hosts claude,opencode
./jev update --source "$PWD"
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev uninstall --hosts claude
```

`auto` prefers native integration. The CLI reports each selected integration and
any fallback reason. A missing host CLI or Muse's explicit unavailable-build
response selects MCP compatibility. Other CLI failures stop the operation.
`--integration native` requires native support; `--integration mcp` explicitly
selects compatibility for the seven configurable hosts. Codex and Pi retain their
existing native integrations in every mode. To change an already-native host back
to MCP, uninstall that host, then install it with `--integration mcp`.

Muse support is probed in the selected user environment. The same binary can reject plugins in an empty HOME and enable them in an existing configured environment. Native setup explicitly approves the owned `mcp_server` capability and verifies `trusted_enabled`; a later manual approval revocation stops managed updates.

Updating a format-1 managed installation migrates its recorded MCP entries and
Skill links automatically. Migration refuses foreign entries, changed links,
modified native package files, and disabled registrations. Native packages carry
physical Skill files, while MCP starts the shared absolute launcher. OpenCode
registers the tools directly through its JavaScript adapter and keeps a standalone
Skill. Credentials remain outside packages and configuration.

The shared runtime means updates apply to all managed hosts together. Private
receipts retain before-images and rollback failures. Ordinary failures attempt
rollback; a crash or concurrent external edits can require manual repair. Native
CLI commands can retain their own caches, trust records, or policy tables after
removal. The manager removes its registrations and owned package files and does
not restore old whole-file settings over unrelated changes.

## Formats and evidence

Validated on macOS on 2026-09-20. These are separate acceptance layers:

| Host | Native mechanism | Current evidence |
|---|---|---|
| Codex | `.codex-plugin/plugin.json`, dedicated local marketplace | Existing native integration; previous isolated CLI lifecycle proof retained |
| Claude Code 2.1.277 | `.claude-plugin/plugin.json`, relative marketplace source, `.mcp.json` | Real isolated CLI lifecycle; installed manifest MCP handshake, five tools and offline call |
| OpenCode 1.18.31 | Config `plugin` array, bundled object export with `server()` | Real host API discovered five tools and object schemas; direct bundled executor offline call |
| Muse 1.3.0-R3401.1 | `.muse-plugin/plugin.json`, explicit MCP capability | Real project-scope A-to-B lifecycle using the configured user environment, with MCP capability approval and `trusted_enabled` readback; empty HOME falls back to MCP + Skill |
| Grok 1.0.34 | Root `plugin.json`, `.mcp.json`, native plugin CLI | Real isolated CLI lifecycle; installed manifest MCP handshake, five tools and offline call |
| Gemini CLI 0.60.0 | `gemini-extension.json`, native extension CLI | Real isolated CLI lifecycle; installed manifest MCP handshake, five tools and offline call |
| Cursor 3.20.17 | Physical folder at `~/.cursor/plugins/local/jev-kit` | Package, lifecycle files, MCP transport and offline call verified; editor UI discovery remains unverified |
| VS Code 1.138.0 | Agent Plugins 1.0 manifest, user `chat.pluginLocations` | Package/schema, settings lifecycle, MCP transport and offline call verified; Copilot UI discovery remains unverified |
| Pi | Bundled native extension + Skill | Existing SDK integration and prior real Jev-call evidence retained |

The deterministic offline call supplies an absent quote and expects
`quote_not_found` with zero provider requests. For Claude/Gemini/Grok, the MCP test
launches the command from the host-installed manifest; it does not claim a model
chose to use Jev. OpenCode's public local API exposes tool discovery but no direct
execution endpoint, so its executor was called separately without a model request.

The newer OpenCode V2 adapter uses `ctx.tool.transform`, declares the `jev`
namespace and registers the same five operations. It has contract tests only;
there is no live V2 acceptance claim. A runtime lacking the documented registrar
fails explicitly rather than silently loading an empty plugin.

The development profile was migrated from all nine managed format-1 integrations to native registrations. All nine passed configuration/inventory readback. The installed shared MCP runtime also completed a real Jev evidence request on synthetic text (`supports`, no review required); this verifies the common runtime, not model-triggered use in every host. Automated coverage passed 55 JavaScript tests and 57 Python tests.

`status` checks package hashes, registration ownership and native CLI inventory.
It is not a model-usage or editor-UI check. Restart affected hosts after changes.
JSONC settings are refused safely; this installer currently supports strict JSON
and Grok TOML on macOS/Linux, not Windows or remote editor environments.

## Sources

- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [OpenCode V1 plugins](https://dev.opencode.ai/docs/plugins/) and [V2 plugin tools](https://opencode.ai/v2/docs/build/plugins)
- [Muse native manifest](https://meta-models.github.io/muse-code-sdk/next/guides/plugins/reference/manifest/)
- [Grok plugin guide](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/09-plugins.md)
- [Gemini extension reference](https://geminicli.com/docs/extensions/reference/)
- [Cursor plugins](https://prod.cursor.com/docs/plugins)
- [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
- [Agent Plugins specification](https://agent-plugins.org/specification)
