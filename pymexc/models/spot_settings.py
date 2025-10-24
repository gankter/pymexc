from pydantic import BaseModel

class SpotSettings(BaseModel):
    proto:bool = True
    