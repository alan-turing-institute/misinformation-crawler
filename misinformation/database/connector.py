import logging
import yaml
import pkg_resources
import pyodbc
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from .exceptions import RecoverableDatabaseError
from .models import Webpage

import struct


logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

def handle_datetimeoffset(dto_value):
    # ref: https://github.com/mkleehammer/pyodbc/issues/134#issuecomment-281739794
    tup = struct.unpack("<6hI2h", dto_value)  # e.g., (2017, 3, 16, 10, 35, 18, 0, -6, 0)
    tweaked = [tup[i] // 100 if i == 6 else tup[i] for i in range(len(tup))]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:07d} {:+03d}:{:02d}".format(*tweaked)



class Connector():
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


    def add_entry(self, entry):
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
                raise RecoverableDatabaseError("  refusing to add duplicate database entry for: {}".format(entry.article_url))
            # Re-raise the exception if it had a different cause
            else:
                raise

    def read_entries(self, entry_type, site_name=None):
        session = self.session_factory()
        if site_name:
            entries = session.query(entry_type).filter_by(site_name=site_name).all()
        else:
            entries = session.query(entry_type).all()
        session.close()
        return entries
