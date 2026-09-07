class MarketData:
    @classmethod
    def create(cls,stock_id,timestamp,
               open,high,low,close,volume,):

        if high < open:
            raise ValueError("High cannot be lower than Open")
        market_data = cls()

        market_data.stock_id = stock_id
        market_data.timestamp = timestamp
        market_data.open = open
        market_data.high = high
        market_data.low = low
        market_data.close = close
        market_data.volume = volume

        return market_data