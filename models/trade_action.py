class TradeAction:
    MARKET = 'MARKET'  # market order for an immediate execution
    LIMIT = 'LIMIT'  # limit trade
    PENDING = 'PENDING'  # order for the execution under specified conditions
    SLTP = 'SLTP'  # Modify Stop Loss and Take Profit values of an opened position
    MODIFY = 'MODIFY'  # modify the parameters of the order placed previously
    REMOVE = 'REMOVE'  # delete the pending order placed previously
    CLOSE_BY = 'CLOSE_BY'  # close a position by and opposite one
