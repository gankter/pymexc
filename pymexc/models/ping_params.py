
from pydantic import BaseModel



class PingParams(BaseModel):
    ping_interval:int
    ping_message:str
    