



import hashlib
import hmac
import logging
import time
from abc import ABC
from typing import Literal, Union
from urllib.parse import urlencode

from curl_cffi import requests


WEB_ENDPOINT = "https://www.mexc.com/api"

class WebHTTP:
    
    def __init__(self) -> None:
        
        self.session = requests.AsyncSession()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
            }
        )
    
    # https://www.mexc.com/api/platform/asset/api/asset/spot/currency/v3?currency=TMX 
    # https://www.mexc.com/api/platform/spot/market-v2/web/symbolsV2

    async def call(
        self,
        method: Union[Literal["GET"], Literal["POST"], Literal["PUT"], Literal["DELETE"]],
        router: str,
        auth: bool = True,
        *args,
        **kwargs,
    ) -> dict:
        
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if kwargs.get("params"):
            kwargs["params"] = {k: v for k, v in kwargs["params"].items() if v is not None}
        else:
            kwargs["params"] = {}

        timestamp = str(int(time.time() * 1000))
        kwargs["params"]["timestamp"] = timestamp
        kwargs["params"]["recvWindow"] = self.recvWindow

        kwargs["params"] = {k: v for k, v in sorted(kwargs["params"].items())}
        params = kwargs.pop("params")

        response = await self.session.request(method, f"{self.base_url}{router}", params=params, *args, **kwargs)

        return response.json()
    
    
    async def symbols_info_v2():
        pass


class SpotHTTP(_WebHTTP):
    def __init__(self, api_key: str = None, api_secret: str = None, proxies: dict = None):
        super().__init__(api_key, api_secret, SPOT, proxies=proxies)


    def sign(self, query_string: str) -> str:
        """
        Generates a signature for an API request using HMAC SHA256 encryption.

        Args:
            **kwargs: Arbitrary keyword arguments representing request parameters.

        Returns:
            A hexadecimal string representing the signature of the request.
        """
        # Generate signature
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    async def call(
        self,
        method: Union[Literal["GET"], Literal["POST"], Literal["PUT"], Literal["DELETE"]],
        router: str,
        auth: bool = True,
        *args,
        **kwargs,
    ) -> dict:
        if not router.startswith("/"):
            router = f"/{router}"

        # clear None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if kwargs.get("params"):
            kwargs["params"] = {k: v for k, v in kwargs["params"].items() if v is not None}
        else:
            kwargs["params"] = {}

        timestamp = str(int(time.time() * 1000))
        kwargs["params"]["timestamp"] = timestamp
        kwargs["params"]["recvWindow"] = self.recvWindow

        kwargs["params"] = {k: v for k, v in sorted(kwargs["params"].items())}
        params = kwargs.pop("params")
        encoded_params = urlencode(params, doseq=True).replace("+", "%20")

        if self.api_key and self.api_secret and auth:
            params["signature"] = self.sign(encoded_params)

        response = await self.session.request(method, f"{self.base_url}{router}", params=params, *args, **kwargs)

        if not response.ok:
            print(response.json())
            raise MexcAPIError(f"(code={response.json()['code']}): {response.json()['msg']}")

        return response.json()
    
    
if __name__ == "__main__":
    