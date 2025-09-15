
def _create_subscription_message(topic: str, params: dict, interval: str = None):
        proto = True
        return "@".join(
                    [f"spot@{topic}.v3.api" + (".pb" if proto else "")] 
                    + ([str(interval)] if interval else [])
                    + list(map(str, params.values()))
                )

if __name__ == "__main__":
    x = _create_subscription_message(topic="public.kline",params={"symbol":"BTCUSDT","interval":"Min15"})
    print(x)