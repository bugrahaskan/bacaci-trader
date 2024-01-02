class Database:
    def __init__(self, db_name):
        self._db_name = db_name
        self._conn = None
        self._cur = None
    
    # @db_name.setter
    def _db_name(self, value):
        self._db_name = value
    
    # @db_name.getter
    def _db_name(self):
        return self._db_name
    
    def connect_db(self):
        import sqlite3
        self._conn = sqlite3.connect(self._db_name)
        self._cur = self._conn.cursor()
    
    def create_table(self, table_name, tick=False):
        if tick:
            self.connect_db()

            self._cur.execute(
            '''CREATE TABLE IF NOT EXISTS {} (
            timestamp INTEGER PRIMARY KEY,
            date DATETIME,
            price FLOAT,
            UNIQUE(date),
            UNIQUE(timestamp)
            );
            '''.format(table_name))
        else:
            self.connect_db()

            self._cur.execute(
            '''CREATE TABLE IF NOT EXISTS {} (
            timestamp INTEGER PRIMARY KEY,
            date DATETIME,
            open FLOAT,
            high FLOAT,
            low FLOAT,
            close FLOAT,
            volume FLOAT,
            UNIQUE(date),
            UNIQUE(timestamp)
            );
            '''.format(table_name))
    
    def insert_data(self, df, table_name, tick=False):
        if tick:
            self.create_table(table_name, tick=tick)

            for i in range(df.shape[0]):
                self._cur.execute("INSERT OR REPLACE INTO {} (timestamp, date, price) VALUES (?,?,?)".format(table_name),
                    (
                    df["timestamp"][i],
                    df["date"][i],
                    df["price"][i],
                    )
                )
            self.commit_db() # optional
            self.close_db() # optional
        else:
            self.create_table(table_name, tick=tick)
            for i in range(df.shape[0]):
                self._cur.execute("INSERT OR REPLACE INTO {} (timestamp, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)".format(table_name),
                    (
                    df["timestamp"][i],
                    df["date"][i],
                    df['open'][i],
                    df['high'][i],
                    df['low'][i],
                    df['close'][i],
                    df['volume'][i],
                    )
                )
            self.commit_db() # optional
            self.close_db() # optional
    
    # fetch rows
    # correct if any
    def fetch_rows(self, table_name, start_time: int = None, end_time: int = None, limit: int = None, timestamp: int = None, **kwargs):
        """
        if start_time & end_time & limit : Fetch rows between start_time and end_time. If number of rows greater than limit, return most recent limit number of rows between given dates
        if start_time & end_time         : Fetch rows between start_time and end_time
        if start_time & limit            : Fetch rows from start_time. Max number of rows: limit
        if start_time                    : Fetch rows from start_time
        if end_time & limit              : Fetch maximum limit number of rows with most recent date is end_time
        if end_time                      : Fetch rows with most recent date is end_time
        if limit                         : Fetch last limit number of rows
        if timestamp                     : Fetch a row with given timestamp 
        if None                          : Fetch last row from the table 
        """

        NoneType = type(None)
        if not isinstance(start_time, (int, NoneType)):
            raise TypeError("start_time should be an integer.")
        if not isinstance(end_time, (int, NoneType)):
            raise TypeError("end_time should be an integer.")
        if not isinstance(limit, (int, NoneType)):
            raise TypeError("limit should be an integer.")
        if not isinstance(timestamp, (int, NoneType)):
            raise TypeError("timestamp should be an integer.")

        self.connect_db()

        if 'first' and 'column' in kwargs:
            query = "SELECT {} FROM {} ORDER BY timestamp LIMIT 1".format(
                kwargs.get("column"), table_name)
        elif 'first' in kwargs:
            query = "SELECT * FROM {} ORDER BY timestamp LIMIT 1".format(
                table_name)

        else:
            if start_time is not None:
                if end_time is not None:
                    if limit is not None:
                        query = "SELECT * FROM {} WHERE timestamp >= {} and timestamp <= {} ORDER BY timestamp DESC LIMIT {}".format(
                            table_name, start_time, end_time, limit)
                    elif limit is None:
                        query = "SELECT * FROM {} WHERE timestamp >= {} and timestamp <= {} ORDER BY timestamp".format(
                            table_name, start_time, end_time)
                elif end_time is None:
                    if limit is not None:
                        query = "SELECT * FROM {} WHERE timestamp >= {} ORDER BY timestamp LIMIT {}".format(
                            table_name, start_time, limit)
                    elif limit is None:
                        query = "SELECT * FROM {} WHERE timestamp >= {}".format(
                            table_name, start_time)
            elif start_time is None:
                if end_time is not None:
                    if limit is not None:
                        query = "SELECT * FROM (SELECT * FROM {} WHERE timestamp <= {} ORDER BY timestamp DESC LIMIT {}) ORDER BY timestamp".format(
                            table_name, end_time, limit)
                    if limit is None:
                        query = "SELECT * FROM {} WHERE timestamp <= {}".format(
                            table_name, end_time)
                elif end_time is None:
                    if limit is not None:
                        query = "SELECT * FROM (SELECT * FROM {} ORDER BY timestamp DESC LIMIT {}) ORDER BY timestamp".format(
                            table_name, limit)
                    elif limit is None:
                        if timestamp is not None:
                            query = "SELECT * FROM {} WHERE timestamp = {}".format(
                                table_name, timestamp)
                        elif timestamp is None:
                            query = "SELECT * FROM {} ORDER BY timestamp DESC LIMIT 1".format(
                                table_name)

        self._cur.execute(query)
        rows = self._cur.fetchall()
        self._conn.close()
        return [list(row) for row in rows]

    def commit_db(self):
        self._conn.commit()

    def close_db(self):
        self._conn.close()
    
