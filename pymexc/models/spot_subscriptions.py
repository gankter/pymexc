from pydantic import BaseModel
from enum import Enum

class Topics(Enum):
    PUBLIC_AGGRE_DEALS = "public.aggre.deals"
    PUBLIC_KLINE = "public.kline"
    PUBLIC_AGGRE_DEPTH = "public.aggre.depth"
    PUBLIC_LIMIT_DEPTH = "public.limit.depth"
    PUBLIC_AGGRE_BOOK_TICKER = "public.aggre.bookTicker"
    PUBLIC_BOOK_TICKER_BATCH = "public.bookTicker.batch"
    PRIVATE_DEALS = "private.deals"
    PRIVATE_ACCOUNT = "private.account"
    PRIVATE_ORDERS = "private.orders"

class SubscriptionParams(BaseModel):
    symbol: str = None
    interval: str = None
    level: str = None
    proto: bool = True

class MessageShaper:
    TEMPLATES = {
        Topics.PUBLIC_AGGRE_DEALS: "spot@{type}.v3.api{proto}@{interval}@{symbol}",
        Topics.PUBLIC_KLINE: "spot@{type}.v3.api{proto}@{interval}@{symbol}",
        Topics.PUBLIC_AGGRE_DEPTH: "spot@{type}.v3.api{proto}@{interval}@{symbol}",
        Topics.PUBLIC_LIMIT_DEPTH: "spot@{type}.v3.api{proto}@{symbol}@{level}",
        Topics.PUBLIC_AGGRE_BOOK_TICKER: "spot@{type}.v3.api{proto}@{interval}@{symbol}",
        Topics.PUBLIC_BOOK_TICKER_BATCH: "spot@{type}.v3.api{proto}@{symbol}",
        Topics.PRIVATE_ACCOUNT: "",
        Topics.PRIVATE_DEALS: "",
        Topics.PRIVATE_ORDERS: ""
    }

    @staticmethod
    def shape_message(sub_type: Topics, params: SubscriptionParams = None) -> str | list:
        template = MessageShaper.TEMPLATES.get(sub_type)
        if callable(template):
            return template()
        return template.format(
            type=sub_type.value,
            proto=".pb" if params.proto else "",
            interval=params.interval or "",
            symbol=params.symbol or "",
            level=params.level or ""
        )

"""proto = True
message_shaper_dict = {
            "public.aggre.deals": lambda params: f"spot@public.aggre.deals.v3.api{(".pb" if proto else "")}@{params['interval']}@{params['symbol']}",
            "public.kline": lambda params: f"spot@public.kline.v3.api{(".pb" if proto else "")}@{params['interval']}@{params['symbol']}",
            "public.aggre.depth": lambda params: f"spot@public.aggre.depth.v3.api{(".pb" if proto else "")}@{params['interval']}@{params['symbol']}", 
            "public.limit.depth": lambda params: f"spot@public.limit.depth.v3.api{(".pb" if proto else "")}@{params['symbol']}@{params['level']}",
            "public.aggre.bookTicker": lambda params: f"spot@public.aggre.bookTicker.v3.api{(".pb" if proto else "")}@{params['interval']}@{params['symbol']}",
            "public.bookTicker.batch": lambda params: f"spot@public.bookTicker.batch.v3.api{(".pb" if proto else "")}@{params['symbol']}",
            "private.account": lambda : [{}],
            "private.deals": lambda : [{}],
            "private.orders": lambda : [{}]
        }"""

import time
# Использование
pars = {
    "symbol":"BTCUSDT",
    "interval":"1m",
    "proto":True,
}
params = SubscriptionParams(**pars)
start = time.perf_counter()
#message_shaper_dict["public.aggre.deals"](params.model_dump())
message = MessageShaper.shape_message(Topics.PUBLIC_AGGRE_DEALS, params)
end = time.perf_counter()
print((end-start)*1e6)
start = time.perf_counter()
current_subscribed_topics:dict[Topics,int] = dict().fromkeys(Topics._member_map_.values(), 0)
end = time.perf_counter()
print((end-start)*1e6)
print(current_subscribed_topics)  # spot@public.aggre.deals.v3.api.pb@1m@BTCUSDT