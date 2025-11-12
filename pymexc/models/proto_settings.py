
#from pydantic import BaseModel
from dataclasses import dataclass

@dataclass
class ProtoSettings:
    proto: bool = True
    extend_proto_body:bool = False
    proto_bodies:dict = None
    
    def __post_init__(self):
        if self.proto and self.proto_bodies is None:
            raise ValueError("protobodies must be initialized")

