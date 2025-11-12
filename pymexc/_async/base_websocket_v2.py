

import asyncio
import json
import websockets
import logging
import ssl

from abc import ABC, abstractmethod
from aiolimiter import AsyncLimiter
from typing import Awaitable, Callable, Union, Literal, get_args
from websockets.exceptions import WebSocketException
from pymexc.proto import ProtoTyping, PushDataV3ApiWrapper


from pymexc.models import (SpotMessageShaper, 
                           SpotSubscriptionParams, 
                           SpotTopics, 
                           FuturesMessageShaper, 
                           FuturesSubscriptionParams, 
                           FuturesTopics,
                           ProxySettings,
                           ApiSettings,
                           ProtoSettings,
                           CallbackSettings)

logger = logging.getLogger(__name__)

SPOT = "wss://wbs-api.mexc.com/ws"
FUTURES = "wss://contract.mexc.com/edge"

class _BaseMessageParser:
    
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
    def is_auth_message(message:dict):
        return message.get("channel", "") == "rs.login"
    
    @staticmethod
    def is_pong_message(message:dict):
        return message.get("msg", "") in ("pong", "clientId", "PONG")
    
    @staticmethod
    def is_error_message(message: dict):
        return message.get("channel", "") == "rs.error"

class _SpotMessageParser(_BaseMessageParser):

    @staticmethod
    def is_subscription_message(message:dict):
        if message.get("id") == 0 and message.get("code") == 0 and message.get("msg"):
            return True
        else:
            return False
    
class _FuturesMessageParser(_BaseMessageParser):
    
    @staticmethod
    def is_subscription_message(message:dict):
        return message.get("channel", "").startswith("rs.sub") or message.get("channel", "") == "rs.personal.filter"

class _AsyncWebSocketManagerV2(ABC):

    @property
    @abstractmethod
    def market_type(self): ...
 
    @property
    def auth(self):
        self.__api_settings.auth

    def __init__(self,
                 loop,
                 callback_settings: CallbackSettings,
                 proto_settings: ProtoSettings,
                 api_settings: ApiSettings,
                 proxy_settings:ProxySettings,
                 sending_limiter:AsyncLimiter,
                 ping_interval = 20,
                 ) -> None:
 
        
        self.base_callback = callback_settings.base_callback
        self.use_common_callback = callback_settings.use_common_callback
        self._common_callback = callback_settings.common_callback
        self.use_common_callback_for_topic = callback_settings.use_common_callback_for_topic
        
        self.ping_interval = ping_interval
        self.event_loop:asyncio.AbstractEventLoop = loop
        self.extend_proto_body = proto_settings.extend_proto_body()
        
        self.__api_settings = api_settings
        
        self._sending_limiter = sending_limiter # or AsyncLimiter(max_rate = 100, time_period = 1)

        self.proxy_settings = proxy_settings
        self.use_proto = proto_settings.proto
        self.proto_bodies = proto_settings.proto_bodies
        
        
        self.retries = 10
        self.subscriptions = []
        self.chunk_size = 50
        self._connected = False
        self.callback_directory = dict()

        
        self.proxy_str = self.proxy_settings.get_proxy_url() if self.proxy_settings else None
        
        self._sending_queue = asyncio.Queue()
        self._ping_message = json.dumps({"method": "ping"})
    
    def _set_callback_sign(self, topic_sign: str, callback_function: Callable):
        self.callback_directory[topic_sign] = callback_function

    def _get_callback_sign(self, topic_sign: str) -> Union[Callable[..., None], None]:
        return self.callback_directory.get(topic_sign)
    
    def _pop_callback_sign(self, topic_sign: str) -> Union[Callable[..., None], None]:
        return self.callback_directory.pop(topic_sign, None)
    
    #REVIEW а нужно ли мне вообще колбеки по топикам делать?
    #def _set_callback_topic(self, topic_name:str):
    #    pass
    
    #def _get_callback_topic(self, topic_name:str):
    #    pass

    #def _pop_callback(self, topic_sign: str) -> Union[Callable[..., None], None]:
    #    return self.callback_directory.pop(topic_sign) if self.callback_directory.get(topic_sign) else None

    
    def get_proto_body(self, message: ProtoTyping.PushDataV3ApiWrapper) -> dict:
        if self.extend_proto_body:
            return message
        #TODO мб парсер пусть возвращает топик из enum?
        topic = _BaseMessageParser._topic(message.channel)

        if topic in self.proto_bodies:
            return getattr(message, self.proto_bodies[topic])  # default=message
        else:
            logger.warning(f"Body for topic {topic} not found. | Message: {message.__dict__}")
            return message

    async def _on_open(self):
        self._connected = True
        
    async def _on_message(self, message: Union[str, bytes], parse_only: bool):
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
            async with self._sending_limiter:
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

    #TODO сделать обработку таким образом что-бы можно для одних и тех же топиков устанавливать 1 коллбек
    def _process_normal_message(self, message: dict | ProtoTyping.PushDataV3ApiWrapper, parse_only: bool = True, return_wrapper_data = True):
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
        
        if self.use_common_callback:
            callback_function = self._common_callback
        #elif self.use_common_callback_for_topic:
        #    callback_function = self._get_callback_topic()
        else:
            callback_function = self._get_callback_sign(topic)
            
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


# # # # # # # # # #
#                 #
#     FUTURES     #
#                 #
# # # # # # # # # #


class _FuturesWebSocketManager(_AsyncWebSocketManagerV2):
    
    def __init__(self,
                 loop:asyncio.AbstractEventLoop,
                 callback_settings:CallbackSettings,  
                 api_settings:ApiSettings,
                 proxy_settings:ProxySettings,
                 proto = False):
        
        
        proto_settings = ProtoSettings(proto = proto, extend_proto_body = False, proto_bodies = None)
        
        if callback_settings.base_callback is None: 
            callback_settings.base_callback = self._handle_message
        
        super().__init__(loop = loop,
                         callback_settings = callback_settings,
                         proto_settings = proto_settings,
                         api_settings = api_settings,
                         proxy_settings = proxy_settings,
                         sending_limiter = AsyncLimiter(max_rate = 20, time_period = 1))
        
        self.current_subscribed_topics:dict[FuturesTopics,int] = dict().fromkeys(FuturesTopics._member_map_.values(), 0)

    def _subscribe_one(self, callback: Callable, topic:FuturesTopics, params: dict):

        params['proto'] = False #self.use_proto пока Mexc не реализовал Protobuf для фьючей
        
        subscribe_message = FuturesMessageShaper.shape_message(action = "sub", sub_type = topic, params = FuturesSubscriptionParams(**params))
        subscribe_signature = FuturesMessageShaper.shape_signature(sub_type = topic, params = FuturesSubscriptionParams(**params))
        
        self.subscriptions.append(subscribe_signature)
        self.current_subscribed_topics[topic] += 1
        if not self.use_common_callback:
            self._set_callback_sign(topic_sign = subscribe_signature, callback_function = callback )
        return subscribe_message
    
    def _unsubscribe_one(self, topic: FuturesTopics, params: dict):
        
        if self.current_subscribed_topics[topic] <= 0:
            # Ты даже на него не подписан ЛОХ
            return None
        
        params['proto'] = False #self.use_proto
        
        subscribe_message = FuturesMessageShaper.shape_message(action="unsub", sub_type = topic, params = FuturesSubscriptionParams(**params))
        subscribe_signature = FuturesMessageShaper.shape_signature(sub_type = topic, params = FuturesSubscriptionParams(**params))
        
        self.subscriptions.remove(subscribe_signature)
        self.current_subscribed_topics[topic] -= 1
        
        if not self.use_common_callback:
            self._pop_callback_sign(topic_sign = subscribe_signature)
        logger.debug(f"Unsubscribed from {topic.value} with subscription signature {subscribe_signature}")
        
        return subscribe_message
    
    async def subscribe(self, topic: FuturesTopics, params_list: list, callback: Callable = None):
        
        if not isinstance(topic, FuturesTopics):
            raise TypeError(f"argument 'topic' must be a type FuturesTopics")
        
        
        subscription_args_params = [self._subscribe_one(callback, topic, params) for params in params_list]
        for message in subscription_args_params:
            self.write(message)
        

    async def unsubscribe(self, topic: FuturesTopics, params_list:list[dict]):
        if not isinstance(topic, SpotTopics):
            raise TypeError(f"argument 'topic' must be a type FuturesTopics")
        
        unsub_args_params = [message for message in [self._unsubscribe_one(topic, params) for params in params_list] if message is not None]
        
        for message in unsub_args_params:
            self.write(message)
            
    def _process_subscription_message(self, message):
        logger.info(f"sub: {message}")

    def _handle_message(self, message):
        
        if isinstance(message, dict) and _FuturesMessageParser.is_subscription_message(message):
            self._process_subscription_message(message)
        else:
            self._process_normal_message(message, return_wrapper_data = True)


class _SpotWebSocketManager(_AsyncWebSocketManagerV2):

    def __init__(self,
                 loop:asyncio.AbstractEventLoop,
                 callback_settings:CallbackSettings,  
                 api_settings:ApiSettings,
                 proxy_settings:ProxySettings, 
                 proto=True, 
                 ):
        
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
        proto_settings = ProtoSettings(proto = proto, extend_proto_body = False, proto_bodies = bodies)
        
        if callback_settings.base_callback is None: 
            callback_settings.base_callback = self._handle_message

        super().__init__(
                         loop = loop,
                         callback_settings = callback_settings,
                         proto_settings = proto_settings,
                         api_settings = api_settings,
                         proxy_settings = proxy_settings,
                         sending_limiter = AsyncLimiter(max_rate = 100, time_period = 1))
        
        self.current_subscribed_topics:dict[SpotTopics,int] = dict().fromkeys(SpotTopics._member_map_.values(), 0)

    def _subscribe_one(self, callback: Callable, topic:SpotTopics, params: dict):

        params['proto'] = self.use_proto
        
        subscribe_message = SpotMessageShaper.shape_message(sub_type = topic, params = SpotSubscriptionParams(**params))
        self.subscriptions.append(subscribe_message)
        self.current_subscribed_topics[topic] += 1
        
        if not self.use_common_callback:
            self._set_callback_sign(topic_sign = subscribe_message, callback_function = callback )
        return subscribe_message

    def _unsubscribe_one(self, topic: SpotTopics, params: dict):
        
        if self.current_subscribed_topics[topic] <= 0:
            # Ты даже на него не подписан ЛОХ
            return None
        
        params['proto'] = self.use_proto
        
        subscribe_message = SpotMessageShaper.shape_message(sub_type = topic, params = SpotSubscriptionParams(**params))
        self.subscriptions.remove(subscribe_message)
        self.current_subscribed_topics[topic] -= 1
        
        if not self.use_common_callback:
            self._pop_callback_sign(topic_sign = subscribe_message)
        logger.debug(f"Unsubscribed from {topic.value} with subscription message {subscribe_message}")
        return subscribe_message

    async def subscribe(self, topic: SpotTopics, params_list: list, callback: Callable = None):
        
        if not isinstance(topic, SpotTopics):
            raise TypeError(f"argument 'topic' must be a type Topics")
        
        
        subscription_args_params = [self._subscribe_one(callback, topic, params) for params in params_list]
        subscription_args = {
            "method": "SUBSCRIPTION",
            "params": subscription_args_params,
        }
        self.write(json.dumps(subscription_args))

    async def unsubscribe(self, topic: SpotTopics, params_list:list[dict]):
        if not isinstance(topic, SpotTopics):
            raise TypeError(f"argument 'topic' must be a type SpotTopics")
        
        unsub_args_params = [message for message in [self._unsubscribe_one(topic, params) for params in params_list] if message is not None]
        unsub_args = {
            "method": "UNSUBSCRIPTION",
            "params": unsub_args_params,
        }
        self.write(json.dumps(unsub_args))

    def _process_subscription_message(self, message):
        logger.info(f"sub: {message}")
        

    def _handle_message(self, message):
        
        if isinstance(message, dict) and _SpotMessageParser.is_subscription_message(message):
            self._process_subscription_message(message)
        else:
            self._process_normal_message(message, return_wrapper_data = True)
            
class _FuturesWebSocket(_FuturesWebSocketManager):
    listenKey: str

    @property
    def market_type(self):
        return "futures"
    
    def __init__(
        self,
        callback_settings: CallbackSettings,
        api_settings: ApiSettings,
        proxy_settings: ProxySettings,
        loop: asyncio.AbstractEventLoop = None,
    ):
        self.ws_name = "FuturesV1"
        self.endpoint = FUTURES
        loop = loop or asyncio.get_event_loop()
        
        super().__init__(loop = loop,
                         callback_settings = callback_settings,
                         api_settings = api_settings,
                         proxy_settings = proxy_settings)


    async def connect(self):
        self.connection_task = self.event_loop.create_task(self._connect(self.endpoint)) 

    async def disconnect(self):
        self.connection_task.cancel()
        await asyncio.sleep(0.2)

    async def _ws_subscribe(self, topic:FuturesTopics, params_list: list[dict], callback = None):
        if not self._connected:
            #raise ValueError("Не подключено")
            await self._connect(self.endpoint)
            await asyncio.sleep(0.1)
            
        await self.subscribe(topic, callback, params_list)


class _SpotWebSocket(_SpotWebSocketManager):
    listenKey: str

    @property
    def market_type(self):
        return "spot"
    
    def __init__(
        self,
        callback_settings: CallbackSettings,
        api_settings: ApiSettings,
        proxy_settings: ProxySettings,
        loop: asyncio.AbstractEventLoop,
    ):
        self.ws_name = "SpotV3"
        self.endpoint = SPOT
        super().__init__(loop = loop,
                         callback_settings = callback_settings,
                         api_settings = api_settings,
                         proxy_settings = proxy_settings)


    async def connect(self):
        self.connection_task = self.event_loop.create_task(self._connect(self.endpoint)) 

    async def disconnect(self):
        self.connection_task.cancel()
        await asyncio.sleep(0.2)

    async def _ws_subscribe(self, topic:SpotTopics, params_list: list[dict], callback = None):
        if not self._connected:
            #raise ValueError("Не подключено")
            await self._connect(self.endpoint)
            await asyncio.sleep(0.1)
            
        await self.subscribe(topic, callback, params_list)

    