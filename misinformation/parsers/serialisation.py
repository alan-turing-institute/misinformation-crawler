from scrapy.http.response.html import HtmlResponse
from scrapy.http.request import Request

def request_to_dict(request):
    d = {
        'url': request.url,
        'method': request.method,
        'headers': request.headers.to_unicode_dict(),
        'body': request.body.decode(request._encoding),
        'cookies': request.cookies,
        'meta': request.meta,
        '_encoding': request._encoding,
        'priority': request.priority,
        'dont_filter': request.dont_filter,
        'flags': request.flags
    }
    return d

def request_from_dict(d):
    r = Request(
            url=d['url'],
            method=d['method'],
            headers=d['headers'],
            body=d['body'].encode(d['_encoding']),
            cookies=d['cookies'],
            meta=d['meta'],
            encoding=d['_encoding'],
            priority=d['priority'],
            dont_filter=d['dont_filter'],
            flags=d.get('flags')
        )
    return r


def response_to_dict(response):
    d = {
        "status": response.status,
        "headers": response.headers.to_unicode_dict(),
        "text": response.text,
        "request": request_to_dict(response.request),
        "flags": response.flags,
    }
    return d


def response_from_dict(d):
    request = request_from_dict(d["request"])
    r = HtmlResponse(
            d["url"],
            status=d["status"],
            headers=d["headers"],
            body=d["text"].encode("utf-8"),
            flags=d["flags"],
            request=request,
            encoding="utf-8",
        )
    return r


