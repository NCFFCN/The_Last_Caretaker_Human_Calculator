English | [繁體中文](./README/README_tc.md) | [简体中文](./README/README_sc.md)

# The Last Caretaker Human Calculator

A command-line interface (CLI) tool designed for solving profession combinations in **The Last Caretaker**. It utilizes an integer linear optimization model to identify valid item combinations to achieve a target profession, while efficiently avoiding unwanted collateral professions.

## Project Structure
- `main.py`: The entry point and main CLI loop handling user input.
- `core.py`: Contains the core logic for the calculator, optimization models, and search algorithms.
- `managers.py`: Handles file loading, data processing, and state management (e.g., Inventory, Humans).
- `models.py`: Defines the data structures and classes used across the application.
- `translations.py`: Manages multi-language support (English, Traditional Chinese, Simplified Chinese).
- `constants.py`: Stores application-wide constants.

## Requirements
Install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```
*If `requirements.txt` is not available, ensure you have `pandas`, `numpy`, and `scipy` or `pulp` installed depending on your optimization backend.*

## Data Files (CSV)
The tool requires specific CSV files to operate correctly. Place them in the corresponding data folders:
- Human Data (`Data/Human.csv`)
- Food Data (`Data/Food.csv`)
- Memory Data (`Data/Memory.csv`)
- Inventory Data (`Data/Inventory/Inventory_template.csv`)

You can dynamically update the source folders or files during runtime using the `set` command. These preferences are persistently saved in `settings.json`.

> *Note: If you change paths manually outside of runtime, edit `settings.json` before launching the tool.*

## Usage
Run the application via:
```bash
python main.py
```

## Core Commands
At the prompt, you can:
- Enter a profession name to search for profession. Use commas (,) to enter multiple professions in one session.
- Type `list` to show all available professions.
- Type `reload` to reload the CSV file.
- Type `set -<category>` to open the file selection helper for a specific category (`-human`, `-food`, `-memory`, or `-inventory`).
- Type `h` or `help` to see all commands.
- Type `q` or `quit` to exit the program.

> *Tips: For the `set` command, the first `<category>` does not need to be followed by a hyphen `-`, but subsequent ones do.*

### Example:
#### Profession Name
```text
Enter Profession (or 'help' to see all command): Guard,Station Protector
```
#### "Set" Command
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

> *Note: The profession name should be entered in the display language set in `settings.json` (English, Traditional Chinese, or Simplified Chinese).*

## Independent Calculation Mode
By default, when you enter multiple targets (e.g., `Guard, Station Protector`), the tool uses a **deductive inventory** approach. This means that if the first target consumes certain items from your inventory, those items are marked as used and are not available for subsequent targets in the same session. This simulates a real-world scenario where you have a limited pool of resources. If you want to calculate each target **independently** (i.e., assuming a fresh inventory for each calculation), prefix your input with a `?`.

### Example:
```text
Enter Profession (or 'help' to see all command): ?Guard, Station Protector
```

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
Solver Hard Constraint:
1. Cannot create different category of profession.

Solver Prioritizes:
1. Custom item priority (e.g.: Teddy Bear = 1, Ash Book = 3)
2. Total items count
3. Remaining stats exceed the total
4. If multiple solutions have the same score in the above three prioritizes, the solver will slightly favor the food category with custom priority 1.

## Global Settings (`settings.json`)
The application behaviour is controlled via `settings.json`:
- `lang`: Language preference (`en`, `tc`, `sc`).
- `unlimited_search`: Toggles limits on search combinations. (Default: `false`)
- `max_attempts`: Maximum search iterations. (Default: 25)
- `unlimited_inventory`: No inventory limitation. (Default: `false`)
- `deduct_inventory`: Whether to deduct used items from the inventory automatically. (Default: `false`)
- `save_as_new_file`: Save inventory updates to a new file instead of overwriting. (Default: `true`)
- `show_summary`: Toggle the visual summary block after successful calculations. (Default: `true`)
- `summary_items_per_row`: Defines how many item blocks to display per row in the summary. (Default: `4`)
- `data`: Define the default paths for the `human`, `food`, `memory`, and `inventory` CSV files.
- `log_mode`: Enable/disable exporting output to the log. (Default: `true`)
- `log_folder`: Defines default folder path for log files.

> *Note: If `unlimited_search = true`, custom priorities will still use the files in the `data` list in the `settings.json` file. Please confirm that custom priorities meet your needs before starting the program.*

## Language Support
The display language is controlled by the `lang` setting in `settings.json`:
- `"en"` for English.
- `"tc"` for Traditional Chinese.
- `"sc"` for Simplified Chinese.

All translated text is defined in `translations.py`.

## Notes
- Only items available in the inventory data file are considered by the solver. Please choose the correct inventory file
- The stat list is defined by `ALL_STAT_COLS`, so the CSV headers and code must stay aligned for correct matching.
- It will automatically reload the latest inventory if the following conditions are met.
  1. `deduct_inventory = True`
  2. `unlimited_inventory = False`
  3. Not in independent calculation mode
  4. There are successful targets