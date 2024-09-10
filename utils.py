import base64
import calendar
import datetime
import sys
from database_manager import MongoDB


class Utils:
    dateFormat = "%d-%m-%Y"
    timeFormat = "%H:%M:%S"
    dateTimeFormat = "%d-%m-%Y %H:%M:%S"

    @staticmethod
    def roundUserLotSize(user_lot_size, trade_quantity, min_lot_size):
        """ This function returns the quantity for trade according to entered lot size by user and minimum lotsize of
        symbol """

        try:
            final_result = ((trade_quantity * user_lot_size) // min_lot_size) * min_lot_size
            return max(final_result, min_lot_size)
        except Exception as error:
            Utils.printErrorString('utils', 'roundUserLotSize', error)

    @staticmethod
    def isHoliday(datetime_obj):
        """ This function return True if given date is holiday and returns False if it is not a holiday in Indian
        Stock Market """

        try:
            day_of_week = calendar.day_name[datetime_obj.weekday()]
            today = datetime_obj.strftime(Utils.dateFormat)
            holidays = MongoDB.getInstance().findOne(collection_name='holidays', find_filter={'date': today})
            if day_of_week in ["Saturday", "Sunday"] or holidays:
                return True
            else:
                return False
        except Exception as Error:
            Utils.printErrorString('utils', 'isHoliday', Error)

    @staticmethod
    def getTimeOfDay(hours, minutes, seconds, dateTimeObj=None):
        """ This Function Converts the Given Hours, Minutes, Seconds to DateTime Object """
        try:
            if dateTimeObj is None:
                dateTimeObj = datetime.datetime.now()
            dateTimeObj = dateTimeObj.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)
            return dateTimeObj
        except Exception as Error:
            Utils.printErrorString('utils', 'getTimeOfDay', Error)

    @staticmethod
    def getWeeklyExpiryDayDate(dateTimeObj=None):
        """ Return the Weekly Expiry Day Based on Given Datetime Object """
        try:
            if dateTimeObj is None:
                dateTimeObj = datetime.datetime.now()

            if dateTimeObj.weekday() >= 3:
                daysToAdd = -1 * (dateTimeObj.weekday() - 3)
            else:
                daysToAdd = 3 - dateTimeObj.weekday()
            datetimeExpiryDay = dateTimeObj + datetime.timedelta(days=daysToAdd)
            while Utils().isHoliday(datetimeExpiryDay):
                datetimeExpiryDay = datetimeExpiryDay - datetime.timedelta(days=1)

            datetimeExpiryDay = Utils.getTimeOfDay(0, 0, 0, datetimeExpiryDay)
            return datetimeExpiryDay
        except Exception as e:
            Utils.printErrorString('utils', 'getWeeklyExpiryDayDate', e)

    @staticmethod
    def getMarketStartTime(dateTimeObj=None):
        """ This Function Converts the Given DataTime Object to Market Start Time """

        return Utils.getTimeOfDay(9, 15, 0, dateTimeObj)

    @staticmethod
    def getMarketEndTime(dateTimeObj=None):
        """ This Function Converts the Given DataTime Object to Market End Time """

        return Utils.getTimeOfDay(15, 30, 0, dateTimeObj)

    @staticmethod
    def isMarketOpen():
        """ Check if Market is Open or Close """

        if Utils.isTodayHoliday():
            return False
        now = datetime.datetime.now()
        marketStartTime = Utils.getMarketStartTime()
        marketEndTime = Utils.getMarketEndTime()
        return marketStartTime <= now <= marketEndTime

    @staticmethod
    def isTodayHoliday():
        """ Check if Today is Holiday or Not """

        return Utils().isHoliday(datetime.datetime.now())

    @staticmethod
    def getMonthlyExpiryDayDate(datetimeObj=None):
        """ Return the Monthly Expiry Day Date Based on Given Datetime Object """
        try:
            if datetimeObj is None:
                datetimeObj = datetime.datetime.now()
            year = datetimeObj.year
            month = datetimeObj.month
            lastDay = calendar.monthrange(year, month)[1]  # 2nd entry is the last day of the month
            datetimeExpiryDay = datetime.datetime(year, month, lastDay)
            while calendar.day_name[datetimeExpiryDay.weekday()] != 'Thursday':
                datetimeExpiryDay = datetimeExpiryDay - datetime.timedelta(days=1)
            while Utils().isHoliday(datetimeExpiryDay):
                datetimeExpiryDay = datetimeExpiryDay - datetime.timedelta(days=1)

            datetimeExpiryDay = Utils.getTimeOfDay(0, 0, 0, datetimeExpiryDay)
            return datetimeExpiryDay
        except Exception as e:
            Utils.printErrorString('utils', 'getMonthlyExpiryDayDate', e)

    @staticmethod
    def prepareWeeklyOptionsSymbol(inputSymbol, strike, optionType, expiry_format='%d%b%y', numWeeksPlus=0):
        """ Prepare the Given Input Symbol to Broker Based Weekly Option Symbol Format. Default Expiry Format
        %d%b%y Based on Angel One Broker """
        try:
            expiryDate = Utils.getWeeklyExpiryDayDate()
            todayMarketStartTime = Utils.getMarketStartTime()
            expiryDayMarketEndTime = Utils.getMarketEndTime(expiryDate)

            if numWeeksPlus > 0:
                expiryDate = expiryDate + datetime.timedelta(days=numWeeksPlus * 7)
                expiryDate = Utils.getWeeklyExpiryDayDate(expiryDate)

            if todayMarketStartTime > expiryDayMarketEndTime:
                expiryDate = expiryDate + datetime.timedelta(days=6)
                expiryDate = Utils.getWeeklyExpiryDayDate(expiryDate)

            # Check if monthly and weekly expiry same
            expiryDateMonthly = Utils.getMonthlyExpiryDayDate()

            middle = expiryDate.strftime(expiry_format).upper()

            if expiryDate == expiryDateMonthly:
                middle = expiryDate.strftime("%y%b").upper()
            else:
                if expiryDate.month >= 10:
                    y = expiryDate.strftime("%y")
                    mon = expiryDate.strftime("%b").upper()[0]
                    d = expiryDate.strftime("%d")
                    middle = y + mon + d
                else:
                    middle = expiryDate.strftime("%y%#m%d")

            optionSymbol = (inputSymbol + middle + str(strike) + optionType).upper()
            return optionSymbol
        except Exception as e:
            Utils.printErrorString('utils', 'prepareWeeklyOptionsSymbol', e)

    @staticmethod
    def zerodhaToAngelSymbol(base_symbol, expiry_date, strike_price, option_type=None):
        try:
            expiry_date = datetime.datetime.strptime(expiry_date, "%d%b%Y")
            expiry_date_angel = expiry_date.strftime("%d%b%y").upper()
            strike_price = str(int(float(strike_price)))
            return base_symbol + expiry_date_angel + strike_price + option_type
        except Exception as e:
            Utils.printErrorString('utils', 'zerodhaToAngelSymbol', e)

    @staticmethod
    def kotakToAngelSymbol(base_symbol, expiry_date, strike_price, option_type=None):
        return base_symbol + expiry_date + str(strike_price) + option_type

    @staticmethod
    def printErrorString(file_name, function_name, error):
        print(f"{datetime.datetime.now().replace(microsecond=0)}, {file_name} {function_name} error on line {format(sys.exc_info()[-1].tb_lineno)}: {type(error).__name__} {error}")

    @staticmethod
    def getSymbolToken(symbol):
        find_filter = {'symbol': symbol}
        value_filter = {'_id': 0, 'token': 1}
        symbol_data = MongoDB.getInstance().findOne("symbol_token", find_filter, value_filter)
        return symbol_data['token']

    @staticmethod
    def getEpoch(datetimeObj=None):
        """ This Function Converts the Given DataTime Object to EPOCH Time(Seconds) """

        if datetimeObj is None:
            datetimeObj = datetime.datetime.now()
        epochSeconds = datetime.datetime.timestamp(datetimeObj)
        return int(epochSeconds)  # converting double to long

    @staticmethod
    def decodeBase64(data):
        """ This function returns Decoded data of given base64 data. """

        data_bytes = base64.b64decode(data)
        return data_bytes.decode("utf-8")
