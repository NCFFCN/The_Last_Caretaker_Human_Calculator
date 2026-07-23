import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List


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
    has_requirements: np.ndarray
