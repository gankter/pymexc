from typing import Union, Callable, Awaitable
from pydantic import BaseModel

class HandlerMessage(BaseModel):
    base_callback = None
    commn_callback = None
    use_common_callback: bool = True
    use_topic_callback:bool = True
    use_symbol_callback:bool = True
    callback_by_topic: Union[Callable,Awaitable] = None
    callback_by_symbol: Union[Callable,Awaitable] = None

#spot_subscripton_shaper = {
#
#}