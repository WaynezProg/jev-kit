# Jev Kit

[English](README.md) | **繁體中文**

為 coding agents 提供以既有來源為依據的證據檢查，以及範圍明確的批次判斷，由 [TypeSafe Jev](https://typesafe.ai/) 驅動。

Jev Kit 整合了 [jev-use](https://github.com/shitianfang/jev-use) 的批次引擎、[jev-mcp](https://github.com/jkudish/jev-mcp) 的任務模式，以及本機來源與引文驗證。這是獨立整合專案，並非上述專案或 TypeSafe 的官方版本。

| 工具 | 用途 |
|---|---|
| `jev_evidence` | 依每項主張指定的來源檢查證據，並在本機比對提供的引文 |
| `jev_classify` | 使用同一組分類定義，批次分類多筆資料 |
| `jev_extract` | 從數量受限的 regex 候選項中，選出來源中的確切值 |
| `jev_decide` | 根據提供的證據與要求，比較 2–6 個選項 |
| `jev_rerank` | 選擇性重排最多 30 筆既有搜尋候選結果，保留所有 ID |

直接使用既有來源與工具輸出即可，呼叫 Jev 前不需要額外請 LLM 摘要。Host 仍須組成工具輸入並檢查結果，因此這本身不代表總 token 成本更低、開發更快，或能降低所需的 thinking level。

目前證據支持一個較窄的候選用途：[範圍受限的瀏覽器決策迴圈](#where-jev-helped-bounded-browser-decision-loops)。[程式碼搜尋重排](#code-search-reranking-results) 相較字詞搜尋，能改善配對目標的排序，但落後於 Fable，也沒有加快小型修復流程。一般的 inline review 仍增加額外負擔；[模型層級測試](benchmarks/model-tiers/results/RESULTS.md) 中的證據分流則以準確率換取速度。請維持選用模式，並針對工作負載驗證。0.3.0 已透過 CLI、MCP 與 Pi 提供可選的候選重排功能；它本身不執行搜尋。瀏覽器執行器與完整搜尋 adapters 仍屬實驗性功能。

<a id="quick-start"></a>

## 快速開始

<a id="new-upstream-evaluation-and-ego-lite-prototype"></a>

### 上游專案評估與 Ego Lite 原型

Jev Kit 維持統一入口。現在可選擇使用 `./jev browser --input job.json`，在 **Ego Lite 上執行固定版本的 jev-ultrafast policy**，透過 Ego Page 操作與獨立的完成條件檢查執行任務。既有的五個 MCP 判斷工具不變。

較嚴格的對照允許 Fable 在同一個回覆中批次執行最多五個動作，並產生欄位文字。六次本機表單測試全部通過：Jev 中位時間為 **6.35 s**，batch Fable low 為 **7.30 s**，降低 13.0%。在 Wikipedia 上，Jev 最初通過 **3/4**，batch Fable 為 **4/4**。針對目標消失情況進行小範圍修正與測試後，兩者皆通過 4/4，中位時間為 **5.42 s 與 7.23 s**，降低 25.1%。這些只是樣本很小、任務已熟悉的診斷結果，不能推廣成一般可靠性或模型能力的結論。所有失敗都保留在[瀏覽器報告](benchmarks/ego-upstream/README.md)中。

原版 fast-jev-compaction 在 12/12 次合成情境重播中保留必要事實，序列化資料大小的中位數減少 **31.6%**；但壓縮加後續執行共需 **2.87 s**，完整 context 則為 **2.66 s**。真實 Foreman/Codex 測試未改善正確性或速度：兩組都通過 2/2 項外部檢查，但 Foreman 只完成 1/2 個任務，而且耗時更長。這兩個 hook 都不會預設啟用。

[完整評估與限制](docs/upstream-evaluation.md) · [Ego adapter 設定](integrations/ego-browser/README.md)

<a id="existing-judgment-tools"></a>

### 既有判斷工具

需要 Node.js 22+。Repository 已包含可直接執行的 bundles，不必安裝 dependencies。Host 安裝另需 Python 3.11+ 與 POSIX shell；安裝程式已在 macOS 測試，未在 Windows 測試。

```sh
git clone https://github.com/WaynezProg/jev-kit.git
cd jev-kit
node scripts/configure-mcp.mjs
```

透過 `TYPESAFE_API_KEY` 或 `TYPESAFE_API_KEY_FILE` 提供 TypeSafe API key。建議使用 repository 外的私人檔案，權限設為 `0600`。對於不繼承 shell 環境變數的桌面 host，既有 fallback 路徑為 `~/.config/jev-benchmark/typesafe-api-key`。Key 不會放入 MCP 設定或工具參數。

```sh
# 指向你已安全填入 key 的檔案。
export TYPESAFE_API_KEY_FILE="$HOME/.config/jev-kit/typesafe-api-key"

# 離線 schema 驗證，不需要 key 或網路。
node dist/cli.js evidence --input examples/evidence.json --validate-only

# 真實 API 請求；建立新的結果紀錄檔。
node dist/cli.js evidence --input examples/evidence.json --output /tmp/jev-evidence-result.json
```

提供的任務文字會傳送給 TypeSafe 進行模型判斷。請只提供相關且已獲授權的資料，不要包含 credentials。本機引文不匹配，以及部分無候選項的檢查，不需要呼叫 API。

<a id="one-command-host-management"></a>

## 一個指令管理各平台

0.4.0 新增了支援平台的 native packages 與遷移功能。

適用於已安裝 Git、Node.js 22+、Python 3.11+ 的 macOS/Linux：

```sh
curl -fsSL https://raw.githubusercontent.com/WaynezProg/jev-kit/main/install.sh | sh
```

這會下載乾淨的 checkout，並安裝至 `~/.local/share/jev-kit`。安裝程式會偵測已存在設定檔的 host，以及既有的 Codex/Pi 目錄。API credentials 需另行設定。如要先檢查腳本，可先下載後再於本機執行；若已 clone repository，等效指令為：

```sh
./jev install
```

可以指定一個、多個 host，或明確為全部九個 host 建立整合：

```sh
./jev install --hosts claude,opencode
./jev install --hosts all
```

預設為 `--integration auto`，優先使用 host 的 native package；只有在 host CLI 不存在，或回報 native plugins 不可用時，才 fallback 至 MCP + Skill。`--integration native` 採嚴格模式，不支援時直接失敗，不會 fallback。`--integration mcp` 則明確選擇相容模式。已採用 native 整合的 host，須先移除該整合，才能改裝 MCP 模式。

| Host 選項 | 管理方式 |
|---|---|
| `codex` | 使用 Codex CLI，將 native plugin 安裝至專用的本機 marketplace |
| `claude` | 透過 Claude CLI 管理 native plugin |
| `opencode` | JavaScript native plugin 提供五個工具，搭配獨立 Skill |
| `muse` | Host 啟用 plugins 時使用 native plugin；否則明確 fallback 至 MCP + Skill |
| `grok` | 透過 Grok CLI 管理 native plugin |
| `gemini` | 透過 Gemini CLI 管理 native extension |
| `cursor` | 透過本機 native plugin 目錄載入套件 |
| `vscode` | 透過 `chat.pluginLocations` 註冊 Agent Plugin |
| `pi` | Native extension + Skill |

Native packages 會複製實際的 Skill 檔案，並透過絕對路徑使用共用 runtime launcher，不包含 API key。Codex 與 Pi 沿用既有 native 整合。管理器會檢查 native package 檔案、註冊資料、MCP 項目與 Skill links 是否屬於受管理的安裝；如果來源或檔案遭修改、或不屬於管理器，便停止操作，不會直接取代。Host 明確停用的政策不會被覆蓋。這是統一的生命週期管理器，不代表每個 host 都使用相同套件格式，或都已完成真實 UI 驗收。目前會安全拒絕 JSONC／含註解 JSON；使用管理器前，請先將該設定轉為嚴格 JSON。此 POSIX 安裝程式不支援 Windows。

安裝後，即使沒有原始 checkout，仍可使用管理器：

```sh
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev update
~/.local/share/jev-kit/jev uninstall --hosts muse
~/.local/share/jev-kit/jev uninstall
```

`update` 會將 GitHub 最新的 `main` 下載至暫存目錄，一併更新所有受管理的 host。暫存 clone 之後會移除，不執行 npm scripts，也不安裝 dependencies。使用 `--source /absolute/checkout` 可改用本機版本。切換共用 runtime 前，會先建立並檢查以內容雜湊識別的 release。`./jev update --source "$PWD"` 也會在同一次 transaction 中遷移所有既有 format-1 管理紀錄。若要從較新的 checkout 新增 host，請先更新共用 release。Codex 會透過 native CLI 更新 plugin cache。

`uninstall` 只移除紀錄中由管理器持有的設定項目、註冊資料、native package 檔案，以及 Skill／extension links。它保留其他設定、credentials、release snapshots、管理器本身與私人操作紀錄，不會用舊的整份備份覆寫使用者後來新增的設定。若受管理的項目、link 或檔案遭手動修改，會拒絕操作並回報衝突。一般寫入或 native CLI 失敗時會盡力回復；這不保證當機時的原子性，因此同時發生的外部修改或電腦當機，可能需要依操作紀錄修復。在所有整合都移除前，請保留 runtime 目錄。

`status` 回報設定是否偏離管理紀錄，以及已安裝的 release；它不是即時 MCP 連線測試。既有 session 可能保留舊工具，安裝、更新或移除後請重新啟動，並在 Codex 開啟新 task。

<a id="migrating-the-earlier-installer"></a>

### 從舊版安裝程式遷移

管理器不會自動接管既有設定。若曾使用舊的 `scripts/install-hosts.py`，可以遷移與指定來源目錄完全一致的項目：

```sh
./jev install --adopt-from /absolute/path/to/old/jev-kit
```

這也會將符合條件的 Codex Jev plugin 遷移至專用 managed marketplace，保留其他 plugins。任何不匹配都會在修改 host 設定前停止，舊來源目錄也會保留。若要從較新的 checkout 為既有受管理 runtime 新增 host，請先執行 `./jev update --source "$PWD"`。

私人備份與操作紀錄位於 `~/.local/share/jev-kit/receipts`；備份可能包含其他 server 的 credentials，請勿分享此目錄。各 host 的套件格式與驗收細節，請見 [native 整合說明](docs/native-integrations.md)。

<a id="compatibility-evidence"></a>

### 相容性驗證證據

九個 host 的生命週期測試涵蓋安裝、更新、選擇性移除、重複操作、format-1 遷移、手動修改、其他設定保留，以及 state 寫入失敗後的回復。在開發用 Mac 上，Claude 2.1.277、Gemini 0.60.0 與 Grok 1.0.34 都通過隔離環境的 CLI 生命週期測試，其安裝後 manifest 也完成 MCP `tools/list` 與離線引文檢查。OpenCode 1.18.31 在隔離 HOME 中通過 native host 工具探索測試：`/experimental/tool/ids` 與 catalog 列出全部五個 Jev tools 及 schemas；V2 目前僅有契約測試，尚無由 host 觸發的 Jev 呼叫驗證。Cursor 與 VS Code 通過 package、schema、config 與 MCP 檢查，但尚未完成 editor UI 載入驗收。Muse 1.3.0-R3401.1 在既有使用者環境中，通過 project-scope 安裝、實際改版更新、MCP 授權狀態回讀與移除；同一個 binary 在空白 HOME 會拒絕 plugins，因此由實際能力檢查決定是否 fallback。Pi 的實際 SDK 已載入工具並完成真實 Jev 呼叫。其他 host 版本的行為可能不同。

若要手動整合，`node scripts/configure-mcp.mjs` 會建立本機 `.mcp.json`，將其中的 command／args 複製至 host 設定即可。`node dist/cli.js serve` 使用 stdio，不是 HTTP。Pi extension 位於 `dist/pi-extension.js`，共用 Skill 位於 `skills/jev-kit/`。

安裝後可使用這樣的要求：

> 使用 jev-kit 將這些 issues 分成 bug、feature 或人工複核。保留原始 ID 與尚未確定的項目。

<a id="optional-candidate-reranking"></a>

## 可選的候選結果重排

將 ripgrep、code graph 或文件檢索的既有結果，連同查詢、穩定的候選 ID 與原文交給 `jev_rerank`。`top_k` 只選出排序前段供檢查，其餘 ID 與 hashes 都會保留在結果紀錄中。Source references 留在本機。

```sh
node dist/cli.js rerank --input examples/rerank.json --output /tmp/jev-rerank-result.json
```

只有一個候選項時，不呼叫 API。兩到三十個候選項會使用一個 score batch，送入模型的 UTF-8 state 上限為 160 KB。遇到無效回應、逾時或缺少 key 時，會保留原始順序，標記為 `partial` 並加上複核旗標。排序不保證正確性或相關性；請保留原文，必要時擴大檢索範圍。這是可選功能，因為下方實驗尚未證明能加快 coding 工作。

下一個能力實驗請見 [debug 證據與可執行驗證設計](https://github.com/WaynezProg/jev-kit/blob/main/docs/agent-capability-next.md)。這是待測試的設計，尚未實作或驗證。

<a id="code-search-reranking-results"></a>

## Code-search reranking 結果

我們測試一個在搜尋流程內運作的設計：先取回 30 個候選項，讓 Jev 在一次請求中為全部 30 個評分，再將重排後前五個候選項的原始程式碼片段交給主模型。Agent 不會為 Jev 重打或摘要來源。原始 IDs 與順序會保留；provider 失敗時會退回原排序，其餘候選項仍可供擴展。這是實驗性 adapter；`search_code`/`search_docs` 不是已發佈的 MCP tools。只量測了程式碼。

公開檢索測試從 CodeSearchNet Python 抽取 64 個查詢；移除 docstrings 與註解，並排除無法解析的項目後，共使用 989 個函式。全部 64 個都會評分，其中三個的目標不在 top30。標準答案（gold）只標示與查詢配對的函式，並非人類逐一判定過的完整相關結果。

| 指定流程 | 目標排名第一 | 目標在 top5 | 新增排序實際耗時中位數 |
|---|---:|---:|---:|
| 原始 BM25 排序 | 30/64 (46.9%) | 48/64 (75.0%) | 不呼叫模型 |
| Jev 批次 Score | 45/64 (70.3%) | 54/64 (84.4%) | 1.13 s |
| Fable low，以一次呼叫選出 top5 | 60/64 (93.8%) | 61/64 (95.3%) | 3.32 s |

Jev 相較 BM25 的 Top-1 提升 23.4 個百分點，但仍落後 Fable 23.4 個百分點。指定的 Jev 流程包含五次退回原始排序的情況；Fable 流程包含兩次因 session 額度限制、未取得模型回應而退回原排序的情況。時間包含 程序啟動與網路的額外耗時；取得有效回應時的 API 耗時中位數為 1.07 s（Jev，n=59）與 1.55 s（Fable，n=62）。**未通過事先訂定的檢索驗收門檻。**

接著以四個實驗分組對八個自行撰寫的 Python 修正任務各執行兩次。每個分組都通過 16/16 隱藏測試執行，但總實際耗時中位數為：BM25 top5 **4.42 s**、Jev top5 **5.25 s**、Fable-reranked top5 **7.64 s**、direct top30 **4.36 s**。八個目標原本都已在 BM25 top5，因此這是簡易的成本與退步風險篩檢。Jev 相較 full30 約減少 45% 主模型輸入，但 BM25 top5 已達到近似輸入量且更快。**未通過事先訂定的 coding 驗收門檻。**重複執行不會讓八個任務成為 16 個獨立任務。

另一項驗證修正後，對全部 64 個查詢重新執行，得到 64/64 有效 Jev 回應，但 Top-1 為 44/64、Recall@5 為 51/64。這個事後診斷不取代原始結果，也不能用來做條件一致的延遲比較。建議仍為 **可選的語意搜尋，不宣稱預設能加快 coding**。更廣泛的 repository 修復與文件檢索 仍未驗證。

[設計](benchmarks/rerank/DESIGN.md) · [重現方式](benchmarks/rerank/README.md) · [結果與失敗](benchmarks/rerank/results/RESULTS.md) · [數值捨入追蹤](benchmarks/rerank/results/ROUNDING.md) · [所有嘗試](benchmarks/rerank/results/runs.json)

<a id="where-jev-helped-bounded-browser-decision-loops"></a>

## Jev 有幫助之處：範圍受限的瀏覽器決策迴圈

目前最強的正向結果來自 **在瀏覽器工具內取代重複的主模型決策**。瀏覽器狀態與可執行選項已存在；Jev 選出下一個動作，由執行器點擊，再根據下一次觀察繼續決策。上層 coding agent 不必重寫工具參數，也不必審查每個中間選擇。

我們在實際 Ego Lite 中執行八個自行撰寫的本機瀏覽器操作精靈（四個目錄篩選、四個文件導覽任務），各重複三次。全部實驗分組使用相同的可見 DOM、執行器與最終路徑驗證器。Claude Fable 5.1 low 在每個任務維持一個持續運行的程序，避免每一步都重新啟動 CLI。

| 路徑 | 已驗證完成 | 單次嘗試實際耗時中位數 | 主模型呼叫次數 |
|---|---:|---:|---:|
| 本機關鍵字規則 | 6/24 | 0.65 s；成功案例為 3.19 s | 0 |
| 一次 LLM 語意規劃 + 固定比對器 | 21/24 | 7.43 s | 24 |
| Claude 每一步都選擇 | 24/24 | 8.40 s | 96 |
| Jev 每一步都選擇 | **24/24** | **3.82 s** | **0**；96 次 Jev 呼叫 |

Jev 路徑的任務實際耗時中位數比逐步 Claude **縮短 54.6%**，觀察到的完成率相同，並通過事先訂定的實用性驗收門檻。全部 96 次嘗試都有保留。沒有任何實驗分組點錯目標；規則與單次規劃組都會在無法處理時放棄選擇。兩者皆能完成的六對情況中，Jev 比 本機規則 慢。規劃組使用模型產生的語意詞彙加上比對器，並不代表所有可能的程式化自動操作策略。

這是正向的 **合成情境下的瀏覽器迴圈初步測試**，不是一般網頁操作可靠性的證明。八個不同任務都有固定選項，且 app 知道正確路線；未測試 文字輸入、真實網路競態、frames、登入與長程規劃。總實際耗時包含 模型初始化、決策、瀏覽器操作與最終驗證；不包括初始導覽與觀察。即使使用相同執行器，各實驗組的瀏覽器操作耗時仍不同，因此不能將整體收益完全歸因於 API 延遲。

候選產品是持續運行的瀏覽器子任務執行器：能以確定性規則處理時優先使用規則，需要語意判斷時才由 Jev 從受限選項中選擇，無法解決時明確交回上層。此混合 fallback 策略仍需驗證。**瀏覽器迴圈是 benchmark 程式碼，不是已發佈的 MCP 功能。**它與五個已發佈的判斷工具分開。

[測試方案與重現方式](benchmarks/browser-loop/README.md) · [完整結果與耗時拆解](benchmarks/browser-loop/results/RESULTS.md) · [每次嘗試](benchmarks/browser-loop/results/runs.json) · [既有瀏覽器專案比較](benchmarks/browser-loop/RESEARCH.md)

<a id="real-coding-agent-measurements-2026-09-20"></a>

## 真實 coding-agent 量測（2026-09-20）

使用真實、已通過驗證的 CLI／模型呼叫；每組 A/B 對照都使用相同的 18 筆 來源證據記錄 與 25 筆 issue 分流記錄。這些是 coding agents 內的受控判斷，**不是端到端 coding 生產力的 benchmark**。所有設定組合都要求 low effort，但不同 provider 的 effort 標籤並不等價。

完整研究包含 **六個 CLI、四個指定模型的 76 次 agent 執行**，以及 12 個獨立 Jev 批次。主要實驗批次 每個任務/實驗分組有三次重複（48 次執行）。以下正確標籤計數聚合同一筆記錄的重複觀察；時間為每批中位數。

| Host / 指定 model | 任務 | 正確標籤：direct → Jev | 秒數：direct → Jev | 有效 Jev 介入 |
|---|---|---:|---:|---:|
| Claude Code / Fable 5.1 | Issue routing | 75/75 → 75/75 | 6.31 → 23.19 | 3/3 |
| Claude Code / Fable 5.1 | Code evidence | 54/54 → 54/54 | 5.47 → 97.42 | 3/3 |
| Codex / GPT-5.6 Luna | Issue routing | 75/75 → 75/75 | 10.64 → 43.25 | 3/3 |
| Codex / GPT-5.6 Luna | Code evidence | 52/54 → 52/54 | 12.76 → 146.58 | 0/3 |
| Muse / Spark 1.3 Contributor | Issue routing | 75/75 → 75/75 | 32.10 → 37.43 | 3/3 |
| Muse / Spark 1.3 Contributor | Code evidence | 53/54 → 51/54 | 24.57 → 58.00 | 2/3 |
| Pi / GPT-5.6 Luna | Issue routing | 75/75 → 75/75 | 12.01 → 33.99 | 3/3 |
| Pi / GPT-5.6 Luna | Code evidence | 52/54 → 53/54 | 15.19 → 140.45 | 0/3 |

**標準 inline MCP/extension 路徑沒有顯示一致的正確率或速度優勢。**兩個實驗分組的所有主要 issue 分流答案 都正確。程式碼證據判斷的結果有好有壞。一個 Codex direct run 漏掉一筆記錄；缺失記錄視為錯誤。

12 次 inline code-evidence 介入中只有 5 次以保留輸入的狀態完成：六次呼叫改變了來源 bytes，另一次因 duplicate IDs 被拒絕。失敗/變更呼叫後的正確最終答案仍留在表中；它們不代表 Jev 有幫助。無害的項目重排與 absent/null optional quotes 會 normalize，但來源文字會精確比較。

Jev service work 通常每批約耗時 1–2 秒。其餘時間來自 host startup、argument generation 與 final review。有回報主模型用量的情況下，inline delegation 在這些工作負載增加了 input 與 output tokens。Muse 未報告主模型 token usage。Cached tokens 只計算一次，token 總數也不等於實際金額。

<a id="additional-hosts"></a>

### 其他 hosts

後續另一個 cohort 每個任務/實驗分組使用兩次重複（16 runs），不與主要 timing 合併。

| Host / 指定 model | 任務 | 正確標籤：direct → Jev | 秒數：direct → Jev | 有效 Jev 介入 |
|---|---|---:|---:|---:|
| Grok Build / Grok 4.6 | Issue routing | 50/50 → 50/50 | 18.70 → 47.74 | 2/2 |
| Grok Build / Grok 4.6 | Code evidence | 36/36 → 36/36 | 23.20 → 129.52 | 0/2 |
| OpenCode / GPT-5.6 Luna | Issue routing | 50/50 → 50/50 | 9.14 → 32.49 | 2/2 |
| OpenCode / GPT-5.6 Luna | Code evidence | 35/36 → 36/36 | 14.02 → 139.49 | 0/2 |

最初選定的 OpenCode Spark free endpoint 在 availability probe 回傳 HTTP 403。在開始任何有評分的 additional-host run 前，改選既有 OpenAI OAuth 的 Luna。失敗 probe 已[另行揭露](benchmarks/agent-ab/results/availability.json)。

<a id="experimental-fixed-file-input"></a>

### 實驗性的固定檔案輸入

另一項 12-run study 使用 empty-argument tool，讀取 runner 提供的精確輸入。它有新的 direct baselines、相同的 code-evidence records，且各重複三次。全部六次 file-tool calls 都保留輸入。

| Host / model | 正確標籤：direct → file tool | 秒數：direct → file tool |
|---|---:|---:|
| Codex / GPT-5.6 Luna | 54/54 → 51/54 | 13.43 → 23.45 |
| Pi / GPT-5.6 Luna | 51/54 → 51/54 | 16.15 → 15.94 |

File adapter 大幅降低先前階段看到的長 inline-call overhead，但未建立正確率提升或相較 direct judgment 的一般優勢。**此 adapter 是 benchmark code，不是已發佈 MCP feature。**既有 CLI 已接受 input files。

<a id="standalone-jev-and-batch-composition"></a>

### 獨立 Jev 執行與批次組成

在輸入已準備好且沒有 host/model review 時，Jev 很快。我們也以 agents 使用的精確 shuffled orders 重複 direct-engine check；輸入內容與 gold labels 固定。每個 cell 都有三次重複。

| Input order / task | 秒數中位數 | Raw correct | 未標記 correct | 留待 review |
|---|---:|---:|---:|---:|
| Grouped / code evidence | 0.90 | 54/54 | 50/50 | 4 |
| Grouped / issue routing | 1.06 | 75/75 | 60/60 | 15 |
| Shuffled / code evidence | 0.91 | 50/54 | 36/37 | 17 |
| Shuffled / issue routing | 1.14 | 75/75 | 60/60 | 15 |

**有一個錯誤的 code-evidence 判斷未被標記供 review。**Confidence 不是 correctness guarantee。Grouping/order 與 batch composition 在此小型探索性 follow-up 呈現不同結果；兩個 order cohorts 是依序而非 counterbalanced，因此不是受控的 causal estimate。Standalone 實際耗時不含輸入準備與 agent review，不能呈現為 completed-agent speedups。

<a id="how-to-use-these-findings"></a>

### 如何使用這些發現

- 優先使用已是 structured data 的批次。透過程式碼或 CLI 的 `--input` path 傳入原始文字，再 review unresolved rows。避免僅為呼叫 Jev 而付費讓 model 重寫長來源。
- 當額外檢查值得一次 tool round trip 時，對 compact、bounded judgments 使用 inline MCP。主模型已能妥善處理的例行問題可以留在 direct path。
- 依來源或任務測試將相關記錄分組；此 sample 顯示 batch composition 可能重要，但改善尚未普遍建立。
- 保持 Jev optional。File-based transport 是有前景的 integration improvement；較低 thinking levels、較佳 coding quality 與較低總 monetary cost 仍需獨立實驗。

完整[結果與 token tables](benchmarks/agent-ab/results/RESULTS.md)、[per-run data](benchmarks/agent-ab/results/runs.json)、[fixtures、methodology 與 reproduction commands](benchmarks/agent-ab/README.md)均公開。重複次數少、自行撰寫的 gold labels、不同 host contexts 與 provider caching 限制 generalization。這些 tests 未證明加入 Jev 可降低 model thinking level。

<a id="separate-model-tier-goals-quality-versus-speed"></a>

## 分開評估模型層級目標：品質與速度

後續研究使用同一個 Claude Code harness 與 48 個新撰寫的 source-bound cases，每個路徑三次重複。Programmatic input 避免昂貴的 LLM argument-copying step。Haiku 接收所有原始 evidence 加 advisory Jev judgments；Fable 的 cascade 只 review unresolved rows 與未標記 rows 中 deterministic 的 10% sample。總實際耗時包含 Jev 與主模型 review。

| 目標 / 比較 | 正確：direct → with Jev | 總秒數中位數：direct → with Jev | 結果 |
|---|---:|---:|---|
| Lower-tier quality: Haiku 4.5 | 140/144 → 140/144 | 73.42 → 87.67 | 無淨正確率提升；較慢 |
| Higher-tier speed: Fable 5.1 low | 142/144 → 139/144 | 9.65 → 6.35 | 耗時減少 34.2%，但品質退步 |

**兩條路徑都未通過各自事先訂定的驗收門檻。**Lower-tier assistance 至少需要 5 個百分點 gain；higher-tier routing 需要至少 30% 較低的實際耗時中位數，且沒有 aggregate 或 per-repeat 正確率損失，並且觀察到的未 review error 至多 1%。Fable cascade 中 112 個自動接受的 judgments 有兩個錯誤。Confidence 加上小型 audit 未能保留品質。

這是 48 個不同的自行撰寫案例，各重複三次，並非 144 個獨立 production cases。Haiku 的 native default 使用大量 thinking tokens；Fable 明確設為 low effort。Model tier 與 thinking level 是不同變數，這個實驗沒有顯示可降低 thinking levels。高 direct scores 也幾乎沒有空間顯示很大的 lower-tier improvement。Post-run review 找到一個含糊的 guarantee claim（case 42）。事後排除它後，Haiku 在有或無 Jev 時皆為 140/141，而 Fable 為 141/141 → 139/141；結論不變。原始 key 與 scores 都有保留，這個排除明確屬於 post-hoc。完整 [protocol](benchmarks/model-tiers/README.md)、[results](benchmarks/model-tiers/results/RESULTS.md) 與 [per-run predictions](benchmarks/model-tiers/results/runs.json) 均公開。

另一項[24-run 真實 GitHub issue study](benchmarks/cascade/README.md) 比較 direct LLM、rules-first、Jev-first 與 rules-plus-Jev paths。沒有 Jev path 通過相對兩個 no-Jev baselines 的 combined gate。既有 GitHub tags 證實只是弱 reference labels，而非可靠 semantic answers，因此那些 agreement scores 不得呈現為 decision accuracy。一個失敗的 Jev API call 回退到 main-model review，並保留在結果中。

實務上的下一步，是以獨立 adjudication 的 production sample 測試 optional batch classifier 或 ranker，並使用低成本 rules baseline 和明確 error tolerance。這些結果不支持預設自動接受 evidence claims、universal installation 或一般性的 coding-productivity claim。實驗 runners 不改變已發佈 plugin/MCP behavior。

<a id="results-and-limits"></a>

## 結果與限制

- 檢查 `status` 與每一項的 `requires_review`。標記為待複核的暫定答案，仍屬未解決項目。
- 來源支持某項主張，不代表已獨立證明主張為真。Confidence 也不保證正確。
- 無效的 provider 回應會在轉換成判斷結果前被拒絕。來源有反提示注入的框架設計，但這不是安全邊界，也不保證能抵抗 prompt injection。
- 不提供 approval gate、任意指令執行、自動 context pruning，或修改模型設定的功能。
- CLI exit code `0` 表示處理完成，`3` 表示需要複核，`2` 表示輸入無效或服務／驗證失敗。Exit code `0` 不代表任務已驗收，或主張為真。
- 結果紀錄會建立為新的 `0600` 檔案，包含 ID、來源／主張 hashes、判斷結果、usage、實際使用的 model 與時間。完整來源留在原始輸入中，請保留以便重播驗證。
- TypeSafe 請求使用固定 endpoint、15 秒 timeout，且不會自動 retry。API 可用性與費用由外部服務決定。

請見[輸入 schemas 與範例](skills/jev-kit/references/inputs.md)，以及 [agent Skill](skills/jev-kit/SKILL.md)。

<a id="development-and-checks"></a>

## 開發與檢查

```sh
npm ci --ignore-scripts
npm run build
npm test
python3 -m unittest discover -s test -p '*_test.py'
```

離線測試涵蓋格式錯誤的回應、來源與引文綁定、批次處理、候選擷取、決策衝突、CLI 結果紀錄、獨立 bundles、MCP 契約、Pi 註冊，以及 host 設定保留。另有需要 API key 的 live smoke test，會呼叫全部五個工具：

```sh
node scripts/smoke.mjs /tmp/new-jev-live-smoke.json
```

測試只能證明已涵蓋的行為，不能證明對任意任務的語意可靠性。Repository 只包含公開 benchmark fixtures 與去識別化的指標，不包含私人 agent logs 或本機安裝操作紀錄。

<a id="license-and-provenance"></a>

## 授權與來源

本整合採用 MIT 授權。Vendored components 保留上游授權；確切的 upstream commits、調整內容與 dependency notices 記錄於 [THIRD_PARTY.md](THIRD_PARTY.md) 與 `vendor/`。`jev-use` 固定使用收錄於 repository 的 source／build，不依賴整合當時無法取得的 npm 版本。
