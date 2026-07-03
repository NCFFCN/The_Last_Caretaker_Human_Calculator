<b>English</b></span> | <a href="README_tc.md"><b>繁體中文</b></a></span> | <a href="README_sc.md"><b>简体中文</b></a></span>

# The Last Caretaker Human Calculator

A small CLI tool for solving profession combinations in **The Last Caretaker**. It uses an integer linear optimization model to search for a valid item combination for a target profession while avoiding unwanted collateral professions.

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
- Type `help` to see all command.

Example:
```text
Enter Target Profession (or 'help' to see all command): Guard T2
```
```text
Enter Target Profession (or 'help' to see all command): Guard, Site Guardian
```

Note: The profession name should be entered in the display language set in `main.py` (English, Traditional Chinese, or Simplified Chinese).

### Independent Calculation Mode (Temporary Inventory)
By default, when you enter multiple targets (e.g., `Guard T2, Site Guardian`), the tool uses a **deductive inventory** approach. This means that if the first target consumes certain items from your inventory, those items are marked as used and are not available for subsequent targets in the same session. This simulates a real-world scenario where you have a limited pool of resources.
If you want to calculate each target **independently** (i.e., assuming an unlimited or fresh inventory for each calculation), prefix your input with a `?`.

Example:
```text
Enter Target Profession (or 'help' to see all command): ?Guard T2, Site Guardian
```

The prompt will pop out:
```text
[System] Independent calculation mode is enabled: Multiple targets entered this time will not deduct inventory from each other.
```
In this mode, the calculator ignores temporary inventory and each calculation will target the best combination of current inventory data, as if all items were available, without deducting those items from the next target.

## Professionals required by each committee
Deck operations
```text
Maintenance Engineer, Basic Supplier, Nutrient Handler, Door Jammer
```

Habitat Care
```text
Room Supervisor, Health Assistant, Teacher, Lab Technician
```

Transit & Distribution
```text
System Engineer, Distributor, Growth Specialist, Guard
```

Power & Security
```text
Energy Engineer, Resource Director, Station Quartermaster, Station Protector
```

Cognitive Resilience
```text
Theoretical Scientist, Neuro Specialist, Professor, Star Analyzer
```

Culture & Memory
```text
Visual Technician, Sculptor, Cultural Archivist, Manual Holder
```

Governance & Logistics
```text
Settlement Governor, Logistics High Command, Biosphere Director, Guardian of Humanity
```

Deep Systems
```text
Quantum Engineer, Quantum Physicist, Neural Architect, Sustenance Architect
```

Meaning & Frontier
```text
Existential Expressionist, Frontier Explorer, Mission Seeker, Colonel of Humanity
```

Field Continuance
```text
Field Research Scientist, Existential Chancellor, Station Roamer, Doctor
```

## Search logic
The solver prioritizes:
1. Custom item priority (e.g.: Teddy Bear = 1, Ash Book = 3)
2. Total items count
3. Remaining stats exceed the total
4. It can create different category of profession.

## Search Settings
The search behavior is controlled directly in `main.py`:

- `UNLIMITED_SEARCH`: Indicates whether the calculator searches indefinitely. (Default: `False`)
- `MAX_ATTEMPTS`: Defines the maximum number of search attempts when `UNLIMITED_SEARCH = False`. (Default: `20`)
- `PRIORITY_WEIGHT` and `ITEM_COUNT_WEIGHT` control how strongly the solver prefers lower-priority-cost and lower-item-count solutions.
- `BIG_M` is used to exclude combinations of professions that are not of the same category.

## Inventory Settings
The inventory update behavior is also controlled in `main.py`:
- `DEDUCT_INVENTORY`: Indicates whether the inventory file will be modified after a successful combination is found. (Default: `False`)
- `SAVE_AS_NEW_FILE`: Indicates that when `DEDUCT_INVENTORY = True`, the updated inventory will be saved to a new CSV file with a timestamp, instead of overwriting the original file. (Default: `True`)

## Language Support
The display language is controlled by the `LANG` setting in `main.py`:
- `"en"` for English.
- `"tc"` for Traditional Chinese.
- `"sc"` for Simplified Chinese.

All translated text are defined in `translations.py`.

## Notes
- Only items available in the `inventory.csv` file are considered by the solver.
- The stat list is defined by `ALL_STAT_COLS`, so the CSV headers and code must stay aligned for correct matching.

## Version History
### v0.1.0
- Initial release

### v0.1.1
- Optimize translation

### v0.2.0
- Improved search settings parameters
- Improved file name handling

### v0.2.1
- Changed data file naming

### v0.3.0
- Improved data file saving mechanism
- Optimize translation

### v0.3.1
- Improved the inclusion of timestamps when saving new `inventory.csv`

### v0.4.0
- Improved the main settings of the script
- Improved data loading and processing mechanism
- Improved the handling of profession input
- Improved inventory management
- Improved combination finding logic
- Added "summary of successful combinations" mechanism
- Improved output formatting
- Added Simplified Chinese translation
- Optimize translation
- Updated README.md

### v0.5.0
- Added special category profession called "Star Child" to `Human.csv`
- Added special item called "Star Child" to `Inventory.csv` and `Memory.csv`
- Expanded `Memory.csv` and `Inventory.csv` "PECO" to "Keys To Imagination" and "PECO Athletics" series
- Fixed several bugs
- Added more command options (help, reload, ?)
- Expanded translation support in the interface
- Optimize translations to match in-game proprietary names
- Updated `README.md`

### v0.5.1
- Normalized `inventory.csv` column naming

### v0.5.2
- Fixed several bugs

### v0.5.3
- Updated `README.md`

### v0.6.0
- Updated `README.md`
- Added `README_tc.md` and `README_sc.md`
- Updated `Human.csv` data
- Expanded translation to support the interface
- Fixed several bugs

### v0.7.0
- Optimize translation
- Added the logic for calculating the decay penalty after adding an attribute exceeding 200.
- Improved overall code management and structure (`main.py` rebuilt)

### v0.7.1
- Added "Version History" sections to all `README.md` files
- Optimize translation

### v0.7.2
- Updated `README.md`

### v0.7.3
- Updated all `README.md` files

### v0.7.4
- Fixed the keys in the `RAW_TO_EFF` dictionary were incorrect.

### v0.7.5
- Fixed `inventory.csv` column name mismatch and ordering issues.