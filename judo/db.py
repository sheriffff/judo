import pandas as pd
import sqlite3

from pathlib import Path


class SQLiteConnection:
    def __init__(self, path, logger=None):
        """
        Args:
            path: (Path) Path to the database file
        """
        if not isinstance(path, Path):
            path = Path(path)

        try:
            self.connection = sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True)
        except sqlite3.OperationalError:
            raise sqlite3.OperationalError(f'Unable to open {str(path.absolute())}')
        self.path = path
        self.logger = logger

    def query(self, query_string, values=None, empty_response=False, lastrowid=False):
        cursor = self.connection.cursor()
        if values is None:
            cursor.execute(query_string)
            self.connection.commit()
        else:
            cursor.execute(query_string, values)
            self.connection.commit()
        if empty_response and lastrowid:
            return cursor.lastrowid
        elif empty_response and not lastrowid:
            return
        elif lastrowid and not empty_response:
            return cursor.fetchall(), cursor.lastrowid
        else:
            return cursor.fetchall()

    def as_pandas(self, query_string, index_col=None, parse_dates=None, columns=None, params=None):
        """
        Return query as pandas data frame

        Args:
            query_string: SQL valid query
            index_col: Column to be used as index
            parse_dates: See pandas.read_sql parse_dates
            columns: See pandas.read_sql columns
            params: See pandas.read_sql params

        Returns:
            A pandas.DataFrame
        """
        return pd.read_sql(query_string, self.connection, index_col=index_col,
                           parse_dates=parse_dates, columns=columns, params=params)


    def commit(self):
        self.connection.commit()


    def add_table(self, name, df: pd.DataFrame, if_exists='replace', index=False):
        """
        Add a dataframe to the table

        Args:
            name: Name of the table
            df: Dataframe to be written to
            if_exists(str): {‘fail’, ‘replace’, ‘append’}, default ‘fail’.

        """
        try:
            assert isinstance(df, pd.DataFrame)
        except AssertionError as e:
            if self.logger is not None:
                self.logger.exception(e)
            raise TypeError('df, Expected type pandas.DataFrame or geopandas.GeoDataFrame')

        df.to_sql(name=name, con=self.connection, if_exists=if_exists, index=index)


    def append_table(self, name, df: pd.DataFrame):
        """
        Append a dataframe to the table

        Args:
            name: Name of the table
            df: Dataframe to be written to

        Returns:
        """
        try:
            assert isinstance(df, pd.DataFrame)
        except AssertionError as e:
            if self.logger is not None:
                self.logger.exception(e)
            raise TypeError('df, Expected type pandas.DataFrame or geopandas.GeoDataFrame')

        df.to_sql(name=name, con=self.connection, if_exists='append')

    def drop_table(self, table_name):
        try:
            self.query("drop table {}".format(table_name))

        except sqlite3.OperationalError:
            if self.logger is not None:
                self.logger.warning(f"Trying to drop a table that does not exist: {table_name}")


    def query_all(self, table_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM {}".format(table_name))
        return cursor.fetchall()


    def query_all_as_pandas(self, table_name, index_col=None, parse_dates=None, columns=None, params=None):
        """
        Return query as pandas data frame

        :param table_name: Name of table to extract
        :param index_col: Column to be used as index
        :param parse_dates: See pandas.read_sql parse_dates
        :param columns: See pandas.read_sql columns
        :param params: See pandas.read_sql params
        :return: A pandas.DataFrame
        """
        return pd.read_sql('SELECT * FROM {}'.format(table_name), self.connection, index_col=index_col,
                           parse_dates=parse_dates, columns=columns, params=params)

    def count_rows(self, table_name):
        count = self.query(f'SELECT COUNT(*) FROM {table_name}')
        return count[0][0]

    def check_table_empty(self, table_name):
        if self.count_rows(table_name) == 0:
            return True
        else:
            return False


    def close(self):
        self.connection.close()


conn = SQLiteConnection('../judo_big.sql')
