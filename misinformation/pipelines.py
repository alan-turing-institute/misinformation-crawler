import json
import os
import pkg_resources
import pyodbc
from scrapy.exceptions import NotConfigured
from scrapy.exporters import JsonItemExporter
import yaml


class ArticleJsonFileExporter(object):

    def __init__(self):
        self.exporter = None

    @classmethod
    def from_crawler(cls, crawler):
        exporter = crawler.settings['ARTICLE_EXPORTER']
        if exporter != 'file':
            # if this isn't specified in settings, the pipeline will be completely disabled
            raise NotConfigured
        return cls()

    # Initialise pipeline when crawler opened
    def open_spider(self, spider):
        output_dir = "articles"
        output_file = "{}_extracted.txt".format(spider.config['site_name'])
        # Ensure output directory exists
        if not(os.path.isdir(output_dir)):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        f = open(output_path, 'wb')
        self.exporter = JsonItemExporter(f)
        self.exporter.start_exporting()

    # Tidy up after crawler closed
    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.exporter.file.close()

    def process_item(self, article, spider):
        self.exporter.export_item(article)
        spider.logger.info("Successfully crawled: {}".format(article["article_url"]))
        return article


class ArticleDatabaseExporter(object):

    def __init__(self):
        self.encoder = None
        self.conn = None
        self.cursor = None
        self.insert_row_sql = """DECLARE @JSON NVARCHAR(MAX) = ?

INSERT INTO [articles_v4]
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

    # Initialise pipeline when crawler opened
    def open_spider(self, spider):
        # Load database configuration from file in secrets folder
        db_config = yaml.load(pkg_resources.resource_string(__name__, "../secrets/db_config.yml"))
        # Set up database connection
        self.conn = pyodbc.connect(
            'DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password}'.format(
                driver=db_config['driver'], server=db_config['server'], database=db_config['database'],
                user=db_config['user'], password=db_config['password']
            ))
        self.cursor = self.conn.cursor()
        # Set up JSON encoder
        self.encoder = json.JSONEncoder(ensure_ascii=False)

    # Tidy up after crawler closed
    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, article, spider):
        row = self.encoder.encode(dict(article))
        try:
            self.cursor.execute(self.insert_row_sql, row)
            self.conn.commit()
        # Check for duplicate key exceptions and report informative log message
        except pyodbc.IntegrityError as e:
            if "Cannot insert duplicate key" in str(e):
                error_string = str(e).split("(")[4]
                spider.logger.warning("Refusing to add duplicate entry for: {}".format(article["article_url"]))
            else:
                # If this wasn't a duplicate key exception then re-raise it
                raise
        # Check for database size exceptions and report information log message
        except pyodbc.ProgrammingError as e:
            if "reached its size quota" in str(e):
                spider.close_down = True
                spider.logger.error("Closing down as the database has reached its size quota.")
            else:
                # If this wasn't a duplicate key exception then re-raise it
                raise
        spider.logger.info("Finished crawling: {}".format(article["article_url"]))
        return article
