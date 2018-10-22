import json
import pkg_resources
import pyodbc
import yaml


class ArticleJsonExporterPipeline(object):

    def __init__(self):
        self.encoder = None
        self.conn = None
        self.cursor = None
        self.insert_row_sql = """DECLARE @JSON NVARCHAR(MAX) = ?

INSERT INTO articles_v2
    SELECT crawl_id, crawl_date, site_name, article_url, title, author, publication_date,
    plain_content, structured_content, metadata FROM OPENJSON (@JSON) 
    WITH(
    crawl_id UNIQUEIDENTIFIER,
    crawl_date DATETIMEOFFSET(7),
    site_name NVARCHAR(800),
    article_url NVARCHAR(800),
    title NVARCHAR(max),
    author NVARCHAR(max),
    publication_date DATETIME2(7),
    plain_content NVARCHAR(max) AS JSON,
    structured_content NVARCHAR(max) AS JSON,
    metadata NVARCHAR(max) AS JSON)"""

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
        self.cursor.execute(self.insert_row_sql, row)
        self.conn.commit()
        spider.logger.info("Successfully crawled: {}".format(article["article_url"]))
        return article
