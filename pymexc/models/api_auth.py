from pydantic import BaseModel

class ApiAuth(BaseModel):
    api_key:str
    api_secret:str