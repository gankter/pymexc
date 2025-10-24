
from pydantic import BaseModel

class ProxySettings1(BaseModel):
    http_proxy_host:str
    http_proxy_port:str
    http_no_proxy:bool
    http_proxy_auth:str
    http_proxy_timeout:int


from pydantic import BaseModel, ConfigDict, field_validator, HttpUrl
from typing import Optional
import re

class ProxySettings(BaseModel):
    host: str
    port: int
    protocol: str = "http"  # По умолчанию HTTP
    username: Optional[str] = None
    password: Optional[str] = None

    model_config = ConfigDict(
        extra="forbid",  # Запретить лишние поля
        str_strip_whitespace=True  # Удалять пробелы из строк
    )

    @field_validator("host")
    def validate_host(cls, v):
        # Проверка, что хост — это IP-адрес или доменное имя
        ip_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        domain_pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        if not (re.match(ip_pattern, v) or re.match(domain_pattern, v)):
            raise ValueError("Некорректный хост: должен быть IP-адресом или доменным именем")
        return v

    @field_validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Порт должен быть в диапазоне 1-65535")
        return v

    @field_validator("protocol")
    def validate_protocol(cls, v:str):
        valid_protocols = ["http", "https", "socks4", "socks5"]
        if v.lower() not in valid_protocols:
            raise ValueError(f"Протокол должен быть одним из: {', '.join(valid_protocols)}")
        return v.lower()

    def get_proxy_url(self) -> str:
        """Формирует URL прокси для использования в WebSocket."""
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"
    
    

# Пример использования
if __name__ == "__main__":
    import time
    try:
        # Корректные настройки
        start = time.perf_counter()
        proxy = ProxySettings(host="proxy.example.com", port=8080, protocol="https", username="user", password="pass")
        end = time.perf_counter()
        print((end-start)*1e6)
        start = time.perf_counter()
        url = proxy.host  # https://user:pass@proxy.example.com:8080
        end = time.perf_counter()
        print((end-start)*1e6)
        print(url)
        # Некорректный порт
        #invalid_proxy = ProxySettings(host="proxy.example.com", port=99999)
    except ValueError as e:
        print(f"Ошибка: {e}")