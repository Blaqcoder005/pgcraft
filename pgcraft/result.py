class Result:
    def __init__(self, data=None, count=None):
        self._data = data
        self._count = count

    @property
    def data(self):
        return self._data

    @property
    def count(self):
        return self._count

    def __repr__(self):
        if self._count is not None:
            return f"Result(count={self._count})"
        if isinstance(self._data, list):
            return f"Result(rows={len(self._data)})"
        return f"Result(data={self._data})"
