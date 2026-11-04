"""Aplicación pura de efectos de una decisión sobre las 5 stats del mundo."""

from collections.abc import Mapping

STAT_KEYS: tuple[str, ...] = ("poblacion", "comida", "moral", "defensa", "oro")
STAT_MIN = 0
STAT_MAX = 100


def _clamp(value: int) -> int:
    return max(STAT_MIN, min(STAT_MAX, value))


def validate_effects(effects: Mapping[str, object]) -> None:
    """Falla rápido si los efectos traen stats desconocidas o deltas no enteros."""
    for key, delta in effects.items():
        if key not in STAT_KEYS:
            raise ValueError(f"Stat desconocida en los efectos: {key!r}")
        if isinstance(delta, bool) or not isinstance(delta, int):
            raise ValueError(f"El delta de {key!r} debe ser un entero, llegó {delta!r}")


def apply_effects(stats: Mapping[str, int], effects: Mapping[str, int]) -> dict[str, int]:
    """Devuelve unas stats nuevas con los deltas sumados y recortadas a 0–100.
    Nunca modifica `stats` ni `effects`."""
    validate_effects(effects)
    missing = [key for key in STAT_KEYS if key not in stats]
    if missing:
        raise ValueError(f"Faltan stats en el estado del mundo: {', '.join(missing)}")
    return {key: _clamp(int(stats[key]) + int(effects.get(key, 0))) for key in STAT_KEYS}
