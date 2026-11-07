from .result import Result
from .exception import NotFoundError, MultipleRowsError, QueryError


class QueryBuilder:
    def __init__(self, backend, table_name):
        self._backend = backend
        self._table = table_name
        self._action = "SELECT"
        self._select_clause = "*"
        self._count_mode = None
        self._filters = []
        self._order_by = None
        self._limit_val = None
        self._offset_val = None
        self._single_mode = False
        self._update_data = {}
        self._insert_data = None
        self._cache_ttl = None
        self._cache_backend = None

    # --- Action methods ---

    def select(self, columns="*", count=None):
        self._action = "SELECT"
        self._select_clause = columns
        self._count_mode = count
        return self

    def insert(self, data):
        self._action = "INSERT"
        self._insert_data = data
        return self

    def update(self, data):
        self._action = "UPDATE"
        self._update_data = data
        return self

    def delete(self):
        self._action = "DELETE"
        return self

    # --- Filter methods ---

    def eq(self, column, value):
        self._filters.append((f"{column} = %s", value))
        return self

    def neq(self, column, value):
        self._filters.append((f"{column} != %s", value))
        return self

    def gt(self, column, value):
        self._filters.append((f"{column} > %s", value))
        return self

    def gte(self, column, value):
        self._filters.append((f"{column} >= %s", value))
        return self

    def lt(self, column, value):
        self._filters.append((f"{column} < %s", value))
        return self

    def lte(self, column, value):
        self._filters.append((f"{column} <= %s", value))
        return self

    def like(self, column, pattern):
        self._filters.append((f"{column} LIKE %s", pattern))
        return self

    def ilike(self, column, pattern):
        self._filters.append((f"{column} ILIKE %s", pattern))
        return self

    def is_(self, column, value):
        if value is None:
            self._filters.append((f"{column} IS NULL", None))
        else:
            self._filters.append((f"{column} IS %s", value))
        return self

    def in_(self, column, values):
        self._filters.append((f"{column} = ANY(%s)", list(values)))
        return self

    def contains(self, column, value):
        import json
        if isinstance(value, (dict, list)):
            self._filters.append((f"{column} @> %s::jsonb", json.dumps(value)))
        else:
            self._filters.append((f"{column} @> %s", value))
        return self

    # --- Modifiers ---

    def order(self, column, desc=False, nullsfirst=False):
        direction = "DESC" if desc else "ASC"
        nulls = "NULLS FIRST" if nullsfirst else "NULLS LAST"
        self._order_by = f"ORDER BY {column} {direction} {nulls}"
        return self

    def limit(self, count):
        self._limit_val = count
        return self

    def offset(self, count):
        self._offset_val = count
        return self

    def range(self, from_idx, to_idx):
        self._limit_val = to_idx - from_idx + 1
        self._offset_val = from_idx
        return self

    def single(self):
        self._single_mode = True
        return self

    def maybe_single(self):
        self._single_mode = True
        return self

    def cache(self, ttl: int = 60):
        self._cache_ttl = ttl
        return self
    # --- Build WHERE clause ---
    def _build_where(self, args):
        if not self._filters:
            return "", args
        clauses = [f[0] for f in self._filters]
        where = " WHERE " + " AND ".join(clauses)
        for f in self._filters:
            if f[1] is not None:
                args.append(
                    self._backend.serialize_value(f[1])
                )
        return where, args

    # --- Execute ---

    def execute(self):
        args = []

        # COUNT query
        if self._count_mode == "exact":
            query = f"SELECT COUNT(*) FROM {self._table}"
            where, args = self._build_where(args)
            query += where
            _, rows = self._backend.execute(query, args)
            count = rows[0][0] if rows else 0
            return Result(data=[], count=count)

        # SELECT
        # Check cache first
        if self._cache_ttl and self._cache_backend:
            cache_key = self._build_cache_key()
            cached = self._cache_backend.get(cache_key)
            if cached is not None:
                return Result(data=cached)

        # SELECT
        if self._action == "SELECT":
            # Check cache first
            cache_key = None
            if self._cache_ttl and self._cache_backend:
                cache_key = self._build_cache_key()
                cached = self._cache_backend.get(cache_key)
                if cached is not None:
                    return Result(data=cached)

            query = f"SELECT {self._select_clause} FROM {self._table}"
            where, args = self._build_where(args)
            query += where
            if self._order_by:
                query += f" {self._order_by}"
            if self._limit_val is not None:
                query += f" LIMIT {self._limit_val}"
            if self._offset_val is not None:
                query += f" OFFSET {self._offset_val}"

            columns, rows = self._backend.execute(query, args)
            if not columns:
                return Result(data=[])

            data = [self._backend.row_to_dict(columns, row) for row in rows]

            if self._single_mode:
                if len(data) == 0:
                    return Result(data=None)
                return Result(data=data[0])

            # Store in cache after fetching
            if cache_key and self._cache_backend:
                self._cache_backend.set(cache_key, data, ttl=self._cache_ttl)

            return Result(data=data)

        # INSERT
        if self._action == "INSERT":
            records = self._insert_data if isinstance(self._insert_data, list) else [self._insert_data]
            cols = ", ".join(records[0].keys())
            placeholders = ", ".join(["%s"] * len(records[0]))
            query = f"INSERT INTO {self._table} ({cols}) VALUES ({placeholders}) RETURNING *"

            all_rows = []
            for record in records:
                values = [self._backend.serialize_value(v) for v in record.values()]
                columns, rows = self._backend.execute(query, values)
                if columns and rows:
                    all_rows.extend([self._backend.row_to_dict(columns, r) for r in rows])

            is_list = isinstance(self._insert_data, list)
            return Result(data=all_rows if is_list else (all_rows[0] if all_rows else None))

        # UPDATE
        if self._action == "UPDATE":
            set_clause = ", ".join([f"{k} = %s" for k in self._update_data.keys()])
            query = f"UPDATE {self._table} SET {set_clause}"
            args = [self._backend.serialize_value(v) for v in self._update_data.values()]
            where, args = self._build_where(args)
            query += where + " RETURNING *"

            columns, rows = self._backend.execute(query, args)
            data = [self._backend.row_to_dict(columns, r) for r in rows] if columns else []
            return Result(data=data)

        # DELETE
        if self._action == "DELETE":
            query = f"DELETE FROM {self._table}"
            where, args = self._build_where(args)
            query += where + " RETURNING *"

            columns, rows = self._backend.execute(query, args)
            data = [self._backend.row_to_dict(columns, r) for r in rows] if columns else []
            return Result(data=data)


    # ... normal execute logic ...


        return Result(data=data)

        raise QueryError(f"Unknown action: {self._action}")

    def _build_cache_key(self):
        filters_str = str(self._filters)
        return f"pgcraft:{self._table}:{self._select_clause}:{filters_str}"
