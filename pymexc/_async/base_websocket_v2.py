

import asyncio
import json
import websockets
import logging
 
from websockets.exceptions import WebSocketException
from pymexc.proto import ProtoTyping, PublicSpotKlineV3Api, PushDataV3ApiWrapper

logger = logging.getLogger(__name__)



class _AsyncWebSocketManagerV2:
    
    def __init__(self,
                 base_callback = None,
                 ping_interval = 20,
                 loop = None) -> None:
        
        
        self.base_callback = base_callback or self._handle_message
        self.ping_interval = ping_interval
        self.subscriptions = []
        self.chunk_size = 50
        self.connected = False
        self.event_loop:asyncio.AbstractEventLoop = loop
        self._ping_message = json.dumps({"method": "ping"})
    
    async def _on_open(self):
        self.connected = True
        
    async def _on_message(self, message: str, parse_only: bool):
        """
        Parse incoming messages.
        """
        if isinstance(message, str):
            _message = json.loads(message)

        elif isinstance(message, bytes):
            # Deserialize message
            #print(f"Распарсил {message}")
            _message = PushDataV3ApiWrapper()
            _message.ParseFromString(message)
            #print(f" полученное сообщение {_message}")
        else:
            raise ValueError(f"Unserializable message type: {type(message)} | {message}")

        if parse_only:
            return _message
        #print(self.callback)
        await self.base_callback(_message)
        
    async def _on_error(self):
        pass
        
        
    async def _active_ping(self,conn: websockets.ClientConnection):
        while True:
            await conn.send(self._ping_message)
            await asyncio.sleep(self.ping_interval)
                

    async def _read(self, conn: websockets.ClientConnection):      
        try:
            async for msg in conn:
                await self._on_message(msg) 
        finally:
            await self._on_close()
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
                
                    
    async def _handle_message(self, message: dict):
        def is_auth_message():
            return message.get("channel", "") == "rs.login"

        def is_subscription_message():
            return message.get("channel", "").startswith("rs.sub") or message.get("channel", "") == "rs.personal.filter"

        def is_pong_message():
            return message.get("channel", "") in ("pong", "clientId")

        def is_error_message():
            return message.get("channel", "") == "rs.error"

        if is_auth_message():
            self._process_auth_message(message)
        elif is_subscription_message():
            self._process_subscription_message(message)
        elif is_pong_message():
            pass
        elif is_error_message():
            print(f"WebSocket return error: {message}")
        else:
            await self._process_normal_message(message , return_wrapper_data = False)
    
    async def _connect(self, url):
        stopped = False
        retried = 0
        self.endpoint = url
        try:
            conn = await websockets.connect(self.endpoint, compression=None)
        
        except (WebSocketException, ConnectionRefusedError, OSError) as e:
            '''logger.warning(
                    "failed to connect to server for the %d time, try again later: %s", MLCUSDT
                    retried + 1,
                    e,
                )'''    
            await asyncio.sleep(0.5 * retried)
        else:
            tasks: list[asyncio.Task] = list()
            try:
                tasks.append(self.event_loop.create_task(self._write(conn)))
                tasks.append(self.event_loop.create_task(self._read(conn)))
                tasks.append(self.event_loop.create_task(self._active_ping(conn)))
                self.main_loop = asyncio.gather(*tasks)
                await self.main_loop
            except websockets.ConnectionClosed:
                logger.warning("websocket connection lost, retry to reconnect")
            except asyncio.CancelledError:
                await conn.close()
                stopped = True
            finally:
                # user callback tasks are not our concern
                for task in tasks:
                    task.cancel()