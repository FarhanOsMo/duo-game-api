"""Element effectiveness (mirrors the game's getMultiplier in Luau)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# The game's Luau names these two explicitly: when one of them attacks an
# element that is strong against it, the hit is still Strong instead of
# Resisted. It is a rule in code, not in elements.json, so it lives here.
MUTUAL_STRONG_ELEMENTS = frozenset({"Light", "Dark"})


@dataclass(frozen=True)
class ElementChart:
    strong_against: Mapping[str, Sequence[str]]
    strong: float
    resisted: float
    neutral: float


def get_multiplier(chart: ElementChart, attack: str, defend: str) -> float:
    attack_strong = chart.strong_against.get(attack)
    defend_strong = chart.strong_against.get(defend)
    if attack_strong is None or defend_strong is None:
        # Unknown elements are neutral rather than an error, as in the game.
        return 1.0
    if defend in attack_strong:
        return chart.strong
    if attack in defend_strong:
        return chart.strong if attack in MUTUAL_STRONG_ELEMENTS else chart.resisted
    return chart.neutral


def effectiveness_matrix(chart: ElementChart) -> dict[str, dict[str, float]]:
    """Every attacker x defender pair, computed from the rules rather than stored."""
    names = sorted(chart.strong_against)
    return {a: {d: get_multiplier(chart, a, d) for d in names} for a in names}
