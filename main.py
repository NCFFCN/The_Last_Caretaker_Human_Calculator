import datetime
import os
import re
import sys
import pulp
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Tuple
from translations import (
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


@dataclass
class SolverItem:
    name: str
    count: int
    stats: np.ndarray
    priority: float
    Kind: str


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


def normalize_profession_input(user_input: str, prof_df: pd.DataFrame) -> str:
    user_input_lower = user_input.strip().lower()

    reverse_map = {str(v).lower(): str(k) for k, v in PROFESSION_TRANSLATIONS.get(LANG, {}).items()}

    if user_input_lower in reverse_map:
        return reverse_map[user_input_lower]

    if user_input_lower in prof_df["Profession"].str.lower().values:
        return user_input.strip()

    def remove_tier(name: str) -> str:
        return re.sub(r"\s*t\d+$", "", str(name), flags=re.IGNORECASE).strip()

    user_input_base = remove_tier(user_input_lower)

    for raw_name in prof_df["Profession"]:
        raw_name_str = str(raw_name)
        translated_name = display_profession_name(raw_name_str).lower()

        if (
            remove_tier(translated_name) == user_input_base
            or remove_tier(raw_name_str.lower()) == user_input_base
        ):
            return raw_name_str

    return user_input.strip()


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

    if "Profession" in df.columns:
        df["Profession"] = df["Profession"].astype(str).str.strip()

    if "Category" in df.columns:
        df["Category"] = df["Category"].astype(str).str.strip()

    for col in ALL_STAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    return df


def normalize_items(df: pd.DataFrame, source_col: str) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={source_col: "Name"})

    if "Name" in df.columns:
        df["Name"] = df["Name"].astype(str).str.strip()

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

    if "Name" in df.columns:
        df["Name"] = df["Name"].astype(str).str.strip()

    if "Kind" in df.columns:
        df["Kind"] = df["Kind"].astype(str).str.strip().str.lower()

    if "Count" in df.columns:
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)
    else:
        df["Count"] = 0

    return df


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    human_file = resolve_existing_file(["Human.csv", "human.csv", "Humans.csv", "humans.csv"])
    food_file = resolve_existing_file(["Food.csv", "food.csv", "Foods.csv", "foods.csv"])
    memory_file = resolve_existing_file(["Memory.csv", "memory.csv", "Memories.csv", "memories.csv"])
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
            missing.append(path if path else "Inventory.csv, Food.csv, Memories.csv, Humans.csv")

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
        result["Count"] = 0
        result["available"] = True
        result["Kind"] = kind_filter.lower()
        return result

    inv = inventory_df.copy()
    inv = inv[inv["Kind"] == kind_filter.lower()]
    merged = items_df.merge(inv[["Name", "Count"]], on="Name", how="left")
    merged["Count"] = merged["Count"].fillna(0).astype(int)
    merged["available"] = merged["Count"] > 0
    merged["Kind"] = kind_filter.lower()

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
    target_row = professions.loc[professions["Profession"].str.lower() == target_profession.strip().lower()]

    if target_row.empty:
        return None

    row = target_row.iloc[0]
    target_name = row["Profession"]

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
                    name=row["Name"],
                    count=int(row["Count"]),
                    stats=row[ALL_STAT_COLS].to_numpy(dtype=int),
                    priority=float(row["Priority"]),
                    Kind="food",
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
                    Kind="memory",
                )
            )

    target_mask = target_stats > 0
    useful_items = [item for item in available_items if np.any(item.stats[target_mask] > 0)]

    return useful_items


def get_allowed_jobs(professions: pd.DataFrame, target: TargetInfo) -> List[str]:
    allowed_jobs = []
    for _, row in professions.iterrows():
        name = row["Profession"]
        category = row["Category"]
        tier = get_tier(name)

        if name == target.name or (category == target.category and tier < target.tier):
            allowed_jobs.append(name)

    return allowed_jobs


def compute_triggered_professions(
    current_stats: np.ndarray,
    professions: pd.DataFrame,
    target_name: str | None = None,
) -> List[Tuple[str, str, int, int]]:
    prof_matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)
    prof_names = professions["Profession"].tolist()
    prof_categories = professions["Category"].tolist()

    triggered = []
    for i in range(len(prof_matrix)):
        name = prof_names[i]
        category = prof_categories[i]

        if name == "Star Child" and target_name != "Star Child":
            continue

        requirements = prof_matrix[i]
        if np.sum(requirements) > 0 and all(
            current_stats[j] >= requirements[j] for j in range(len(requirements)) if requirements[j] > 0
        ):
            triggered.append((name, category, get_tier(name), i))

    triggered.sort(key=lambda item: (-item[2], item[0]))
    return triggered


def print_success(
    target_info: TargetInfo,
    food_lines: List[str],
    memory_lines: List[str],
    total_items_count: int,
    current_stats: np.ndarray,
    target_stats: np.ndarray,
    triggered_profs: List[Tuple[str, str, int, int]],
):
    print(f"\n{t('success', category=display_category_name(target_info.category))}")
    print(display_profession_name(target_info.name))
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

    print("\n" + "%" * 70)


def save_inventory(inventory_df: pd.DataFrame, used_counts: dict):
    updated = inventory_df.copy()

    for item_name, used_count in used_counts.items():
        mask = updated["Name"].str.lower() == item_name.lower()
        updated.loc[mask, "Count"] = updated.loc[mask, "Count"] - used_count

    updated["Count"] = updated["Count"].clip(lower=0)

    if not SAVE_AS_NEW_FILE:
        output_path = "Inventory.csv"
    else:
        output_path = f"Inventory2_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

    updated.to_csv(output_path, sep=";", index=False)

    return updated


def find_combination(
    target_profession: str,
    professions: pd.DataFrame,
    foods: pd.DataFrame,
    memories: pd.DataFrame,
    inv_df: pd.DataFrame,
) -> Tuple[Optional[str], Optional[dict]]:
    professions = professions.copy()
    professions["Profession"] = professions["Profession"].astype(str).str.strip()

    target_info = get_target_info(professions, target_profession)
    if target_info is None:
        return None, None

    useful_items = build_solver_items(foods, memories, target_info.stats)
    if not useful_items:
        return "NO_STATS", None

    allowed_jobs = get_allowed_jobs(professions, target_info)
    prob = pulp.LpProblem("LastCaretaker", pulp.LpMinimize)

    x = {
        i: pulp.LpVariable(f"x_{i}", lowBound=0, upBound=useful_items[i].count, cat=pulp.LpInteger)
        for i in range(len(useful_items))
    }

    total_stats = {
        k: pulp.lpSum(x[i] * useful_items[i].stats[k] for i in range(len(useful_items)))
        for k in range(len(ALL_STAT_COLS))
    }

    excess_vars = []
    for k in range(len(ALL_STAT_COLS)):
        if target_info.stats[k] > 0:
            excess = pulp.LpVariable(f"e_{k}", lowBound=0, cat=pulp.LpContinuous)
            excess_vars.append(excess)
            prob += total_stats[k] >= target_info.stats[k]
            prob += total_stats[k] - target_info.stats[k] == excess

    priority_penalty = pulp.lpSum(x[i] * useful_items[i].priority for i in range(len(useful_items)))
    total_items = pulp.lpSum(x[i] for i in range(len(useful_items)))
    prob += PRIORITY_WEIGHT * priority_penalty + ITEM_COUNT_WEIGHT * total_items + pulp.lpSum(excess_vars)

    attempt = 1
    seen_bad_jobs = set()
    prof_matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)

    while UNLIMITED_SEARCH or attempt <= MAX_ATTEMPTS:
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[prob.status] != "Optimal":
            print(t("failed_no_valid_combo"))
            return "IMPOSSIBLE", None

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
            if item.Kind == "food":
                food_lines.append(line)
            else:
                memory_lines.append(line)

        triggered_profs = compute_triggered_professions(current_stats, professions)
        collaterals = [p[0] for p in triggered_profs if p[0] not in allowed_jobs]

        if not collaterals:
            print_success(
                target_info=target_info,
                food_lines=food_lines,
                memory_lines=memory_lines,
                total_items_count=total_items_count,
                current_stats=current_stats,
                target_stats=target_info.stats,
                triggered_profs=triggered_profs,
            )

            used_counts = {useful_items[i].name: count for i, count in counts.items()}

            if DEDUCT_INVENTORY:
                save_inventory(inv_df, used_counts)

            return "SUCCESS", used_counts

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
        print(f"\n{t('reason', targets=', '.join(translated_collaterals))}")
        print("\n" * 2 + "X" * 70 + f"\n{t('retrying')}\n" + "X" * 70 + "\n")

        bad_job_idx = next(p[3] for p in triggered_profs if p[0] in collaterals)
        bad_req = tuple(int(v) for v in prof_matrix[bad_job_idx].tolist())

        if bad_req in seen_bad_jobs:
            print(t("failed_no_pure_route", category=display_category_name(target_info.category)))
            return "IMPOSSIBLE", None

        seen_bad_jobs.add(bad_req)

        y_vars = []
        for k in range(len(ALL_STAT_COLS)):
            if bad_req[k] > 0:
                y_var = pulp.LpVariable(f"fail_{attempt}_{k}", cat=pulp.LpBinary)
                y_vars.append(y_var)
                prob += total_stats[k] <= (bad_req[k] - 1) + BIG_M * (1 - y_var)

        prob += pulp.lpSum(y_vars) >= 1
        attempt += 1

    print(t("failed_attempt_limit", max_attempts=MAX_ATTEMPTS))
    return "IMPOSSIBLE", None


def visual_ljust(text: str, width: int) -> str:
    vis_len = sum(2 if ord(c) > 127 else 1 for c in text)
    return text + " " * max(0, width - vis_len)


def format_summary_rows(items: List[str], items_per_row: int, col_width: int = 38) -> List[str]:
    if not items:
        return [" - None"]

    rows = []
    for i in range(0, len(items), items_per_row):
        chunk = items[i : i + items_per_row]
        row = "".join(visual_ljust(item, col_width) for item in chunk)
        rows.append(row.rstrip())
    return rows


def build_summary_for_target(
    target: str,
    prof_df: pd.DataFrame,
    food_df: pd.DataFrame,
    mem_df: pd.DataFrame,
    inv_df: pd.DataFrame,
):
    avail_foods = apply_inventory(food_df, inv_df, "food")
    avail_mems = apply_inventory(mem_df, inv_df, "memory")
    normalized_target = normalize_profession_input(target, prof_df)

    professions = prof_df.copy()
    professions["Profession"] = professions["Profession"].astype(str).str.strip()

    target_info = get_target_info(professions, normalized_target)
    if target_info is None:
        return None

    useful_items = build_solver_items(avail_foods, avail_mems, target_info.stats)
    if not useful_items:
        return None

    allowed_jobs = get_allowed_jobs(professions, target_info)
    prob = pulp.LpProblem("LastCaretakerSummary", pulp.LpMinimize)

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
        if target_info.stats[k] > 0:
            excess = pulp.LpVariable(f"e_{k}", lowBound=0, cat=pulp.LpContinuous)
            excess_vars.append(excess)
            prob += total_stats[k] >= target_info.stats[k]
            prob += total_stats[k] - target_info.stats[k] == excess

    priority_penalty = pulp.lpSum(x[i] * useful_items[i].priority for i in range(len(useful_items)))
    total_items = pulp.lpSum(x[i] for i in range(len(useful_items)))
    prob += PRIORITY_WEIGHT * priority_penalty + ITEM_COUNT_WEIGHT * total_items + pulp.lpSum(excess_vars)

    attempt = 1
    seen_bad_jobs = set()
    prof_matrix = professions[ALL_STAT_COLS].to_numpy(dtype=int)

    while UNLIMITED_SEARCH or attempt <= MAX_ATTEMPTS:
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[prob.status] != "Optimal":
            return None

        counts = {}
        for i in range(len(useful_items)):
            value = x[i].varValue
            if value is not None and value > 0.5:
                counts[i] = int(round(value))

        current_stats = np.zeros(len(ALL_STAT_COLS), dtype=int)
        food_items = []
        memory_items = []
        total_items_count = 0

        for i, count in counts.items():
            item = useful_items[i]
            current_stats += item.stats * count
            total_items_count += count
            line = f" - {display_item_name(item.name)} x{count}"
            if item.Kind == "food":
                food_items.append(line)
            else:
                memory_items.append(line)

        triggered_profs = compute_triggered_professions(current_stats, professions)
        collaterals = [p for p in triggered_profs if p[0] not in allowed_jobs and p[1] != "Special"]

        if not collaterals:
            return {
                "target_info": target_info,
                "food_items": food_items,
                "memory_items": memory_items,
                "total_items_count": total_items_count,
                "current_stats": current_stats,
                "target_stats": target_info.stats,
                "triggered_profs": triggered_profs,
                "used_counts": {useful_items[i].name: count for i, count in counts.items()},
            }

        bad_job_idx = collaterals[0][3]
        bad_req = tuple(int(v) for v in prof_matrix[bad_job_idx].tolist())

        if bad_req in seen_bad_jobs:
            return None

        seen_bad_jobs.add(bad_req)

        y_vars = []
        for k in range(len(ALL_STAT_COLS)):
            if bad_req[k] > 0:
                y_var = pulp.LpVariable(f"fail_{attempt}_{k}", cat=pulp.LpBinary)
                y_vars.append(y_var)
                prob += total_stats[k] <= (bad_req[k] - 1) + BIG_M * (1 - y_var)

        prob += pulp.lpSum(y_vars) >= 1
        attempt += 1

    return None


def build_summary_sections(summary: dict) -> dict:
    target_info = summary["target_info"]

    stats_lines = []
    for k in range(len(ALL_STAT_COLS)):
        if summary["target_stats"][k] > 0:
            stat_name = display_stat_name(ALL_STAT_COLS[k])
            stats_lines.append(f" - {stat_name}: {summary['current_stats'][k]}/{summary['target_stats'][k]}")

    buildable_lines = [f" - {display_profession_name(p[0])}" for p in summary["triggered_profs"]]

    return {
        "title": [display_profession_name(target_info.name)],
        "divider": ["-" * 30],
        "foods_title": [f"{t('foods')}"],
        "foods": summary["food_items"] if summary["food_items"] else [" - None"],
        "memories_title": [f"{t('memories')}"],
        "memories": summary["memory_items"] if summary["memory_items"] else [" - None"],
        "items": [t("items", count=summary["total_items_count"])],
        "stats_title": [f"{t('stats')}"],
        "stats": stats_lines if stats_lines else [" - None"],
        "buildable_title": [f"{t('buildable')}"],
        "buildable": buildable_lines if buildable_lines else [" - None"],
    }


def pad_lines(lines: List[str], height: int) -> List[str]:
    return lines + [""] * (height - len(lines))


def render_parallel_section(section_name: str, chunk_sections: List[dict], block_width: int, gap: int):
    max_height = max(len(section[section_name]) for section in chunk_sections)
    padded_sections = [pad_lines(section[section_name], max_height) for section in chunk_sections]

    for line_idx in range(max_height):
        row_line = (" " * gap).join(
            visual_ljust(section_lines[line_idx], block_width) for section_lines in padded_sections
        )
        print(row_line.rstrip())


def print_success_summary(summary_results: List[dict]):
    if not summary_results:
        return

    print("\n" + "=" * 70)
    print(f"{t('summary')}")
    print("=" * 70)

    block_width = 38
    gap = 4

    all_sections = [build_summary_sections(summary) for summary in summary_results]

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
            render_parallel_section(section_name, chunk, block_width, gap)

        print("\n" + "." * ((block_width + gap) * len(chunk)))


def print_profession_list(prof_df: pd.DataFrame):
    prof_view = prof_df.copy()
    prof_view["Tier"] = prof_view["Profession"].apply(get_tier)
    sorted_profs = prof_view.sort_values(by=["Category", "Tier", "Profession"])

    cat_to_profs = {}
    for _, row in sorted_profs.iterrows():
        cat = row["Category"]
        if cat not in cat_to_profs:
            cat_to_profs[cat] = []
        cat_to_profs[cat].append(display_profession_name(row["Profession"]))

    categories = list(cat_to_profs.keys())
    col_width = 38

    print(f"\n" + "=" * (col_width * min(3, len(categories))))
    print(f"  {t('profession_list')}")
    print("=" * (col_width * min(3, len(categories))))

    for i in range(0, len(categories), 3):
        chunk = categories[i : i + 3]

        header_line = ""
        for cat in chunk:
            cat_display = f"[{display_category_name(cat)}]"
            header_line += visual_ljust(cat_display, col_width)
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
                row_line += visual_ljust(item, col_width)
            print(row_line)

        print("\n" + "." * (col_width * len(chunk)))

    print("\n" * 2)


def main():
    prof_df, food_df, mem_df, inv_df = load_data()

    print(f"\n{t('title')}")

    while True:
        user_input = input(f"\n{t('prompt')} ").strip()

        if user_input.lower() == "q":
            break

        if user_input.lower() == "list":
            print_profession_list(prof_df)
            continue

        if user_input.lower() == "help":
            print(f"{t('help')}")
            continue

        if user_input.lower() == "reload":
            try:
                prof_df, food_df, mem_df, inv_df = load_data()
                print("\n" + "=" * 50)
                print(f"{t('csv_reloaded')}")
                print("=" * 50)
            except Exception as e:
                print(f"\n{t('read_fail'), e}")
            continue

        independent_calc = False
        if user_input.startswith("?"):
            independent_calc = True
            user_input = user_input[1:].strip()
            print(f"\n{t('inv_sep')}")

        targets = [t.strip() for t in user_input.replace("，", ",").split(",") if t.strip()]

        if not targets:
            continue

        current_inv_df = inv_df.copy()
        successful_targets = []

        for target in targets:
            if independent_calc:
                current_inv_df = inv_df.copy()

            avail_foods = apply_inventory(food_df, current_inv_df, "food")
            avail_mems = apply_inventory(mem_df, current_inv_df, "memory")

            normalized_target = normalize_profession_input(target, prof_df)

            print(f"\n" + "=" * 70)
            print(f"{t('calculating', target=target)}")
            print("=" * 70)

            result_status, used_counts = find_combination(
                normalized_target,
                prof_df,
                avail_foods,
                avail_mems,
                current_inv_df,
            )

            if result_status is None:
                print(t("not_found", target=target))
            elif result_status == "NO_STATS":
                print(t("no_stats"))
            elif result_status == "SUCCESS" and used_counts:
                successful_targets.append(target)

                if not independent_calc:
                    for item_name, count in used_counts.items():
                        mask = current_inv_df["Name"].str.lower() == item_name.lower()
                        current_inv_df.loc[mask, "Count"] -= count
                    current_inv_df["Count"] = current_inv_df["Count"].clip(lower=0)

        if SHOW_SUMMARY and successful_targets:
            summary_inv_df = inv_df.copy()
            summary_results = []

            for target in successful_targets:
                if independent_calc:
                    summary_inv_df = inv_df.copy()

                summary = build_summary_for_target(
                    target=target,
                    prof_df=prof_df,
                    food_df=food_df,
                    mem_df=mem_df,
                    inv_df=summary_inv_df,
                )
                if summary:
                    summary_results.append(summary)
                    if not independent_calc:
                        for item_name, count in summary["used_counts"].items():
                            mask = summary_inv_df["Name"].str.lower() == item_name.lower()
                            summary_inv_df.loc[mask, "Count"] -= count
                        summary_inv_df["Count"] = summary_inv_df["Count"].clip(lower=0)

            print_success_summary(summary_results)


if __name__ == "__main__":
    main()
