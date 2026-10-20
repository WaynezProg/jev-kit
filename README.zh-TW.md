# Jev Kit

[English](README.md) | **繁體中文**

以 [TypeSafe Jev](https://typesafe.ai/) 為 coding agent 提供批次判斷，以及實驗性的 Ego Lite 瀏覽器自動操作。

## 功能

### 批次語意判斷

整合 `jev-use` 與 `jev-mcp` 的引擎和任務模式，加入本機來源與引文驗證。直接傳入既有文字或工具輸出，不必先讓另一個 LLM 摘要。

| 工具 | 能做什麼 | 使用情境 |
|---|---|---|
| `jev_evidence` | 每份輸入最多 256 組主張與來源；本機核對精確引文，回傳支持、矛盾、證據不足或待審查 | 核對報告引用、發布說明，或比對回答與 logs／文件 |
| `jev_classify` | 將最多 64 筆資料分到 2–32 個自訂類別，可設人工審查類別 | Issue 分流、回饋歸類、工具輸出分類 |
| `jev_extract` | 先用 regex 找候選，再依語意選出原文中的精確值；最多 8 個欄位 | 從多個版本號、日期或識別碼中找出需要的值 |
| `jev_decide` | 依優先條件比較 2–6 個已知方案，檢查最多 3 項需求，標記缺失或衝突的證據 | 根據已知利弊選擇實作方案或處理路徑 |
| `jev_rerank` | 重排最多 30 筆既有搜尋結果，選出優先閱讀項目並保留其餘所有 ID | 決定先看哪些程式碼片段或文件段落 |

這些工具提供判斷建議。來源與選項由呼叫端提供，不會自行搜尋缺少的證據或執行選出的方案。[輸入 schemas 與範例](skills/jev-kit/references/inputs.md)。

建議把同類資料一次提交，使用固定分類與問題。0.4.1 版每批維持最多 8 筆、每次工具呼叫最多同時處理 4 批，依長度拆分完整 evidence，並讓每批相同來源只傳一次。已有本機 JSON 時直接使用檔案 CLI，避免模型重新抄寫來源。少量來源已在主模型上下文時，兩種 host 的實測都是直接推理較快；也觀察到高信心錯誤，因此只複核 review 標記不能可靠地維持正確率。

#### 圖片輸入——實驗性

`jev_evidence`、`jev_classify`、`jev_decide` 的項目（evidence items、classify items、decide candidates）可加 `images: [{"path": "/absolute/file.png"}]`，每項最多 4 張；有圖片時 classify 的 `text`、evidence 的 `source_text` 可省略。只支援 PNG、JPEG，依檔案內容判斷格式；單張 ≤8 MiB、每邊 280–1568 px；每個 request 合計 ≤20 MiB、≤16 張。分批時圖片與所屬項目同批送出。jev-kit 自動加上必要的 `TypeSafe-Danger-Zone-Images` header。Receipt 只記圖片數量與 SHA-256，不含圖片內容。`--validate-only` 可離線檢查檔案。TypeSafe 圖片功能仍是實驗性，格式、限制與準確度可能變動。Request 使用 `jev-1.14.0`（可用 `JEV_KIT_MODEL` 覆寫）。

### Ego Lite 瀏覽器自動操作——實驗性

提供目標、起始網址與預期結果，由固定版本的 `jev-ultrafast` policy 選擇動作，再交給 Ego Lite 執行。

- 點擊控制項、填寫欄位、選擇選項與切換頁面，用於搜尋、表單與文章查找；欄位文字由設定的 text model 或 Claude CLI helper 產生。
- 操作前檢查目標身分、可見性與頁面狀態；遇到支援處理的過期目標錯誤，重新觀察與選擇動作。
- 獨立核對預期 URL 或頁面文字，不只依賴 Jev 回報完成。
- 可設允許的網站 origins、步數與時間預算；觀察到 popup／dialog 時停止並交回呼叫端，動作與結果寫入私人 receipt。

```sh
~/.local/share/jev-kit/jev browser --input job.json
```

需另行設定 Ego Lite 與 upstream。時間限制在操作間檢查；登入、交易批准、frames、shadow DOM 與 popup 接續操作不在已驗證範圍內。[設定方式與 job 範例](integrations/ego-browser/README.md)。

### Agent 整合與安裝管理

- **Native 整合、MCP 與 Skill**：讓支援的工具使用同一組五個判斷工具；附帶 Skill 說明適用時機與不確定結果的處理方式。
- **CLI 批次處理**：從 JSON 檔案或 stdin 讀取資料，回傳結構化 JSON，也可用 `--validate-only` 離線檢查輸入。
- **共用安裝管理器**：偵測 host、選擇整合方式、一起更新受管理的工具、檢查設定是否被改動，並在保留其他設定的前提下個別移除整合。

安裝後由 agent 選擇呼叫工具，不會自動加入權限 hooks、context compaction 或模型路由。

### 審查與結果追蹤

低信心、資料不完整或回應無效的判斷會標記待審查；rerank 失敗時保留候選原始順序。本機引文檢查、沒有擷取候選或只有一筆排序候選時，可略過模型呼叫。

結果包含審查標記、耗時，以及模型回應提供的實際模型與 usage；依來源判斷的工具另保留 ID／來源參照與 hashes，方便核對原始輸入。CLI 可將結果寫成新的私人 receipt，不覆蓋既有檔案。

## 安裝

需要 Git、Node.js 22+、Python 3.11+ 與 POSIX shell。Host 安裝已在 macOS 實測，不支援 Windows。

```sh
curl -fsSL https://raw.githubusercontent.com/WaynezProg/jev-kit/main/install.sh | sh
```

安裝器會偵測已設定的 **Codex、Claude Code、OpenCode、Muse、Grok、Gemini CLI、Cursor、VS Code 與 Pi**。優先使用 native 整合，支援時可退回 MCP + Skill。

將 TypeSafe API key 存入 `~/.config/jev-benchmark/typesafe-api-key`，檔案權限設為 `0600`；也可在 host 環境設定 `TYPESAFE_API_KEY`／`TYPESAFE_API_KEY_FILE`。安裝後重啟工具，Codex 另開新 task。

```sh
# 查看狀態、更新、移除
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev update
~/.local/share/jev-kit/jev uninstall
```

[各工具設定與驗證範圍](docs/native-integrations.md)。Cursor／VS Code 尚未驗證 editor UI discovery；OpenCode V2 僅有 contract tests。

## 測試效果

以下為實際工作流程的測量。瀏覽器對照組是**每次最多規劃五個動作的 Fable 5.1 low**，時間皆為中位數。

| 測試情境 | 結果 |
|---|---|
| 批次排程：32 筆雙語資料，各 3 次 | Evidence **1.106 → 0.315 秒**，classification **1.072 → 0.331 秒**；配對答案標籤不變。擴成每批 32 筆會降低準確率。這是判斷階段的耗時，不是整個 agent 的耗時 |
| 共用來源 evidence：8 個主張，配對 CLI 各 3 次 | Input tokens **9,855 → 4,633**，減少 **53%**；兩版每次都答對 **8/8**。節省幅度取決於來源重複程度 |
| 新瀏覽器任務：3 項，各 2 次 | Jev **4/6**，兩種 Fable policy 都 **6/6**。Jev 在可見語意選項較快（**4.17 vs 8.29 秒**）；文字輸入由 Fable batch 較快，Jev 在兩次動態相依欄位測試均停住 |
| 兩種 host 的 evidence 流程：18 筆，各 2 次 | 直接使用 Codex/Luna、Claude/Fable 都是 **36/36**。Jev 輔助較慢；只複核標記項目分別降為 **33/36、35/36**。此項比較使用凍結的優化前 runtime |
| Ego Lite：3 個表單任務，各跑 2 次 | 兩組皆通過 6/6；Jev **6.35 秒**，Fable **7.30 秒**，耗時減少 13.0% |
| Ego Lite：2 個 Wikipedia 任務，各跑 2 次，修正後重測 | 兩組皆通過 4/4；Jev **5.42 秒**，Fable **7.23 秒**，耗時減少 25.1% |
| 程式碼搜尋：64 個 queries | 配對目標排第一的比例：BM25 **46.9%**、Jev **70.3%**、Fable **93.8%**。另一次修復測試中，Jev 比 BM25 慢：**5.25 秒 vs 4.42 秒** |
| 模型輔助 | Haiku 準確率沒有提升；Fable 分流雖較快，但準確率下降。尚未證明可降低所需 thinking level |

新測試以下的早期瀏覽器數據使用熟悉任務，Wikipedia 在修正前只通過 3/4。新的動態相依欄位失敗，讓適用範圍縮小為已觀察到的控制項與少量文字生成。樣本仍少，不能宣稱普遍加速 coding、降低成本或可靠地降低 thinking level。

[瀏覽器數據](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/ego-upstream/README.md) · [搜尋與修復數據](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/rerank/results/RESULTS.md) · [模型比較](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/model-tiers/results/RESULTS.md) — 連結固定於測試當時的歷史版本。

0.4.1 本機工程驗證：2026-09-21 通過 **51 個 JavaScript + 36 個 Python 測試**，涵蓋並行失敗隔離、固定結果順序、來源綁定與超大輸入處理。[最近發布的 macOS／Linux CI](https://github.com/WaynezProg/jev-kit/actions/runs/35521891562) 對應較早版本，不代表本次本機修改已通過遠端 CI。工程檢查與上述任務效果分開計算。
