import base64
from io import BytesIO
from scrapy.http.response.html import HtmlResponse
from scrapy.http.request import Request
from warcio.archiveiterator import ArchiveIterator
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter


def request_from_dict(d):
    r = Request(url=d["url"],
                method=d["method"],
                headers=d["headers"],
                body=d["body"],
                cookies=d["cookies"],
                encoding=d["_encoding"],
                )
    return r


def response_from_dict(d):
    request = request_from_dict(d["request"])
    r = HtmlResponse(d["url"],
                     status=d["status"],
                     headers=d["headers"],
                     body=d["body"],
                     request=request,
                     encoding="utf-8",
                     )
    return r


def warc_from_response(response, resolved_url):
    f_output = BytesIO()
    writer = WARCWriter(f_output, gzip=True)
    # Response
    response_header_items = list(response.headers.to_unicode_dict().items())
    response_headers = StatusAndHeaders("200 OK", response_header_items, protocol="HTTP/1.0")
    response_record = writer.create_warc_record(resolved_url, "response", payload=BytesIO(response.body), http_headers=response_headers)
    writer.write_record(response_record)
    # Request
    request_header_items = list(response.request.headers.to_unicode_dict().items())
    request_headers = StatusAndHeaders("200 OK", request_header_items, protocol="HTTP/1.0")
    request_record = writer.create_warc_record(resolved_url, "request", payload=BytesIO(response.request.body), http_headers=request_headers)
    request_record.rec_headers.add_header("WARC-Concurrent-To", response_record.rec_headers.get_header("WARC-Record-ID"))
    writer.write_record(request_record)
    contents = f_output.getvalue()
    f_output.close()
    return contents


def response_from_warc(file_bytes):
    content = {}
    for record in ArchiveIterator(BytesIO(file_bytes)):
        # Load response
        if record.rec_type == "response":
            response_id = record.rec_headers.get_header("WARC-Record-ID")
            content["url"] = record.rec_headers.get_header("WARC-Target-URI")
            content["status"] = record.http_headers.get_statuscode()
            content["headers"] = dict(record.http_headers.headers)
            content["body"] = record.content_stream().read()
        # Load corresponding request
        elif record.rec_headers.get_header("WARC-Concurrent-To") == response_id:
            if record.rec_type == "request":
                content["request"] = {}
                content["request"]["url"] = content["url"]
                content["request"]["status"] = record.http_headers.get_statuscode()
                content["request"]["headers"] = dict(record.http_headers.headers)
                content["request"]["method"] = "GET"
                content["request"]["body"] = record.content_stream().read()
                content["request"]["_encoding"] = "utf-8"
                content["request"]["cookies"] = record.http_headers.get_header("cookie")
    # Build a response and return it
    return response_from_dict(content)


def string_from_warc(file_bytes):
    return base64.encodebytes(file_bytes).decode("utf-8")
