"""Zonas de La Última Luz: las 7 regiones de El Valle de la Grieta (map-data.json).

Cada ronda la niebla de la Grieta cubre una región, de fuera hacia dentro:
bahia → campos → bosque → cementerio → muralla → plaza (6 rondas). Las Cumbres
Heladas (`cumbres`) son la Arena: nunca caen y acogen la ronda final, la 7.
"""

ARENA = "cumbres"
FALL_ORDER: tuple[str, ...] = ("bahia", "campos", "bosque", "cementerio", "muralla", "plaza")
ZONE_IDS: tuple[str, ...] = (*FALL_ORDER, ARENA)
TOTAL_ROUNDS = len(ZONE_IDS)

ZONE_NAMES: dict[str, str] = {
    "plaza": "Plaza del Ciclo",
    "bahia": "Bahía del Gremio",
    "muralla": "Muralla del Norte",
    "cementerio": "Cementerio de la Grieta",
    "campos": "Campos y Molinos",
    "bosque": "Bosque de los Exploradores",
    "cumbres": "Cumbres Heladas",
}


def zone_for_round(round_number: int) -> str:
    """Zona donde se libra el duelo de la ronda `round_number` (1..TOTAL_ROUNDS)."""
    if not 1 <= round_number <= TOTAL_ROUNDS:
        raise ValueError(f"La ronda debe estar entre 1 y {TOTAL_ROUNDS}, llegó {round_number}")
    return ZONE_IDS[round_number - 1]


def zone_falls(zone: str) -> bool:
    """True si la zona queda cubierta por la niebla al resolverse su duelo."""
    return zone != ARENA
