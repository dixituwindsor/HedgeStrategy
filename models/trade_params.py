import datetime
from database_manager import SqliteDB
from utils import Utils


class TradeParams:
    def __init__(self):
        self.ACTION = None  # Trade operation type. Possible Actions are available in TradeAction Class. Type String.
        self.TICKET = None  # Unique ID for every trade. It is used for modifying pending orders. Type String.
        self.SYMBOL = None  # Trading symbol is necessary for order modification and position close operations. Type String.
        self.SYMBOL_TOKEN = None  # Instrument Symbol Token provided by broker. Different for every broker. Type String.
        self.ENTRY_TYPE = None  # Order type. Possible Types are available in OrderType Class. Type String.
        self.EXCHANGE = None  # Exchange of Trade or Symbol. Possible Exchanges are available at Exchanges Class. Type String.
        self.STRATEGY_CODE = None  # Strategy code. It will be strategy specific and Unique for every strategy. Type String.
        self.PRODUCT_TYPE = None  # Possible Product types are available in ProductType Class. Type String.
        self.ENTRY_PRICE = None  # Actual entry. This will be different from requestedEntry if the order placed is Market order. Type integer.
        self.QUANTITY = None  # Requested quantity. Type integer.
        self.STOPLOSS = None  # StopLoss level of the order. This is the current stop loss. In case of trailing SL the current stopLoss and initialStopLoss will be different after some time. Type float.
        self.TARGET = None  # Target price if applicable. Type integer.
        self.ORDER_STATE = None  # state of the trade can be found in OrderState Class. Type string.
        self.CREATE_TIME = datetime.datetime.now().replace(microsecond=0)  # Timestamp when the trade is created (Not triggered). Type datetime.
        self.PNL = None  # Profit loss of the trade. If trade is Active this shows the unrealized pnl else realized pnl. Type integer.
        self.EXIT_PRICE = None  # Exit price of the trade. Type integer.
        self.EXIT_REASON = None
        self.DATE = datetime.date.today()

    @staticmethod
    def storeTrade(class_obj):
        try:
            sqlite_db = SqliteDB.getInstance()
            trade_dict = class_obj.__dict__
            columns = list(trade_dict.keys())
            columns[8] = columns[8] + " REAL"
            columns[12] = columns[12] + " REAL"
            columns[13] = columns[13] + " REAL"
            columns = ", ".join(columns)
            sqlite_db.createTable('Trades', columns)
            sqlite_db.insertData('Trades', [trade_dict])
        except Exception as e:
            Utils.printErrorString("trade_params", "storeTrade", e)
