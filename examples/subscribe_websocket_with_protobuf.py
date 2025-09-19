import logging
import time
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pymexc._async import spot
from pymexc.proto import ProtoTyping


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def handle_message(msg: ProtoTyping.PublicAggreDealsV3Api, wrapper_data):
    #pass
    print(msg)
    for deal in msg.deals:
        match deal.tradeType:
            case 1:
                tradeType = "куплено на"
            case 2:
                tradeType = "продано на"  
        
    
        print(f"{tradeType}: {float(deal.price) * float(deal.quantity)} по цене {deal.price} в момент времени {deal.time}") 
    #print(float(msg.deals[0].price) * float(msg.deals[0].quantity))


# Init futures WebSocket client with your credentials and provide personal callback for capture all account data


# Subscribe for kline topic
import threading

async def dummy():
    while True:
        await asyncio.sleep(1)
        print("sleep 1 second")


def main():
    event_loop = asyncio.new_event_loop()
    threading.Thread(target = event_loop.run_forever, daemon = True).start()

    ws_client = spot.WebSocket(api_key=None, api_secret=None, proto=True, loop = event_loop)

    event_loop.create_task(ws_client.public_aggre_deals_stream(handle_message, symbol='BTCUSDT', interval="100ms"))
    event_loop.create_task(asyncio.sleep(5))
    event_loop.create_task(ws_client.public_aggre_deals_stream(handle_message, symbol="ADAUSDT", interval="100ms"))
    event_loop.create_task(asyncio.sleep(5))
    event_loop.create_task(ws_client.unsubscribe(ws_client.public_aggre_deals_stream, params_list = [dict(symbol="BTCUSDT", interval="100ms") ]))
    event_loop.create_task(asyncio.sleep(5))
    event_loop.create_task(ws_client.unsubscribe(ws_client.public_aggre_deals_stream, params_list = [dict(symbol="ADAUSDT", interval="100ms") ] ))

    asyncio.run_coroutine_threadsafe(coro=dummy(), loop=event_loop).result()

    #while True:
    #time.sleep(0.2)
    #pass

if __name__ == "__main__":
    main()
    

# loop program forever for save websocket connection

