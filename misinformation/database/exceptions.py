class DatabaseError(Exception):
    """Base class for database exceptions"""


class NonRecoverableDatabaseError(DatabaseError):
    """Raised for non-recoverable errors (eg. connection failure)"""


class RecoverableDatabaseError(DatabaseError):
    """Raised for understood and recoverable errors (eg. duplicate keys)"""
