## Version History
### v1.0.0
- Added `set` command to support interactive file selection, custom folders, and direct file paths
- Added `unlimited_inventory` setting to allow searching for professions without being limited by inventory
- Added `log_mode` and `log_folder` settings, allowing all output to be saved to the log, thus keeping the CLI clean
- Extracted global configurations to `settings.json`
- For better maintenance, all `Class` in `main.py` have been split into different files.
- All CSV files have been moved to the `Data` folder
- Improved error handling and data handling in the program
- Expanded translation to support the interface
- Optimize translation
- Updated all `README.md` files
- The `Version History` section in all README files has been moved to the `VH.md` file.

### v0.7.5
- Fixed the Intelligence value for `Quantum Physicist T4`

### v0.7.4
- Added feature: if `DEDUCT_INVENTORY = true`, `SAVE_AS_NEW_FILE = false`, not in independent calculation mode and there are successful targets, it will reload the latest inventory automatically

### v0.7.3
- Fixed the keys in the `RAW_TO_EFF` dictionary were incorrect
- Fixed `inventory.csv` column name mismatch and ordering issues

### v0.7.2
- Updated all `README.md` files

### v0.7.1
- Added "Version History" sections to all `README.md` files
- Optimize translation

### v0.7.0
- Optimize translation
- Added the logic for calculating the decay penalty after adding an attribute exceeding 200
- Improved overall code management and structure (main.py rebuilt)

### v0.6.0
- Updated `README.md`
- Added `README_tc.md` and `README_sc.md`
- Updated `Human.csv` data
- Expanded translation to support the interface
- Fixed several bugs.

### v0.5.3
- Updated `README.md`

### v0.5.2
- Fixed several bugs

### v0.5.1
- Normalized `inventory.csv` column naming

### v0.5.0
- Added special category profession called `Star Child` to `Human.csv`
- Added special item called `Star Child` to `Inventory.csv` and `Memory.csv`
- Expanded `PECO` to `Keys To Imagination` and `PECO Athletics` series in `Memory.csv` and `Inventory.csv`
- Fixed several bugs
- Added more command options (help, reload, ?)
- Expanded translation support in the interface
- Optimize translations to match in-game proprietary names
- Updated `README.md`

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
- Updated `README.md`

### v0.3.1
- Improved the inclusion of timestamps when saving new inventory.csv

### v0.3.0
- Improved data file saving mechanism
- Optimize translation

### v0.2.1
- Changed data file naming

### v0.2.0
- Improved search settings parameters
- Improved file name handling

### v0.1.1
- Optimize translation

### v0.1.0
- Initial release