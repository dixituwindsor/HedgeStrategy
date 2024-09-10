import datetime
import os
import socket
import threading
import time
from dotenv import load_dotenv
from angel_ticker import AngelTicker
from database_manager import MongoDB, SqliteDB
from models import Exchanges, OrderState, OrderType, ProductType, TradeAction, TradeParams
from serials import GenerateSeries
from utils import Utils
from getltp import getLtp


class HedgeStrategy:
    def __init__(self):
        self.mongodb = MongoDB.getInstance()
        self.sql_db = SqliteDB.getInstance()
        self.deleteOldTradesInSqlite()
        load_dotenv()
        self.websocket_ip = os.getenv('WEBSOCKET_IP')
        self.websocket_port = os.getenv('WEBSOCKET_PORT')
        self.is_strategy_started = False
        self.buy_trade = None
        self.sell_trade = None
        self.magic_number = 2312
        self.buy_strategy_code = 'HSB001'
        self.sell_strategy_code = 'HSS001'
        self.symbol = 'BANKNIFTY06OCT2239400CE'
        self.exchange = 'NFO'
        self.min_quantity = 25
        self.input_quantity = 50
        self.stop_loss = 30
        self.target = 20
        self.price_change = 10
        self.start_time = "09:20:00"
        self.end_time = "15:05:00"
        self.trading_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        self.new_trade_data = None
        self.premium_levels = None
        self.current_level = None
        self.angel_ticker = AngelTicker(self)
        threading.Thread(target=self.angel_ticker.run, args=(self.symbol,), daemon=True).start()
        self.PREV_LTP = None
        self.LTP = None

    def deleteOldTradesInSqlite(self):
        self.sql_db.deleteData('Trades')

    def getPremiumLevels(self, LTP):
        try:
            upper_levels = []
            lower_levels = []
            for a in range(1, 3):
                upper_level = LTP + (a * self.price_change)
                if upper_level > 0:
                    upper_levels.append(round(upper_level, 2))

                lower_level = LTP - (a * self.price_change)
                if lower_level > 0:
                    lower_levels.append(round(lower_level, 2))
            print("Start Price: ", LTP)
            lower_levels.reverse()
            return lower_levels + [LTP] + upper_levels
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "getPremiumLevels", e)

    def checkPositionIsOpen(self, price):
        try:
            if self.sql_db.isTableExists("Trades"):
                buy_trade = self.sql_db.findData(columns="*", table_name="Trades", condition=f"ENTRY_PRICE='{price}' AND ORDER_STATE='{OrderState.OPEN}' AND ENTRY_TYPE='BUY' AND DATE='{str(datetime.date.today())}'")
                sell_trade = self.sql_db.findData(columns="*", table_name="Trades", condition=f"ENTRY_PRICE='{price}' AND ORDER_STATE='{OrderState.OPEN}' AND ENTRY_TYPE='SELL' AND DATE='{str(datetime.date.today())}'")
                return {'BUY': buy_trade != [], 'SELL': sell_trade != []}
            else:
                return {'BUY': False, 'SELL': False}
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "checkPositionIsOpen", e)

    def placeTrades(self, price):
        """ This function will Place one Call Trade and one Put Trade. """

        try:
            price = float(price)
            position_exists = self.checkPositionIsOpen(price)
            print("position_exists: ", position_exists)
            if not position_exists['BUY']:
                self.buy_trade = self.placeNewOrder(self.symbol, Exchanges.NFO, OrderType.BUY, self.min_quantity, price, self.stop_loss, self.target, TradeAction.LIMIT,
                                                    self.buy_strategy_code, OrderState.OPEN, ProductType.CARRYFORWARD, ticket=str(GenerateSeries.getInstance().getNumber()))
            else:
                self.buy_trade = self.placeNewOrder(self.symbol, Exchanges.NFO, OrderType.BUY, self.min_quantity, price, self.stop_loss, self.target, TradeAction.LIMIT,
                                                    self.buy_strategy_code, OrderState.OPEN, ProductType.CARRYFORWARD, ticket=str(GenerateSeries.getInstance().getNumber()),
                                                    store_trade=False)
            if not position_exists['SELL']:
                self.sell_trade = self.placeNewOrder(self.symbol, Exchanges.NFO, OrderType.SELL, self.min_quantity, price, self.stop_loss, self.target, TradeAction.LIMIT,
                                                     self.sell_strategy_code, OrderState.OPEN, ProductType.CARRYFORWARD, ticket=str(GenerateSeries.getInstance().getNumber()))
            else:
                self.sell_trade = self.placeNewOrder(self.symbol, Exchanges.NFO, OrderType.SELL, self.min_quantity, price, self.stop_loss, self.target, TradeAction.LIMIT,
                                                     self.sell_strategy_code, OrderState.OPEN, ProductType.CARRYFORWARD, ticket=str(GenerateSeries.getInstance().getNumber()),
                                                     store_trade=False)
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "placeTrades", e)

    def OnTick(self):
        """ This function will run on every websocket Tick and will check The conditions of Strategy according to LTP of Placed Trades. """
        try:
            while True:
                if self.isTodayTradingDay() and self.isTradingTime():
                    self.LTP = self.angel_ticker.LTP
                    if self.LTP is not None and self.PREV_LTP != self.LTP:
                        print(self.LTP)
                        self.PREV_LTP = self.LTP
                        self.LTP = float(self.LTP)
                        if not self.is_strategy_started:
                            self.LTP = getLtp("NFO", self.symbol)
                            print("starting LTP: ", self.LTP)
                            self.premium_levels = self.getPremiumLevels(self.LTP)
                            print("premium_levels: ", self.premium_levels)
                            self.current_level = self.premium_levels.index(self.LTP)
                            print("current_level: ", self.current_level)
                            self.placeTrades(self.LTP)
                            self.is_strategy_started = True

                        market_direction = self.monitorTrades()
                        self.targetHit(self.checkTargetHit(), market_direction)
                        self.stopLossHit(self.checkStopLossHit())

                if self.buy_trade is not None and self.sell_trade is not None and not self.isTradingTime():
                    self.closeAllPositions("STRATEGY TIME COMPLETED")
                    self.buy_trade = None
                    self.sell_trade = None
                    self.is_strategy_started = False
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "OnTick", e)

    def monitorTrades(self):
        try:
            if self.buy_trade is not None and self.sell_trade is not None:
                price_change = self.isPriceChanged()
                print("price_change: ", price_change)
                if price_change == "INCREASED":
                    price = self.premium_levels[self.current_level + 1]
                    self.placeTrades(price)
                    self.current_level = self.premium_levels.index(price)
                    if self.current_level == (len(self.premium_levels) - 1):
                        self.premium_levels.append(round((price + self.price_change), 2))

                if price_change == "DECREASED":
                    if self.current_level == 0:
                        self.placeTrades(self.premium_levels[0])
                    else:
                        self.placeTrades(self.premium_levels[self.current_level - 1])

                    if self.current_level != 0:
                        self.current_level = self.premium_levels.index(self.premium_levels[self.current_level - 1])

                    if self.current_level == 0:
                        self.premium_levels.insert(0, round((self.premium_levels[0] - self.price_change), 2))

                print("current_level: ", self.current_level)
                print("premium_levels: ", self.premium_levels)
                return price_change
            else:
                if not self.isTradingTime():
                    self.is_strategy_started = False

        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'monitorTrades', e)

    def targetHit(self, trades, market_direction):
        try:
            if trades and market_direction is not None:
                print("Target Hit Trades: ", trades)
                for trade in trades:
                    if market_direction == "INCREASED":
                        entry_price = self.premium_levels[self.premium_levels.index(trade['ENTRY_PRICE']) + 1]
                    else:
                        entry_price = self.premium_levels[self.premium_levels.index(trade['ENTRY_PRICE']) - 1]

                    self.positionClose(entry_price=trade['ENTRY_PRICE'], entry_type=trade['ENTRY_TYPE'], exit_reason="TARGET HIT")
                    if trade['ENTRY_TYPE'] == "BUY":
                        self.positionClose(entry_price=entry_price, entry_type="SELL", exit_reason="TARGET HIT OPPOSITE")
                    else:
                        self.positionClose(entry_price=entry_price, entry_type="BUY", exit_reason="TARGET HIT OPPOSITE")
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "targetHit", e)

    def stopLossHit(self, trades):
        try:
            if trades:
                print("StopLoss Hit Trades: ", trades)
                for trade in trades:
                    self.positionClose(entry_price=trade['ENTRY_PRICE'], entry_type=trade['ENTRY_TYPE'], exit_reason="STOPLOSS HIT")
                    if trade['ENTRY_TYPE'] == "BUY":
                        self.sell_trade.QUANTITY = int(self.sell_trade.QUANTITY) + int(self.input_quantity) + int(trade['QUANTITY'])
                        print("Qunatity Increase: ", self.sell_trade.__dict__)

                        if self.current_level == 0:
                            self.generateTradeString(self.sell_trade, 'ENTRY', is_stop_loss_hit=True, quantity=int(self.input_quantity) + int(trade['QUANTITY']),
                                                     price=self.premium_levels[self.current_level + 1])
                        else:
                            self.generateTradeString(self.sell_trade, 'ENTRY', is_stop_loss_hit=True, quantity=int(self.input_quantity) + int(trade['QUANTITY']),
                                                     price=self.premium_levels[self.current_level])

                        self.sql_db.updateData(table_name="Trades", value_dict=self.sell_trade.__dict__,
                                               condition=f"ENTRY_PRICE='{self.sell_trade.ENTRY_PRICE}' AND ENTRY_TYPE='{self.sell_trade.ENTRY_TYPE}' AND ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'")
                    else:
                        self.buy_trade.QUANTITY = int(self.buy_trade.QUANTITY) + int(self.input_quantity) + int(trade['QUANTITY'])
                        print("Qunatity Increase: ", self.buy_trade.__dict__)

                        if self.current_level == 0:
                            self.generateTradeString(self.buy_trade, 'ENTRY', is_stop_loss_hit=True, quantity=int(self.input_quantity) + int(trade['QUANTITY']),
                                                     price=self.premium_levels[self.current_level + 1])
                        else:
                            self.generateTradeString(self.buy_trade, 'ENTRY', is_stop_loss_hit=True, quantity=int(self.input_quantity) + int(trade['QUANTITY']),
                                                     price=self.premium_levels[self.current_level])

                        self.sql_db.updateData(table_name="Trades", value_dict=self.buy_trade.__dict__,
                                               condition=f"ENTRY_PRICE='{self.buy_trade.ENTRY_PRICE}' AND ENTRY_TYPE='{self.buy_trade.ENTRY_TYPE}' AND ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'")
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "stopLossHit", e)

    def checkStopLossHit(self):
        try:
            if self.buy_trade is not None and self.sell_trade is not None:
                buy_sl_hit = f"ENTRY_TYPE='BUY' AND ORDER_STATE='{OrderState.OPEN}' AND STOPLOSS>='{self.LTP}' AND DATE='{str(datetime.date.today())}'"
                sell_sl_hit = f"ENTRY_TYPE='SELL' AND ORDER_STATE='{OrderState.OPEN}' AND STOPLOSS<='{self.LTP}' AND DATE='{str(datetime.date.today())}'"
                buy_sl_hit_trades = self.sql_db.findData(columns='TICKET,ENTRY_TYPE,ENTRY_PRICE,QUANTITY', table_name='Trades', condition=buy_sl_hit)
                sell_sl_hit_trades = self.sql_db.findData(columns='TICKET,ENTRY_TYPE,ENTRY_PRICE,QUANTITY', table_name='Trades', condition=sell_sl_hit)
                return buy_sl_hit_trades + sell_sl_hit_trades
            else:
                return []
        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'checkStopLossHit', e)

    def checkTargetHit(self):
        try:
            if self.buy_trade is not None and self.sell_trade is not None:
                buy_target_hit = f"ENTRY_TYPE='BUY' AND ORDER_STATE='{OrderState.OPEN}' AND TARGET<='{self.LTP}' AND DATE='{str(datetime.date.today())}'"
                sell_target_hit = f"ENTRY_TYPE='SELL' AND ORDER_STATE='{OrderState.OPEN}' AND TARGET>='{self.LTP}' AND DATE='{str(datetime.date.today())}'"
                buy_target_hit_trades = self.sql_db.findData(columns='TICKET,ENTRY_TYPE,ENTRY_PRICE', table_name='Trades', condition=buy_target_hit)
                sell_target_hit_trades = self.sql_db.findData(columns='TICKET,ENTRY_TYPE,ENTRY_PRICE', table_name='Trades', condition=sell_target_hit)
                return buy_target_hit_trades + sell_target_hit_trades
            else:
                return []
        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'checkTargetHit', e)

    def isPriceChanged(self):
        try:
            if self.LTP >= float(self.buy_trade.ENTRY_PRICE) + self.price_change:
                return 'INCREASED'

            if self.LTP <= float(self.buy_trade.ENTRY_PRICE) - self.price_change:
                return 'DECREASED'
        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'isPriceChanged', e)

    def placeNewOrder(self, symbol, exchange, order_type, order_volume, order_price, order_sl, order_target, trade_action, strategy_code,
                      order_state, product_type, ticket=None, store_trade=True):
        """ This function places new order. """

        try:
            trade = TradeParams()
            trade.STRATEGY_CODE = strategy_code
            trade.TICKET = ticket
            trade.SYMBOL = symbol
            trade.SYMBOL_TOKEN = Utils.getSymbolToken(symbol)
            trade.PRODUCT_TYPE = product_type
            trade.EXCHANGE = exchange
            trade.ENTRY_TYPE = order_type
            trade.ENTRY_PRICE = order_price
            trade.QUANTITY = order_volume

            if order_type == "BUY":
                trade.STOPLOSS = round((order_price - order_sl), 2)
                trade.TARGET = round((order_price + order_target), 2)
            else:
                trade.STOPLOSS = round((order_price + order_sl), 2)
                trade.TARGET = round((order_price - order_target), 2)

            trade.ACTION = trade_action
            trade.ORDER_STATE = order_state

            if store_trade:
                trade.storeTrade(trade)
                self.generateTradeString(trade, "ENTRY", order_price)

            return trade
        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'placeNewOrder', e)

    def closeAllPositions(self, exit_reason, symbol=None):
        """ This function closes ALL the open positions. """

        try:
            condition = f"ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'"

            if symbol:
                condition = f"SYMBOL='{symbol}' AND ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'"

            open_position = self.sql_db.findData(columns="*", table_name="Trades", condition=condition)
            if open_position:
                for position in open_position:
                    self.positionClose(position['ENTRY_PRICE'], position['ENTRY_TYPE'], exit_reason)
        except Exception as e:
            Utils.printErrorString('Base_Strategy', 'closeAllPositions', e)

    def positionClose(self, entry_price, entry_type, exit_reason):
        """ This function closes the order with specific ticket. """

        try:
            order_params = self.sql_db.findData(columns="*", table_name="Trades",
                                                condition=f"ENTRY_PRICE='{entry_price}' AND ENTRY_TYPE='{entry_type}' AND ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'")
            if order_params:
                order_params = order_params[0]
                if self.current_level == 0:
                    self.generateTradeString(order_params, "EXIT", self.premium_levels[self.current_level + 1])
                else:
                    self.generateTradeString(order_params, "EXIT", self.premium_levels[self.current_level])
                order_params['EXIT_PRICE'] = self.LTP
                pnl = self.getTradePNL(order_params)
                order_params['PNL'] = "{0:.2f}".format(pnl)
                order_params['ORDER_STATE'] = OrderState.CLOSE
                order_params['EXIT_REASON'] = exit_reason
                self.sql_db.updateData(table_name='Trades', value_dict=order_params, condition=f"ENTRY_PRICE='{entry_price}' AND ENTRY_TYPE='{entry_type}' AND ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'")
                print("Close Trade Ticket: ", order_params['TICKET'])
        except Exception as e:
            print("Not Closed Trade Ticket: ", entry_price)
            Utils.printErrorString('hedgestrategy', 'positionClose', e)

    def isTodayTradingDay(self):
        """ This function will check whether today is trading day or strategy or not according to trading_days list. """

        try:
            return datetime.datetime.today().strftime("%a") in self.trading_days
        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'isTodayTradingDay', e)

    def isTradingTime(self):
        """ This function will check whether current time is trading time of the strategy according to start_time and end_time of the strategy. """

        try:
            start_time = datetime.time(*map(int, self.start_time.split(':')))
            end_time = datetime.time(*map(int, self.end_time.split(':')))
            if start_time <= datetime.datetime.now().time().replace(microsecond=0) <= end_time:
                return True
            else:
                if start_time > datetime.datetime.now().time().replace(microsecond=0):
                    return self.waitForMarketStart(start_time)
        except Exception as e:
            Utils.printErrorString('hedgestrategy', 'isTradingTime', e)

    @staticmethod
    def waitForMarketStart(start_time):
        """ This function will return True when market will start, if market is not started yet. """

        try:
            start_date_time = datetime.datetime.now()
            start_date_time = start_date_time.replace(hour=start_time.hour, minute=start_time.minute,
                                                      second=start_time.second, microsecond=0)
            while True:
                time.sleep(1)
                if start_date_time.timestamp() == datetime.datetime.now().replace(microsecond=0).timestamp():
                    return True
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "waitForMarketStart", e)

    @staticmethod
    def getTradePNL(trade):
        """ This function calculates profit loss of the given trade dictionary. """

        try:
            if trade['ENTRY_TYPE'] == "BUY":
                pnl = (float(trade['EXIT_PRICE']) - float(trade['ENTRY_PRICE'])) * int(trade['QUANTITY'])
            else:
                pnl = (float(trade['ENTRY_PRICE']) - float(trade['EXIT_PRICE'])) * int(trade['QUANTITY'])
            return pnl
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "getTradePNL", e)

    @staticmethod
    def getStopLossAmount(price, percentage, order_type):
        """ This function will return StopLoss Amount (price +/- percentage amount) according to given order type, percentage, and price. """

        try:
            if order_type == OrderType.BUY:
                per = (percentage * price) / 100
                return price - per
            else:
                per = (percentage * price) / 100
                return price + per
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "getStopLossAmount", e)

    @staticmethod
    def getTakeProfitAmount(price, percentage, order_type):
        """ This function will return Target Amount (price +/- percentage amount) according to given order type, percentage, and price. """

        try:
            if order_type == OrderType.BUY:
                per = (percentage * price) / 100
                return price + per
            else:
                per = (percentage * price) / 100
                return price - per
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "getTakeProfitAmount", e)

    def generateTradeString(self, trade, trade_type, price, is_stop_loss_hit=False, quantity=None):
        try:
            if isinstance(trade, dict):
                if not is_stop_loss_hit:
                    trade_string = f"NORMAL,{trade['SYMBOL']},{trade['ENTRY_TYPE']},{trade['EXCHANGE']},{trade['ACTION']},{trade['PRODUCT_TYPE']},DAY,{price},0.0,0.0,{trade['QUANTITY']},{trade['STRATEGY_CODE']},{trade_type}"
                else:
                    trade_string = f"NORMAL,{trade['SYMBOL']},{trade['ENTRY_TYPE']},{trade['EXCHANGE']},{trade['ACTION']},{trade['PRODUCT_TYPE']},DAY,{price},0.0,0.0,{quantity},{trade['STRATEGY_CODE']},{trade_type}"
            else:
                if not is_stop_loss_hit:
                    trade_string = f"NORMAL,{trade.SYMBOL},{trade.ENTRY_TYPE},{trade.EXCHANGE},{trade.ACTION},{trade.PRODUCT_TYPE},DAY,{price},0.0,0.0,{trade.QUANTITY},{trade.STRATEGY_CODE},{trade_type}"
                else:
                    trade_string = f"NORMAL,{trade.SYMBOL},{trade.ENTRY_TYPE},{trade.EXCHANGE},{trade.ACTION},{trade.PRODUCT_TYPE},DAY,{price},0.0,0.0,{quantity},{trade.STRATEGY_CODE},{trade_type}"

            if trade_type == 'EXIT':
                if "BUY" in trade_string:
                    trade_string = trade_string.replace("BUY", "SELL")
                else:
                    trade_string = trade_string.replace("SELL", "BUY")

            print("trade_string: ", trade_string)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.connect((self.websocket_ip, int(self.websocket_port)))
                server.send(trade_string.encode())
                server.close()
        except Exception as e:
            Utils.printErrorString("hedgestrategy", "generateTradeString", e)

    # def placeRemainingTrades(self, price):
    #     try:
    #         buy_quantity = 0
    #         sell_quantity = 0
    #         open_trades = self.sql_db.findData(columns="*", table_name="Trades", condition=f"ORDER_STATE='{OrderState.OPEN}' AND DATE='{str(datetime.date.today())}'")
    #         for trade in open_trades:
    #             if trade['ENTRY_TYPE'] == "BUY":
    #                 buy_quantity += int(trade['QUANTITY'])
    #             else:
    #                 sell_quantity += int(trade['QUANTITY'])
    #
    #         if buy_quantity > sell_quantity:
    #             self.placeNewOrder(self.symbol, Exchanges.NFO, OrderType.SELL, buy_quantity - sell_quantity, price, self.stop_loss, self.target, TradeAction.MARKET,
    #                                self.sell_strategy_code, OrderState.OPEN, ProductType.CARRYFORWARD, ticket=str(GenerateSeries.getInstance().getNumber()))
    #         elif sell_quantity > buy_quantity:
    #             self.placeNewOrder(self.symbol, Exchanges.NFO, OrderType.BUY, sell_quantity - buy_quantity, price, self.stop_loss, self.target, TradeAction.MARKET,
    #                                self.buy_strategy_code, OrderState.OPEN, ProductType.CARRYFORWARD, ticket=str(GenerateSeries.getInstance().getNumber()))
    #
    #         self.buy_trade = None
    #         self.sell_trade = None
    #         self.is_strategy_started = False
    #     except Exception as e:
    #         Utils.printErrorString("hedgestrategy", "placeRemainingTrades", e)
