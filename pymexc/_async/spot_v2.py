"""
### Spot API
Documentation: https://mexcdevelop.github.io/apidocs/spot_v3_en/#introduction

### Usage

```python
from pymexc import spot

api_key = "YOUR API KEY"
api_secret = "YOUR API SECRET KEY"

async def handle_message(message):
    # handle websocket message
    print(message)

# initialize HTTP client
spot_client = spot.HTTP(api_key = api_key, api_secret = api_secret)
# initialize WebSocket client
ws_spot_client = spot.WebSocket(api_key = api_key, api_secret = api_secret)

# make http request to api
print(spot_client.exchange_info())

# create websocket connection to public channel (spot@public.deals.v3.api@BTCUSDT)
# all messages will be handled by function `handle_message`
ws_spot_client.deals_stream(handle_message, "BTCUSDT")

# loop forever for save websocket connection
while True:
    ...

"""

import asyncio
import logging
from asyncio import AbstractEventLoop
from typing import Callable, List, Literal, Optional, Union
import warnings

logger = logging.getLogger(__name__)



    #from pymexc._async.base import _SpotHTTP, SPOT as SPOT_HTTP
from pymexc._async.base_websocket_v2 import _SpotWebSocket, SPOT as SPOT_WS

from pymexc.models.proxy import ProxySettings
from pymexc.models.api_settings import ApiConfig
from pymexc.models.spot_subscriptions import Topics

class WebSocket(_SpotWebSocket):
    def __init__(
        self,
        api_auth: ApiConfig = None,
        listenKey: Optional[str] = None,
        #ping_interval: Optional[int] = 20,
        #ping_timeout: Optional[int] = None,
        #retries: Optional[int] = 10,
        #restart_on_error: Optional[bool] = True,
        #trace_logging: Optional[bool] = False,
        #http_proxy_host: Optional[str] = None,
        #http_proxy_port: Optional[int] = None,
        #http_no_proxy: Optional[list] = None,
        #http_proxy_auth: Optional[tuple] = None,
        #http_proxy_timeout: Optional[int] = None,
        proxy_settings:ProxySettings = None,
        loop: Optional[AbstractEventLoop] = None,
        proto: Optional[bool] = False,
        extend_proto_body: Optional[bool] = False,
        use_common_callback = False,
        commn_callback = None,
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

        kwargs = dict(
            #api_key=api_key,
            #api_secret=api_secret,
           # ping_interval=ping_interval,
            #ping_timeout=ping_timeout,
            #retries=retries,
            #restart_on_error=restart_on_error,
            #trace_logging=trace_logging,
            #http_proxy_host=http_proxy_host,
            #http_proxy_port=http_proxy_port,
           # http_no_proxy=http_no_proxy,
            #http_proxy_auth=http_proxy_auth,
            #http_proxy_timeout=http_proxy_timeout,
            loop=loop,
            proto = proto,
            extend_proto_body = extend_proto_body,
            use_common_callback = use_common_callback,
            commn_callback = commn_callback,
        )
        self.listenKey = listenKey

        super().__init__(**kwargs)

        # for keep alive connection to private spot websocket
        # need to send listen key at connection and send keep-alive request every 60 mins
        if api_auth.api_key and api_auth.api_secret:
            # setup keep-alive connection loop
            loop.create_task(self._keep_alive_loop())

    async def _keep_alive_loop(self):
        """
        Runs a loop that sends a keep-alive message every 59 minutes to maintain the connection
        with the MEXC API.

        :return: None
        """

        if not self.listenKey:
            auth = await HTTP(api_key=self.api_key, api_secret=self.api_secret).create_listen_key()
            self.listenKey = auth.get("listenKey")
            logger.debug(f"create listenKey: {self.listenKey}")

        if not self.listenKey:
            raise Exception(f"ListenKey not found. Error: {auth}")

        self.endpoint = f"{SPOT_WS}/ws?listenKey={self.listenKey}"

        while True:
            await asyncio.sleep(59 * 60)  # 59 min

            if self.listenKey:
                resp = await HTTP(api_key=self.api_key, api_secret=self.api_secret).keep_alive_listen_key(
                    self.listenKey
                )
                logger.debug(f"keep-alive listenKey - {self.listenKey}. Response: {resp}")
            else:
                break

    # <=================================================================>
    #
    #                                Public
    #
    # <=================================================================>

    async def public_aggre_deals_stream(self, symbol: Union[str, List[str]], interval: Literal["100ms","10s"] = None, callback: Callable[..., None] = None):
        """
        ### Trade Streams
        The Trade Streams push raw trade information; each trade has a unique buyer and seller.

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#trade-streams

        :param callback: the callback function
        :type callback: Callable[..., None]
        :param symbol: the name of the contract
        :type symbol: Union[str,List[str]]
        :param interval: the interval for the stream, default is None. Possible values '100ms' or '10s'
        :type symbol: str

        :return: None
        """

        await asyncio.sleep(4)
        if isinstance(symbol, str):
            symbols = [symbol]  # str
        else:
            symbols = symbol  # list
        params_list = [dict(symbol = s, interval = interval) for s in symbols]
        #topic = "public.aggre.deals"
  
        await self._ws_subscribe(Topics.PUBLIC_AGGRE_DEALS, callback, params_list)

    async def public_kline_stream(self, 
                           callback: Callable[..., None], 
                           symbol: Union[str, List[str]], 
                           interval: Literal["Min1", "Min5", "Min15", "Min30", "Min60", "Hour4", "Hour8","Day1", "Week1", "Month1"]):
        """
        ### Kline Streams
        The Kline/Candlestick Stream push updates to the current klines/candlestick every second.

        subscribe pattern spot@public.kline.v3.api.pb@<symbol>@<interval>

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#kline-streams

        :param callback: the callback function
        :type callback: Callable[..., None]
        :param symbol: the name of the contract
        :type symbol: str
        :param interval: the interval of the kline
        :type interval: str

        :return: None
        """
        if isinstance(symbol, str):
            symbols = [symbol]  # str
        else:
            symbols = symbol  # list

        params_list = [dict(symbol = s, interval = interval) for s in symbols]

        #topic = "public.kline"
        
        await self._ws_subscribe(Topics.PUBLIC_KLINE, callback, params_list)

    async def public_aggre_depth_stream(self, callback: Callable[..., None], symbol: Union[str, List[str]], interval: Literal["10ms","100ms"]):
        """
        ### Diff.Depth Stream
        If the quantity is 0, it means that the order of the price has been cancel or traded,remove the price level.

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#diff-depth-stream

        :param callback: the callback function
        :type callback: Callable[..., None]
        :param symbol: the name of the contract
        :type symbol: str

        :return: None
        """
        if isinstance(symbol, str):
            symbols = [symbol]  # str
        else:
            symbols = symbol  # list

        params_list = [dict(symbol = s, interval = interval) for s in symbols]

        #topic = "public.aggre.depth"
        await self._ws_subscribe(Topics.PUBLIC_AGGRE_DEPTH, callback, params_list)

    async def public_limit_depth_stream(self, callback: Callable[..., None], symbol: Union[str, List[str]], level: Literal[5,10,20]):
        """
        ### Partial Book Depth Streams
        Top bids and asks, Valid are 5, 10, or 20.

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#partial-book-depth-streams

        :param callback: the callback function
        :type callback: Callable[..., None]
        :param symbol: the name of the contract
        :type symbol: str
        :param level: the level of the depth. Valid are 5, 10, or 20.
        :type level: int

        :return: None
        """
        if isinstance(symbol, str):
            symbols = [symbol]  # str
        else:
            symbols = symbol  # list
        
        params_list = [dict(symbol = s, level = level) for s in symbols]
        #topic = "public.limit.depth"
        await self._ws_subscribe(Topics.PUBLIC_LIMIT_DEPTH, callback, params_list)

    async def public_aggre_bookTicker_stream(self, callback: Callable[..., None], symbol: Union[str, List[str]]):
        """
        ### Individual Symbol Book Ticker Streams
        Pushes any update to the best bid or ask's price or quantity in real-time for a specified symbol.

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#partial-book-depth-streams

        :param callback: the callback function
        :type callback: Callable[..., None]
        :param symbols: the names of the contracts
        :type symbols: str

        :return: None
        """
        if isinstance(symbol, str):
            symbols = [symbol]  # str
        else:
            symbols = symbol  # list
        
        params_list = [dict(symbol = s) for s in symbols]

        #topic = "public.aggre.bookTicker"
        await self._ws_subscribe(Topics.PUBLIC_AGGRE_BOOK_TICKER, callback, params_list)

    async def public_bookTicker_batch_stream(self, callback: Callable[..., None], symbol: Union[str, List[str]]):
        """
        ### Individual Symbol Book Ticker Streams (Batch Aggregation)
        This batch aggregation version pushes the best order information for a specified trading pair.

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#individual-symbol-book-ticker-streams-batch-aggregation

        :param callback: the callback function
        :type callback: Callable[..., None]
        :param symbols: the names of the contracts
        :type symbols: List[str]

        :return: None
        """
        if isinstance(symbol, str):
            symbols = [symbol]  # str
        else:
            symbols = symbol  # list

        params_list = [dict(symbol=s) for s in symbols]

        #topic = "public.bookTicker.batch"
        await self._ws_subscribe(Topics.PUBLIC_BOOK_TICKER_BATCH, callback, params_list)

    # <=================================================================>
    #
    #                                Private
    #
    # <=================================================================>

    async def private_account_update(self, callback: Callable[..., None]):
        """
        ### Spot Account Update
        The server will push an update of the account assets when the account balance changes.

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#websocket-user-data-streams

        :param callback: the callback function
        :type callback: Callable[..., None]

        :return: None
        """
        params = [{}]
        #topic = "private.account"
        await self._ws_subscribe(Topics.PRIVATE_ACCOUNT, callback, params)

    async def private_account_deals(self, callback: Callable[..., None]):
        """
        ### Spot Account Deals

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#spot-account-deals

        :param callback: the callback function
        :type callback: Callable[..., None]

        :return: None
        """
        params = [{}]
        #topic = "private.deals"
        await self._ws_subscribe(Topics.PRIVATE_DEALS, callback, params)

    async def private_account_orders(self, callback: Callable[..., None]):
        """
        ### Spot Account Orders

        https://mexcdevelop.github.io/apidocs/spot_v3_en/#spot-account-orders

        :param callback: the callback function
        :type callback: Callable[..., None]

        :return: None
        """
        params = [{}]
        #topic = "private.orders"
        await self._ws_subscribe(Topics.PRIVATE_ORDERS, callback, params)
