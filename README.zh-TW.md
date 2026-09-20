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
| Ego Lite：3 個表單任務，各跑 2 次 | 兩組皆通過 6/6；Jev **6.35 秒**，Fable **7.30 秒**，耗時減少 13.0% |
| Ego Lite：2 個 Wikipedia 任務，各跑 2 次，修正後重測 | 兩組皆通過 4/4；Jev **5.42 秒**，Fable **7.23 秒**，耗時減少 25.1% |
| 程式碼搜尋：64 個 queries | 配對目標排第一的比例：BM25 **46.9%**、Jev **70.3%**、Fable **93.8%**。另一次修復測試中，Jev 比 BM25 慢：**5.25 秒 vs 4.42 秒** |
| 模型輔助 | Haiku 準確率沒有提升；Fable 分流雖較快，但準確率下降。尚未證明可降低所需 thinking level |

瀏覽器樣本少且任務已熟悉，Wikipedia 在修正前只通過 3/4。目前結果支持繼續試用瀏覽器情境，尚不能宣稱普遍加速 coding 或降低成本。

[瀏覽器數據](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/ego-upstream/README.md) · [搜尋與修復數據](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/rerank/results/RESULTS.md) · [模型比較](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/model-tiers/results/RESULTS.md) — 連結固定於測試當時的歷史版本。

工程驗證：2026-09-21 通過 **47 個 JavaScript + 36 個 Python 測試**及 [macOS／Linux CI](https://github.com/WaynezProg/jev-kit/actions/runs/35521891562)。這些驗證實作品質，與上述任務效果分開計算。
