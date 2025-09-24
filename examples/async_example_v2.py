
import asyncio
import threading
import time
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pymexc._async.spot_v2 import WebSocket
from pymexc.proto import ProtoTyping

async def handle_message(msg,x):
    print(msg)



async def main():
    event_loop = asyncio.get_event_loop()
    #threading.Thread(target = event_loop.run_forever, daemon = True).start()

    ws_client = WebSocket(api_key=None, api_secret=None, proto=True, loop = event_loop, use_common_callback = True, commn_callback = handle_message)
    #await ws_client.connect()
    await asyncio.gather(ws_client.connect(), ws_client.public_aggre_deals_stream(symbol="MLCUSDT",interval="100ms"))
    while True:
        try:
            await asyncio.sleep(0.1)
        except KeyboardInterrupt as e:
            print(e)
            break

if __name__ == "__main__":
    asyncio.run(main())

