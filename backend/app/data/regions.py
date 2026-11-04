"""Las 7 regiones de El Valle de la Grieta, espejo de frontend/public/mapa/map-data.json.

Un test (tests/test_decision_bank.py) comprueba que los nombres coinciden con el mapa.
"""

from types import MappingProxyType

REGION_NAMES: MappingProxyType[str, str] = MappingProxyType(
    {
        "plaza": "Plaza del Ciclo",
        "bahia": "Bahía del Gremio",
        "muralla": "Muralla del Norte",
        "cementerio": "Cementerio de la Grieta",
        "campos": "Campos y Molinos",
        "bosque": "Bosque de los Exploradores",
        "cumbres": "Cumbres Heladas",
    }
)
REGION_IDS: tuple[str, ...] = tuple(REGION_NAMES)


def region_name(region: str | None) -> str | None:
    """Nombre legible de la región, o None si no hay región o no se conoce."""
    if region is None:
        return None
    return REGION_NAMES.get(region)
