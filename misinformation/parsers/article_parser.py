from azure.storage.blob import BlockBlobService
from ..database import Connector, Webpage
from ..items import Article
import datetime
import json
from scrapy.http.response.html import HtmlResponse
from .serialisation import response_from_dict
from ..extractors import extract_element

class ArticleParser(Connector):
    def __init__(self):
        super().__init__()
        self.block_blob_service = BlockBlobService(account_name="misinformationcrawldata", account_key=self.db_config["blob_storage_key"])
        self.blob_container_name = "raw-crawled-pages"


    def process_site(self, site_name, config):

        entries = self.read_entries(Webpage, site_name=site_name)

        print("Loaded {} pages for {}".format(len(entries), site_name))


        for entry in entries:
            # Load data from blob storage
            blob_key = entry.blob_key
            blob = self.block_blob_service.get_blob_to_text(self.blob_container_name, blob_key)
            # print(blob.content)
            # print("blob.content", type(blob.content))
            # blob_data = json.loads(json.loads(blob.content)) # double decoding needed as we had to convert the scrapy.Item to a dict
            blob_data = json.loads(blob.content)
            # print(blob_data)
            # print("blob_data", type(blob_data))

            # Create article with pre-existing information
            article = Article()
            article["crawl_id"] = blob_data["crawl_id"]
            article["crawl_datetime"] = blob_data["crawl_datetime"] #.replace(tzinfo=datetime.timezone.utc).isoformat()
            article["site_name"] = entry.site_name
            article["article_url"] = entry.article_url

            # Construct response
            response = response_from_dict(blob_data)
            print("response")
            print(response)

            # First extract the content (or use the default content)
            try:
                article_html = extract_element(response, config["article"]["content"])
            except KeyError:
                article_html = extract_element(response, "/html")

            print("article_html", article_html)


            # if "article" in config:
            #     # Extract article content
            #     if "content" in config["article"]:
            #         # Extract article content from specified element if present
            #         config["article"]["content"]["warn_if_missing"] = False
            #         article_html = extract_element(response, config["article"]["content"])
            #         if article_html is not None:
            #             custom_readability_article = parse_to_json(article_html, content_digests, node_indexes, False)
            #             article["content"] = custom_readability_article["content"]
            #             article["plain_content"] = custom_readability_article["plain_content"]
            #             article["plain_text"] = custom_readability_article["plain_text"]
            #     # Only try to extract other data if the article has identified content
            #     if "content" in article and article["content"] is not None:
            #         # Extract title
            #         if "title" in config["article"]:
            #             article["title"] = extract_element(response, config["article"]["title"])
            #         # Extract byline
            #         if "byline" in config["article"]:
            #             article["byline"] = extract_element(response, config["article"]["byline"])
            #         # Extract publication_datetime
            #         if "publication_datetime" in config["article"]:
            #             datetime_string = extract_element(response, config["article"]["publication_datetime"])
            #             if "datetime-format" in config["article"]["publication_datetime"]:
            #                 dt_format = config["article"]["publication_datetime"]["datetime-format"]
            #                 iso_string = extract_datetime_string(datetime_string, dt_format)
            #             else:
            #                 iso_string = extract_datetime_string(datetime_string)
            #             article["publication_datetime"] = iso_string
            # # ... otherwise simply use the default values from parsing the whole page
            # else:
            #     default_readability_article = parse_to_json(page_html, content_digests, node_indexes, False)
            #     article["title"] = default_readability_article["title"]
            #     article["byline"] = default_readability_article["byline"]
            #     article["content"] = default_readability_article["content"]
            #     article["plain_content"] = default_readability_article["plain_content"]
            #     article["plain_text"] = default_readability_article["plain_text"]


            print(article)


            # print(type(blob_data["page_html"]), blob_data["page_html"])


    # title = scrapy.Field()
    # byline = scrapy.Field()
    # publication_datetime = scrapy.Field()
    # metadata = scrapy.Field()
    # plain_content = scrapy.Field()
    # plain_text = scrapy.Field()
    # content = scrapy.Field()






    # article["article_url"] = resolved_url if resolved_url else response.url
    # article["request_meta"] = response.request.meta

    # # Set default article fields by running readability on full page HTML
    # page_spec = xpath_extract_spec("/html", "largest")
    # page_html = extract_element(response, page_spec)
    # article["page_html"] = page_html



    # # Extract additional article metadata
    # if "metadata" in config:
    #     # Initialise metadata field
    #     article["metadata"] = dict()
    #     # Attempt to extract all metadata fields
    #     for fieldname in config["metadata"]:
    #         article["metadata"][fieldname] = extract_element(response, config["metadata"][fieldname])

    # # Add crawl information if provided
    # if crawl_info:
    #     article["crawl_id"] = crawl_info["crawl_id"]
    #     article["crawl_datetime"] = crawl_info["crawl_datetime"]

    # # Ensure all fields included in article even if no data extracted for them
    # if "title" not in article:
    #     article["title"] = None
    # if "byline" not in article:
    #     article["byline"] = None
    # if "publication_datetime" not in article:
    #     article["publication_datetime"] = None
    # if "content" not in article:
    #     article["content"] = None
    # if "plain_content" not in article:
    #     article["plain_content"] = None
    # if "plain_content" not in article:
    #     article["plain_text"] = None
    # if "metadata" not in article:
    #     article["metadata"] = None

    # return article




    #     # s.query(Book).all()
