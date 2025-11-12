#from spot_subscriptions import Topics as SpotTopics

from api_settings import ApiSettings
from callback_settings import CallbackSettings
from proto_settings import ProtoSettings
from pymexc.models.proxy_settings import ProxySettings


# Spot alias
from spot_subscriptions import SubscriptionParams as SpotSubscriptionParams
from spot_subscriptions import MessageShaper as SpotMessageShaper
from spot_subscriptions import Topics as SpotTopics

# Futures alias

from futures_subscriptions import SubscriptionParams as FuturesSubscriptionParams
from futures_subscriptions import MessageShaper as FuturesMessageShaper
from futures_subscriptions import Topics as FuturesTopics

__all__ = [
    'ApiSettings','CallbackSettings','ProtoSettings','ProxySettings',
    'SpotSubscriptionParams', 'SpotMessageShaper', 'SpotTopics',
    'FuturesSubscriptionParams', 'FuturesMessageShaper', 'FuturesTopics',
]
