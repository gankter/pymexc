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


async def handle_message(msg: ProtoTyping.PublicAggreDealsV3Api):
    #pass
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


async def main():
    ws_client = spot.WebSocket(api_key=None, api_secret=None, proto=True)
    await ws_client.deals_stream(handle_message, symbol="BTCUSDT", interval="100ms")
    #while True:
    #time.sleep(0.2)
    #pass

if __name__ == "__main__":
    loop = asyncio.new_event_loop()

# run main function
    loop.run_until_complete(main())

    # run forever for keep websocket connection
    loop.run_forever()
    

# loop program forever for save websocket connection

