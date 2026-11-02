from pydantic import BaseModel


class WorldStateOut(BaseModel):
    season_number: int
    season_name: str
    phase: str
    poblacion: int
    comida: int
    moral: int
    defensa: int
    oro: int
