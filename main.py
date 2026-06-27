import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import pulp

from translations import (
    LANG,
    TEXT,
    CATEGORY_TRANSLATIONS,
    PROFESSION_TRANSLATIONS,
    ITEM_TRANSLATIONS,
    STAT_TRANSLATIONS,
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
]

# Setting to True will allow the solver to keep searching for alternative combinations indefinitely until a valid one is found.
UNLIMITED_SEARCH = True
MAX_ATTEMPTS = 10

# Setting to True will save the updated inventory to a new file named "Inventory2.csv" instead of overwriting the original inventory file.
SAVE_AS_NEW_FILE = True

BIG_M = 10000

PRIORITY_WEIGHT = 1000000
ITEM_COUNT_WEIGHT = 10000


@dataclass
class SolverItem:
    name: str
    count: int
    stats: np.ndarray
    priority: float
    kind: str


@dataclass
class TargetInfo:
    name: str
    category: str
    tier: int
    stats: np.ndarray


def t(key, **kwargs):
    return TEXT[LANG][key].format(**kwargs)


def display_category_name(name):
    return CATEGORY_TRANSLATIONS.get(LANG, {}).get(name, name)


def display_profession_name(name):
    return PROFESSION_TRANSLATIONS.get(LANG, {}).get(name, name)


def display_item_name(name):
    return ITEM_TRANSLATIONS.get(LANG, {}).get(name, name)


def display_stat_name(name):
    return STAT_TRANSLATIONS.get(LANG, {}).get(name, name)


def normalize_profession_input(user_input):
    user_input = user_input.strip()
    reverse_map = {v.lower(): k for k, v in PROFESSION_TRANSLATIONS.get(LANG, {}).items()}
    return reverse_map.get(user_input.lower(), user_input)


def resolve_existing_file(candidates: List[str]) -> Optional[str]:
    for filename in candidates:
        if os.path.exists(filename):
            return filename
    return None


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    return df


def read_csv_checked(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", skipinitialspace=True)
    return clean_text_columns(df)


def normalize_humans(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={"Profession": "profession"})

    if "profession" in df.columns:
        df["profession"] = df["profession"].astype(str).str.strip()

    for col in ALL_STAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    return df


def normalize_items(df: pd.DataFrame, source_col: str) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={source_col: "name"})

    if "name" in df.columns:
        df["name"] = df["name"].astype(str).str.strip()

    for col in ALL_STAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    if "Priority" in df.columns:
        df["Priority"] = pd.to_numeric(df["Priority"], errors="coerce").fillna(1)
    else:
        df["Priority"] = 1

    return df


def normalize_inventory(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={"Name": "name", "Count": "inventory_count", "Kind": "kind"})

    if "name" in df.columns:
        df["name"] = df["name"].astype(str).str.strip()

    if "kind" in df.columns:
        df["kind"] = df["kind"].astype(str).str.strip().str.lower()

    if "inventory_count" in df.columns:
        df["inventory_count"] = pd.to_numeric(df["inventory_count"], errors="coerce").fillna(0).astype(int)
    else:
        df["inventory_count"] = 0

    return df


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    human_file = resolve_existing_file(["Humans.csv", "humans.csv", "Human.csv", "human.csv"])
    food_file = resolve_existing_file(["Food.csv", "food.csv", "Foods.csv", "foods.csv"])
    memory_file = resolve_existing_file(["Memories.csv", "memories.csv", "Memory.csv", "memory.csv"])
    inventory_file = resolve_existing_file(
        ["Inventory.csv", "inventory.csv", "Inventories.csv", "inventories.csv"]
    )

    files = {
        "Humans": human_file,
        "Food": food_file,
        "Memories": memory_file,
        "Inventory": inventory_file,
    }

    missing = []
    for _, path in files.items():
        if not path or not os.path.exists(path):
            missing.append(path if path else "Inventory.csv or inventory.csv")

    if missing:
        print(t("missing_files", files=", ".join(missing)))
        sys.exit(1)

    humans = normalize_humans(read_csv_checked(files["Humans"]))
    foods = normalize_items(read_csv_checked(files["Food"]), "Food")
    memories = normalize_items(read_csv_checked(files["Memories"]), "Memory")
    inventory = normalize_inventory(read_csv_checked(files["Inventory"]))

    return humans, foods, memories, inventory


def apply_inventory(items_df: pd.DataFrame, inventory_df: pd.DataFrame, kind_filter: str) -> pd.DataFrame:
    if inventory_df.empty:
        result = items_df.copy()
        result["inventory_count"] = 0
        result["available"] = True
        result["kind"] = kind_filter.lower()
        return result

    inv = inventory_df.copy()
    inv = inv[inv["kind"] == kind_filter.lower()]
    merged = items_df.merge(inv[["name", "inventory_count"]], on="name", how="left")
    merged["inventory_count"] = merged["inventory_count"].fillna(0).astype(int)
    merged["available"] = merged["inventory_count"] > 0
    merged["kind"] = kind_filter.lower()

    return merged[merged["available"]].copy()


def get_tier(prof_name: str) -> int:
    if "T1" in prof_name:
        return 1
    if "T2" in prof_name:
        return 2
    if "T3" in prof_name:
        return 3
    if "T4" in prof_name:
        return 4
    return 5


def get_target_info(professions: pd.DataFrame, target_profession: str) -> Optional[TargetInfo]:
    target_row = professions.loc[professions["profession"].str.lower() == target_profession.strip().lower()]

    if target_row.empty:
        return None

    row = target_row.iloc[0]
    target_name = row["profession"]

    return TargetInfo(
        name=target_name,
        category=row["Category"],
        tier=get_tier(target_name),
        stats=row[ALL_STAT_COLS].to_numpy(dtype=int),
    )


def build_solver_items(
    foods: pd.DataFrame, memories: pd.DataFrame, target_stats: np.ndarray
) -> List[SolverItem]:
    available_items: List[SolverItem] = []

    for _, row in foods.iterrows():
        if row["available"]:
            available_items.append(
                SolverItem(
                    name=row["name"],
                    count=int(row["inventory_count"]),
                    stats=row[ALL_STAT_COLS].to_numpy(dtype=int),
                    priority=float(row["Priority"]),
                    kind="food",
                )
            )

    for _, row in memories.iterrows():
        if row["available"]:
            available_items.append(
                SolverItem(
                    name=row["name"],
                    count=int(row["inventory_count"]),
                    stats=row[ALL_STAT_COLS].to_numpy(dtype=int),
                    priority=float(row["Priority"]),
                    kind="memory",
                )
            )

    target_mask = target_stats > 0
    useful_items = [item for item in available_items if np.any(item.stats[target_mask] > 0)]

    return useful_items


def get_allowed_jobs(professions: pd.DataFrame, target: TargetInfo) -> List[str]:
    allowed_jobs = []
    for _, row in professions.iterrows():
        name = row["profession"]
        category = row["Category"]
        tier = get_tier(name)

        if name == target.name or (category == target.category and tier < target.tier):
            allowed_jobs.append(name)

    return allowed_jobs


def compute_triggered_professions(
    current_stats: np.ndarray,
    professions: pd.DataFrame,
) -> List[Tuple[str, str, int, int]]:
    prof_matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)
    prof_names = professions["profession"].tolist()
    prof_categories = professions["Category"].tolist()

    triggered = []
    for i in range(len(prof_matrix)):
        requirements = prof_matrix[i]
        if np.sum(requirements) > 0 and all(
            current_stats[j] >= requirements[j] for j in range(len(requirements)) if requirements[j] > 0
        ):
            triggered.append((prof_names[i], prof_categories[i], get_tier(prof_names[i]), i))

    triggered.sort(key=lambda item: (-item[2], item[0]))
    return triggered


def print_success(
    food_lines: List[str],
    memory_lines: List[str],
    total_items_count: int,
    current_stats: np.ndarray,
    target_stats: np.ndarray,
    triggered_profs: List[Tuple[str, str, int, int]],
):
    print(f"\n{t('success')}")
    print("-" * 70)

    print(f"\n{t('foods')}")
    for line in food_lines:
        print(line)

    print(f"\n{t('memories')}")
    for line in memory_lines:
        print(line)

    print(f"\n{t('items', count=total_items_count)}")
    print(f"\n{t('stats')}")

    for k in range(len(ALL_STAT_COLS)):
        if target_stats[k] > 0:
            stat_name = display_stat_name(ALL_STAT_COLS[k])
            print(f" - {stat_name}: {current_stats[k]}/{target_stats[k]}")

    print(f"\n{t('buildable')}")
    for p in triggered_profs:
        print(f" - {display_profession_name(p[0])}")


def ask_to_deduct_inventory() -> bool:
    answer = input(f"\n{t('deduct_inventory')} (y/N): ").strip().lower()
    return answer in ("y", "yes")


def save_inventory_change(inventory_df: pd.DataFrame, used_counts: dict, output_path: str):
    updated = inventory_df.copy()

    for item_name, used_count in used_counts.items():
        mask = updated["name"].str.lower() == item_name.lower()
        updated.loc[mask, "inventory_count"] = updated.loc[mask, "inventory_count"] - used_count

    updated["inventory_count"] = updated["inventory_count"].clip(lower=0)

    if not SAVE_AS_NEW_FILE:
        output_path = "Inventory.csv"
    else:
        output_path = "Inventory2.csv"

    updated.to_csv(output_path, sep=";", index=False)

    return updated


def solve_with_reasoning(
    target_profession: str,
    professions: pd.DataFrame,
    foods: pd.DataFrame,
    memories: pd.DataFrame,
    inv_df: pd.DataFrame,
) -> Optional[str]:
    professions = professions.copy()
    professions["profession"] = professions["profession"].astype(str).str.strip()

    target = get_target_info(professions, target_profession)
    if target is None:
        return None

    useful_items = build_solver_items(foods, memories, target.stats)
    if not useful_items:
        return "NO_STATS"

    allowed_jobs = get_allowed_jobs(professions, target)
    prob = pulp.LpProblem("LastCaretaker", pulp.LpMinimize)

    x = {
        i: pulp.LpVariable(
            f"x_{i}",
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
        if target.stats[k] > 0:
            excess = pulp.LpVariable(f"e_{k}", lowBound=0, cat=pulp.LpContinuous)
            excess_vars.append(excess)
            prob += total_stats[k] >= target.stats[k]
            prob += total_stats[k] - target.stats[k] == excess

    priority_penalty = pulp.lpSum(x[i] * useful_items[i].priority for i in range(len(useful_items)))
    total_items_var = pulp.lpSum(x[i] for i in range(len(useful_items)))
    prob += PRIORITY_WEIGHT * priority_penalty + ITEM_COUNT_WEIGHT * total_items_var + pulp.lpSum(excess_vars)

    attempt = 1
    seen_bad_jobs = set()
    prof_matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)

    while UNLIMITED_SEARCH or attempt <= MAX_ATTEMPTS:
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[prob.status] != "Optimal":
            print(t("failed_combo"))
            return "IMPOSSIBLE"

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
            line = f" - {display_item_name(item.name)} x{count}"
            if item.kind == "food":
                food_lines.append(line)
            else:
                memory_lines.append(line)

        food_lines.sort()
        memory_lines.sort()

        triggered_profs = compute_triggered_professions(current_stats, professions)
        collaterals = [p[0] for p in triggered_profs if p[0] not in allowed_jobs]

        if not collaterals:
            print_success(
                food_lines=food_lines,
                memory_lines=memory_lines,
                total_items_count=total_items_count,
                current_stats=current_stats,
                target_stats=target.stats,
                triggered_profs=triggered_profs,
            )

            if ask_to_deduct_inventory():
                used_counts = {useful_items[i].name: count for i, count in counts.items()}
                save_inventory_change(inv_df, used_counts)

            return "SUCCESS"

        print(f"\n{t('evaluating')} - {attempt}")
        print("-" * 70)

        print(f"\n{t('foods')}")
        if food_lines:
            for line in food_lines:
                print(line)
        else:
            print(" - None")

        print(f"\n{t('memories')}")
        if memory_lines:
            for line in memory_lines:
                print(line)
        else:
            print(" - None")

        translated_collaterals = [display_profession_name(p) for p in collaterals]
        print(f"\n{t('reason', jobs=', '.join(translated_collaterals))}\n")
        print(f"\n{t('retrying')}\n")

        bad_job_idx = next(p[3] for p in triggered_profs if p[0] in collaterals)
        bad_req = tuple(int(v) for v in prof_matrix[bad_job_idx].tolist())

        if bad_req in seen_bad_jobs:
            print(t("failed_combo"))
            return "IMPOSSIBLE"

        seen_bad_jobs.add(bad_req)

        y_vars = []
        for k in range(len(ALL_STAT_COLS)):
            if bad_req[k] > 0:
                y_var = pulp.LpVariable(f"fail_{attempt}_{k}", cat=pulp.LpBinary)
                y_vars.append(y_var)
                prob += total_stats[k] <= (bad_req[k] - 1) + BIG_M * (1 - y_var)

        prob += pulp.lpSum(y_vars) >= 1
        attempt += 1

    print(t("failed_combo"))
    return "IMPOSSIBLE"


def print_profession_list(prof_df: pd.DataFrame):
    prof_view = prof_df.copy()
    prof_view["Tier"] = prof_view["profession"].apply(get_tier)
    sorted_profs = prof_view.sort_values(by=["Category", "Tier", "profession"])

    current_cat = ""
    for _, row in sorted_profs.iterrows():
        if row["Category"] != current_cat:
            current_cat = row["Category"]
            print(f"\n{t('category_header', category=display_category_name(current_cat))}")
        print(f" - {display_profession_name(row['profession'])}")

    print("\n" * 3)


def main():
    prof_df, food_df, mem_df, inv_df = load_data()

    print(f"\n{t('title')}")

    while True:
        target = input(f"\n{t('prompt')} ").strip()

        if target.lower() == TEXT[LANG]["quit"]:
            break

        if target.lower() == TEXT[LANG]["list"]:
            print_profession_list(prof_df)
            continue

        normalized_target = normalize_profession_input(target)

        avail_foods = apply_inventory(food_df, inv_df, "food")
        avail_mems = apply_inventory(mem_df, inv_df, "memory")

        print(f"\n{t('calculating', target=target)}\n")
        result = solve_with_reasoning(
            normalized_target,
            prof_df,
            avail_foods,
            avail_mems,
            inv_df,
        )

        if result is None:
            print(t("not_found", target=target))
        elif result == "NO_STATS":
            print(t("no_stats"))


if __name__ == "__main__":
    main()
