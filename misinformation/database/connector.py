import yaml
import pkg_resources
import sqlalchemy
from azure.storage.blob import BlockBlobService
from .exceptions import RecoverableDatabaseError, NonRecoverableDatabaseError


class Connector():
    def __init__(self, blob_container_name="warc-files"):
        # Database connections
        self._db_config = None
        self._engine = None
        self._session_factory = None
        # Blob storage
        self._block_blob_service = None
        self.blob_container_name = blob_container_name

    @property
    def block_blob_service(self):
        if not self._block_blob_service:
            self._block_blob_service = BlockBlobService(account_name="misinformationcrawldata", account_key=self.db_config["blob_storage_key"])
        return self._block_blob_service

    @property
    def db_config(self):
        if not self._db_config:
            try:
                self._db_config = yaml.load(pkg_resources.resource_string(__name__, "../../secrets/db_config.yml"), Loader=yaml.FullLoader)
            except FileNotFoundError:
                raise RecoverableDatabaseError("Could not load database connection information")
        return self._db_config

    def open_session(self):
        if not self._engine:
            self._engine = sqlalchemy.create_engine("mssql+pyodbc://{user}:{password}@{server}:1433/{database}?driver={driver}".format(
                database=self.db_config["database"],
                driver=self.db_config["driver"],
                password=self.db_config["password"],
                server=self.db_config["server"],
                user=self.db_config["user"],
            ))
        if not self._session_factory:
            self._session_factory = sqlalchemy.orm.sessionmaker(bind=self._engine)
        return self._session_factory()

    def get_blob_content(self, blob_key):
        blob = self.block_blob_service.get_blob_to_bytes(self.blob_container_name, blob_key)
        return blob.content

    def add_entry(self, entry):
        """Attempt to commit transaction to the database."""
        try:
            session = self.open_session()
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
            if "Login timeout expired" in str(err):
                raise NonRecoverableDatabaseError("Could not login to the database. Ending the crawl.")
            raise  # Re-raise the exception if it had a different cause
        # Check for database size or lost connection exceptions and report informative log message
        except sqlalchemy.exc.ProgrammingError as err:
            if "reached its size quota" in str(err):
                raise NonRecoverableDatabaseError("The database has reached its size quota. Ending the crawl.")
            raise  # Re-raise the exception if it had a different cause

    def read_entries(self, entry_type, max_entries=None, site_name=None):
        try:
            session = self.open_session()
            if site_name:
                if max_entries:
                    entries = session.query(entry_type).filter_by(site_name=site_name).limit(max_entries).all()
                else:
                    entries = session.query(entry_type).filter_by(site_name=site_name).all()
            else:
                if max_entries:
                    entries = session.query(entry_type).limit(max_entries).all()
                else:
                    entries = session.query(entry_type).all()
            session.close()
            return entries
        except sqlalchemy.exc.OperationalError:
            raise RecoverableDatabaseError("Could not read entries from database.")
