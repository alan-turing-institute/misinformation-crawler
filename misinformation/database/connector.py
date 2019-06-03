import yaml
import pkg_resources
import sqlalchemy
from azure.storage.blob import BlockBlobService
from .exceptions import RecoverableDatabaseError, NonRecoverableDatabaseError


class Connector():
    def __init__(self):
        # Database connections
        self.db_config = yaml.load(pkg_resources.resource_string(__name__, "../../secrets/db_config.yml"), Loader=yaml.FullLoader)
        self.engine = sqlalchemy.create_engine("mssql+pyodbc://{user}:{password}@{server}:1433/{database}?driver={driver}".format(
            database=self.db_config["database"],
            driver=self.db_config["driver"],
            password=self.db_config["password"],
            server=self.db_config["server"],
            user=self.db_config["user"],
        ))
        self.session_factory = sqlalchemy.orm.sessionmaker(bind=self.engine)
        # Blob storage
        self.block_blob_service = BlockBlobService(account_name='misinformationcrawldata', account_key=self.db_config["blob_storage_key"])
        self.blob_container_name = "warc-files"

    def add_entry(self, entry):
        '''Attempt to commit transaction to the database.'''
        try:
            session = self.session_factory()
            session.add(entry)
            session.commit()
            session.close()
            return
        # Check for duplicate key exceptions and report informative log message
        except sqlalchemy.exc.IntegrityError as err:
            if "Violation of UNIQUE KEY constraint" in str(err):
                raise RecoverableDatabaseError("  refusing to add duplicate database entry for: {}".format(entry.article_url))
            raise  # Re-raise the exception if it had a different cause
        # Check for database communication failure and report informative log message
        except sqlalchemy.exc.OperationalError as err:
            if "Communication link failure" in str(err):
                raise NonRecoverableDatabaseError("Lost connection with the database. Ending the crawl.")
            raise  # Re-raise the exception if it had a different cause
        # Check for database size or lost connection exceptions and report informative log message
        except sqlalchemy.exc.ProgrammingError as err:
            if "reached its size quota" in str(err):
                raise NonRecoverableDatabaseError("The database has reached its size quota. Ending the crawl.")
            raise  # Re-raise the exception if it had a different cause

    def read_entries(self, entry_type, column=None, site_name=None):
        session = self.session_factory()

        query_list = [entry_type]
        if column:
            query_list += column
        print(query_list)

        if site_name:
            entries = session.query(*query_list).filter_by(site_name=site_name).all()
        else:
            entries = session.query(*query_list).all()
        session.close()
        return entries

