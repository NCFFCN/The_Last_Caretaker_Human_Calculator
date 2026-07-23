[English](../README.md) | [繁體中文](README_tc.md) | 简体中文

# The Last Caretaker Human Calculator
一个用于解决《The Last Caretaker》中职业组合问题的命令行工具。它使用整数线性优化模型来找出可达成目标职业的有效物品组合，同时有效避免不必要的附带职业。

## 项目结构
- `main.py`：入口点与主要 CLI 循环，负责处理用户输入。
- `core.py`：包含计算器的核心逻辑、优化模型与搜索算法。
- `managers.py`：处理文件加载、数据处理与状态管理（例如 Inventory、Humans）。
- `models.py`：定义整个应用中使用的数据结构与类。
- `translations.py`：管理多语言支持（英文、繁体中文、简体中文）。
- `constants.py`：存储全局常量。

## 使用要求
使用 `pip` 安装所需的 Python 包：

```bash
pip install -r requirements.txt
```

*(如果 `requirements.txt` 不可用，请确保已安装 `pandas`、`numpy` 与 `scipy` 或 `pulp`，具体取决于优化后端。)*

## 数据文件（CSV）
計算器运行前需要特定的 CSV 文件，请放置在对应的数据目录中：
- 人类数据（`Data/Human.csv`）
- 食物数据（`Data/Food.csv`）
- 记忆数据（`Data/Memory.csv`）
- 库存数据（`Data/Inventory/Inventory_template.csv`）

您可以在运行期间使用 `set` 命令动态更新来源目录或文件。这些设置会被永久保存到 `settings.json` 中。

> *注意：如果您在运行期间之外手动更改路径，请在启动計算器前先编辑 `settings.json`。*

## 使用方式
通过以下方式运行应用程序：

```bash
python main.py
```

## 核心命令
在提示符下，您可以：
- 输入职业名称来搜索职业组合。可以使用逗号（,）在同一次会话中输入多个职业。
- 输入 `list` 以显示所有可用职业。
- 输入 `reload` 以重新加载 CSV 文件。
- 输入 `set -<category>` 以打开指定类别的文件选择辅助工具（`-human`、`-food`、`-memory` 或 `-inventory`）。
- 输入 `h` 或 `help` 以查看所有命令。
- 输入 `q` 或 `quit` 以退出程序。

> *提示：`set` 命令的第一个 `<category>` 不需要加上连字符 `-`，但后续类别需要。*

### 示例
#### 职业名称
```text
Enter Profession (or 'help' to see all command): Guard,Station Protector
```

#### 「Set」命令
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

> *注意：职业名称应以 `settings.json` 中设置的显示语言（英文、繁体中文或简体中文）输入。*

## 独立计算模式
默认情况下，当您输入多个目标（例如 `Guard, Station Protector`）时，計算器会使用“扣减式库存”方法。这表示如果第一个目标消耗了库存中的某些物品，这些物品会被标记为已使用，并且在同一个会话中不会再提供给后续目标使用。这会模拟真实世界中资源有限的情况。如果您想让每个目标“独立”计算（也就是假设每次计算都使用新的库存），请在输入前加上 `?`。

#### 示例
```text
Enter Profession (or 'help' to see all command): ?Guard, Station Protector
```

## 各委员会所需专业人员
甲板作业
```text
Maintenance Engineer, Basic Supplier, Nutrient Handler, Door Jammer
```

栖息地照护
```text
Room Supervisor, Health Assistant, Teacher, Lab Technician
```

交通与配送
```text
System Engineer, Distributor, Growth Specialist, Guard
```

能源与安全
```text
Energy Engineer, Resource Director, Station Quartermaster, Station Protector
```

认知韧性
```text
Theoretical Scientist, Neuro Specialist, Professor, Star Analyzer
```

文化与记忆
```text
Visual Technician, Sculptor, Cultural Archivist, Manual Holder
```

治理与物流
```text
Settlement Governor, Logistics High Command, Biosphere Director, Guardian of Humanity
```

深度系统
```text
Quantum Engineer, Quantum Physicist, Neural Architect, Sustenance Architect
```

意义与前沿
```text
Existential Expressionist, Frontier Explorer, Mission Seeker, Colonel of Humanity
```

野外延续
```text
Field Research Scientist, Existential Chancellor, Station Roamer, Doctor
```

## 搜索逻辑
求解器的硬性约束：
1. 不能创建不同类别的职业。

求解器优先顺序：
1. 自定义物品优先权（例如：Teddy Bear = 1、Ash Book = 3）
2. 总物品数量
3. 剩余数值超过总数
4. 如果上述三项优先顺序的解法分数相同，求解器会略微偏好食物类别中自定义优先权为 1 的方案。

## 全局设置（`settings.json`）

应用行为由 `settings.json` 控制：
- `lang`：语言偏好（`en`、`tc`、`sc`）。
- `unlimited_search`：切换搜索组合的上限。（默认：`false`）
- `max_attempts`：最大搜索迭代次数。（默认：`25`）
- `unlimited_inventory`：是否不限制库存。（默认：`false`）
- `deduct_inventory`：是否在计算后自动从库存中扣除已使用物品。（默认：`false`）
- `save_as_new_file`：是否将库存更新保存为新文件，而不是覆盖原文件。（默认：`true`）
- `show_summary`：是否在成功计算后显示摘要区块。（默认：`true`）
- `summary_items_per_row`：定义摘要中每行显示多少个物品区块。（默认：`4`）
- `data`：定义 `human`、`food`、`memory` 与 `inventory` CSV 文件的默认路径。
- `log_mode`：启用或禁用将输出导出至日志。（默认：`true`）
- `log_folder`：定义日志文件的默认文件夹路径。

> *注意：如果 `unlimited_search = true`，自订优先顺序仍使用 `settings.json` 文件中 `data` 清单中的文件。请在启动应用前确认自订优先顺序是否符合您的需求。*

## 语言支持

显示语言由 `settings.json` 中的 `lang` 设置控制：
- `"en"` 表示英文。
- `"tc"` 表示繁体中文。
- `"sc"` 表示简体中文。

所有翻译文本都定义在 `translations.py` 中。

## 注意

- 求解器仅会考虑库存数据文件中实际存在的物品，请选择正确的库存文件。
- 统计字段由 `ALL_STAT_COLS` 定义，因此 CSV 标头与代码必须保持一致，才能正确匹配。
- 如果下列条件成立，它会自动重新加载最新库存：
  1. `deduct_inventory = True`
  2. `unlimited_inventory = False`
  3. 不在独立计算模式下
  4. 有成功目标