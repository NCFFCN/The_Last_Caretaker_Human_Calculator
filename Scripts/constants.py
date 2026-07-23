CONFIG_FILE = "settings.json"

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

PRIORITY_WEIGHT = 1000
ITEM_COUNT_WEIGHT = 10

RAW_TO_EFF = {
    1: 1,
    2: 2,
    5: 3,
    9: 4,
    13: 5,
    19: 6,
    23: 7,
    29: 8,
    36: 9,
    43: 10,
    51: 11,
    59: 12,
    68: 13,
    77: 14,
    87: 15,
    97: 16,
    107: 17,
    118: 18,
    130: 19,
    142: 20,
    154: 21,
    167: 22,
    180: 23,
    193: 24,
    206: 25,
}
EFF_TO_RAW = {y_eff: n_raw for n_raw, y_eff in RAW_TO_EFF.items()}
