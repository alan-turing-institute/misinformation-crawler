from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementNotVisibleException, ElementNotInteractableException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import visibility_of_element_located, element_to_be_clickable
from selenium.webdriver.support.wait import WebDriverWait


class JSLoadButtonMiddleware:
    """Scrapy middleware to bypass javascript 'load more' buttons using selenium.

    Javascript load buttons are identified by searching for XPath patterns.

    Selenium will keep pressing the button until one of the following occurs:
        1. The button disappears (eg. when there are no more articles to load)
        2. The page takes too long to load (currently 60s)
        3. A maximum number of button presses is reached (currently 10000)
    """
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.seen_urls = set()
        self.timeout = 60
        self.max_button_clicks = 10000
        self.button_xpaths = [
            '//input[contains(@class, "agree")]',
            '//button[@name="agree"]',
            '//button[@class="qc-cmp-button"]',
            '//button[@class="btn-more"]',
            '//button[text()="Show More"]',
            '//button[text()="Load More"]',
            '//button[contains(@class, "show-more")]',
            '//button[@phx-track-id="load more"]',
            '//form[@class="gdpr-form"]/input[@class="btn"]'
        ]

    def first_load_button_xpath(self):
        """Find the first load button on the page - there may be more than one."""
        for button_xpath in self.button_xpaths:
            try:
                self.driver.find_element_by_xpath(button_xpath)
                return button_xpath
            except WebDriverException:
                pass
        return None

    def response_contains_button(self, response):
        """Search for a button in the response."""
        for button_xpath in self.button_xpaths:
            if response.xpath(button_xpath):
                return True
        return False

    def process_response(self, request, response, spider):
        """Process the page response using the selenium driver if applicable.

        As the selenium driver is much slower than the the normal scrapy crawl,
        we only do this if we actively identify the page as having a javascript
        load button.
        """
        # Do not process the same request URL twice
        if request.url in self.seen_urls:
            return response
        self.seen_urls.add(request.url)

        # Look for a button using xpaths on the scrapy response
        if not self.response_contains_button(response):
            return response

        # Load the URL using chromedriver
        self.driver.get(request.url)

        # We should only reach this point if we have found a javascript load button
        spider.logger.info('Identified a javascript load button on {}.'.format(request.url))

        # Keep track of the number of clicks performed
        n_clicks_performed = 0
        cached_page_source = None

        while True:
            try:
                # We need a nested try block here, since the WebDriverWait
                # inside the ElementNotVisibleException or the
                # ElementNotInteractableException can throw a
                # TimeoutException that we want to handle in the same way as
                # other TimeoutExceptions
                try:
                    # Cache the page source in case the page crashes
                    cached_page_source = self.driver.page_source

                    # Look for a load button and store its location so that we
                    # can check when the page is reloaded
                    load_button_xpath = self.first_load_button_xpath()
                    load_button = self.driver.find_element_by_xpath(load_button_xpath)
                    button_location = load_button.location

                    # Sending a keypress of 'Return' to the button works even
                    # when the button is not currently visible in the viewport.
                    # The other option is to scroll the window before clicking,
                    # but that seems messier.
                    load_button.send_keys(Keys.RETURN)

                    # Track the number of clicks that we've performed
                    n_clicks_performed += 1
                    spider.logger.info('Clicked the load button once ({} times in total).'.format(n_clicks_performed))

                    # Terminate if we're at the maximum number of clicks
                    if n_clicks_performed >= self.max_button_clicks > 0:
                        spider.logger.info('Finished loading more articles after clicking button {} times.'.format(n_clicks_performed))
                        break

                    # Wait until the page has been refreshed. We test for this
                    # by checking whether the load button has moved location.
                    # NB. the default poll frequency is 0.5s so if we want
                    # short timeouts this needs to be changed in the
                    # WebDriverWait constructor
                    WebDriverWait(self.driver, self.timeout).until(lambda _: button_location != load_button.location)

                except ElementNotVisibleException:
                    # This can happen when the page refresh makes a previously
                    # found element invisible until the page load is finished
                    WebDriverWait(self.driver, self.timeout).until(visibility_of_element_located((By.XPATH, load_button_xpath)))
                except ElementNotInteractableException:
                    # This can happen when the page refresh makes an element
                    # non-clickable for some period
                    WebDriverWait(self.driver, self.timeout).until(element_to_be_clickable((By.XPATH, load_button_xpath)))
            except (NoSuchElementException, StaleElementReferenceException):
                # If there are still available buttons on the page then repeat
                if self.first_load_button_xpath():
                    continue
                else:
                    spider.logger.info('Terminating button clicking since there are no more load buttons on the page.')
                    break
            except TimeoutException:
                spider.logger.info('Terminating button clicking after exceeding timeout of {} seconds.'.format(self.timeout))
                break
            except WebDriverException:
                spider.logger.info('Terminating button clicking after losing connection to the page.')
                break

        # Get appropriately encoded HTML from the page
        try:
            html_str = self.driver.page_source.encode(request.encoding)
        except WebDriverException:
            html_str = cached_page_source.encode(request.encoding)

        # Add any cookies that we may have collected to the spider so that they
        # can be used for future requests
        spider.update_cookies(self.driver.get_cookies())
        return HtmlResponse(body=html_str, url=request.url, encoding=request.encoding, request=request)

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()
