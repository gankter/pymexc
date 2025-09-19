import asyncio
import json
import logging
import time
import warnings
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List, Union, Optional


import aiohttp
import websockets.client

from pymexc.base_websocket import (
    _WebSocketManager,
    SPOT,
    FUTURES,
)
from aiohttp import ClientSession, ClientTimeout

if TYPE_CHECKING:
    from .spot import HTTP

logger = logging.getLogger(__name__)


class _AsyncWebSocketManager(_WebSocketManager):
    endpoint: str

    def __init__(
        self,
        callback_function,
        ws_name,
        api_key=None,
        api_secret=None,
        subscribe_callback=None,
        ping_interval=20,
        ping_timeout=None,
        retries=10,
        restart_on_error=True,
        trace_logging=False,
        private_auth_expire=1,
        http_proxy_host=None,
        http_proxy_port=None,
        http_no_proxy=None,
        http_proxy_auth=None,
        http_proxy_timeout=None,
        loop=None,
        proto=False,
        extend_proto_body=False,
    ):
        super().__init__(
            callback_function,
            ws_name,
            api_key=api_key,
            api_secret=api_secret,
            subscribe_callback=subscribe_callback,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            retries=retries,
            restart_on_error=restart_on_error,
            trace_logging=trace_logging,
            private_auth_expire=private_auth_expire,
            http_proxy_host=http_proxy_host,
            http_proxy_port=http_proxy_port,
            http_no_proxy=http_no_proxy,
            http_proxy_auth=http_proxy_auth,
            http_proxy_timeout=http_proxy_timeout,
            proto=proto,
            extend_proto_body=extend_proto_body,
        )
        self.connected = False
        self.loop = loop or asyncio.get_event_loop()
        self.locker = asyncio.Lock()

        if ping_timeout:
            warnings.warn(
                "ping_timeout is deprecated for async websockets, please use just ping_interval.",
            )

    async def _on_open(self):
        self.connected = True
        super()._on_open()

    async def _loop_recv(self):
        try:
            async for msg in self.ws:
                if msg.type in [aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY]:
                    await self._on_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    await self._on_error(msg)
                    break
        finally:
            await self._on_close()
            await self.session.close()

    async def _on_message(self, message: str | bytes):
        """
        Parse incoming messages.
        """
        _message = super()._on_message(message, parse_only=True)
        await self.callback(_message)

    def is_connected(self):
        return self.connected

    async def _connect(self, url):
        """
        Open websocket in a thread.
        """

        async def resubscribe_to_topics():
            if not self.subscriptions:
                # There are no subscriptions to resubscribe to, probably
                # because this is a brand new WSS initialisation so there was
                # no previous WSS connection.
                return

            for subscription_message in self.subscriptions:
                await self.ws.send_json(subscription_message)

        self.attempting_connection = True

        self.endpoint = url

        # Attempt to connect for X seconds.
        retries = self.retries
        if retries == 0:
            infinitely_reconnect = True
        else:
            infinitely_reconnect = False

        while (infinitely_reconnect or retries > 0) and not self.is_connected():
            logger.info(f"WebSocket {self.ws_name} attempting connection...")

            self.session = ClientSession()
            timeout = ClientTimeout(total=60)
            self.ws = await self.session.ws_connect(
                url=url,
                proxy=f"http://{self.proxy_settings['http_proxy_host']}:{self.proxy_settings['http_proxy_port']}"
                if self.proxy_settings["http_proxy_host"]
                else None,
                proxy_auth=self.proxy_settings["http_proxy_auth"],
                timeout=timeout,
            )

            # parse incoming messages
            await self._on_open()
            self.loop.create_task(self._loop_recv())

            if not self.is_connected():
                # If connection was not successful, raise error.
                if not infinitely_reconnect and retries <= 0:
                    self.exit()
                    raise Exception(
                        f"WebSocket {self.ws_name} ({self.endpoint}) connection "
                        f"failed. Too many connection attempts. pymexc will no "
                        f"longer try to reconnect."
                    )

        logger.info(f"WebSocket {self.ws_name} connected")

        # If given an api_key, authenticate.
        if self.api_key and self.api_secret:
            await self._auth()

        await resubscribe_to_topics()

        self.attempting_connection = False

    async def _auth(self):
        msg = super()._auth(parse_only=True)

        # Authenticate with API.
        await self.ws.send_json(msg)

    async def _on_error(self, error: Exception):
        super()._on_error(error, parse_only=True)

        # Reconnect.
        if self.restart_on_error and not self.attempting_connection:
            self._reset()
            await self._connect(self.endpoint)

    async def _on_close(self):
        self.connected = False
        super()._on_close()


    async def _process_normal_message(self, message: dict, return_wrapper_data:bool): 
        callback_function, callback_data, wrapper_data = super()._process_normal_message(message=message,
                                                                                         return_wrapper_data = return_wrapper_data,
                                                                                         parse_only=True)

        if callback_function is None:
            return
        
        if asyncio.iscoroutinefunction(callback_function):
            await callback_function(callback_data,wrapper_data)
        else:
            callback_function(callback_data,wrapper_data)
            
        


# # # # # # # # # #
#                 #
#     FUTURES     #
#                 #
# # # # # # # # # #


class _FuturesWebSocketManager(_AsyncWebSocketManager):
    def __init__(self, ws_name, **kwargs):
        callback_function = (
            kwargs.pop("callback_function") if kwargs.get("callback_function") else self._handle_incoming_message
        )
        
        self.message_shaper_dict = {
            "tickers": lambda params: f"futures@ticker{(".pb" if self.proto else "")}@_",
            "deal": lambda params: f"futures@deal{(".pb" if self.proto else "")}@{params['symbol']}",
            "depth": lambda params: f"futures@depth{(".pb" if self.proto else "")}@{params['symbol']}", 
            "depth.full": lambda params: f"futures@depth.full{(".pb" if self.proto else "")}@{params['symbol']}",
            "kline": lambda params: f"futures@kline{(".pb" if self.proto else "")}@{params['symbol']}@{params['interval']}",
            "funding.rate": lambda params: f"spot@public.bookTicker.batch.v3.api{(".pb" if self.proto else "")}@{params['symbol']}",
            "index.price": lambda : [{}],
            "fair.price": lambda : [{}],
            "filter": lambda : [{}]
        }
        
        super().__init__(callback_function, ws_name, **kwargs)
        
    def _subscribe_one(self, topic: str, callback: Callable, params: dict, message_shaper: Callable):
        subscribe_message = message_shaper(params)
        self._check_callback_directory(subscribe_message)
        self.subscriptions.append(subscribe_message)
        self._set_callback(topic = subscribe_message, callback_function = callback )
        return subscribe_message
    
    def _unsubscribe_one(self, topic: str, params: dict, message_shaper: Callable ):
        subscribe_message = message_shaper(params)
        #self._check_callback_directory(f"{topic}@{params.get("symbol","_")}")
        self.subscriptions.remove(subscribe_message)
        self._pop_callback(topic = subscribe_message)
        logger.debug(f"Unsubscribed from {topic} with subscription message {subscribe_message}")
        return {"method": topic, "param": params}

    async def subscribe(self, topic, callback, params):
        
        subscription_message = self._subscribe_one(topic, callback, params, message_shaper = self.message_shaper_dict[topic])
        self._check_callback_directory(subscription_message)

        while not self.is_connected():
            # Wait until the connection is open before subscribing.
            await asyncio.sleep(0.1)

        await self.ws.send_json({"method": f"sub.{topic}", "param": params} )
        
        self.last_subsctiption = subscription_message

    async def unsubscribe(self, topic: str | Callable, params: Optional[dict] ) -> None:

        if isinstance(topic, str):
            self._unsubscribe_one(self, topic, params, self.message_shaper_dict[topic])
            await self.ws.send_json({"method": f"unsub.{topic}", "param": params})
            
            logger.debug(f"Unsubscribed from {topic}, params: {params}")
        else:
            # this is a func, get name
            topic_name = topic.__name__.replace("_stream", "").replace("_", ".")

            return await self.unsubscribe(topic_name,param=params)

    async def _process_auth_message(self, message: dict):
        # If we get successful futures auth, notify user
        if message.get("data") == "success":
            logger.debug(f"Authorization for {self.ws_name} successful.")
            self.auth = True

        # If we get unsuccessful auth, notify user.
        elif message.get("data") != "success":  # !!!!
            logger.debug(f"Authorization for {self.ws_name} failed. Please check your API keys and restart.")

    async def _handle_incoming_message(self, message: dict):
        def is_auth_message():
            return message.get("channel", "") == "rs.login"

        def is_subscription_message():
            return message.get("channel", "").startswith("rs.sub") or message.get("channel", "") == "rs.personal.filter"

        def is_pong_message():
            return message.get("channel", "") in ("pong", "clientId")

        def is_error_message():
            return message.get("channel", "") == "rs.error"

        if is_auth_message():
            await self._process_auth_message(message)
        elif is_subscription_message():
            self._process_subscription_message(message)
        elif is_pong_message():
            pass
        elif is_error_message():
            print(f"WebSocket return error: {message}")
        else:
            await self._process_normal_message(message , return_wrapper_data = False)

    async def custom_topic_stream(self, topic, callback):
        return await self.subscribe(topic=topic, callback=callback)


class _FuturesWebSocket(_FuturesWebSocketManager):
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        loop: asyncio.AbstractEventLoop = None,
        subscribe_callback: Callable = None,
        **kwargs,
    ):
        self.ws_name = "FuturesV1"
        self.endpoint = FUTURES
        loop = loop or asyncio.get_event_loop()

        if subscribe_callback:
            loop.create_task(self.connect())

        super().__init__(
            self.ws_name,
            api_key=api_key,
            api_secret=api_secret,
            loop=loop,
            subscribe_callback=subscribe_callback,
            **kwargs,
        )
    def disconnect(self):
        if self.is_connected():
            self.exit()
        #await asyncio.sleep(1)

    async def connect(self):
        if not self.is_connected():
            await self._connect(self.endpoint)

    async def _ws_subscribe(self, topic, callback, params: list = []):
        #await self.connect()
        
        if not self.is_connected():
            await self._connect(self.endpoint)
            
        await self.subscribe(topic, callback, params)


# # # # # # # # # #
#                 #
#       SPOT      #
#                 #
# # # # # # # # # #


class _SpotWebSocketManager(_AsyncWebSocketManager):
    def __init__(self, ws_name, **kwargs):
        callback_function = (
            kwargs.pop("callback_function") if kwargs.get("callback_function") else self._handle_incoming_message
        )
        self.message_shaper_dict = {
            "public.aggre.deals": lambda params: f"spot@public.aggre.deals.v3.api{(".pb" if self.proto else "")}@{params['interval']}@{params['symbol']}",
            "public.kline": lambda params: f"spot@public.kline.v3.api{(".pb" if self.proto else "")}@{params['interval']}@{params['symbol']}",
            "public.aggre.depth": lambda params: f"spot@public.aggre.depth.v3.api{(".pb" if self.proto else "")}@{params['interval']}@{params['symbol']}", 
            "public.limit.depth": lambda params: f"spot@public.limit.depth.v3.api{(".pb" if self.proto else "")}@{params['symbol']}@{params['level']}",
            "public.aggre.bookTicker": lambda params: f"spot@public.aggre.bookTicker.v3.api{(".pb" if self.proto else "")}@{params['interval']}@{params['symbol']}",
            "public.bookTicker.batch": lambda params: f"spot@public.bookTicker.batch.v3.api{(".pb" if self.proto else "")}@{params['symbol']}",
            "private.account": lambda : [{}],
            "private.deals": lambda : [{}],
            "private.orders": lambda : [{}]
        }
        super().__init__(callback_function, ws_name, **kwargs)


        self.private_topics = ["account", "deals", "orders"]

    def _subscribe_one(self, topic: str, callback: Callable, params: dict, message_shaper: Callable):
        subscribe_message = message_shaper(params)
        self._check_callback_directory(subscribe_message)
        self.subscriptions.append(subscribe_message)
        self._set_callback(topic = subscribe_message, callback_function = callback )
        return subscribe_message
    
    def _unsubscribe_one(self, topic: str, params: dict, message_shaper: Callable = None):
        subscribe_message = message_shaper(params)
        #self._check_callback_directory(f"{topic}@{params.get("symbol","_")}")
        self.subscriptions.remove(subscribe_message)
        self._pop_callback(topic = subscribe_message)
        logger.debug(f"Unsubscribed from {topic} with subscription message {subscribe_message}")
        return subscribe_message

    async def subscribe(self, topic: str, callback: Callable, params_list: list):
        
        subscription_args_params = [self._subscribe_one(topic, callback, params, self.message_shaper_dict[topic]) for params in params_list ]
        
        subscription_args = {
            "method": "SUBSCRIPTION",
            "params": subscription_args_params,
        }

        while not self.is_connected():
            # Wait until the connection is open before subscribing.
            await asyncio.sleep(0.1)

        await self.ws.send_json(subscription_args)
        
        self.last_subsctiption = subscription_args_params[-1]
       

    async def unsubscribe(self, topic: str | Callable, params_list:list[dict]):

        if isinstance(topic, str):
            unsub_args_params = [self._unsubscribe_one(topic, params, self.message_shaper_dict[topic]) for params in params_list ]
            #topic = f"private.{topic}"if topic in self.private_topics else f"public.{topic}"
                # if user provide function .book_ticker_stream()
                #.replace("book.ticker", "bookTicker")
                #for topic in topics
            
            # remove callbacks
            #for topic in topics:
            #    self._pop_callback(topic)

            # send unsub message

            await self.ws.send_json(
                {
                    "method": "UNSUBSCRIPTION", # "@".join([f"spot@{t}.v3.api" + (".pb" if self.proto else "")]) for t in topics
                    "params": unsub_args_params,
                }
            )

            # remove subscriptions from list
            '''for i, sub in enumerate(self.subscriptions):
                new_params = [x for x in sub["params"] for _topic in topics if _topic not in x]
                if new_params:
                    self.subscriptions[i]["params"] = new_params
                else:
                    self.subscriptions.remove(sub)
                break'''

            
        else:
            # some funcs in list
            
            str_topic_short = topic.__name__.replace("_stream", "").replace("_", ".") if getattr(topic, "__name__", None) else topic
            #str_topic = f"spot@{str_topic_short}.v3.api{(".pb" if self.proto else "")}"
            print(str_topic_short)
            
            return await self.unsubscribe(str_topic_short, params_list)

    async def _handle_incoming_message(self, message):
        def is_subscription_message():
            if message.get("id") == 0 and message.get("code") == 0 and message.get("msg"):
                return True
            else:
                return False

        if isinstance(message, dict) and is_subscription_message():
            self._process_subscription_message(message)
        else:
            await self._process_normal_message(message, return_wrapper_data = True)

    async def custom_topic_stream(self, topic, callback):
        return await self.subscribe(topic=topic, callback=callback)


class _SpotWebSocket(_SpotWebSocketManager):
    listenKey: str
    http: "HTTP"

    def __init__(
        self,
        endpoint: str = SPOT,
        api_key: str = None,
        api_secret: str = None,
        loop: asyncio.AbstractEventLoop = None,
        **kwargs,
    ):
        self.ws_name = "SpotV3"
        self.endpoint = endpoint
        loop = loop or asyncio.get_event_loop()

        

        super().__init__(self.ws_name, api_key=api_key, api_secret=api_secret, loop=loop, **kwargs)
    
        

    async def _ws_subscribe(self, topic, callback, params_list: list[dict]):
        # Можно сюда передать функцию - формирователь сообщения

        if not self.is_connected():
            await self._connect(self.endpoint)

        await self.subscribe(topic, callback, params_list)
