import datetime
import json
import os
import re
from .constants import CONFIG_FILE
from pathlib import Path
from .translations import *


class ConfigManager:
    def __init__(self):
        self.config_file = Path(CONFIG_FILE)
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        self.settings = self.load_global_settings()

        self.lang = self.settings.get("lang", "en")
        self.unlimited_search = self.settings.get("unlimited_search", False)
        self.max_attempts = self.settings.get("max_attempts", 25)
        self.unlimited_inventory = self.settings.get("unlimited_inventory", True)
        self.deduct_inventory = self.settings.get("deduct_inventory", False)
        self.save_as_new_file = self.settings.get("save_as_new_file", True)
        self.show_summary = self.settings.get("show_summary", True)
        self.summary_items_per_row = self.settings.get("summary_items_per_row", 4)
        self.log_mode = self.settings.get("log_mode", True)
        self.log_folder = self.settings.get("log_folder", "Log")

        self.human_path = self._resolve_path("human", "Human", "Human_template.csv")
        self.food_path = self._resolve_path("food", "Food", "Food_template.csv")
        self.memory_path = self._resolve_path("memory", "Memory", "Memory_template.csv")
        self.inventory_path = self._resolve_path("inventory", "Inventory", "Inventory_template.csv")

    def reload_state(self):
        self.load_settings()

    def load_global_settings(self):
        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Error] Failed to load {self.config_file}. {e}")

        return {}

    def _resolve_path(self, key, default_folder, default_filename):
        data = self.settings.get("data", {})
        path = data.get(key, default_folder)

        if not isinstance(path, str):
            print(I18n.t("WARN_unknown_path_value", key=key))
            path = str(default_folder)

        normalized = Path(path.replace("\\", os.sep).replace("/", os.sep)).expanduser()
        if normalized.suffix.lower() == ".csv":
            return str(normalized)

        return str(normalized / default_filename)

    def get_paths(self):
        return {
            "human": self.human_path,
            "food": self.food_path,
            "memory": self.memory_path,
            "inventory": self.inventory_path,
        }

    def update_path(self, key, path):
        path_str = self._normalize_path_string(path)

        if key == "human":
            self.human_path = path_str
        elif key == "food":
            self.food_path = path_str
        elif key == "memory":
            self.memory_path = path_str
        elif key == "inventory":
            self.inventory_path = path_str

    def _normalize_path_string(self, path):
        path_obj = Path(path).expanduser()
        abs_path = path_obj if path_obj.is_absolute() else path_obj.resolve()
        cwd = Path.cwd().resolve()

        try:
            rel = os.path.relpath(abs_path, cwd)
            path_str = rel if not rel.startswith("..") else str(abs_path)
        except Exception:
            path_str = str(abs_path)

        return path_str.replace("\\", "/")

    def save_config(self):
        if "data" not in self.settings:
            self.settings["data"] = {}

        self.settings["data"]["human"] = Path(self.human_path).as_posix()
        self.settings["data"]["food"] = Path(self.food_path).as_posix()
        self.settings["data"]["memory"] = Path(self.memory_path).as_posix()
        self.settings["data"]["inventory"] = Path(self.inventory_path).as_posix()

        try:
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(I18n.t("ERR_save_file", file=self.config_file) + str(e))


class I18n:
    @staticmethod
    def t(key, **kwargs):
        lang_dict = TEXT.get(CONFIG.lang, TEXT["en"])
        text_template = lang_dict.get(key, TEXT["en"].get(key, key))
        try:
            return text_template.format(**kwargs)
        except KeyError:
            return f"{text_template} (Missing translation || key / value not match)"

    @staticmethod
    def display_category_name(name):
        return CATEGORY_TRANSLATIONS.get(CONFIG.lang, {}).get(name, name)

    @staticmethod
    def display_profession_name(name):
        table = PROFESSION_TRANSLATIONS.get(CONFIG.lang, {})
        if name is None:
            return table
        return table.get(name, name)

    @staticmethod
    def display_item_name(name):
        return ITEM_TRANSLATIONS.get(CONFIG.lang, {}).get(name, name)

    @staticmethod
    def display_stat_name(name):
        return STAT_TRANSLATIONS.get(CONFIG.lang, {}).get(name, name)


class LogManager:
    def __init__(self):
        self.is_logging = False
        self.log_content = []
        self.log_file = ""
        self.total_attempts = 0

    def reload_state(self):
        self.is_logging = False
        self.log_content = []
        self.log_file = ""
        self.total_attempts = 0

    def start_session(self, title: str):
        if not CONFIG.log_mode:
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title.replace(" ", "")) or "Session"

        log_dir = Path(CONFIG.log_folder)
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = str(log_dir / f"{safe_title}_{timestamp}.log")
        self.is_logging = True
        self.log_content = [I18n.t("LOG_session_start", timestamp=timestamp)]
        self.total_attempts = 0

    def print(self, message: str, to_cli: bool = True, to_log: bool = True):
        if self.is_logging and to_log:
            self.log_content.append(message)

        if to_cli:
            print(message)

    def increase_attempt(self):
        self.total_attempts += 1

    def end_session(self):
        if not self.is_logging:
            return
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_content))
        except Exception as e:
            print(I18n.t("ERR_save_file", file=self.log_file) + str(e))

        self.is_logging = False
        self.log_content = []


CONFIG = ConfigManager()
LOG_MANAGER = LogManager()


def reload_managers():
    CONFIG.reload_state()
    LOG_MANAGER.reload_state()
