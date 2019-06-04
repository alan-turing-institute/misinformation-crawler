"""
This module contains functionality for interacting with Azure databases
"""
from .connector import Connector
from .exceptions import DatabaseError, NonRecoverableDatabaseError, RecoverableDatabaseError
from .models import Article, Webpage

__all__ = [
    "Article",
    "Connector",
    "DatabaseError",
    "NonRecoverableDatabaseError",
    "RecoverableDatabaseError",
    "Webpage",
]
