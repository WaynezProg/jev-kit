# Sources and local adaptations

- jev-use 0.6.1, https://github.com/shitianfang/jev-use/tree/56f3099ba5a9049195f931486450610ba1567514, MIT. Fixed source and its tested build are vendored under vendor/jev-use because this version was unavailable in the npm registry during integration. The runtime uses its batch judge engine, native TypeSafe adapter and escalation behavior. Raw answers are validated by our StrictBackend before engine projection. Package metadata is reduced for local dependency use; original source/build are unchanged.
- jev-mcp 0.5.0, https://github.com/jkudish/jev-mcp/tree/67dd9fa5a6e895909f1b2d80bf45534c29cff25a, MIT. vendor/mcp-helpers.js adapts probability margin, classification thresholds, escape hatches and regex-worker candidate extraction. It adds worker memory/exit handling and CommonJS eval compatibility. Task templates adapt classify/extract/decide patterns. Attribution retained in vendor/jev-mcp-LICENSE.
- Local jev-evidence 0.1.1 supplies the evidence criteria, exact-quote check, per-item source binding, source/claim hashes and review-first interpretation.

The two upstream gate implementations are not exposed. The five judgment MCP tools have no approval hook, arbitrary command execution, source retrieval, automatic pruning or model-setting mutation. This is an independent integration, not an upstream release.

- Experimental Ego adapter: browser-use/jev-ultrafast at `1231850a0bf1a0c0341fe408ef1668dbbfdfac46`, MIT. Its policy and DOM reader are imported from a separate pinned checkout. Execution guards adapt its node identity, page-state and occlusion checks to Ego Page methods; notice retained in `integrations/ego-browser/UPSTREAM-LICENSE`. This optional CLI job executes browser actions and is separate from the five judgment tools.
