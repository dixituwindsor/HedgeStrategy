import datetime
import os
import sys
from dotenv import load_dotenv
from smartapi import SmartWebSocket
from database_manager import MongoDB
from utils import Utils


def on_close(ws, close_status_code, close_msg):
    print(datetime.datetime.now(), "close")


class AngelTicker:
    def __init__(self, view):
        try:
            self.view = view
            load_dotenv()
            self.email = os.getenv('TRADE_MANAGER_EMAIL')
            self.ws = None
            self.mongodb = MongoDB.getInstance()
            self.ticker = None
            self.token = None
            self.LTP = None
        except Exception as e:
            print(datetime.datetime.now(), "websocket  Angleticker init error on line {}".format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

    def run(self, symbol):
        try:
            if self.view.isTodayTradingDay() and self.view.isTradingTime():
                admin_data = self.mongodb.findOne(collection_name='api', find_filter={'admin_id': self.email}, value_filter={"_id": 0})
                FEED_TOKEN = admin_data['feedToken']
                CLIENT_CODE = admin_data['userid']
                self.ticker = SmartWebSocket(FEED_TOKEN, CLIENT_CODE)
                self.token = Utils.getSymbolToken(symbol)
                self.ticker._on_open = self.on_open
                self.ticker._on_message = self.on_message
                self.ticker._on_error = self.on_error
                self.ticker._on_close = on_close
                self.ticker.connect()
        except Exception as e:
            self.run(symbol)
            print(datetime.datetime.now(), "websocket  Angleticker run error:", e)

    def on_message(self, ws, message):
        try:
            for msg in message:
                if 'ltp' in msg and msg['tk'] == self.token:
                    self.LTP = msg['ltp']
        except Exception as e:
            print(datetime.datetime.now(), "websocket  Angleticker on_message error on line {}".format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

    def on_open(self, ws):
        try:
            subscribe_token = f"nse_fo|{self.token}"
            self.ticker.subscribe("mw", subscribe_token)
        except Exception as e:
            print(datetime.datetime.now(), "websocket  Angleticker on_open error on line {}".format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

    @staticmethod
    def on_error(ws, error):
        pass
