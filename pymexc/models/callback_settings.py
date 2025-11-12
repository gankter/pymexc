from pydantic import BaseModel
from typing import Callable, Awaitable, Union

class CallbackSettings(BaseModel):
    
    base_callback: Union[None, Callable, Awaitable]
    use_common_callback: bool
    common_callback: Union[None, Callable, Awaitable] = None
    use_common_callback_for_topic = False
    
    def __post_init__(self):
        if self.use_common_callback and self.common_callback is None:
            raise ValueError("if flag 'use_common_callback' is True common_callback must be initialized")
            

    