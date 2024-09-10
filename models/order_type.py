# class OrderType:
#     LIMIT = "LIMIT"
#     MARKET = "MARKET"
#     SL_MARKET = "SL_MARKET"
#     SL_LIMIT = "SL_LIMIT"


class OrderType:
    BUY = 'BUY'  # market buy order
    SELL = 'SELL'  # market sell order
    BUY_LIMIT = 'BUY_LIMIT'  # buy limit pending order
    SELL_LIMIT = 'SELL_LIMIT'  # sell limit pending order
    BUY_STOP = 'BUY_STOP'  # buy stop pending order
    SELL_STOP = 'SELL_STOP'  # sell stop pending order
    BUY_STOP_LIMIT = 'BUY_STOP_LIMIT'  # Upon reaching the order price, a pending Buy Limit order is placed at the StopLimit price
    SELL_STOP_LIMIT = 'SELL_STOP_LIMIT'  # Upon reaching the order price, a pending Sell Limit order is placed at the StopLimit price
    CLOSE_BY = 'CLOSE_BY'  # order to close a position by an opposite one
