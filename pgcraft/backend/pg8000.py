import pg8000
import json
from ..exception import ConnectionError, QueryError

class Pg8000Backend:
    def __init__(self, host, database, user, password, port=5432, ssl_context=None):
        self.conn_params = {
            "host": host,
            "database": database,
            "user": user,
            "password": password,
            "port": port,
        }
        if ssl_context is not None:
            self.conn_params["ssl_context"] = ssl_context

    def connect(self):
        try:
            return pg8000.connect(**self.conn_params)
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

    def execute(self, query, args=None):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(query, tuple(args or []))
            conn.commit()

            try:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return columns, rows
            except Exception:
                return None, None
        except Exception as e:
            conn.rollback()
            raise QueryError(f"Query failed: {e}\nQuery: {query}\nArgs: {args}")
        finally:
            cursor.close()
            conn.close()

    def serialize_value(self, value):
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    def row_to_dict(self, columns, row):
        result = {}
        for col, val in zip(columns, row):
            # Convert UUID to string
            if hasattr(val, 'hex') and hasattr(val, 'int'):
                result[col] = str(val)
            else:
                result[col] = val
        return result
