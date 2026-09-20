# Jev Kit

[English](README.md) | **繁體中文**

以 [TypeSafe Jev](https://typesafe.ai/) 為 coding agent 提供來源綁定的證據檢查與有限範圍的批次判斷。

Jev Kit 整合 [jev-use](https://github.com/shitianfang/jev-use) 的批次引擎、[jev-mcp](https://github.com/jkudish/jev-mcp) 的任務模式，以及本機來源與引文驗證。這是獨立整合專案。

## 功能

| 工具 | 用途 |
|---|---|
| `jev_evidence` | 逐項比對主張與各自來源，並在本機核對提供的引文 |
| `jev_classify` | 依共同分類表批次分類資料 |
| `jev_extract` | 從有限的 regex 候選中選出精確值 |
| `jev_decide` | 依證據與需求比較 2–6 個選項 |
| `jev_rerank` | 選擇性重排最多 30 筆既有搜尋候選，保留所有 ID |

適合直接處理既有來源與工具輸出的批次資料，無須先讓另一個 LLM 摘要。未確定的結果交回主 agent 審查。Jev 維持選用：本專案不代表已證明能提高寫程式的正確率、降低總成本、加速開發或降低所需 thinking level。

另提供[實驗性的 Ego Lite adapter](integrations/ego-browser/README.md)，透過固定版本的 `jev-ultrafast` policy 執行明確指定的瀏覽器工作，與上述五個判斷工具分開使用。

## 安裝

需要 Git、Node.js 22+、Python 3.11+ 與 POSIX shell。Host 安裝已在 macOS 實測；不支援 Windows。Repo 內附 runtime bundles，使用時不必安裝 npm dependencies。

```sh
curl -fsSL https://raw.githubusercontent.com/WaynezProg/jev-kit/main/install.sh | sh
```

安裝器會下載乾淨的 checkout、偵測既有 host 設定，並安裝到 `~/.local/share/jev-kit`。如需先檢查程式或指定 host：

```sh
git clone https://github.com/WaynezProg/jev-kit.git
cd jev-kit
./jev install --hosts claude,opencode
```

透過 `TYPESAFE_API_KEY`，或由 `TYPESAFE_API_KEY_FILE` 指定的私人檔案提供 TypeSafe API key。檔案請放在 repo 外，權限設為 `0600`。無法繼承 shell 環境變數的桌面 host，可使用支援的預設檔案 `~/.config/jev-benchmark/typesafe-api-key`。憑證須另行設定，不會寫入產生的 host packages。

```sh
# 指向已安全填入 key 的私人檔案。
export TYPESAFE_API_KEY_FILE="$HOME/.config/jev-benchmark/typesafe-api-key"

# 在 checkout 中離線驗證，不需要 key 或網路。
node dist/cli.js evidence --input examples/evidence.json --validate-only

# 實際呼叫 API；輸出路徑必須尚不存在。
node dist/cli.js evidence --input examples/evidence.json --output /tmp/jev-evidence-result.json
```

判斷時會把提供的任務文字送往 TypeSafe，請只提供相關且已授權的內容，不要包含憑證。本機引文不符及部分候選為空的情況會略過 API。

## 支援的工具

| Host selector | 管理的整合方式 |
|---|---|
| `codex` | 專用 local marketplace 中的 native plugin |
| `claude` | 透過 Claude CLI 安裝 native plugin |
| `opencode` | JavaScript native plugin + Skill |
| `muse` | 環境支援時使用 native plugin，否則使用 MCP + Skill |
| `grok` | 透過 Grok CLI 安裝 native plugin |
| `gemini` | 透過 Gemini CLI 安裝 native extension |
| `cursor` | 本機 native plugin package |
| `vscode` | 透過 `chat.pluginLocations` 註冊 Agent Plugin |
| `pi` | Native extension + Skill |

`--integration auto` 優先使用 native package；只有找不到 host CLI 或 host 回報 native plugin 不可用時，才退回 MCP + Skill。`--integration native` 要求 native 支援；`--integration mcp` 為七個可配置的 host 選擇相容模式。Codex 與 Pi 一律使用 native 整合。已安裝 native 整合的 host，須先移除才能切換至 MCP。

Native 包裝不會自動啟用 hooks 或修改模型設定。Cursor／VS Code 已通過 package 與 MCP 檢查，但尚未驗證 editor UI discovery。OpenCode V1 已驗證工具發現，V2 僅有 contract tests。Muse 可用性取決於其設定環境。詳見[各 host 的驗證範圍與限制](docs/native-integrations.md)。

## 更新與移除

安裝後不必保留原始 checkout，即可使用管理器：

```sh
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev update
~/.local/share/jev-kit/jev uninstall --hosts muse
~/.local/share/jev-kit/jev uninstall
```

在 checkout 中可用 `./jev install --hosts all` 建立全部九個 host 的整合。`update` 下載 GitHub `main`，一起更新所有受管理的 host；`update --source /absolute/checkout` 則使用本機來源。從較新的 checkout 加入 host 前，請先更新共用 runtime。

管理器會核對檔案歸屬，遇到已修改檔案、非本工具建立的項目或明確停用的註冊時停止。移除僅清除受管理的整合，保留其他設定、憑證、release snapshots 與私人 receipts。一般錯誤會嘗試 rollback；當機或同時修改可能需要手動修復。不接受 JSONC／含註解的 JSON，host JSON 設定必須使用 strict JSON。

`status` 檢查設定與安裝清單，不代表模型已實際使用工具。安裝、更新或移除後請重啟受影響的 host，Codex 另開新 task。`~/.local/share/jev-kit/receipts` 中的私人備份與 receipts 可能包含其他服務的憑證，請勿上傳 GitHub。

## 在 agent 或 CLI 中使用

安裝後可向 agent 提出：

> 使用 jev-kit，把這些 issues 分成 bug、feature 或 manual review，保留 ID 與未解決項目。

手動設定 MCP 時，執行 `node scripts/configure-mcp.mjs` 產生本機 `.mcp.json`，再將 command／args 放入 host 設定。`node dist/cli.js serve` 使用 stdio。獨立的 Pi extension 位於 `dist/pi-extension.js`。

五個工具都能透過 CLI 讀取檔案：

```sh
node dist/cli.js rerank --input examples/rerank.json --output /tmp/jev-rerank-result.json
```

Rerank 接收既有搜尋結果，不負責搜尋。`top_k` 選出優先檢查的候選，其餘 ID 保留在 receipt。回應無效、timeout 或缺少 key 時，會保留原始順序並標記待審查。請保留原文供後續檢查。

詳見[輸入 schemas 與範例](skills/jev-kit/references/inputs.md)及 [agent Skill](skills/jev-kit/SKILL.md)。

## Ego Lite 瀏覽器工作

需要執行中的 Ego Lite、`ego-browser` CLI，以及使用 Python 3.12+、`uv` 建立的獨立固定版本 upstream checkout。依照 [adapter 設定與 job 範例](integrations/ego-browser/README.md)準備後執行：

```sh
./jev browser --input job.json --validate-only
./jev browser --input job.json
```

Adapter 觀察頁面控制項，讓 Jev 選擇下一個動作，操作前檢查目標，再獨立驗證提供的結果條件。產生欄位文字需要設定 text model 或 Claude CLI helper。登入、交易批准、frames、shadow DOM 與 popup 接續操作不在已驗證範圍內。此功能仍屬實驗性質，不會因安裝 host 整合而自動啟用。

## 如何解讀結果

- 先看 `status` 與各項的 `requires_review`，未解決項目需要審查。
- 來源支持某主張，不等於獨立證明其為真。Confidence 與排序不保證正確。
- 五個判斷工具不抓取來源、不執行任意指令、不批准動作、不自動刪減 context，也不修改模型設定。來源的提示包裝不構成 prompt injection 安全邊界。
- 判斷工具的 CLI exit `0` 代表處理完成，`3` 代表需要審查，`2` 代表輸入或服務／驗證錯誤。Exit `0` 不代表任務已完成驗收。
- 判斷工具的 receipts 為新建的 `0600` 檔案，包含 ID、hashes、結果、usage、實際模型與時間。請保留原始輸入以便重現。
- 判斷請求使用固定 TypeSafe endpoint、15 秒 timeout，且不自動重試。API 可用性與費用由外部服務決定。

## 開發

```sh
npm ci --ignore-scripts
npm run build
npm test
python3 -m unittest discover -s test -p '*_test.py'
```

離線測試涵蓋判斷契約、來源綁定、異常回應、bundles、MCP／native 註冊、host 生命週期設定保留，以及瀏覽器操作檢查。另有需要 key 的 live smoke test，會實際呼叫五個工具：

```sh
node scripts/smoke.mjs /tmp/new-jev-live-smoke.json
```

`dist/` 與 `vendor/` 刻意保留在 Git，讓乾淨安裝不必另外執行 npm setup。本機實驗、benchmark 報告、憑證、logs、receipts 與暫存產物不納入 Git。

## 授權

MIT。Vendored 元件保留各自的 upstream 授權。固定版本、調整項目與來源標示見 [THIRD_PARTY.md](THIRD_PARTY.md)，資料處理說明見 [SECURITY.md](SECURITY.md)。
