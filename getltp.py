import os
from dotenv import load_dotenv
from smartapi import SmartConnect
from utils import Utils
from database_manager import MongoDB


def getLtp(exchange, symbol):
    load_dotenv()
    email = os.getenv('TRADE_MANAGER_EMAIL')
    mongodb = MongoDB.getInstance()
    api_data = mongodb.findOne(collection_name='api', find_filter={'admin_id': email}, value_filter={"_id": 0})
    angel = SmartConnect(api_key=api_data['apikey'], access_token=api_data['jwtToken'])
    token = Utils.getSymbolToken(symbol)
    ltp_data = angel.ltpData(exchange, symbol, token)
    return ltp_data['data']['ltp']
