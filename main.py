import datetime
import os
import shlex
from pathlib import Path
from typing import Optional
import Scripts.managers as managers
from Scripts.managers import I18n
from Scripts.core import CsvRepository, InventoryService, ProfessionService, SolverEngine, SummaryRenderer


class App:
    def __init__(self):
        self.folders = managers.CONFIG.get_paths().copy()
        self.prof_df, self.food_df, self.mem_df, self.inv_df = CsvRepository.load_data()
        self.prof_service = ProfessionService(self.prof_df)
        self.solver = SolverEngine(self.prof_service)

    @staticmethod
    def _expand_path(path_str: str) -> Path:
        return Path(path_str).expanduser()

    @classmethod
    def _is_existing_csv_file(cls, path_str: str) -> bool:
        path = cls._expand_path(path_str)
        return path.is_file() and path.suffix.lower() == ".csv"

    @staticmethod
    def _safe_input(prompt: str = "") -> Optional[str]:
        try:
            return input(prompt)
        except (KeyboardInterrupt, EOFError):
            print("\n" + I18n.t("FH_operation_cancel"))
            return None

    @staticmethod
    def _get_display_path(path_str: str) -> Path:
        try:
            path_obj = Path(path_str).expanduser().resolve()
            return path_obj.relative_to(Path.cwd().resolve())
        except (ValueError, OSError):
            return Path(path_str).expanduser()

    def reload(self) -> bool:
        try:
            managers.reload_managers()
            self.prof_df, self.food_df, self.mem_df, self.inv_df = CsvRepository.load_data()
            self.prof_service = ProfessionService(self.prof_df)
            self.solver = SolverEngine(self.prof_service)
            self.folders = managers.CONFIG.get_paths().copy()

            print("\n" + "=" * 100)
            print(I18n.t("SYS_csv_reloaded"))
            print("=" * 100)
            return True
        except SystemExit:
            print(I18n.t("ERR_reload_fail_path"))
            return False
        except Exception as e:
            print(I18n.t("ERR_reload_fail") + str(e))
            return False

    def file_select(self, target_var: str, custom_folder: str = None) -> Optional[str]:
        raw_path = custom_folder if custom_folder else self.folders.get(target_var, target_var)
        path_obj = Path(raw_path).expanduser()
        browse_dir = path_obj.parent if path_obj.suffix.lower() == ".csv" else path_obj
        if not browse_dir.exists() or not browse_dir.is_dir():
            warn_key = "WARN_folder_not_found" if not browse_dir.exists() else "WARN_folder_not_dir"
            print(I18n.t(warn_key, folder=browse_dir))

            choice = self._safe_input(I18n.t("FH_r_re-enter"))
            if choice and choice.strip().lower() == "r":
                new_path = self._safe_input(I18n.t("FH_input_path"))
                if new_path and self._is_existing_csv_file(new_path.strip()):
                    return str(Path(new_path.strip()).expanduser())
                return self.file_select(target_var, custom_folder=new_path.strip() if new_path else None)

            print(I18n.t("FH_operation_cancel"))
            return None

        file_list = []

        try:
            entries = os.listdir(browse_dir)
        except OSError:
            print(I18n.t("WARN_folder_not_found"), folder=browse_dir)
            return None

        for f in entries:
            if f.lower().endswith(".csv"):
                full_path = os.path.join(browse_dir, f)
                try:
                    mtime = os.path.getmtime(full_path)
                    file_list.append((f, mtime))
                except OSError:
                    continue

        file_list.sort(key=lambda x: x[1], reverse=True)
        files = [item[0] for item in file_list]

        print(I18n.t("FH_select_file", target=target_var))
        print(I18n.t("FH_0_remain_unchanged"))

        for i, f in enumerate(files, 1):
            full_path = os.path.join(browse_dir, f)
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                mtime = "Unknown"
            print(f"    {i}: {f} {I18n.t('FH_last_modified', mtime=mtime)}")

        option_custom = len(files) + 1
        print(I18n.t("FH_custom_path", option_custom=option_custom))

        while True:
            choice_str = self._safe_input(I18n.t("FH_input_num"))
            if choice_str is None:
                print(I18n.t("FH_operation_cancel"))
                return None
            try:
                choice = int(choice_str.strip())
                if choice == 0:
                    print(I18n.t("FH_operation_cancel"))
                    return None
                elif 1 <= choice <= len(files):
                    selected_path = (browse_dir / files[choice - 1]).resolve()
                    return str(self._get_display_path(str(selected_path)))
                elif choice == option_custom:
                    full_custom = self._safe_input(I18n.t("FH_input_path"))
                    if full_custom:
                        full_custom_path = full_custom.strip("\"'")
                        if self._is_existing_csv_file(full_custom_path):
                            return str(Path(full_custom_path).expanduser().resolve())
                        print("  " + I18n.t("ERR_missing_files", files=full_custom_path))
                    print(I18n.t("FH_operation_cancel"))
                    return None
                else:
                    print(I18n.t("ERR_invalid_num"))
            except ValueError:
                print(I18n.t("ERR_invalid_num"))

    def _set(self, user_input: str) -> bool:
        try:
            tokens = shlex.split(user_input, posix=False)[1:]
            tokens = [t.strip("\"'") for t in tokens]
        except ValueError as e:
            print(I18n.t("ERR_invalid_value") + str(e))
            return True

        if not tokens:
            print(I18n.t("ERR_invalid_set_command"))
            return True

        updates = {}
        i = 0
        valid_path_vars = {"human", "food", "memory", "inventory"}

        while i < len(tokens):
            token = tokens[i]
            target_var = token.lstrip("-").lower()
            if target_var not in valid_path_vars:
                print(I18n.t("WARN_unknown_token", token=token))
                i += 1
                continue

            arg = None
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                arg = tokens[i + 1]

            if arg is None:
                print("\n" + "=" * 100)
                print(I18n.t("FH_enter_file_select_helper"))
                print("=" * 100)

                new_filename = self.file_select(target_var)
                if new_filename:
                    try:
                        display_path = Path(new_filename).relative_to(Path.cwd())
                    except ValueError:
                        display_path = Path(new_filename)

                    print(I18n.t("SYS_change_read_file", file=display_path))
                    updates[target_var] = new_filename

                print("\n" + "=" * 100)
                print(I18n.t("FH_exit_file_select_helper"))
                print("=" * 100)

                i += 1
                continue

            expanded_arg = self._expand_path(arg)
            if self._is_existing_csv_file(arg):
                new_filename = str(expanded_arg.resolve())
                try:
                    display_path = Path(new_filename).relative_to(Path.cwd())
                except ValueError:
                    display_path = Path(new_filename)

                print(I18n.t("SYS_change_read_file", file=display_path))
                updates[target_var] = new_filename
            elif expanded_arg.exists() and expanded_arg.is_dir():
                print("\n" + "=" * 100)
                print(I18n.t("FH_enter_file_select_helper"))
                print("=" * 100)

                new_filename = self.file_select(target_var, custom_folder=str(expanded_arg))
                if new_filename:
                    try:
                        display_path = Path(new_filename).relative_to(Path.cwd())
                    except ValueError:
                        display_path = Path(new_filename)

                    print(I18n.t("SYS_change_read_file", file=display_path))
                    updates[target_var] = new_filename

                print("\n" + "=" * 100)
                print(I18n.t("FH_exit_file_select_helper"))
                print("=" * 100)

            else:
                print("  " + I18n.t("ERR_missing_files", files=arg))
                print(I18n.t("FH_operation_cancel"))

            i += 2

        if updates:
            old_paths = {"human": managers.CONFIG.human_path, "food": managers.CONFIG.food_path, "memory": managers.CONFIG.memory_path, "inventory": managers.CONFIG.inventory_path}

            for key, file_path in updates.items():
                managers.CONFIG.update_path(key, file_path)

            managers.CONFIG.save_config()

            if not self.reload():
                for key, old_path in old_paths.items():
                    managers.CONFIG.update_path(key, old_path)

                managers.CONFIG.save_config()

        return True

    def run(self):
        print("\n" + I18n.t("title"))

        while True:
            raw_input = self._safe_input("\n" + I18n.t("prompt"))
            if raw_input is None:
                print("\nExiting...")
                break

            user_input = raw_input.strip()
            if not user_input:
                continue

            if user_input.lower() in {"quit", "q"}:
                break
            if user_input.lower() == "list":
                self.prof_service.print_profession_list()
                continue
            if user_input.lower() in {"help", "h"}:
                print(I18n.t("help"))
                continue
            if user_input.lower() == "reload":
                self.reload()
                continue
            if user_input.lower().startswith("set"):
                self._set(user_input)
                continue

            independent_mode = False
            if user_input.startswith("?"):
                independent_mode = True
                user_input = user_input[1:].strip()
                print("\n" + I18n.t("SYS_independent_calculation"))

            targets = [target.strip() for target in user_input.replace("，", ",").split(",") if target.strip()]
            if not targets:
                continue

            valid_targets = []
            invalid_targets = []
            for target in targets:
                normalized_target = self.prof_service.normalize_input(target)
                target_info = self.prof_service.get_target_info(normalized_target)
                if target_info is None:
                    invalid_targets.append(target)
                else:
                    valid_targets.append((target, target_info))

            if not valid_targets:
                for invalid_target in invalid_targets:
                    print("\n" + "=" * 100)
                    print(I18n.t("FAILED_profession_not_found", target=invalid_target))
                    print("=" * 100)
                continue

            current_inv_df = self.inv_df.copy()
            summary_results = []
            current_session_ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            managers.LOG_MANAGER.start_session(user_input)
            managers.LOG_MANAGER.print(I18n.t("LOG_user_input", user_input=user_input), False)

            for invalid_target in invalid_targets:
                managers.LOG_MANAGER.print("\n" + "=" * 100)
                managers.LOG_MANAGER.print(I18n.t("FAILED_profession_not_found", target=invalid_target))
                managers.LOG_MANAGER.print("=" * 100)

            for target, target_info in valid_targets:
                if independent_mode:
                    current_inv_df = self.inv_df.copy()
                    managers.LOG_MANAGER.total_attempts = 0

                avail_foods = InventoryService.apply_inventory(self.food_df, current_inv_df, "food")
                avail_mems = InventoryService.apply_inventory(self.mem_df, current_inv_df, "memory")

                managers.LOG_MANAGER.print("\n" * 2 + "=" * 100)
                managers.LOG_MANAGER.print(I18n.t("RESULT_calculating", target=target))
                managers.LOG_MANAGER.print("=" * 100)

                result_status, result = self.solver.find_combination(target_info, avail_foods, avail_mems, current_inv_df, current_session_ts)

                if managers.CONFIG.log_mode and managers.LOG_MANAGER.total_attempts > 0:
                    managers.LOG_MANAGER.print(I18n.t("LOG_total_attemps", target=target, total=managers.LOG_MANAGER.total_attempts), managers.CONFIG.log_mode, False)

                if result_status == "NOT_ENOUGH_ITEMS":
                    managers.LOG_MANAGER.print(I18n.t("FAILED_not_enough_items"))
                elif result_status == "SUCCESS" and result:
                    summary_results.append(result)

                    if not independent_mode and not managers.CONFIG.unlimited_inventory:
                        current_inv_df = InventoryService.apply_used_counts(current_inv_df, result["used_counts"])

            if managers.CONFIG.show_summary and summary_results:
                SummaryRenderer.print_summary(summary_results)

            managers.LOG_MANAGER.end_session()

            if managers.CONFIG.deduct_inventory and not managers.CONFIG.unlimited_inventory and not independent_mode and summary_results:
                self.inv_df = current_inv_df.copy()
                InventoryService.save_inventory(self.inv_df, current_session_ts)

                print("\n" + "=" * 100)
                print(I18n.t("SYS_csv_reloaded"))
                print("=" * 100)


def main():
    App().run()


if __name__ == "__main__":
    main()
