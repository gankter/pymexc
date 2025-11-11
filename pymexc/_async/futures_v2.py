"""
### Futures API
Documentation: https://mexcdevelop.github.io/apidocs/contract_v1_en/#update-log

### Usage

```python
from pymexc import futures

api_key = "YOUR API KEY"
api_secret = "YOUR API SECRET KEY"

def handle_message(message):
    # handle websocket message
    print(message)

# initialize HTTP client
futures_client = futures.HTTP(api_key = api_key, api_secret = api_secret)
# initialize WebSocket client
ws_futures_client = futures.WebSocket(api_key = api_key, api_secret = api_secret)

# make http request to api
print(futures_client.index_price("MX_USDT"))

# create websocket connection to public channel (sub.tickers)
# all messages will be handled by function `handle_message`
ws_futures_client.tickers_stream(handle_message)

# loop forever for save websocket connection
while True:
    ...

"""

import logging
from asyncio import AbstractEventLoop
from typing import Awaitable, Callable, Dict, List, Literal, Optional, Union
import warnings

logger = logging.getLogger(__name__)


"""
SPOT = "wss://wbs-api.mexc.com/ws"
FUTURES = "wss://contract.mexc.com/edge"
FUTURES_PERSONAL_TOPICS = [
    "order",
    "order.deal",
    "position",
    "plan.order",
    "stop.order",
    "stop.planorder",
    "risk.limit",
    "adl.level",
    "asset",
    "liquidate.risk",
]

"""
#try:
#    from .base import _FuturesHTTP
#    from ..base_websocket import FUTURES_PERSONAL_TOPICS, _FuturesWebSocket
#except ImportError:
from pymexc._async.base import _FuturesHTTP
from pymexc._async.base_websocket import _FuturesWebSocket
from ..base_websocket import FUTURES_PERSONAL_TOPICS


class WebSocket(_FuturesWebSocket):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        loop: Optional[AbstractEventLoop] = None,
        personal_callback: Optional[Awaitable[Callable[..., None]]] = None,
        ping_interval: Optional[int] = 20,
        ping_timeout: Optional[int] = None,
        retries: Optional[int] = 10,
        restart_on_error: Optional[bool] = True,
        trace_logging: Optional[bool] = False,
        #http_proxy_host: Optional[str] = None,
        #http_proxy_port: Optional[int] = None,
        #http_no_proxy: Optional[list] = None,
        #http_proxy_auth: Optional[tuple] = None,
        #http_proxy_timeout: Optional[int] = None,
        proto: Optional[bool] = False,
    ):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            subscribe_callback=personal_callback,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            retries=retries,
            restart_on_error=restart_on_error,
            trace_logging=trace_logging,
            #http_proxy_host=http_proxy_host,
            #http_proxy_port=http_proxy_port,
            #http_no_proxy=http_no_proxy,
            #http_proxy_auth=http_proxy_auth,
            #http_proxy_timeout=http_proxy_timeout,
            loop=loop,
        )

        if proto:
            warnings.warn("proto is not supported in futures websocket api", DeprecationWarning)

    async def unsubscribe(self, method: str | Callable, param):
        personal_filters = ["personal.filter", "filter", "personal"]
        if (
            method in personal_filters
            or getattr(method, "__name__", "").replace("_stream", "").replace("_", ".") in personal_filters
        ):
            return await self.personal_stream(lambda: ...)

        return await super().unsubscribe(method,param)

    async def tickers_stream(self, callback: Awaitable[Callable[..., None]]):
        """
        ### Tickers
        Get the latest transaction price, buy-price, sell-price and 24 transaction volume of all the perpetual contracts on the platform without login.
        Send once a second after subscribing.

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]

        :return: None
        """
        params = {}
        topic = "tickers"
        await self._ws_subscribe(topic, callback, params)

    async def ticker_stream(self, callback: Awaitable[Callable[..., None]], symbol: str):
        """
        ### Ticker
        Get the latest transaction price, buy price, sell price and 24 transaction volume of a contract,
        send the transaction data without users' login, and send once a second after subscription.

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        params = dict(symbol=symbol)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "ticker"
        await self._ws_subscribe(topic, callback, params)

    async def deal_stream(self, callback: Awaitable[Callable[..., None]], symbol: str):
        """
        ### Transaction
        Access to the latest data without login, and keep updating.

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        params = dict(symbol=symbol)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "deal"
        await self._ws_subscribe(topic, callback, params)

    async def depth_stream(self, callback: Awaitable[Callable[..., None]], symbol: str):
        """
        ### Depth

        Tip: [411.8, 10, 1] 411.8 is price, 10 is the order numbers of the contract ,1 is the order quantity

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        params = dict(symbol=symbol)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "depth"
        await self._ws_subscribe(topic, callback, params)

    async def depth_full_stream(self, callback: Awaitable[Callable[..., None]], symbol: str, limit: int = 20):
        """
        ### Depth full

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str
        :param limit: Limit could be 5, 10 or 20, default 20 without define., only subscribe to the full amount of one gear
        :type limit: int

        :return: None
        """
        params = dict(symbol=symbol, limit=limit)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "depth.full"
        await self._ws_subscribe(topic, callback, params)

    async def kline_stream(
        self,
        callback: Awaitable[Callable[..., None]],
        symbol: str,
        interval: Literal["Min1", "Min5", "Min15", "Min60", "Hour1", "Hour4", "Day1", "Week1"] = "Min1",
    ):
        """
        ### K-line
        Get the k-line data of the contract and keep updating.

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str
        :param interval: Min1, Min5, Min15, Min30, Min60, Hour4, Hour8, Day1, Week1, Month1
        :type interval: str

        :return: None
        """
        params = dict(symbol=symbol, interval=interval)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "kline"
        await self._ws_subscribe(topic, callback, params)

    async def funding_rate_stream(self, callback: Awaitable[Callable[..., None]], symbol: str):
        """
        ### Funding rate
        Get the contract funding rate, and keep updating.

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        params = dict(symbol=symbol)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "funding.rate"
        await self._ws_subscribe(topic, callback, params)

    async def index_price_stream(self, callback: Awaitable[Callable[..., None]], symbol: str):
        """
        ### Index price
        Get the index price, and will keep updating if there is any changes.

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        params = dict(symbol=symbol)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "index.price"
        await self._ws_subscribe(topic, callback, params)

    async def fair_price_stream(self, callback: Awaitable[Callable[..., None]], symbol: str):
        """
        ### Fair price

        https://mexcdevelop.github.io/apidocs/contract_v1_en/#public-channels

        :param callback: the callback function
        :type callback: Awaitable[Callable[..., None]]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        params = dict(symbol=symbol)

        # clear none values
        params = {k: v for k, v in params.items() if v is not None}

        topic = "fair.price"
        await self._ws_subscribe(topic, callback, params)

    # <=================================================================>
    #
    #                                PRIVATE
    #
    # <=================================================================>

    async def filter_stream(self, callback: Callable, params: Dict[str, List[dict]] = {"filters": []}):
        """
        ## Filter personal data about account
        Provide `{"filters":[]}` as params for subscribe to all info
        """
        if params.get("filters") is None:
            raise ValueError("Please provide filters")

        topics = [x.get("filter") for x in params.get("filters", [])]
        for topic in topics:
            if topic not in FUTURES_PERSONAL_TOPICS:
                raise ValueError(f"Invalid filter: `{topic}`. Valid filters: {FUTURES_PERSONAL_TOPICS}")

        await self._ws_subscribe("personal.filter", callback, params)
        # set callback for provided filters
        self._set_personal_callback(callback, topics)

    async def personal_stream(self, callback: Awaitable[Callable]):
        await self.filter_stream(callback, params={"filters": []})
        # set callback for all filters
        self._set_personal_callback(callback, FUTURES_PERSONAL_TOPICS)
