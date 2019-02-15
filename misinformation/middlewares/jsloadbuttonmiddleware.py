from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of

class JSLoadButtonMiddleware:
    """Scrapy middleware to bypass javascript 'load more' buttons using selenium.

    Javascript load buttons are identified by searching for particular XPath patterns.

    The selenium driver will keep pressing the button until one of the following conditions occurs:
        1. The button disappears (for example when there are no more articles to load)
        2. The page takes too long to load (currently set to 30s)
        3. A maximum number of button presses is performed (currently set to 10000)
    """

    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.seen_urls = set()
        self.timeout = 30
        self.max_button_clicks = 10000
        self.button_xpaths = [
            '//button[text()="Show More"]',
            '//button[text()="Load More"]'
        ]

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""

        # Do not use the selenium driver if this is not an index page
        if spider.index_page_url_require_regex and not spider.index_page_url_require_regex.search(request.url):
            return None

        # Do not process the same request URL twice
        if request.url in self.seen_urls:
            return None
        self.seen_urls.add(request.url)

        # Load the URL using chromedriver
        self.driver.get(request.url)

        # Count the number clicks performed
        n_clicks_performed = 0

        # Search through button xpaths to see if there is one on the page
        load_button_xpath = None
        for button_xpath in self.button_xpaths:
            try:
                self.driver.find_element_by_xpath(button_xpath)
                load_button_xpath = button_xpath
                break
            except NoSuchElementException:
                continue
        if not load_button_xpath:
            return None

        print("load_button_xpath:", load_button_xpath)
        spider.logger.info('Identified a javascript load button on {}.'.format(request.url))

        while True:
            try:
                # Look for a load button and store its location so that we can
                # check when the page is reloaded
                load_button = self.driver.find_element_by_xpath(load_button_xpath)
                button_location = load_button.location

                # Chromedriver cannot click the button if it is not currently visible on screen
                # self.driver.execute_script("window.scrollTo({x},{y})".format(**load_button.location))
                # load_button.click()

                # Sending a keypress of 'Return' to the button works even when
                # the button is not currently visible in the viewport. The
                # other option is to scroll the window before clicking, but
                # that seems messier.
                load_button.send_keys(Keys.RETURN)

                # Track the number of clicks that we've performed
                n_clicks_performed += 1
                # spider.logger.info('Identified a load button on {}. Clicked it {} times.'.format(request.url, n_clicks_performed))
                spider.logger.info('Clicked the load button once ({} times in total).'.format(n_clicks_performed))

                # Terminate if we're at the maximum number of clicks
                if n_clicks_performed >= self.max_button_clicks > 0:
                    spider.logger.info('Finished loading more articles after clicking button {} times.'.format(n_clicks_performed))
                    break

                # Wait until the page has been refreshed. We test for this by
                # checking whether the load button has moved location
                WebDriverWait(self.driver, self.timeout).until(lambda _: button_location != load_button.location)

            except NoSuchElementException:
                spider.logger.info('Terminating button clicking since the button no longer exists.')
                break
            except TimeoutException:
                spider.logger.info('Terminating button clicking after exceeding timeout of {} seconds.'.format(self.timeout))
                break

        # Turn the page into a response
        html_str = self.driver.page_source.encode(request.encoding)
        return HtmlResponse(body=html_str, url=request.url, encoding=request.encoding, request=request)

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()
