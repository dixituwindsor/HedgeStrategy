# import uuid
from threading import Lock, Thread
from database_manager import SqliteDB


class GenerateSeries:
    __instance = None
    __lock = Lock()
    __Sr = 0

    def __init__(self):
        if GenerateSeries.__instance is None:
            self.__instance = self
            if SqliteDB.getInstance().isTableExists("Trades"):
                trades_data = SqliteDB.getInstance().findData("TICKET", "Trades")
                if trades_data:
                    GenerateSeries.__Sr = int(trades_data[-1]['TICKET'])
        else:
            raise Exception("Can not Generate New Class")

    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = cls()

        # return the singleton instance
        return cls.__instance

    @classmethod
    def getNumber(cls):
        cls.__Sr += 1
        return cls.__Sr

    # @staticmethod
    # def generateTradeID():
    #     """ Generate the Unique ID Based on UUID Library """
    #     print(int(uuid.uuid4()))


if __name__ == '__main__':
    for i in range(10):
        Thread(target=GenerateSeries.getInstance().getNumber).start()
