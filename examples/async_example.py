import asyncio
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from pymexc._async import spot, futures


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
api_key = None#"YOUR API KEY"
api_secret = None#"YOUR API SECRET KEY"


async def handle_message(message: dict,sub_data):
    # handle websocket message
    print(message)

loop = asyncio.new_event_loop()

async def main():
    # SPOT V3

    # initialize HTTP client
    #spot_client = spot.HTTP(api_key=api_key, api_secret=api_secret)
    # initialize WebSocket client
    #ws_spot_client = spot.WebSocket(api_key=api_key, api_secret=api_secret)

    # FUTURES V1

    # initialize HTTP client
    #futures_client = futures.AsyncHTTP(api_key=api_key, api_secret=api_secret)
    # initialize WebSocket client
    #print(futures.WebSocket.__mro__)
    ws_futures_client = futures.WebSocket(api_key=api_key, api_secret=api_secret)

    # SPOT

    # make http request to api
    #print(await spot_client.exchange_info())

    # create websocket connection to public channel (spot@public.deals.v3.api@BTCUSDT)
    # all messages will be handled by function `handle_message`
    #await ws_spot_client.deals_stream(handle_message, "BTCUSDT")

    # Unsubscribe from deals topic
    # await ws_spot_client.unsubscribe(ws_spot_client.deals_stream)
    # OR
    # await ws_spot_client.unsubscribe("deals")

    # FUTURES

    # make http request to api
    #print(await futures_client.index_price("MX_USDT"))

    # create websocket connection to public channel (sub.tickers)
    # all messages will be handled by function `handle_message`
    await ws_futures_client.kline_stream(handle_message,symbol="XRP_USDT",interval="Min5")
    await ws_futures_client.kline_stream(handle_message,symbol="BTC_USDT",interval="Min5")
    await ws_futures_client.kline_stream(handle_message,symbol="SOL_USDT",interval="Min5")
    await ws_futures_client.kline_stream(handle_message,symbol="ADA_USDT",interval="Min5")
    await asyncio.sleep(10)
    # Unsubscribe from tickers topic

    await ws_futures_client.unsubscribe(ws_futures_client.kline_stream, param = dict(symbol="XRP_USDT",interval="Min5"))
    await ws_futures_client.unsubscribe(ws_futures_client.kline_stream, param = dict(symbol="BTC_USDT",interval="Min5"))
    await ws_futures_client.unsubscribe(ws_futures_client.kline_stream, param = dict(symbol="SOL_USDT",interval="Min5"))
    await ws_futures_client.unsubscribe(ws_futures_client.kline_stream, param = dict(symbol="ADA_USDT",interval="Min5"))
    # OR
    # await ws_futures_client.unsubscribe("tickers")

import threading
import time


loop.create_task(main())
threading.Thread(target = loop.run_forever,daemon=True).start()

time.sleep(20)

# create new loop


# run main function

