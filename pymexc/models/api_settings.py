import os
import hashlib
import hmac

from pydantic import BaseModel, field_validator, ValidationInfo
    
class ApiConfig(BaseModel):
    
    auth:bool = False
    api_key:str = None
    api_secret:str = None
    
    @field_validator("api_key","api_secret",mode="after")
    @classmethod
    def check_api_credentials(cls, value:str, info: ValidationInfo):
        """
        Проверяет, что api_key и api_secret не None и не пустые.
        """
        if not info.data["auth"]:
            return value

        if value is None or value.strip() == "":
            raise ValueError(f"api_key and api_secret must be initialized and non-empty")
        return value


    
    """def sign(self, query_string:str):
        
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature"""
    """@classmethod
    def from_env(cls) -> 'ApiAuth':
    
        #Создаёт экземпляр ApiAuth, загружая api_key и api_secret из .env файла.
        
        api_key = os.getenv("MEXC_API_KEY")
        api_secret = os.getenv("MEXC_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("API_KEY or API_SECRET not found in .env file")
        return cls(api_key=api_key, api_secret=api_secret)"""
    
    
if __name__ == "__main__":
    x = ApiConfig(auth=False, api_key="", api_secret="dsf43")
    print(x)