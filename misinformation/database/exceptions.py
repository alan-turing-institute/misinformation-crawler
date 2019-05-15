class DatabaseError(Exception):
   """Base class for database exceptions"""
   pass


class NonRecoverableDatabaseError(DatabaseError):
   """Raised for non-recoverable errors (eg. connection failure)"""
   pass


class RecoverableDatabaseError(DatabaseError):
   """Raised for understood and recoverable errors (eg. duplicate keys)"""
   pass


