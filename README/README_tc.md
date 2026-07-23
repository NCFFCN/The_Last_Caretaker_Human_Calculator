[English](../README.md) | 繁體中文 | [简体中文](README_sc.md)

# The Last Caretaker Human 計算器
一個用於解決《The Last Caretaker》中職業組合問題的命令列工具。它使用整數線性最佳化模型來找出可達成目標職業的有效物品組合，同時有效避免不必要的附帶職業。

## 專案結構
- `main.py`：入口點與主要 CLI 迴圈，負責處理使用者輸入。
- `core.py`：包含計算器的核心邏輯、最佳化模型與搜尋演算法。
- `managers.py`：處理檔案載入、資料處理與狀態管理（例如 Inventory、Humans）。
- `models.py`：定義整個應用程式中使用的資料結構與類別。
- `translations.py`：管理多語言支援（英文、繁體中文、簡體中文）。
- `constants.py`：儲存全域常數。

## 使用要求
使用 `pip` 安裝所需的 Python 套件：

```bash
pip install -r requirements.txt
```

*若 `requirements.txt` 不可用，請確保已安裝 `pandas`、`numpy` 與 `scipy` 或 `pulp`，視最佳化後端而定。*

## 資料檔案 (CSV)
計算器運作前需要特定的 CSV 檔案，請放置於對應的資料資料夾中：
- 人類資料（`Data/Human.csv`）
- 食物資料（`Data/Food.csv`）
- 記憶資料（`Data/Memory.csv`）
- 庫存資料（`Data/Inventory/Inventory_template.csv`）

您可以在執行期間使用 `set` 指令動態更新來源資料夾或檔案。這些設定會被永久儲存在 `settings.json` 中。

> *注意：若您在執行期間以外手動變更路徑，請在啟動計算器前先編輯 `settings.json`。*

## 使用方式
透過以下方式執行應用程式：

```bash
python main.py
```

## 核心指令
在提示字元處，您可以：
- 輸入職業名稱來搜尋職業組合。可使用逗號（,）在同一次會話中輸入多個職業。
- 輸入 `list` 以顯示所有可用職業。
- 輸入 `reload` 以重新載入 CSV 檔案。
- 輸入 `set -<category>` 以開啟指定類別的檔案選擇輔助工具（`-human`、`-food`、`-memory` 或 `-inventory`）。
- 輸入 `h` 或 `help` 以查看所有指令。
- 輸入 `q` 或 `quit` 以離開程式。

> *提示：`set` 指令的第一個 `<category>` 不需要加上連字號 `-`，但後續的類別則需要。*

### 範例
#### 職業名稱
```text
Enter Profession (or 'help' to see all command): Guard,Station Protector
```

#### 「Set」指令
```text
Enter Profession (or 'help' to see all command): set inventory
```

```text
Enter Profession (or 'help' to see all command): set inventory Inventory2
```

```text
Enter Profession (or 'help' to see all command): set inventory Inventory2/Inventory_own.csv
```

```text
Enter Profession (or 'help' to see all command): set inventory -human -food
```

> *注意：職業名稱應以 `settings.json` 中設定的顯示語言（英文、繁體中文或簡體中文）輸入。*

## 獨立計算模式
預設情況下，當您輸入多個目標（例如 `Guard, Station Protector`）時，計算器會使用「扣減式庫存」方法。這表示如果第一個目標消耗了庫存中的某些物品，這些物品會被標記為已使用，並且在同一個會話中不會再提供給後續目標使用。這會模擬真實世界中資源有限的情境。如果您想要讓每個目標「獨立」計算（也就是假設每次計算都使用新的庫存），請在輸入前加上 `?`。

### 範例
```text
Enter Profession (or 'help' to see all command): ?Guard, Station Protector
```

## 各委員會所需專業人員
甲板作業
```text
Maintenance Engineer, Basic Supplier, Nutrient Handler, Door Jammer
```

棲息地照護
```text
Room Supervisor, Health Assistant, Teacher, Lab Technician
```

交通與配送
```text
System Engineer, Distributor, Growth Specialist, Guard
```

能源與安全
```text
Energy Engineer, Resource Director, Station Quartermaster, Station Protector
```

認知韌性
```text
Theoretical Scientist, Neuro Specialist, Professor, Star Analyzer
```

文化與記憶
```text
Visual Technician, Sculptor, Cultural Archivist, Manual Holder
```

治理與物流
```text
Settlement Governor, Logistics High Command, Biosphere Director, Guardian of Humanity
```

深度系統
```text
Quantum Engineer, Quantum Physicist, Neural Architect, Sustenance Architect
```

意義與前沿
```text
Existential Expressionist, Frontier Explorer, Mission Seeker, Colonel of Humanity
```

野外延續
```text
Field Research Scientist, Existential Chancellor, Station Roamer, Doctor
```

## 搜尋邏輯
求解器的硬性條件：
1. 不能創造不同類別的職業。

求解器優先順序：
1. 自訂物品優先權（例如：Teddy Bear = 1, Ash Book = 3）
2. 總物品數量
3. 剩餘數值超過總數
4. 若上述三項優先順序的解法分數相同，求解器會略微偏好食物類別中自訂優先權為 1 的方案。

## 全域設定 (`settings.json`)
程式行為由 `settings.json` 控制：
- `lang`：語言偏好（`en`、`tc`、`sc`）。
- `unlimited_search`：切換搜尋組合的上限。（預設：`false`）
- `max_attempts`：最大搜尋迭代次數。（預設：`25`）
- `unlimited_inventory`：是否不限制庫存。（預設：`false`）
- `deduct_inventory`：是否在計算後自動從庫存中扣除已使用物品。（預設：`false`）
- `save_as_new_file`：是否將庫存更新儲存為新檔案，而不是覆寫原檔。（預設：`true`）
- `show_summary`：是否在成功計算後顯示摘要區塊。（預設：`true`）
- `summary_items_per_row`：定義摘要中每列顯示多少個物品區塊。（預設：`4`）
- `data`：定義 `human`、`food`、`memory` 與 `inventory` CSV 檔案的預設路徑。
- `log_mode`：啟用或停用將輸出匯出至日誌。（預設：`true`）
- `log_folder`：定義日誌檔案的預設資料夾路徑。

> *注意：如果 `unlimited_search = true`，自訂優先順序仍使用 `settings.json` 檔案中 `data` 清單中的檔案。請在啟動程式前確認自訂優先順序是否符合您的需求。*

## 語言支援
顯示語言由 `settings.json` 中的 `lang` 設定控制：
- `"en"` 表示英文。
- `"tc"` 表示繁體中文。
- `"sc"` 表示簡體中文。

所有翻譯文字都定義在 `translations.py` 中。

## 注意
- 求解器僅會考慮庫存資料檔案中實際存在的物品，請選擇正確的庫存檔案。
- 統計欄位由 `ALL_STAT_COLS` 定義，因此 CSV 標頭與程式碼必須保持一致，才能正確比對。
- 若下列條件成立，它會自動重新載入最新庫存：
  1. `deduct_inventory = true`
  2. `unlimited_inventory = false`
  3. 不在獨立計算模式下
  4. 有成功目標