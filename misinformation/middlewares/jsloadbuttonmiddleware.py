from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of

class JSLoadButtonMiddleware:
    """Scrapy middleware to bypass javascript 'load more' buttons using selenium"""

    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.seen_urls = set()
        self.timeout = 10

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""

        # Do not use the selenium driver if this is not an index page
        if spider.infinite_index_url_require_regex and not spider.infinite_index_url_require_regex.search(request.url):
            return None

        # Do not process the same request URL twice
        if request.url in self.seen_urls:
            return None
        self.seen_urls.add(request.url)

        # Load the URL using chromedriver
        self.driver.get(request.url)

        # Count the number clicks performed
        n_clicks_performed = 0
        n_clicks_max = spider.infinite_index_max_clicks

        # Get button xpath
        load_button_xpath = spider.infinite_index_load_button_expression

        while True:
            try:
                # Look for a load button and store its location so that we can
                # check when the page is reloaded
                load_button = self.driver.find_element_by_xpath(load_button_xpath)
                button_location = load_button.location

                # Chromedriver cannot click the button if it is not currently visible on screen
                # self.driver.execute_script("window.scrollTo({x},{y})".format(**load_button.location))
                # load_button.click()

                # Sending a keypress of 'Return' to the button works even if
                # the button is not currently visible in the viewport
                load_button.send_keys(Keys.RETURN)

                # Track the number of clicks that we've performed
                n_clicks_performed += 1
                spider.logger.info('Identified a load button on {}. Clicked it {} times.'.format(request.url, n_clicks_performed))

                # Terminate if we're at the maximum number of clicks
                if n_clicks_performed >= n_clicks_max > 0:
                    spider.logger.info('Finished loading more articles after clicking button {} times.'.format(n_clicks_performed))
                    break

                # Wait until the page has been refreshed. We test for this by
                # checking whether the load button has moved location
                WebDriverWait(self.driver, self.timeout).until(lambda _: button_location != load_button.location)

            except NoSuchElementException:
                spider.logger.info('Terminating button clicking since button could not be found.')
                break
            except TimeoutException:
                spider.logger.info('Terminating button clicking after exceeding timeout of {} seconds.'.format(self.timeout))
                break
            # except WebDriverException:
            #     break


        # Turn the page into a response
        html_str = self.driver.page_source.encode(request.encoding)
        return HtmlResponse(body=html_str, url=request.url, encoding=request.encoding, request=request)

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()
