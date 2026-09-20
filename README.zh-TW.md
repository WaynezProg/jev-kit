# Jev Kit

[English](README.md) | **繁體中文**

以 [TypeSafe Jev](https://typesafe.ai/) 為 coding agent 提供批次判斷，以及實驗性的 Ego Lite 瀏覽器自動操作。

## 功能

| 工具 | 用途 |
|---|---|
| `jev_evidence` | 比對主張與來源，核對精確引文 |
| `jev_classify` | 依共同分類表批次分類資料 |
| `jev_extract` | 從 regex 候選中選出精確值 |
| `jev_decide` | 根據提供的證據比較 2–6 個選項 |
| `jev_rerank` | 重排最多 30 筆既有搜尋結果，保留所有 ID |
| Ego Lite browser | 由 Jev 選擇頁面操作，再獨立檢查指定結果；實驗性功能 |

直接傳入既有來源文字，不確定的結果交回 agent 審查。

[工具輸入與範例](skills/jev-kit/references/inputs.md) · [Ego Lite 設定](integrations/ego-browser/README.md)

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
