import json
import yaml
import pkg_resources
from scrapy.exceptions import NotConfigured
import pyodbc


class ArticleDatabaseExporter():
    def __init__(self):
        self.encoder = None
        self.conn = None
        # Load database configuration from file in secrets folder
        self.db_config = yaml.load(pkg_resources.resource_string(__name__, "../../secrets/db_config.yml"))
        self.insert_row_sql = """DECLARE @JSON NVARCHAR(MAX) = ?

INSERT INTO [articles_v5]
    SELECT crawl_id, crawl_datetime, site_name, article_url, title, byline, publication_datetime,
    content, plain_content, plain_text, metadata FROM OPENJSON (@JSON)
    WITH(
    crawl_id UNIQUEIDENTIFIER,
    crawl_datetime DATETIMEOFFSET(7),
    site_name NVARCHAR(800),
    article_url NVARCHAR(800),
    title NVARCHAR(max),
    byline NVARCHAR(max),
    publication_datetime DATETIME2(7),
    content NVARCHAR(max),
    plain_content NVARCHAR(max),
    plain_text NVARCHAR(max) AS JSON,
    metadata NVARCHAR(max) AS JSON)"""

    @classmethod
    def from_crawler(cls, crawler):
        exporter = crawler.settings['ARTICLE_EXPORTER']
        if exporter != 'database':
            # if this isn't specified in settings, the pipeline will be completely disabled
            raise NotConfigured
        return cls()

    @property
    def cursor(self):
        '''Get the database cursor, attempting to reconnect once if the connection is closed'''
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
        except pyodbc.ProgrammingError as err:
            if "Attempt to use a closed connection." in str(err):
                self.connect_to_database()
            cursor = self.conn.cursor()
        return cursor

    def open_spider(self, _):
        '''Initialise pipeline when crawler is opened'''
        # Connect to the database using configuration from file in secrets folder
        self.connect_to_database()
        # Set up JSON encoder
        self.encoder = json.JSONEncoder(ensure_ascii=False)

    def close_spider(self, _):
        '''Tidy up after crawler is closed'''
        self.conn.close()

    def connect_to_database(self):
        '''Set up database connection'''
        self.conn = pyodbc.connect(
            'DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password}'.format(
                driver=self.db_config['driver'], server=self.db_config['server'],
                database=self.db_config['database'], user=self.db_config['user'],
                password=self.db_config['password']
            ))

    def process_item(self, article, spider):
        '''Add an article to the database'''
        row = self.encoder.encode(dict(article))

        try:
            self.cursor.execute(self.insert_row_sql, row)
            self.conn.commit()
        # Check for duplicate key exceptions and report informative log message
        except pyodbc.IntegrityError as err:
            if "Cannot insert duplicate key" in str(err):
                spider.logger.warning("Refusing to add duplicate entry for: {}".format(article["article_url"]))
            else:
                # Re-raise the exception if it had a different cause
                raise
        # Check for database communication failure and report informative log message
        except pyodbc.OperationalError as err:
            if "Communication link failure" in str(err):
                spider.request_closure = True
                spider.logger.error("Lost connection with the database. Ending the crawl.")
            else:
                # Re-raise the exception if it had a different cause
                raise
        # Check for database size exceptions and report informative log message
        except pyodbc.ProgrammingError as err:
            if "reached its size quota" in str(err):
                spider.request_closure = True
                spider.logger.error("Closing down as the database has reached its size quota.")
            else:
                # Re-raise the exception if it had a different cause
                raise
        spider.logger.info("Finished crawling: {}".format(article["article_url"]))
        return article
