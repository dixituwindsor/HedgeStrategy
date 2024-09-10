import os, sys
import sqlite3
from threading import Lock


# Singleton Class
class SqliteDB:
    __instance = None
    __lock = Lock()

    # Get Instance of the MongoDb Class
    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        if SqliteDB.__instance is None:
            SqliteDB.__instance = self
            self.db_name = 'DataBase/AlgoSuccess.db'
            self.db_conn = sqlite3.connect(self.db_name, check_same_thread=False)
        else:
            raise Exception('Instance is already created for AngelTicker Class. You can not create another object')

    @staticmethod
    def getDatabaseName():
        db_name = os.getenv('SQL_DB_NAME') + ".db"
        db_path = os.path.join(sys.path[1], 'database_manager', db_name)

        if not os.path.exists(db_path):
            with open(db_path, 'w'):
                print("No DataBase Exist. so new DataBase Created")

        return db_name

    def createTable(self, table_name: str, columns_tuple):
        self.db_conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name}({columns_tuple})")
        self.db_conn.commit()

    def findData(self, columns: str, table_name: str, condition=None):
        if condition is None:
            data = self.db_conn.execute(f'SELECT {columns} FROM {table_name}')
            data = self.getDataDict(data)
            return data
        else:
            data = self.db_conn.execute(f'SELECT {columns} FROM {table_name} WHERE {condition}')
            data = self.getDataDict(data)
            return data

    def getDataList(self, columns: str, table_name: str, condition=None):
        if condition is None:
            data = self.db_conn.execute(f'SELECT {columns} FROM {table_name}')
            return [trade_data for trade_data in data.fetchall()]
        else:
            data = self.db_conn.execute(f'SELECT {columns} FROM {table_name} WHERE {condition}')
            return [list(trade_data) for trade_data in data.fetchall()]

    @staticmethod
    def getDataDict(data):
        columns_tuples = data.description
        columns_list = [column[0] for column in columns_tuples]
        data_dict = [dict(zip(columns_list, trade_data)) for trade_data in data.fetchall()]
        return data_dict

    def insertData(self, table_name: str, data_list: list):
        value_tuple = "("
        for _ in data_list[0].keys():
            value_tuple += '?, '
        value_tuple = value_tuple[:-2] + ')'
        arranged_data = self.arrangeDictInSameOrder(data_list)
        self.db_conn.executemany(f"INSERT INTO {table_name} {arranged_data['columns']} VALUES {value_tuple}", arranged_data['values'])
        self.db_conn.commit()

    @staticmethod
    def arrangeDictInSameOrder(data_list):
        columns = tuple(data_list[0].keys())
        values = []
        for data_dict in data_list:
            data_value_list = []
            for column in columns:
                if not isinstance(data_dict[column], str):
                    data_value_list.append(str(data_dict[column]))
                else:
                    data_value_list.append(data_dict[column])
            values.append(data_value_list)
        return {'columns': columns, 'values': values}

    def updateData(self, table_name: str, value_dict: dict, condition=None):
        update_string = self.getUpdateString(value_dict)
        if condition is None:
            self.db_conn.execute(f"UPDATE {table_name} SET {update_string}")
        else:
            self.db_conn.execute(f"UPDATE {table_name} SET {update_string} WHERE {condition}")
        self.db_conn.commit()

    @staticmethod
    def getUpdateString(value_dict):
        update_string = ""
        for key, value in value_dict.items():
            update_string = update_string + f"{key}='{value}'" + ", "
        return update_string[:-2]

    def deleteData(self, table_name: str, condition=None):
        if condition is not None:
            self.db_conn.execute(f"DELETE FROM {table_name} WHERE {condition}")
        else:
            self.db_conn.execute(f"DELETE FROM {table_name}")
        self.db_conn.commit()

    def isTableExists(self, table_name: str):
        table = self.db_conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'").fetchall()
        if not table:
            return False
        else:
            return True

    def dropTable(self, table_name: str):
        self.db_conn.execute(f"DROP TABLE {table_name}")
        self.db_conn.commit()


if __name__ == '__main__':
    sq = SqliteDB.getInstance()
