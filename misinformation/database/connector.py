import logging
import yaml
import pkg_resources
import pyodbc
import sqlalchemy
from sqlalchemy.orm import sessionmaker

logging.getLogger("sqlalchemy").setLevel(logging.ERROR)


class DatabaseError(Exception):
   """Base class for database exceptions"""
   pass


class RecoverableDatabaseError(DatabaseError):
   """Raised for understood and recoverable errors (eg. duplicate keys)"""
   pass


class NonRecoverableDatabaseError(DatabaseError):
   """Raised for non-recoverable errors (eg. connection failure)"""
   pass


class DatabaseConnector():
    def __init__(self):
        self.db_config = yaml.load(pkg_resources.resource_string(__name__, "../../secrets/db_config.yml"))
        self.engine = sqlalchemy.create_engine("mssql+pyodbc://{user}:{password}@{server}:1433/{database}?driver={driver}".format(
            database = self.db_config["database"],
            driver = self.db_config["driver"],
            password = self.db_config["password"],
            server = self.db_config["server"],
            user = self.db_config["user"],
        ))
        self.session_factory = sessionmaker(bind=self.engine)


    def add_dbentry(self, table_name, entry):
        '''Attempt to commit transaction to the database.'''
        try:
            session = self.session_factory()
            session.add(entry)
            session.commit()
            session.close()
            return
        # Check for duplicate key exceptions and report informative log message
        except (pyodbc.IntegrityError, sqlalchemy.exc.IntegrityError) as err:
            if "Violation of UNIQUE KEY constraint" in str(err):
                raise RecoverableDatabaseError("Refusing to add duplicate entry for: {}".format(entry.article_url))
            # Re-raise the exception if it had a different cause
            else:
                raise
