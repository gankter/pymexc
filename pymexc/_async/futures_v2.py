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
#from asyncio import AbstractEventLoop
import asyncio
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
from pymexc._async.base_websocket_v2 import _FuturesWebSocket
from ..base_websocket import FUTURES_PERSONAL_TOPICS

from pymexc.models import ApiSettings, ProxySettings, CallbackSettings, FuturesTopics

class WebSocket(_FuturesWebSocket):
    def __init__(
        self,
        callback_settings: CallbackSettings,
        api_settings: ApiSettings = ApiSettings(),
        listenKey: Optional[str] = None,
        proxy_settings:ProxySettings = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        proto: Optional[bool] = False,
    ):
        """
        Initializes the class instance with the provided arguments.

        :param api_key: API key for authentication. (Optional)
        :type api_key: str

        :param api_secret: API secret for authentication. (Optional)
        :type api_secret: str

        :param listenKey: The listen key for the connection to private channels.
                          If not provided, a listen key will be generated from HTTP api [Permission: SPOT_ACCOUNT_R] (Optional)
        :type listenKey: str

        :param ping_interval: The interval in seconds to send a ping request. (Optional)
        :type ping_interval: int

        :param ping_timeout: The timeout in seconds for a ping request. (Optional)
        :type ping_timeout: int

        :param retries: The number of times to retry a request. (Optional)
        :type retries: int

        :param restart_on_error: Whether or not to restart the connection on error. (Optional)
        :type restart_on_error: bool

        :param trace_logging: Whether or not to enable trace logging. (Optional)
        :type trace_logging: bool

        :param http_proxy_host: The host for the HTTP proxy. (Optional)
        :type http_proxy_host: str

        :param http_proxy_port: The port for the HTTP proxy. (Optional)
        :type http_proxy_port: int

        :param http_no_proxy: A list of hosts to exclude from the HTTP proxy. (Optional)
        :type http_no_proxy: list

        :param http_proxy_auth: The authentication for the HTTP proxy. (Optional)
        :type http_proxy_auth: tuple

        :param http_proxy_timeout: The timeout for the HTTP proxy. (Optional)
        :type http_proxy_timeout: int

        :param loop: The event loop to use for the connection. (Optional)
        :type loop: AbstractEventLoop

        :param proto: Whether or not to use the proto protocol. (Optional)
        :type proto: bool

        :param extend_proto_body: Whether or not to extend the proto body. (Optional)
        :type extend_proto_body: bool
        """
        loop = loop or asyncio.get_event_loop()
        
        self.listenKey = listenKey

        super().__init__(loop=loop,
                         callback_settings=callback_settings,
                         api_settings=api_settings,
                         proxy_settings=proxy_settings,
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
        topic = FuturesTopics.PUBLIC_TICKERS
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

        topic = FuturesTopics.PUBLIC_SINGLE_TICKER
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

        topic = FuturesTopics.PUBLIC_DEALS
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

        topic = FuturesTopics.PUBLIC_DEPTH
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

        topic = FuturesTopics.PUBLIC_DEPTH_FULL
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

        topic = FuturesTopics.PUBLIC_KLINE
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

        topic = FuturesTopics.PUBLIC_FUNDING_RATE
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

        topic = FuturesTopics.PUBLIC_INDEX_PRICE
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

        topic = FuturesTopics.PUBLIC_FAIR_PRICE
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
