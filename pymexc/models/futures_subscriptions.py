
from pydantic import BaseModel
from enum import Enum
import json


self.message_shaper_dict = {
            "tickers": lambda params: f"futures@ticker{(".pb" if self.proto else "")}@_",
            "deal": lambda params: f"futures@deal{(".pb" if self.proto else "")}@{params['symbol']}",
            "depth": lambda params: f"futures@depth{(".pb" if self.proto else "")}@{params['symbol']}", 
            "depth.full": lambda params: f"futures@depth.full{(".pb" if self.proto else "")}@{params['symbol']}",
            "kline": lambda params: f"futures@kline{(".pb" if self.proto else "")}@{params['symbol']}@{params['interval']}",
            "funding.rate": lambda params: f"futures@public.bookTicker.batch.v3.api{(".pb" if self.proto else "")}@{params['symbol']}",
            "index.price": lambda : [{}],
            "fair.price": lambda : [{}],
            "filter": lambda : [{}]
        }

class Topics(Enum):
    PUBLIC_TICKERS = "tickers"
    PUBLIC_SINGLE_TICKER = "ticker"
    PUBLIC_DEALS = "deal"
    PUBLIC_DEPTH = "depth"
    PUBLIC_DEPTH_FULL = "depth.full"
    PUBLIC_KLINE = "kline"
    PUBLIC_FUNDING_RATE = "funding.rate"
    PUBLIC_INDEX_PRICE = "index.price"
    PUBLIC_FAIR_PRICE = "fair.price"
    #PRIVATE_LOGIN = "login"
    PRIVATE_ORDER = "personal.order"
    PRIVATE_ASSETS = "personal.asset"
    PRIVATE_POSITION = "personal.position"
    PRIVATE_FILTER = "filter"

class SubscriptionParams(BaseModel):
    symbol: str = None
    interval: str = None
    level: str = None
    proto: bool = False


class MessageShaper:
    TEMPLATES = {
        Topics.PUBLIC_TICKERS: "futures@{type}.v1.api{proto}",
        Topics.PUBLIC_SINGLE_TICKER: "futures@{type}.v1.api{proto}@{symbol}",
        Topics.PUBLIC_DEALS: "futures@{type}.v1.api{proto}@{symbol}",
        Topics.PUBLIC_KLINE: "futures@{type}.v1.api{proto}@{interval}@{symbol}",
        Topics.PUBLIC_DEPTH: "futures@{type}.v1.api{proto}@{symbol}",
        Topics.PUBLIC_DEPTH_FULL: "futures@{type}.v1.api{proto}@{symbol}@{limit}",
        Topics.PUBLIC_FUNDING_RATE: "futures@{type}.v1.api{proto}@{symbol}",
        Topics.PUBLIC_INDEX_PRICE: "futures@{type}.v1.api{proto}@{symbol}",
        Topics.PUBLIC_FAIR_PRICE: "futures@{type}.v1.api{proto}@{symbol}",
        #Topics.PRIVATE_DEALS: "",
        #Topics.PRIVATE_ORDERS: ""
    }

    @staticmethod
    def shape_signature(sub_type: Topics, params: SubscriptionParams = None) -> str | list:
        """
        signature for inner dict where contains k,v pairs dict[signature:str, callback:Callable]
        """
        template = MessageShaper.TEMPLATES.get(sub_type)
        #if callable(template):
        #    return template()
        return template.format(
            type=sub_type.value,
            proto=".pb" if params.proto else "",
            interval=params.interval or "",
            symbol=params.symbol or "",
            level=params.level or ""
        )
    
    @staticmethod
    def shape_message(sub_type: Topics, params: SubscriptionParams = None, gzip:bool = None) -> str:
        params.proto = None
        return json.dumps({
            "method": "",
            "params": params.model_dump(exclude_none=True),
            "gzip": gzip
        }, allow_nan=False)