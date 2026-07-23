import numpy as np
import os
import pandas as pd
import pulp
import re
import sys
import uuid
from . import managers
from .constants import *
from .managers import I18n
from .models import *
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class StatConverter:
    _SORTED_RAW_TO_EFF = sorted(RAW_TO_EFF.items())

    @staticmethod
    def to_effective_stat(raw_val: int) -> int:
        raw_val = max(0, raw_val)
        if raw_val <= 200:
            return raw_val

        n = raw_val - 200
        eff = 0
        for min_raw, y_eff in StatConverter._SORTED_RAW_TO_EFF:
            if n >= min_raw:
                eff = y_eff
            else:
                break

        return 200 + eff

    @staticmethod
    def to_raw_requirement(eff_val: int) -> int:
        eff_val = max(0, eff_val)
        if eff_val <= 200:
            return eff_val

        y = eff_val - 200

        return 200 + EFF_TO_RAW.get(y, y)


class CsvRepository:
    @staticmethod
    def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.map(lambda c: c.strip() if isinstance(c, str) else c)
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                non_null_mask = df[col].notna()
                df.loc[non_null_mask, col] = df.loc[non_null_mask, col].map(lambda value: value.strip() if isinstance(value, str) else value)
        return df

    @classmethod
    def read_csv_checked(cls, path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(path, sep=";", skipinitialspace=True)
            if len(df.columns) <= 1:
                df = pd.read_csv(path, sep=",", skipinitialspace=True)
            return cls.clean_text_columns(df)
        except pd.errors.EmptyDataError:
            print(I18n.t("ERR_read_data", name=path, col="ALL", cell="Empty File"))
            return pd.DataFrame()
        except Exception as e:
            print(I18n.t("ERR_load_file", file=path) + str(e))
            return pd.DataFrame()

    @staticmethod
    def normalize_humans(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "Profession" in df.columns:
            df["Profession"] = df["Profession"].fillna("").astype(str).str.strip()
        else:
            df["Profession"] = ""

        if "Category" in df.columns:
            df["Category"] = df["Category"].fillna("").astype(str).str.strip()
        else:
            df["Category"] = ""

        for col in ALL_STAT_COLS:
            if col in df.columns:
                numeric_series = pd.to_numeric(df[col], errors="coerce")
                invalid_mask = df[col].notna() & (df[col] != "") & numeric_series.isna()

                if invalid_mask.any():
                    invalid_rows = df.loc[invalid_mask]
                    for idx, row in invalid_rows.iterrows():
                        name = row.get("Profession", row.get("Name", f"Row {idx}"))
                        print(I18n.t("ERR_read_data", name=name, col=col, cell=row[col]))

                df[col] = numeric_series.fillna(0).astype(int)
            else:
                df[col] = 0

        return df

    @staticmethod
    def normalize_items(df: pd.DataFrame, source_col: str) -> pd.DataFrame:
        df = df.copy()
        df = df.rename(columns={source_col: "Name"})

        if "Name" not in df.columns:
            df["Name"] = ""

        df["Name"] = df["Name"].fillna("").astype(str).str.strip()

        for col in ALL_STAT_COLS:
            if col in df.columns:
                numeric_series = pd.to_numeric(df[col], errors="coerce")
                invalid_mask = df[col].notna() & (df[col] != "") & numeric_series.isna()
                if invalid_mask.any():
                    invalid_rows = df.loc[invalid_mask]
                    for idx, row in invalid_rows.iterrows():
                        name = row.get("Name", f"Row {idx}")
                        print(I18n.t("ERR_read_data", name=name, col=col, cell=row[col]))

                df[col] = numeric_series.fillna(0).astype(int)
            else:
                df[col] = 0

        if "Priority" in df.columns:
            df["Priority"] = pd.to_numeric(df["Priority"], errors="coerce").fillna(1)
        else:
            df["Priority"] = 1

        df = df.drop_duplicates(subset=["Name"], keep="first").reset_index(drop=True)
        return df

    @staticmethod
    def normalize_inventory(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["_original_order"] = range(len(df))
        df = df.rename(columns={"Category": "inv_category"})

        if "Name" in df.columns:
            df["Name"] = df["Name"].fillna("").astype(str).str.strip().str.lower()
        else:
            df["Name"] = ""

        if "inv_category" in df.columns:
            df["inv_category"] = df["inv_category"].fillna("").astype(str).str.strip().str.lower()
        else:
            df["inv_category"] = ""

        if "Count" in df.columns:
            df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)
        else:
            df["Count"] = 0

        base_cols = ["Name", "inv_category", "Count", "_original_order"]
        extra_cols = [col for col in df.columns if col not in base_cols]
        agg_dict = {"Count": "sum", "_original_order": "min"}
        for col in extra_cols:
            agg_dict[col] = "first"

        grouped = df.groupby(["Name", "inv_category"], as_index=False).agg(agg_dict)
        return grouped.sort_values("_original_order").drop(columns=["_original_order"]).reset_index(drop=True)

    @classmethod
    def load_data(cls) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        paths = managers.CONFIG.get_paths()
        missing = []
        for label, path in paths.items():
            if not os.path.exists(path) or not os.path.isfile(path):
                missing.append(f"{label} ({path})")

        if missing:
            print(I18n.t("ERR_missing_files", files=", ".join(missing)))
            sys.exit(1)

        humans = cls.normalize_humans(cls.read_csv_checked(paths["human"]))
        foods = cls.normalize_items(cls.read_csv_checked(paths["food"]), "Food")
        memories = cls.normalize_items(cls.read_csv_checked(paths["memory"]), "Memory")
        inventory = cls.normalize_inventory(cls.read_csv_checked(paths["inventory"]))

        return humans, foods, memories, inventory


class ProfessionService:
    def __init__(self, prof_df: pd.DataFrame):
        self.prof_df = prof_df.copy()
        self.lookup = self.build_profession_lookup()
        self.meta = self.build_profession_meta()

    @staticmethod
    def get_tier(prof_name: str) -> int:
        match = re.search(r"\bT([1-5])\b", prof_name, re.IGNORECASE)
        return int(match.group(1)) if match else 5

    def build_profession_lookup(self):
        lookup = {}
        reverse_translate = {str(x).lower(): str(k) for k, x in I18n.display_profession_name(None).items()}
        for raw_name in self.prof_df["Profession"].dropna().astype(str):
            raw_name = raw_name.strip()
            if not raw_name:
                continue

            raw_lower = raw_name.lower()
            lookup.setdefault(raw_lower, raw_name)
            lookup.setdefault(re.sub(r"\s*t\d+$", "", raw_lower, flags=re.IGNORECASE).strip(), raw_name)

            translated = I18n.display_profession_name(raw_name).lower()
            lookup.setdefault(translated, raw_name)
            lookup.setdefault(re.sub(r"\s*t\d+$", "", translated, flags=re.IGNORECASE).strip(), raw_name)

        for translated_lower, raw_name in reverse_translate.items():
            lookup.setdefault(translated_lower, raw_name)

        return lookup

    def normalize_input(self, user_input: str) -> str:
        user_input_lower = user_input.strip().lower()
        return self.lookup.get(user_input_lower, user_input.strip())

    def build_profession_meta(self) -> ProfessionMeta:
        professions = self.prof_df.copy()
        professions["Profession"] = professions["Profession"].fillna("").astype(str).str.strip()
        professions["Category"] = professions["Category"].fillna("").astype(str).str.strip()

        names = professions["Profession"].tolist()
        categories = professions["Category"].tolist()

        tiers = [self.get_tier(name) for name in names]
        matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)
        has_requirements = np.sum(matrix, axis=1) > 0

        return ProfessionMeta(df=professions, matrix=matrix, names=names, categories=categories, tiers=tiers, has_requirements=has_requirements)

    def get_target_info(self, target_profession: str) -> Optional[TargetInfo]:
        target_lower = target_profession.strip().lower()
        for i, name in enumerate(self.meta.names):
            if name.lower() == target_lower:
                return TargetInfo(name=name, category=self.meta.categories[i], tier=self.meta.tiers[i], stats=self.meta.matrix[i].copy())

        return None

    def get_allowed_jobs(self, target: TargetInfo) -> List[str]:
        return [name for name, category, tier in zip(self.meta.names, self.meta.categories, self.meta.tiers) if name == target.name or (category == target.category and tier < target.tier)]

    def compute_triggered_professions(self, current_stats: np.ndarray):
        rows = []
        for idx, (name, category, tier, reqs, has_req) in enumerate(zip(self.meta.names, self.meta.categories, self.meta.tiers, self.meta.matrix, self.meta.has_requirements)):
            if not has_req:
                continue

            req_raw = np.array([StatConverter.to_raw_requirement(int(v)) if int(v) > 0 else 0 for v in reqs])
            ok = True
            for k, req in enumerate(req_raw):
                if req > 0 and int(current_stats[k]) < req:
                    ok = False
                    break
            if ok:
                rows.append((name, category, tier, idx))
        return rows

    def print_profession_list(self):
        prof_view = self.meta.df.copy()
        prof_view["Tier"] = self.meta.tiers
        sorted_profs = prof_view.sort_values(by=["Category", "Tier", "Profession"])

        cat_to_profs = {}
        for _, row in sorted_profs.iterrows():
            cat = row["Category"]
            if cat not in cat_to_profs:
                cat_to_profs[cat] = []
            cat_to_profs[cat].append(I18n.display_profession_name(row["Profession"]))

        categories = list(cat_to_profs.keys())
        col_width = 38

        print(f"\n" + "=" * (col_width * min(3, len(categories))))
        print(f"{I18n.t('LIST_profession_list_title')}")
        print("=" * (col_width * min(3, len(categories))))

        for i in range(0, len(categories), 3):
            chunk = categories[i : i + 3]

            header_line = ""
            for cat in chunk:
                cat_display = f"[{I18n.display_category_name(cat)}]"
                header_line += SummaryRenderer.visual_ljust(cat_display, col_width)

            print(f"\n{header_line}")
            print("-" * (col_width * len(chunk)))

            max_rows = max(len(cat_to_profs[cat]) for cat in chunk)

            for r in range(max_rows):
                row_line = ""
                for cat in chunk:
                    profs_list = cat_to_profs[cat]
                    if r < len(profs_list):
                        item = f" - {profs_list[r]}"
                    else:
                        item = ""
                    row_line += SummaryRenderer.visual_ljust(item, col_width)
                print(row_line)

            print("." * (col_width * len(chunk)))

        print("\n" * 2)


class InventoryService:
    @staticmethod
    def apply_inventory(items_df: pd.DataFrame, inv_df: pd.DataFrame, category: str) -> pd.DataFrame:
        df = items_df.copy()
        inv = inv_df.copy()
        inv = inv[inv["inv_category"].eq(category.lower())]

        inv_counts = dict(zip(inv["Name"], inv["Count"]))

        if managers.CONFIG.unlimited_inventory:
            df["available"] = True
            df["Count"] = 9999
        else:
            df["available"] = df["Name"].str.lower().map(lambda n: inv_counts.get(n, 0) > 0)
            df["Count"] = df["Name"].str.lower().map(lambda n: int(inv_counts.get(n, 0)))

        return df

    @staticmethod
    def apply_used_counts(inv_df: pd.DataFrame, used_counts: Dict[Tuple[str, str], int]) -> pd.DataFrame:
        df = inv_df.copy()
        for (name, category), count in used_counts.items():
            mask = df["Name"].eq(str(name).lower()) & df["inv_category"].eq(str(category).lower())
            if mask.any():
                df.loc[mask, "Count"] = (df.loc[mask, "Count"] - int(count)).clip(lower=0)

        return df

    @staticmethod
    def save_inventory(inv_df: pd.DataFrame, session_ts: str):
        try:
            base_path = Path(managers.CONFIG.inventory_path)

            if managers.CONFIG.save_as_new_file and session_ts:
                save_path = base_path.with_name(f"{base_path.stem}_{session_ts}{base_path.suffix}")
            else:
                save_path = base_path

            save = inv_df.copy().rename(columns={"inv_category": "Category"})
            save["Name"] = save["Name"].astype(str)
            save["Category"] = save["Category"].astype(str)

            save.to_csv(save_path, index=False)

            if managers.CONFIG.save_as_new_file and session_ts:
                managers.CONFIG.update_path("inventory", str(save_path))
                managers.CONFIG.save_config()

        except Exception as e:
            print(I18n.t("ERR_save_file", file=str(save_path)) + str(e))


class SummaryRenderer:
    @staticmethod
    def visual_ljust(text: str, width: int) -> str:
        vis_len = sum(2 if ord(c) > 127 else 1 for c in text)
        return text + " " * max(0, width - vis_len)

    @staticmethod
    def print_success(target_info, food_lines, memory_lines, total_items_count, current_stats, target_stats, triggered_profs):
        managers.LOG_MANAGER.print(I18n.t("SUCCESS_found_combination", category=I18n.display_category_name(target_info.category)), not managers.CONFIG.log_mode)
        managers.LOG_MANAGER.print("-" * 100, not managers.CONFIG.log_mode)

        managers.LOG_MANAGER.print(f"{I18n.t('OUTPUT_foods_title')}", not managers.CONFIG.log_mode)
        for line in food_lines or [" - None"]:
            managers.LOG_MANAGER.print(line, not managers.CONFIG.log_mode)

        managers.LOG_MANAGER.print(f"\n{I18n.t('OUTPUT_memories_title')}", not managers.CONFIG.log_mode)
        for line in memory_lines or [" - None"]:
            managers.LOG_MANAGER.print(line, not managers.CONFIG.log_mode)

        managers.LOG_MANAGER.print(I18n.t("OUTPUT_items_needed", count=total_items_count), not managers.CONFIG.log_mode)

        managers.LOG_MANAGER.print(f"\n{I18n.t('OUTPUT_stats_title')}", not managers.CONFIG.log_mode)

        for idx, stat_name in enumerate(ALL_STAT_COLS):
            if int(target_stats[idx]) > 0:
                eff_current = StatConverter.to_effective_stat(int(current_stats[idx]))
                managers.LOG_MANAGER.print(
                    I18n.t("OUTPUT_display_stats", stat_name=I18n.display_stat_name(stat_name), eff_current=eff_current, target_stats=int(target_stats[idx]), current_stats=int(current_stats[idx])),
                    not managers.CONFIG.log_mode,
                )

        sorted_profs = sorted(triggered_profs, key=lambda x: x[2], reverse=True)
        buildable = [I18n.display_profession_name(name) for name, _, _, _ in sorted_profs]

        managers.LOG_MANAGER.print(f"\n{I18n.t('OUTPUT_buildable_title')}", not managers.CONFIG.log_mode)

        for line in buildable or [" - None"]:
            managers.LOG_MANAGER.print(f" - {line}" if line != " - None" else line, not managers.CONFIG.log_mode)

    @staticmethod
    def build_summary_sections(summary: dict) -> dict:
        stats_lines = []
        for idx, stat_name in enumerate(ALL_STAT_COLS):
            if int(summary["target_stats"][idx]) > 0:
                stats_lines.append(
                    I18n.t(
                        "OUTPUT_display_stats",
                        stat_name=I18n.display_stat_name(stat_name),
                        eff_current=StatConverter.to_effective_stat(int(summary["current_stats"][idx])),
                        target_stats=int(summary["target_stats"][idx]),
                        current_stats=int(summary["current_stats"][idx]),
                    )
                )

        sorted_profs = sorted(summary["triggered_profs"], key=lambda x: x[2], reverse=True)
        buildable_lines = [f" - {I18n.display_profession_name(name)}" for name, _, _, _ in sorted_profs]

        return {
            "title": [I18n.display_profession_name(summary["target_info"].name)],
            "divider": ["-" * 30],
            "foods_title": [I18n.t("OUTPUT_foods_title")],
            "foods": summary["food_lines"] if summary["food_lines"] else [" - None"],
            "memories_title": [I18n.t("OUTPUT_memories_title")],
            "memories": summary["memory_lines"] if summary["memory_lines"] else [" - None"],
            "items": [I18n.t("OUTPUT_items_needed", count=summary["total_items_count"])],
            "stats_title": [I18n.t("OUTPUT_stats_title")],
            "stats": stats_lines if stats_lines else [" - None"],
            "buildable_title": [I18n.t("OUTPUT_buildable_title")],
            "buildable": buildable_lines if buildable_lines else [" - None"],
        }

    @staticmethod
    def pad_lines(lines: List[str], height: int) -> List[str]:
        return lines + [""] * (height - len(lines))

    @staticmethod
    def render_parallel_section(section_name: str, chunk_sections: List[dict], block_width: int, gap: int):
        max_height = max(len(section[section_name]) for section in chunk_sections)
        padded_sections = [SummaryRenderer.pad_lines(section[section_name], max_height) for section in chunk_sections]
        for line_idx in range(max_height):
            row_line = (" " * gap).join(SummaryRenderer.visual_ljust(section_lines[line_idx], block_width) for section_lines in padded_sections)

            managers.LOG_MANAGER.print(row_line.rstrip())

    @staticmethod
    def print_summary(summary_results: List[dict]):
        if not summary_results:
            return

        managers.LOG_MANAGER.print("\n" * 2 + "=" * 100)
        managers.LOG_MANAGER.print(I18n.t("SUM_summary"))
        managers.LOG_MANAGER.print("=" * 100 + "\n")

        block_width, gap = 38, 3
        items_per_row = managers.CONFIG.summary_items_per_row
        all_sections = [SummaryRenderer.build_summary_sections(summary) for summary in summary_results]
        ordered_section_names = ["title", "divider", "foods_title", "foods", "memories_title", "memories", "items", "stats_title", "stats", "buildable_title", "buildable"]

        for i in range(0, len(all_sections), items_per_row):
            chunk = all_sections[i : i + items_per_row]

            for section_name in ordered_section_names:
                SummaryRenderer.render_parallel_section(section_name, chunk, block_width, gap)
                if section_name in {"foods", "memories", "items", "stats"}:
                    managers.LOG_MANAGER.print("")

            line_length = (block_width + gap) * len(chunk) - gap
            managers.LOG_MANAGER.print("." * max(line_length, 0))


class SolverEngine:
    def __init__(self, prof_service: ProfessionService):
        self.prof_service = prof_service

    @staticmethod
    def build_solver_items(foods: pd.DataFrame, memories: pd.DataFrame, target_stats: np.ndarray) -> List[SolverItem]:
        available_items: List[SolverItem] = []
        for _, row in foods.iterrows():
            if row.get("available", False):
                available_items.append(SolverItem(name=row["Name"], count=int(row["Count"]), stats=row[ALL_STAT_COLS].to_numpy(dtype=int), priority=float(row["Priority"]), category="food"))

        for _, row in memories.iterrows():
            if row.get("available", False):
                available_items.append(SolverItem(name=row["Name"], count=int(row["Count"]), stats=row[ALL_STAT_COLS].to_numpy(dtype=int), priority=float(row["Priority"]), category="memory"))

        target_mask = target_stats > 0

        return [item for item in available_items if item.count > 0 and np.any(item.stats[target_mask] > 0)]

    @staticmethod
    def compute_big_m(useful_items: List[SolverItem], stat_idx: int, raw_bad_req: int) -> int:
        max_total_stat = sum(int(item.stats[stat_idx]) * int(item.count) for item in useful_items if int(item.stats[stat_idx]) > 0 and int(item.count) > 0)
        return max(0, max_total_stat - (raw_bad_req - 1))

    def solve_target(self, target_info: TargetInfo, useful_items: List[SolverItem]):
        run_id = uuid.uuid4().hex[:8]

        prob = pulp.LpProblem("LastCaretaker", pulp.LpMinimize)
        x = {i: pulp.LpVariable(f"x_{run_id}_{i}", lowBound=0, upBound=useful_items[i].count, cat=pulp.LpInteger) for i in range(len(useful_items))}
        total_stats = {k: pulp.lpSum(x[i] * useful_items[i].stats[k] for i in range(len(useful_items))) for k in range(len(ALL_STAT_COLS))}
        excess_vars = []
        for k in range(len(ALL_STAT_COLS)):
            if target_info.stats[k] > 0:
                raw_req = StatConverter.to_raw_requirement(int(target_info.stats[k]))
                excess = pulp.LpVariable(f"e_{run_id}_{k}", lowBound=0, cat=pulp.LpContinuous)
                excess_vars.append(excess)
                prob += total_stats[k] >= raw_req
                prob += total_stats[k] - raw_req == excess

        total_excess = pulp.lpSum(excess_vars)
        renewable_food_usage = pulp.lpSum(x[i] for i in range(len(useful_items)) if useful_items[i].category == "food" and float(useful_items[i].priority) == 1)
        non_renewable_penalty = pulp.lpSum(x[i] * useful_items[i].priority for i in range(len(useful_items)) if not (useful_items[i].category == "food" and float(useful_items[i].priority) == 1))
        total_items = pulp.lpSum(x[i] for i in range(len(useful_items)))
        prob.setObjective(PRIORITY_WEIGHT * non_renewable_penalty + ITEM_COUNT_WEIGHT * total_items + total_excess - 0.1 * renewable_food_usage)

        attempt = 1
        seen_bad_jobs = set()
        while managers.CONFIG.unlimited_search or attempt <= managers.CONFIG.max_attempts:
            managers.LOG_MANAGER.increase_attempt()
            try:
                prob.solve(pulp.PULP_CBC_CMD(msg=False))
            except Exception as e:
                managers.LOG_MANAGER.print(I18n.t("ERR_solver_start_fail") + str(e))
                return "IMPOSSIBLE", None

            if pulp.LpStatus[prob.status] != "Optimal":
                return "IMPOSSIBLE", None

            counts = {i: int(round(x[i].varValue)) for i in range(len(useful_items)) if x[i].varValue is not None and x[i].varValue > 0.5}

            current_stats = np.zeros(len(ALL_STAT_COLS), dtype=int)
            food_lines, memory_lines = [], []
            total_items_count = 0
            for i, count in counts.items():
                item = useful_items[i]
                current_stats += item.stats * count
                total_items_count += count
                line = f" - {I18n.display_item_name(item.name)} x{count}"
                if item.category == "food":
                    food_lines.append(line)
                else:
                    memory_lines.append(line)

            triggered_profs = self.prof_service.compute_triggered_professions(current_stats)
            allowed_jobs = self.prof_service.get_allowed_jobs(target_info)
            collateral_rows = [p for p in triggered_profs if p[0] not in allowed_jobs]
            collateral_names = [p[0] for p in collateral_rows]

            if not collateral_rows:
                return "SUCCESS", {
                    "target_info": target_info,
                    "food_lines": food_lines,
                    "memory_lines": memory_lines,
                    "total_items_count": total_items_count,
                    "current_stats": current_stats,
                    "target_stats": target_info.stats,
                    "triggered_profs": triggered_profs,
                    "used_counts": {(useful_items[i].name, useful_items[i].category): count for i, count in counts.items()},
                    "renewable_food_usage": int(round(pulp.value(renewable_food_usage) or 0)),
                    "total_excess": float(pulp.value(total_excess) or 0.0),
                    "non_renewable_penalty": float(pulp.value(non_renewable_penalty) or 0.0),
                }

            managers.LOG_MANAGER.print(I18n.t("RESULT_invalid_combination", attempt=attempt), not managers.CONFIG.log_mode)
            managers.LOG_MANAGER.print("-" * 100, not managers.CONFIG.log_mode)

            managers.LOG_MANAGER.print(f"{I18n.t('OUTPUT_foods_title')}", not managers.CONFIG.log_mode)
            for line in food_lines or [" - None"]:
                managers.LOG_MANAGER.print(line, not managers.CONFIG.log_mode)

            managers.LOG_MANAGER.print(f"\n{I18n.t('OUTPUT_memories_title')}", not managers.CONFIG.log_mode)
            for line in memory_lines or [" - None"]:
                managers.LOG_MANAGER.print(line, not managers.CONFIG.log_mode)

            translated_collaterals = [I18n.display_profession_name(p) for p in collateral_names]

            managers.LOG_MANAGER.print(I18n.t("RESULT_reason", targets=", ".join(translated_collaterals)), not managers.CONFIG.log_mode)
            managers.LOG_MANAGER.print("", False)

            managers.LOG_MANAGER.print("\n" * 2 + "X" * 100, not managers.CONFIG.log_mode, False)
            managers.LOG_MANAGER.print(I18n.t("RESULT_retrying"), not managers.CONFIG.log_mode, False)
            managers.LOG_MANAGER.print("X" * 100 + "\n", not managers.CONFIG.log_mode, False)

            bad_job_idx = collateral_rows[0][3]
            bad_req = tuple(int(v) for v in self.prof_service.meta.matrix[bad_job_idx].tolist())
            if bad_req in seen_bad_jobs:
                return "IMPOSSIBLE", None

            seen_bad_jobs.add(bad_req)

            y_vars = []
            for k in range(len(ALL_STAT_COLS)):
                if bad_req[k] > 0:
                    raw_bad_req = StatConverter.to_raw_requirement(int(bad_req[k]))
                    y_var = pulp.LpVariable(f"fail_{run_id}_{attempt}_{k}", cat=pulp.LpBinary)
                    y_vars.append(y_var)
                    prob += total_stats[k] <= (raw_bad_req - 1) + self.compute_big_m(useful_items, k, raw_bad_req) * (1 - y_var)

            if not y_vars:
                return "IMPOSSIBLE", None

            prob += pulp.lpSum(y_vars) >= 1
            attempt += 1

        return "TIMEOUT", None

    def find_combination(self, target_info: TargetInfo, foods: pd.DataFrame, memories: pd.DataFrame, inv_df: pd.DataFrame, session_timestamp: str = None) -> Tuple[Optional[str], Optional[dict]]:
        useful_items = self.build_solver_items(foods, memories, target_info.stats)
        if not useful_items:
            return "NOT_ENOUGH_ITEMS", None

        result_status, result = self.solve_target(target_info, useful_items)
        if result_status != "SUCCESS" or result is None:
            if result_status == "IMPOSSIBLE":
                managers.LOG_MANAGER.print(I18n.t("FAILED_no_valid_combo"))
            elif result_status == "TIMEOUT":
                managers.LOG_MANAGER.print(I18n.t("FAILED_attempt_limit", max_attempts=managers.CONFIG.max_attempts))

            return result_status, None

        SummaryRenderer.print_success(
            target_info=result["target_info"],
            food_lines=result["food_lines"],
            memory_lines=result["memory_lines"],
            total_items_count=result["total_items_count"],
            current_stats=result["current_stats"],
            target_stats=result["target_stats"],
            triggered_profs=result["triggered_profs"],
        )
        return "SUCCESS", result
