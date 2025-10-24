

import asyncio
import json
import websockets
import logging
import ssl

from abc import ABC,abstractmethod
from aiolimiter import AsyncLimiter
from typing import Awaitable, Callable, Union, Literal, get_args
from websockets.exceptions import WebSocketException
from pymexc.proto import ProtoTyping, PushDataV3ApiWrapper
from pymexc.models.proxy import ProxySettings

logger = logging.getLogger(__name__)

SPOT = "wss://wbs-api.mexc.com/ws"
FUTURES = "wss://contract.mexc.com/edge"

SPOT_AVALIABLE_TOPICS = Literal[
    "public.aggre.deals",
    "public.kline",
    "public.aggre.depth",
    "public.limit.depth",
    "public.aggre.bookTicker",
    "public.bookTicker.batch",
    "private.account",
    "private.deals",
    "private.orders"]

class _SpotMessageParser:
    
    @staticmethod
    def _topic(topic:str):
        return (
            topic.replace("sub.", "")
            .replace("push.", "")
            .replace("rs.sub.", "")
            .replace("spot@", "")
            .replace(".pb", "")
            .split(".v3.api")[0]
        )
    
    @staticmethod
    def _is_auth_message(message:dict):
        return message.get("channel", "") == "rs.login"

    @staticmethod
    def _is_subscription_message(message:dict):
        if message.get("id") == 0 and message.get("code") == 0 and message.get("msg"):
            return True
        else:
            return False
        
    @staticmethod
    def _is_pong_message(message:dict):
        return message.get("msg", "") in ("pong", "clientId","PONG")
    
    @staticmethod
    def _is_error_message(message:dict):
        return message.get("channel", "") == "rs.error"

class _AsyncWebSocketManagerV2(ABC):

    @property
    @abstractmethod
    def market_type(self):...
    

    def __init__(self,
                 base_callback = None,
                 use_common_callback = True,
                 commn_callback = None,
                 ping_interval = 20,
                 loop = None,
                 proto = False,
                 sending_limiter:AsyncLimiter = None,
                 extend_proto_body = False,
                 proxy_settings:ProxySettings = None
                 ) -> None:
 
        
        self.base_callback = base_callback 
        self.use_common_callback = use_common_callback
        self._commn_callback = commn_callback
        self.ping_interval = ping_interval
        self.retries = 10
        self.subscriptions = []
        self.chunk_size = 50
        self._connected = False
        self.event_loop:asyncio.AbstractEventLoop = loop
        self.proto = proto
        self._sending_limiter = sending_limiter or AsyncLimiter(max_rate = 100, time_period = 1)
        self.extend_proto_body = extend_proto_body
        self.callback_directory = dict()

        self.proxy_settings = proxy_settings
        
        
        self.proxy_str = self.proxy_settings.get_proxy_url() if self.proxy_settings else None
        
        self._sending_queue = asyncio.Queue()
        self._ping_message = json.dumps({"method": "ping"})
    
    def _set_callback(self, topic: str, callback_function: Callable):
        self.callback_directory[topic] = callback_function

    def _get_callback(self, topic: str) -> Union[Callable[..., None], None]:
        return self.callback_directory.get(topic)

    def _pop_callback(self, topic: str) -> Union[Callable[..., None], None]:
        return self.callback_directory.pop(topic) if self.callback_directory.get(topic) else None
    
    def get_proto_body(self, message: ProtoTyping.PushDataV3ApiWrapper) -> dict:
        if self.extend_proto_body:
            return message

        topic = _SpotMessageParser._topic(message.channel)
        bodies = {
            "public.kline": "publicSpotKline",
            "public.deals": "publicDeals",
            "public.aggre.depth": "publicAggreDepths",
            "public.aggre.deals": "publicAggreDeals",
            "public.increase.depth": "publicIncreaseDepths",
            "public.limit.depth": "publicLimitDepths",
            "public.bookTicker": "publicBookTicker",
            "private.account": "privateAccount",
            "private.deals": "privateDeals",
            "private.orders": "privateOrders",
        }
        

        if topic in bodies:
            return getattr(message, bodies[topic])  # default=message

        else:
            logger.warning(f"Body for topic {topic} not found. | Message: {message.__dict__}")
            return message

    async def _on_open(self):
        self._connected = True
        
    async def _on_message(self, message: str, parse_only: bool):
        """
        Parse incoming messages.
        """
        if isinstance(message, str):
            _message = json.loads(message)
        elif isinstance(message, bytes):
            _message = PushDataV3ApiWrapper()
            _message.ParseFromString(message)
        else:
            raise ValueError(f"Unserializable message type: {type(message)} | {message}")

        if parse_only:
            return _message

        await self.base_callback(_message)
        
    async def _on_error(self):
        pass

    def write(self,message):
        self._sending_queue.put_nowait(message)

    async def _write(self,conn: websockets.ClientConnection):
        logger.debug(f"задача _write начата")  
        while True:
            msg = await self._sending_queue.get()
            #async with self._sending_limiter:
            await conn.send(msg)

    async def _active_ping(self,conn: websockets.ClientConnection):
        logger.debug(f"задача _active_ping начата")  
        while True:
            await conn.send(self._ping_message)
            await asyncio.sleep(self.ping_interval)
                

    async def _read(self, conn: websockets.ClientConnection):
        logger.debug(f"задача _read начата")      
        try:
            async for msg in conn:
                await self._on_message(msg, parse_only = False) 
        finally:
            #await self._on_close()
            await conn.close()
                    
    async def resubscribe_to_topics(self, conn: websockets.ClientConnection):
        if not self.subscriptions:
            # There are no subscriptions to resubscribe to, probably
            # because this is a brand new WSS initialisation so there was
            # no previous WSS connection.
            return
        
        if len(self.subscriptions) > self.chunk_size:
            result = [self.subscriptions[i:i + self.chunk_size]    
            for i in range(0, len(self.subscriptions), self.chunk_size)]
            
            for chunk in result:
                await conn.send(json.dumps(
                {"method": "SUBSCRIPTION",
                "params": chunk}))
                await asyncio.sleep(0.1)
        else:
            await conn.send(json.dumps(
                {"method": "SUBSCRIPTION",
                "params": self.subscriptions}))

    async def _process_normal_message(self, message: dict | ProtoTyping.PushDataV3ApiWrapper, parse_only: bool = True, return_wrapper_data = True):
        """
        Redirect message to callback function
        """
        logger.debug(f"_process_normal_message: {message}")
        if isinstance(message, dict):
            
            topic:str = message.get("channel") or message.get("c") or message.get("msg")# if not full_topic else (message.get("channel") or message.get("c"))
            topic = topic.replace("push.","")
            return_wrapper_data = False
            callback_data = message
        else:
            topic = message.channel#self._topic(message.channel) if not full_topic else message.channel
            callback_data = self.get_proto_body(message)
            
        if return_wrapper_data:
            wrapper_data = dict(symbol = message.symbol, 
                                symbolId = message.symbolId,
                                createTime = message.createTime, 
                                sendTime = message.sendTime)
        else:
            wrapper_data = None
        
        callback_function =  self._commn_callback if self.use_common_callback else self._get_callback(topic) or self._commn_callback

        if not callback_function:
            logger.warning(f"Callback for topic {topic} not found. | Message: {message}")
            return None, None, None
        else:
            if parse_only:
                return callback_function, callback_data, wrapper_data

            callback_function(callback_data,wrapper_data)
    
    async def _connect(self, url):
        
        retried = 0
        self.endpoint = url

        retries = self.retries if self.retries > 0 else 0
        infinitely_reconnect = retries == 0
        
        while (infinitely_reconnect or retries > 0):
            try:
                #ctx = None
                logger.debug(self.endpoint)
                ctx = ssl.create_default_context()
                conn = await websockets.connect(self.endpoint, 
                                                ssl=ctx ,
                                                compression=None, 
                                                proxy = self.proxy_str)
                
            except (WebSocketException, ConnectionRefusedError, OSError) as e:

                logger.warning("failed to connect to server for the %d time, try again later: %s", retried + 1, e)
                retried += 1    
                await asyncio.sleep(0.5 * retried)

            else:
                logger.debug("Подключилось")
                self._connected = True
                tasks: list[asyncio.Task] = list()

                try:
                    tasks.append(self.event_loop.create_task(self._read(conn)))
                    tasks.append(self.event_loop.create_task(self._write(conn)))
                    tasks.append(self.event_loop.create_task(self._active_ping(conn)))
                    tasks.append(self.event_loop.create_task(self.resubscribe_to_topics(conn=conn)))
                    self.main_loop = asyncio.gather(*tasks)
                    await self.main_loop
                except websockets.ConnectionClosed:
                    logger.warning("websocket connection lost, retry to reconnect")
                except asyncio.CancelledError:
                    await conn.close()
                    self._connected = False
                finally:
                    # user callback tasks are not our concern
                    for task in tasks:
                        task.cancel()




class _SpotWebSocketManager(_AsyncWebSocketManagerV2):

    def __init__(self, base_callback=None, ping_interval=20, loop=None, proto=False, common_callback = None, **kwargs):

        super().__init__(base_callback = base_callback or self._handle_message,
                         ping_interval = ping_interval, 
                         loop = loop, 
                         proto = proto,
                         common_callback = common_callback
                         **kwargs)
        
        self.set_avaliable_topics = set(get_args(SPOT_AVALIABLE_TOPICS))
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
    #def set_callback(self, topic, callback_function:Union[Callable,Awaitable]):
    #    return super()._set_callback(topic, callback_function)

    def _subscribe_one(self, callback: Callable, params: dict, message_shaper: Callable):
        subscribe_message = message_shaper(params)
        self.subscriptions.append(subscribe_message)
        if not self.use_common_callback:
            self._set_callback(topic = subscribe_message, callback_function = callback )
        return subscribe_message
    
    def _unsubscribe_one(self, topic: str, params: dict, message_shaper: Callable = None):
        subscribe_message = message_shaper(params)
        
        self.subscriptions.remove(subscribe_message)
        if self.use_common_callback:
            self._pop_callback(topic = subscribe_message)
        logger.debug(f"Unsubscribed from {topic} with subscription message {subscribe_message}")
        return subscribe_message

    async def subscribe(self, topic: SPOT_AVALIABLE_TOPICS, params_list: list, callback: Callable = None):
        
        if not topic in self.set_avaliable_topics:
            raise ValueError("unknow topic name")
    
        subscription_args_params = [self._subscribe_one(callback, params, self.message_shaper_dict[topic]) for params in params_list ]
        subscription_args = {
            "method": "SUBSCRIPTION",
            "params": subscription_args_params,
        }
        await asyncio.sleep(0.1)
        self.write(json.dumps(subscription_args))

    async def unsubscribe(self, topic: SPOT_AVALIABLE_TOPICS, params_list:list[dict]):

        if not topic in self.set_avaliable_topics:
            raise ValueError("unknow topic name")
        
        unsub_args_params = [self._unsubscribe_one(topic, params, self.message_shaper_dict[topic]) for params in params_list ]
        self.write(json.dumps(
            {
                "method": "UNSUBSCRIPTION",
                "params": unsub_args_params,
            }
        ))

    def _process_subscription_message(self,message):
        print(f"sub: {message}")
        pass

    async def _handle_message(self, message):
        
        
        if isinstance(message, dict) and _SpotMessageParser._is_subscription_message(message):
            self._process_subscription_message(message)
        else:
            await self._process_normal_message(message, return_wrapper_data = True)

            
        


class _SpotWebSocket(_SpotWebSocketManager):
    listenKey: str

    @property
    def market_type(self):
        return "spot"
    
    def __init__(
        self,
        endpoint: str = SPOT,
        #api_key: str = None,
        #api_secret: str = None,
        loop: asyncio.AbstractEventLoop = None,
        common_callback = None,
        **kwargs,
    ):
        self.ws_name = "SpotV3"
        self.endpoint = endpoint
        loop = loop or asyncio.get_event_loop()
        super().__init__(loop = loop, common_callback = common_callback, **kwargs)


    async def connect(self):
        self.connection_task = self.event_loop.create_task(self._connect(self.endpoint)) 

    async def disconnect(self):
        self.connection_task.cancel()
        await asyncio.sleep(0.2)

    async def _ws_subscribe(self, topic:SPOT_AVALIABLE_TOPICS, params_list: list[dict], callback = None):

        if not self._connected:
            print("подключаюсь")
            #raise ValueError("Не подключено")
            await self._connect(self.endpoint)
            await asyncio.sleep(0.1)
            
        print(f"отправляю топик {topic}")
        await self.subscribe(topic, callback, params_list)

    