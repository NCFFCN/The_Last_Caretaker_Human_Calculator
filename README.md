# The Last Caretaker Human Calculator

A small CLI tool for solving lineage-style profession combinations in **The Last Caretaker**. It reads profession, food, memory, and inventory CSV files, then uses an integer linear optimization model to search for a valid item combination for a target profession while avoiding unwanted collateral professions.

## CSV Files

- Human data: `Human.csv` or `human.csv` or `Humans.csv` or `humans.csv`.
- Food data: `Food.csv` or `food.csv` or `Foods.csv` or `foods.csv`.
- Memory data: `Memory.csv` or `memory.csv` or `Memories.csv` or `memories.csv`.
- Inventory data: `Inventory.csv` or `inventory.csv` or `Inventories.csv` or `inventories.csv`.

## Requirements

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The current dependency list includes `numpy`, `pandas`, and `pulp`.

## Usage

Run the calculator from the project folder:

```bash
python main.py
```

At the prompt, you can:

- Enter a profession name such as `Guardian of Humanity T4` or `Guardian of Humanity`.
- Enter multiple targets separated by commas, for example: `Guard T2, Site Guardian T3` or `Guard, Site Guardian`.
- Type `list` to show all available professions grouped by category.
- Type `q` to quit the program.
- Type `reload` to reload CSV files
- Type `help` to see full command.

Example:

```
Enter Target Profession (or 'help' to see full command): Guard T2
```
```
Enter Target Profession (or 'help' to see full command): Guard, Site Guardian
```
```
請輸入目標職業 (或輸入「list」查看全部, 輸入「q」退出): 量子工程師
```

Note: Profession name should be entered in the display language set in `main.py` (English, Traditional Chinese, or Simplified Chinese).

### Independent Calculation Mode (Temporary Inventory)

By default, when you enter multiple targets (e.g., `Guard T2, Site Guardian`), the tool uses a **deductive inventory** approach. This means that if the first target consumes certain items from your inventory, those items are marked as used and are not available for subsequent targets in the same session. This simulates a real-world scenario where you have a limited pool of resources.

If you want to calculate each target **independently** (i.e., assuming an unlimited or fresh inventory for each calculation), prefix your input with a question mark `?`.

Example:
```
Enter Target Profession (or 'help' to see full command): ?Guard T2, Site Guardian
```
In this mode, the solver will ignore the current inventory state and calculate the optimal combination for each target as if all items were available, without deducting them for the next target.

## The professions needed by each committee

Deck operations
```
Maintenance Engineer, Basic Supplier, Nutrient Handler, Door Jammer
```

Habitat Care
```
Room Supervisor, Health Assistant, Teacher, Lab Technician
```

Transit & Distribution
```
System Engineer, Distributor, Growth Specialist, Guard
```

Power & Security
```
Energy Engineer, Resource Director, Station Quartermaster, Station Protector
```

Cognitive Resilience
```
Theoretical Scientist, Neuro Specialist, Professor, Star Analyzer
```

Culture & Memory
```
Visual Technician, Sculptor, Cultural Archivist, Manual Holder
```

Governance & Logistics
```
Settlement Governor, Logistics High Command, Biosphere Director, Guardian of Humanity
```

Deep Systems
```
Quantum Engineer, Quantum Physicist, Neural Architect, Sustenance Architect
```

Meaning & Frontier
```
Existential Expressionist, Frontier Explorer, Mission Seeker, Colonel of Humanity
```

Field Continuance
```
Field Research Scientist, Existential Chancellor, Station Roamer, Doctor
```

## Search logic

The solver prioritizes:

1. Custom item priority (like Ash Book = 3 and Teddy Bear = 1)
2. Total items count
3. Total excess stats
4. Total rejected collateral professions

## Search Settings

The search behavior is controlled directly in `main.py`:

- `UNLIMITED_SEARCH = False` means the solver stops after a limited number of attempts.
- `MAX_ATTEMPTS = 20` defines the maximum number of search attempts when unlimited search is disabled.
- `PRIORITY_WEIGHT` and `ITEM_COUNT_WEIGHT` control how strongly the solver prefers lower-priority-cost and lower-item-count solutions.
- `BIG_M` is used for exclusion constraints when rejecting failed collateral-profession combinations.

## Inventory Settings

The inventory update behavior is also controlled in `main.py`:

- `DEDUCT_INVENTORY = False` means successful combinations do not modify the inventory file.
- `SAVE_AS_NEW_FILE = True` means that when inventory deduction is enabled, the updated inventory is saved to a new timestamped CSV file instead of overwriting the original file.

The loader also supports filename variations such as `Inventory.csv` and `inventory.csv`, as well as similar case variations for other CSV inputs.

## Language Support

The display language is controlled by the `LANG` setting in `main.py`:

- `"en"` for English.
- `"tc"` for Traditional Chinese.
- `"sc"` for Simplified Chinese.

All translated text are defined in `translations.py`.

## Notes

- Only items available in the inventory file are considered by the solver.
- The stat list is defined by `ALL_STAT_COLS`, so the CSV headers and code must stay aligned for correct matching.
- Profession name input supports translated names and partial matching without requiring the tier suffix in some cases.

## AI Disclaimer

This project was created with the assistance of AI tools.****