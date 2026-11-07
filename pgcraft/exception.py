class PgCraftError(Exception):
    """Base exception for pgcraft"""
    pass

class ConnectionError(PgCraftError):
    """Failed to connect to database"""
    pass

class QueryError(PgCraftError):
    """Query execution failed"""
    pass

class NotFoundError(PgCraftError):
    """single() returned no results"""
    pass

class MultipleRowsError(PgCraftError):
    """single() returned more than one row"""
    pass
