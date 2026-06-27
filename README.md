# The Last Caretaker Human Calculator

A small CLI tool for solving lineage-style profession combinations in **The Last Caretaker**.  
It reads profession, food, memory, and inventory data from CSV files, then uses a linear optimization model with integer decision variables to search for a pure combination of items that satisfies a target profession while avoiding unwanted collateral professions.

## Project Files

- Human data: `Humans.csv`
- Food data: `Food.csv`
- Memory data: `Memories.csv`
- Inventory data: `Inventory.csv`
- Main script: `main.py`
- Translation settings: `translations.py`
- Python dependencies: `requirements.txt`

## Requirements

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The current dependency list contains `numpy`, `pandas`, and `pulp`.

## Usage

Run the calculator from the project folder:

```bash
python main.py
```

At the prompt, you can:

- Enter a profession name such as `Guardian of Humanity T4` or `Guard T2`.
- Type `list` to show all available professions.
- Type `q` to quit.

Example:

```text
Enter Target Profession (or 'list' to see all, 'q' to quit): Guard T2
```

## How It Works

The program loads profession data from `Humans.csv`, item stat data from `Food.csv` and `Memories.csv`, and availability data from `Inventory.csv`.  
It normalizes the CSV columns, filters inventory by item kind, and only keeps food or memory items with a positive `inventory_count` before solving.

The solver builds a PuLP minimization model with integer variables for item counts.  
The objective minimizes a weighted combination of total priority cost first, then total item count, and finally excess stats above the target requirements.

For each candidate solution, the program checks which professions would be triggered by the resulting stats and rejects solutions that produce professions outside the allowed lineage for the target.  
When a failed combination is found, the solver adds another constraint and continues searching for an alternative combination.

## Search Settings

The updated code stores the unlimited-search behavior directly in `main.py` with the local setting `UNLIMITED_SEARCH = True`.  
The same file also defines `MAX_ATTEMPTS = 1000`, but that limit is only used when unlimited search is turned off.

The code also supports both `Inventory.csv` and `inventory.csv` when loading the inventory file, which helps avoid filename case issues across environments.

## Notes

- Only items available in the inventory file are considered by the solver.
- The current build uses `Life Expectancy` in `ALL_STAT_COLS`, so the CSV headers and code need to stay aligned for correct stat matching.
- The CLI text and translated profession, category, item, and stat labels are defined in `translations.py`.
- The current implementation includes refactoring for cleaner data loading, normalization, profession evaluation, and solution reporting.

## AI Disclaimer

This project was created with the assistance of AI tools.
