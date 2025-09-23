
import asyncio
from typing import Literal,get_args
from pymexc._async.base_websocket_v2 import _SpotWebSocket

async def handle_push(message,wrapped_data):
    print(message)


async def main():

    x = _SpotWebSocket(base_callback = handle_push )
    params_list = [dict(symbol = "BTCUSDT", interval = "Min1")]
    await x._ws_subscribe(topic="public.kline",params_list = params_list)

    while True:
        await asyncio.sleep(1)

AVALIABLE_TOPICS = Literal["public.aggre.deals",
                    "public.kline",
                    "public.aggre.depth",
                    "public.limit.depth",
                    "public.aggre.bookTicker",
                    "public.bookTicker.batch",
                    "private.account",
                    "private.deals",
                    "private.orders"]

if __name__ == "__main__":
    asyncio.run(main())