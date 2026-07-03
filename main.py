import datetime
import os
import re
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pulp
from translations import (
    CATEGORY_TRANSLATIONS,
    ITEM_TRANSLATIONS,
    PROFESSION_TRANSLATIONS,
    STAT_TRANSLATIONS,
    TEXT,
)

ALL_STAT_COLS = [
    "Height",
    "Intellect",
    "Life Expectancy",
    "Strength",
    "Weight",
    "Adaptability",
    "Communication",
    "Creativity",
    "Discipline",
    "Empathy",
    "Focus",
    "Leadership",
    "Logic",
    "Patience",
    "Wisdom",
    "Star Child",
]

LANG = "en"  # Display language. "en" for English, "tc" for Traditional Chinese, "sc" for Simplified Chinese.

# True: Allow the solver to keep searching for alternative combinations indefinitely until a valid one is found.
# False: Stop after MAX_ATTEMPTS if there are no valid combinations.
UNLIMITED_SEARCH = False
MAX_ATTEMPTS = 20

# True: Deduct the used items from the inventory after a successful combination is found.
# False: Do not modify the inventory after a successful combination is found.
DEDUCT_INVENTORY = False

# True: Save the updated inventory to a new file.
# False: Overwrite the existing inventory file.
SAVE_AS_NEW_FILE = True

# True: Print summary of successful combinations after all targets are processed.
# False: Do not print summary.
SHOW_SUMMARY = True
SUMMARY_ITEMS_PER_ROW = 4

BIG_M = 10000
PRIORITY_WEIGHT = 1000000
ITEM_COUNT_WEIGHT = 10000

RAW_TO_EFF = {
    1: 1,
    2: 2,
    5: 3,
    9: 4,
    13: 5,
    19: 6,
    25: 7,
    31: 8,
    37: 9,
    43: 10,
    50: 11,
    57: 12,
    64: 13,
    71: 14,
    78: 15,
    86: 16,
    94: 17,
    102: 18,
    110: 19,
    119: 20,
    128: 21,
    137: 22,
    147: 23,
    158: 24,
    170: 25,
}
EFF_TO_RAW = {y_eff: n_raw for n_raw, y_eff in RAW_TO_EFF.items()}


@dataclass
class SolverItem:
    name: str
    count: int
    stats: np.ndarray
    priority: float
    category: str


@dataclass
class TargetInfo:
    name: str
    category: str
    tier: int
    stats: np.ndarray


@dataclass
class ProfessionMeta:
    df: pd.DataFrame
    matrix: np.ndarray
    names: List[str]
    categories: List[str]
    tiers: List[int]


class I18n:
    @staticmethod
    def t(key, **kwargs):
        return TEXT[LANG][key].format(**kwargs)

    @staticmethod
    def display_category_name(name):
        return CATEGORY_TRANSLATIONS.get(LANG, {}).get(name, name)

    @staticmethod
    def display_profession_name(name):
        return PROFESSION_TRANSLATIONS.get(LANG, {}).get(name, name)

    @staticmethod
    def display_item_name(name):
        return ITEM_TRANSLATIONS.get(LANG, {}).get(name, name)

    @staticmethod
    def display_stat_name(name):
        return STAT_TRANSLATIONS.get(LANG, {}).get(name, name)


class StatConverter:
    @staticmethod
    def to_effective_stat(raw_val: int) -> int:
        if raw_val <= 200:
            return raw_val

        n = raw_val - 200
        eff = 0

        for min_raw, y_eff in sorted(RAW_TO_EFF.items()):
            if n >= min_raw:
                eff = y_eff
            else:
                break

        return 200 + eff

    @staticmethod
    def to_raw_requirement(eff_val: int) -> int:
        if eff_val <= 200:
            return eff_val

        y = eff_val - 200
        return 200 + EFF_TO_RAW.get(y, y)


class CsvRepository:
    @staticmethod
    def resolve_existing_file(candidates: List[str]) -> Optional[str]:
        for filename in candidates:
            if os.path.exists(filename):
                return filename
        return None

    @staticmethod
    def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.map(lambda c: c.strip() if isinstance(c, str) else c)

        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                non_null_mask = df[col].notna()
                df.loc[non_null_mask, col] = df.loc[non_null_mask, col].map(
                    lambda value: value.strip() if isinstance(value, str) else value
                )

        return df

    @classmethod
    def read_csv_checked(cls, path: str) -> pd.DataFrame:
        df = pd.read_csv(path, sep=";", skipinitialspace=True)
        return cls.clean_text_columns(df)

    @staticmethod
    def normalize_humans(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "Profession" in df.columns:
            df["Profession"] = df["Profession"].fillna("").astype(str).str.strip()

        if "Category" in df.columns:
            df["Category"] = df["Category"].fillna("").astype(str).str.strip()

        for col in ALL_STAT_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            else:
                df[col] = 0

        return df

    @staticmethod
    def normalize_items(df: pd.DataFrame, source_col: str) -> pd.DataFrame:
        df = df.copy()
        df = df.rename(columns={source_col: "Name"})

        if "Name" in df.columns:
            df["Name"] = df["Name"].fillna("").astype(str).str.strip()

        for col in ALL_STAT_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            else:
                df[col] = 0

        if "Priority" in df.columns:
            df["Priority"] = pd.to_numeric(df["Priority"], errors="coerce").fillna(1)
        else:
            df["Priority"] = 1

        return df

    @staticmethod
    def normalize_inventory(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.rename(columns={"Category": "inv_category"})

        if "Name" in df.columns:
            df["Name"] = df["Name"].fillna("").astype(str).str.strip()

        if "inv_category" in df.columns:
            df["inv_category"] = df["inv_category"].fillna("").astype(str).str.strip().str.lower()
        else:
            df["inv_category"] = ""

        if "Count" in df.columns:
            df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)
        else:
            df["Count"] = 0

        return df.groupby(["Name", "inv_category"], as_index=False)["Count"].sum()

    @classmethod
    def load_data(cls) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        file_candidates = {
            "Humans": ["Human.csv", "human.csv", "Humans.csv", "humans.csv"],
            "Food": ["Food.csv", "food.csv", "Foods.csv", "foods.csv"],
            "Memories": ["Memory.csv", "memory.csv", "Memories.csv", "memories.csv"],
            "Inventory": ["Inventory.csv", "inventory.csv", "Inventories.csv", "inventories.csv"],
        }

        files = {
            label: cls.resolve_existing_file(candidates) for label, candidates in file_candidates.items()
        }
        missing = [
            f"{label}: {' / '.join(candidates)}"
            for label, candidates in file_candidates.items()
            if not files[label]
        ]

        if missing:
            print(I18n.t("missing_files", files=", ".join(missing)))
            sys.exit(1)

        humans = cls.normalize_humans(cls.read_csv_checked(files["Humans"]))
        foods = cls.normalize_items(cls.read_csv_checked(files["Food"]), "Food")
        memories = cls.normalize_items(cls.read_csv_checked(files["Memories"]), "Memory")
        inventory = cls.normalize_inventory(cls.read_csv_checked(files["Inventory"]))

        return humans, foods, memories, inventory


class ProfessionService:
    def __init__(self, prof_df: pd.DataFrame):
        self.prof_df = prof_df.copy()
        self.lookup = self.build_profession_lookup(self.prof_df)
        self.meta = self.build_profession_meta(self.prof_df)

    @staticmethod
    def get_tier(prof_name: str) -> int:
        match = re.search(r"\bT([1-5])\b", prof_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 5

    def build_profession_lookup(self, prof_df: pd.DataFrame):
        lookup = {}
        reverse_translate = {str(v).lower(): str(k) for k, v in PROFESSION_TRANSLATIONS.get(LANG, {}).items()}

        def remove_tier(name: str) -> str:
            return re.sub(r"\s*t\d+$", "", str(name), flags=re.IGNORECASE).strip()

        for raw_name in prof_df["Profession"].dropna().astype(str):
            raw_name = raw_name.strip()
            if not raw_name:
                continue

            raw_lower = raw_name.lower()
            lookup.setdefault(raw_lower, raw_name)
            lookup.setdefault(remove_tier(raw_lower), raw_name)

            translated = I18n.display_profession_name(raw_name).lower()
            lookup.setdefault(translated, raw_name)
            lookup.setdefault(remove_tier(translated), raw_name)

        for translated_lower, raw_name in reverse_translate.items():
            lookup.setdefault(translated_lower, raw_name)

        return lookup

    def normalize_input(self, user_input: str) -> str:
        user_input_lower = user_input.strip().lower()
        if user_input_lower in self.lookup:
            return self.lookup[user_input_lower]
        return user_input.strip()

    def build_profession_meta(self, prof_df: pd.DataFrame) -> ProfessionMeta:
        professions = prof_df.copy()
        professions["Profession"] = professions["Profession"].fillna("").astype(str).str.strip()
        professions["Category"] = professions["Category"].fillna("").astype(str).str.strip()

        names = professions["Profession"].tolist()
        categories = professions["Category"].tolist()
        tiers = [self.get_tier(name) for name in names]
        matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)

        return ProfessionMeta(
            df=professions,
            matrix=matrix,
            names=names,
            categories=categories,
            tiers=tiers,
        )

    def get_target_info(self, target_profession: str) -> Optional[TargetInfo]:
        target_lower = target_profession.strip().lower()

        for i, name in enumerate(self.meta.names):
            if name.lower() == target_lower:
                return TargetInfo(
                    name=name,
                    category=self.meta.categories[i],
                    tier=self.meta.tiers[i],
                    stats=self.meta.matrix[i].copy(),
                )

        return None

    def get_allowed_jobs(self, target: TargetInfo) -> List[str]:
        return [
            name
            for name, category, tier in zip(self.meta.names, self.meta.categories, self.meta.tiers)
            if name == target.name or (category == target.category and tier < target.tier)
        ]

    def compute_triggered_professions(
        self,
        current_stats: np.ndarray,
    ) -> List[Tuple[str, str, int, int]]:
        effective_stats = np.array(
            [StatConverter.to_effective_stat(int(s)) for s in current_stats], dtype=int
        )

        has_requirements = np.sum(self.meta.matrix, axis=1) > 0
        meets_requirements = np.all((self.meta.matrix <= 0) | (effective_stats >= self.meta.matrix), axis=1)
        matched_indices = np.where(has_requirements & meets_requirements)[0]

        triggered = [
            (self.meta.names[i], self.meta.categories[i], self.meta.tiers[i], int(i)) for i in matched_indices
        ]
        triggered.sort(key=lambda item: (-item[2], item[0]))
        return triggered

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
        print(f"{I18n.t('profession_list')}")
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

            print("\n" + "." * (col_width * len(chunk)))

        print("\n" * 2)


class InventoryService:
    @staticmethod
    def apply_inventory(
        items_df: pd.DataFrame, inventory_df: pd.DataFrame, category_filter: str
    ) -> pd.DataFrame:
        result = items_df.copy()
        normalized_category = category_filter.lower()

        if result.empty:
            result["Count"] = 0
            result["available"] = False
            result["inv_category"] = normalized_category
            result["_match_name"] = pd.Series(dtype=str)
            return result

        result["_match_name"] = result["Name"].fillna("").astype(str).str.lower()

        if inventory_df.empty:
            result["Count"] = 0
            result["available"] = False
            result["inv_category"] = normalized_category
            return result[result["available"]].copy()

        inv = inventory_df.copy()
        inv = inv[inv["inv_category"] == normalized_category]
        inv["_match_name"] = inv["Name"].fillna("").astype(str).str.lower()

        merged = result.merge(inv[["_match_name", "inv_category", "Count"]], on=["_match_name"], how="left")
        merged["Count"] = merged["Count"].fillna(0).astype(int)
        merged["available"] = merged["Count"] > 0
        merged["inv_category"] = merged["inv_category"].fillna(normalized_category)
        merged = merged.drop(columns=["_match_name"])

        return merged[merged["available"]].copy()

    @staticmethod
    def apply_used_counts_to_inventory(
        inventory_df: pd.DataFrame,
        used_counts: Dict[Tuple[str, str], int],
    ) -> pd.DataFrame:
        updated = inventory_df.copy()

        if updated.empty or not used_counts:
            return updated

        normalized_names = updated["Name"].fillna("").astype(str).str.lower()
        normalized_categories = updated["inv_category"].fillna("").astype(str).str.lower()

        for (item_name, item_category), used_count in used_counts.items():
            mask = (normalized_names == item_name.lower()) & (normalized_categories == item_category.lower())
            updated.loc[mask, "Count"] = updated.loc[mask, "Count"] - used_count

        updated["Count"] = updated["Count"].clip(lower=0)
        return updated

    @classmethod
    def save_inventory(
        cls,
        inventory_df: pd.DataFrame,
        used_counts: Dict[Tuple[str, str], int],
        session_timestamp: str = None,
    ):
        updated = cls.apply_used_counts_to_inventory(inventory_df, used_counts)

        if not SAVE_AS_NEW_FILE:
            output_path = "Inventory.csv"
        else:
            ts = session_timestamp or datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_path = f"Inventory2_{ts}.csv"

        updated.to_csv(output_path, sep=";", index=False)
        return updated


class SolverEngine:
    def __init__(self, profession_service: ProfessionService):
        self.profession_service = profession_service

    @staticmethod
    def build_solver_items(
        foods: pd.DataFrame, memories: pd.DataFrame, target_stats: np.ndarray
    ) -> List[SolverItem]:
        available_items: List[SolverItem] = []

        for _, row in foods.iterrows():
            if row["available"]:
                available_items.append(
                    SolverItem(
                        name=row["Name"],
                        count=int(row["Count"]),
                        stats=row[ALL_STAT_COLS].to_numpy(dtype=int),
                        priority=float(row["Priority"]),
                        category="food",
                    )
                )

        for _, row in memories.iterrows():
            if row["available"]:
                available_items.append(
                    SolverItem(
                        name=row["Name"],
                        count=int(row["Count"]),
                        stats=row[ALL_STAT_COLS].to_numpy(dtype=int),
                        priority=float(row["Priority"]),
                        category="memory",
                    )
                )

        target_mask = target_stats > 0
        useful_items = [
            item for item in available_items if item.count > 0 and np.any(item.stats[target_mask] > 0)
        ]
        return useful_items

    def solve_target(
        self,
        target_info: TargetInfo,
        useful_items: List[SolverItem],
        allowed_jobs: List[str],
        *,
        problem_name: str,
        exclude_special: bool,
        print_attempts: bool,
        fail_status: Optional[str],
        run_id: Optional[str] = None,
    ):
        run_id = run_id or uuid.uuid4().hex[:8]
        prob = pulp.LpProblem(problem_name, pulp.LpMinimize)

        x = {
            i: pulp.LpVariable(
                f"x_{run_id}_{i}",
                lowBound=0,
                upBound=useful_items[i].count,
                cat=pulp.LpInteger,
            )
            for i in range(len(useful_items))
        }

        total_stats = {
            k: pulp.lpSum(x[i] * useful_items[i].stats[k] for i in range(len(useful_items)))
            for k in range(len(ALL_STAT_COLS))
        }

        excess_vars = []
        for k in range(len(ALL_STAT_COLS)):
            if target_info.stats[k] > 0:
                raw_req = StatConverter.to_raw_requirement(int(target_info.stats[k]))
                excess = pulp.LpVariable(f"e_{run_id}_{k}", lowBound=0, cat=pulp.LpContinuous)
                excess_vars.append(excess)
                prob += total_stats[k] >= raw_req
                prob += total_stats[k] - raw_req == excess

        priority_penalty = pulp.lpSum(x[i] * useful_items[i].priority for i in range(len(useful_items)))
        total_items = pulp.lpSum(x[i] for i in range(len(useful_items)))
        prob += PRIORITY_WEIGHT * priority_penalty + ITEM_COUNT_WEIGHT * total_items + pulp.lpSum(excess_vars)

        attempt = 1
        seen_bad_jobs = set()

        while UNLIMITED_SEARCH or attempt <= MAX_ATTEMPTS:
            prob.solve(pulp.PULP_CBC_CMD(msg=False))

            if pulp.LpStatus[prob.status] != "Optimal":
                return fail_status, None

            counts = {}
            for i in range(len(useful_items)):
                value = x[i].varValue
                if value is not None and value > 0.5:
                    counts[i] = int(round(value))

            current_stats = np.zeros(len(ALL_STAT_COLS), dtype=int)
            food_lines = []
            memory_lines = []
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

            triggered_profs = self.profession_service.compute_triggered_professions(current_stats)
            if exclude_special:
                collateral_rows = [
                    p for p in triggered_profs if p[0] not in allowed_jobs and p[1] != "Special"
                ]
                collateral_names = [p[0] for p in collateral_rows]
            else:
                collateral_rows = [p for p in triggered_profs if p[0] not in allowed_jobs]
                collateral_names = [p[0] for p in collateral_rows]

            if not collateral_rows:
                return "SUCCESS", {
                    "target_info": target_info,
                    "food_lines": food_lines,
                    "memory_lines": memory_lines,
                    "food_items": food_lines,
                    "memory_items": memory_lines,
                    "total_items_count": total_items_count,
                    "current_stats": current_stats,
                    "target_stats": target_info.stats,
                    "triggered_profs": triggered_profs,
                    "used_counts": {
                        (useful_items[i].name, useful_items[i].category): count for i, count in counts.items()
                    },
                }

            if print_attempts:
                print(f"\n{I18n.t('evaluating')} - {attempt}")
                print("-" * 70)

                print(f"\n{I18n.t('foods')}")
                if food_lines:
                    for line in food_lines:
                        print(line)
                else:
                    print(" - None")

                print(f"\n{I18n.t('memories')}")
                if memory_lines:
                    for line in memory_lines:
                        print(line)
                else:
                    print(" - None")

                translated_collaterals = [I18n.display_profession_name(p) for p in collateral_names]
                print(f"\n{I18n.t('reason', targets=', '.join(translated_collaterals))}")
                print("\n" * 2 + "X" * 70 + f"\n{I18n.t('retrying')}\n" + "X" * 70 + "\n")

            bad_job_idx = collateral_rows[0][3]
            bad_req = tuple(int(v) for v in self.profession_service.meta.matrix[bad_job_idx].tolist())

            if bad_req in seen_bad_jobs:
                return fail_status, None

            seen_bad_jobs.add(bad_req)

            y_vars = []
            for k in range(len(ALL_STAT_COLS)):
                if bad_req[k] > 0:
                    raw_bad_req = StatConverter.to_raw_requirement(int(bad_req[k]))
                    y_var = pulp.LpVariable(f"fail_{run_id}_{attempt}_{k}", cat=pulp.LpBinary)
                    y_vars.append(y_var)
                    prob += total_stats[k] <= (raw_bad_req - 1) + BIG_M * (1 - y_var)

            if not y_vars:
                return fail_status, None

            prob += pulp.lpSum(y_vars) >= 1
            attempt += 1

        return fail_status, None

    def find_combination(
        self,
        target_profession: str,
        foods: pd.DataFrame,
        memories: pd.DataFrame,
        inv_df: pd.DataFrame,
        session_timestamp: str = None,
    ) -> Tuple[Optional[str], Optional[dict]]:
        target_info = self.profession_service.get_target_info(target_profession)
        if target_info is None:
            return None, None

        useful_items = self.build_solver_items(foods, memories, target_info.stats)
        if not useful_items:
            return "NO_STATS", None

        allowed_jobs = self.profession_service.get_allowed_jobs(target_info)
        result_status, result = self.solve_target(
            target_info,
            useful_items,
            allowed_jobs,
            problem_name="LastCaretaker",
            exclude_special=False,
            print_attempts=True,
            fail_status="IMPOSSIBLE",
        )

        if result_status != "SUCCESS" or result is None:
            if result_status == "IMPOSSIBLE":
                print(I18n.t("failed_no_valid_combo"))
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

        used_counts = result["used_counts"]

        if DEDUCT_INVENTORY:
            InventoryService.save_inventory(inv_df, used_counts, session_timestamp)

        return "SUCCESS", used_counts

    def build_summary(
        self,
        target: str,
        food_df: pd.DataFrame,
        mem_df: pd.DataFrame,
        inv_df: pd.DataFrame,
    ):
        avail_foods = InventoryService.apply_inventory(food_df, inv_df, "food")
        avail_mems = InventoryService.apply_inventory(mem_df, inv_df, "memory")
        normalized_target = self.profession_service.normalize_input(target)

        target_info = self.profession_service.get_target_info(normalized_target)
        if target_info is None:
            return None

        useful_items = self.build_solver_items(avail_foods, avail_mems, target_info.stats)
        if not useful_items:
            return None

        allowed_jobs = self.profession_service.get_allowed_jobs(target_info)
        result_status, result = self.solve_target(
            target_info,
            useful_items,
            allowed_jobs,
            problem_name="LastCaretakerSummary",
            exclude_special=True,
            print_attempts=False,
            fail_status=None,
        )

        if result_status != "SUCCESS" or result is None:
            return None

        return {
            "target_info": result["target_info"],
            "food_items": result["food_items"],
            "memory_items": result["memory_items"],
            "total_items_count": result["total_items_count"],
            "current_stats": result["current_stats"],
            "target_stats": result["target_stats"],
            "triggered_profs": result["triggered_profs"],
            "used_counts": result["used_counts"],
        }


class SummaryRenderer:
    @staticmethod
    def visual_ljust(text: str, width: int) -> str:
        vis_len = sum(2 if ord(c) > 127 else 1 for c in text)
        return text + " " * max(0, width - vis_len)

    @staticmethod
    def print_success(
        target_info: TargetInfo,
        food_lines: List[str],
        memory_lines: List[str],
        total_items_count: int,
        current_stats: np.ndarray,
        target_stats: np.ndarray,
        triggered_profs: List[Tuple[str, str, int, int]],
    ):
        print(f"\n{I18n.t('success', category=I18n.display_category_name(target_info.category))}")
        print(I18n.display_profession_name(target_info.name))
        print("-" * 70)

        print(f"\n{I18n.t('foods')}")
        if food_lines:
            for line in food_lines:
                print(line)
        else:
            print(" - None")

        print(f"\n{I18n.t('memories')}")
        if memory_lines:
            for line in memory_lines:
                print(line)
        else:
            print(" - None")

        print(f"\n{I18n.t('items', count=total_items_count)}")
        print(f"\n{I18n.t('stats')}")

        for k in range(len(ALL_STAT_COLS)):
            if target_stats[k] > 0:
                stat_name = I18n.display_stat_name(ALL_STAT_COLS[k])
                eff_current = StatConverter.to_effective_stat(int(current_stats[k]))
                print(
                    f"{I18n.t('display_stats', stat_name=stat_name, eff_current=eff_current, target_stats=target_stats[k], current_stats=current_stats[k])}"
                )

        print(f"\n{I18n.t('buildable')}")
        for p in triggered_profs:
            print(f" - {I18n.display_profession_name(p[0])}")

        print("\n" + "%" * 70)

    @staticmethod
    def build_summary_sections(summary: dict) -> dict:
        target_info = summary["target_info"]

        stats_lines = []
        for k in range(len(ALL_STAT_COLS)):
            if summary["target_stats"][k] > 0:
                stat_name = I18n.display_stat_name(ALL_STAT_COLS[k])
                eff_current = StatConverter.to_effective_stat(int(summary["current_stats"][k]))
                stats_lines.append(
                    I18n.t(
                        "display_stats",
                        stat_name=stat_name,
                        eff_current=eff_current,
                        target_stats=summary["target_stats"][k],
                        current_stats=summary["current_stats"][k],
                    )
                )

        buildable_lines = [f" - {I18n.display_profession_name(p[0])}" for p in summary["triggered_profs"]]

        return {
            "title": [I18n.display_profession_name(target_info.name)],
            "divider": ["-" * 30],
            "foods_title": [I18n.t("foods")],
            "foods": summary["food_items"] if summary["food_items"] else [" - None"],
            "memories_title": [I18n.t("memories")],
            "memories": summary["memory_items"] if summary["memory_items"] else [" - None"],
            "items": [I18n.t("items", count=summary["total_items_count"])],
            "stats_title": [I18n.t("stats")],
            "stats": stats_lines if stats_lines else [" - None"],
            "buildable_title": [I18n.t("buildable")],
            "buildable": buildable_lines if buildable_lines else [" - None"],
        }

    @staticmethod
    def pad_lines(lines: List[str], height: int) -> List[str]:
        return lines + [""] * (height - len(lines))

    @staticmethod
    def render_parallel_section(section_name: str, chunk_sections: List[dict], block_width: int, gap: int):
        max_height = max(len(section[section_name]) for section in chunk_sections)
        padded_sections = [
            SummaryRenderer.pad_lines(section[section_name], max_height) for section in chunk_sections
        ]

        for line_idx in range(max_height):
            row_line = (" " * gap).join(
                SummaryRenderer.visual_ljust(section_lines[line_idx], block_width)
                for section_lines in padded_sections
            )
            print(row_line.rstrip())

    @staticmethod
    def print_summary(summary_results: List[dict]):
        if not summary_results:
            return

        print("\n" + "=" * 70)
        print(f"{I18n.t('summary')}")
        print("=" * 70)

        block_width = 38
        gap = 4

        all_sections = [SummaryRenderer.build_summary_sections(summary) for summary in summary_results]
        ordered_section_names = [
            "title",
            "divider",
            "foods_title",
            "foods",
            "memories_title",
            "memories",
            "items",
            "stats_title",
            "stats",
            "buildable_title",
            "buildable",
        ]

        for i in range(0, len(all_sections), SUMMARY_ITEMS_PER_ROW):
            chunk = all_sections[i : i + SUMMARY_ITEMS_PER_ROW]

            print("")
            for section_name in ordered_section_names:
                SummaryRenderer.render_parallel_section(section_name, chunk, block_width, gap)

                if section_name in ["divider", "foods", "memories", "items", "stats"]:
                    print("")

            print("." * ((block_width + gap) * len(chunk)))


class App:
    def __init__(self):
        self.prof_df, self.food_df, self.mem_df, self.inv_df = CsvRepository.load_data()
        self.profession_service = ProfessionService(self.prof_df)
        self.solver_engine = SolverEngine(self.profession_service)

    def reload(self):
        self.prof_df, self.food_df, self.mem_df, self.inv_df = CsvRepository.load_data()
        self.profession_service = ProfessionService(self.prof_df)
        self.solver_engine = SolverEngine(self.profession_service)

    def run(self):
        print(f"\n{I18n.t('title')}")

        while True:
            user_input = input(f"\n{I18n.t('prompt')} ").strip()

            if user_input.lower() == "q":
                break

            if user_input.lower() == "list":
                self.profession_service.print_profession_list()
                continue

            if user_input.lower() == "help":
                print(f"{I18n.t('help')}")
                continue

            if user_input.lower() == "reload":
                try:
                    self.reload()
                    print("\n" + "=" * 50)
                    print(f"{I18n.t('csv_reloaded')}")
                    print("=" * 50)
                except Exception as e:
                    print(f"\n{I18n.t('read_fail')}: {e}")
                continue

            independent_calc = False
            if user_input.startswith("?"):
                independent_calc = True
                user_input = user_input[1:].strip()
                print(f"\n{I18n.t('inv_sep')}")

            targets = [
                target.strip() for target in user_input.replace("，", ",").split(",") if target.strip()
            ]
            if not targets:
                continue

            current_inv_df = self.inv_df.copy()
            successful_targets = []
            current_session_ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            for target in targets:
                if independent_calc:
                    current_inv_df = self.inv_df.copy()

                avail_foods = InventoryService.apply_inventory(self.food_df, current_inv_df, "food")
                avail_mems = InventoryService.apply_inventory(self.mem_df, current_inv_df, "memory")
                normalized_target = self.profession_service.normalize_input(target)

                print(f"\n" + "=" * 70)
                print(f"{I18n.t('calculating', target=target)}")
                print("=" * 70)

                result_status, used_counts = self.solver_engine.find_combination(
                    normalized_target,
                    avail_foods,
                    avail_mems,
                    current_inv_df,
                    current_session_ts,
                )

                if result_status is None:
                    print(I18n.t("not_found", target=target))
                elif result_status == "NO_STATS":
                    print(I18n.t("no_stats"))
                elif result_status == "SUCCESS" and used_counts:
                    successful_targets.append(target)

                    if not independent_calc:
                        current_inv_df = InventoryService.apply_used_counts_to_inventory(
                            current_inv_df, used_counts
                        )

            if SHOW_SUMMARY and successful_targets:
                summary_inv_df = self.inv_df.copy()
                summary_results = []

                for target in successful_targets:
                    if independent_calc:
                        summary_inv_df = self.inv_df.copy()

                    summary = self.solver_engine.build_summary(
                        target=target,
                        food_df=self.food_df,
                        mem_df=self.mem_df,
                        inv_df=summary_inv_df,
                    )
                    if summary:
                        summary_results.append(summary)
                        if not independent_calc:
                            summary_inv_df = InventoryService.apply_used_counts_to_inventory(
                                summary_inv_df,
                                summary["used_counts"],
                            )

                SummaryRenderer.print_summary(summary_results)


def main():
    App().run()


if __name__ == "__main__":
    main()
