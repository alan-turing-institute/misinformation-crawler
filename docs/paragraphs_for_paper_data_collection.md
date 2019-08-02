Data Collection
-----

To create the dataset, we utilised the Python package "scrapy" to crawl a list of X websites. The misinformation-crawler code was set up so that new sites could be added by updating a config yaml file. For each new site, we first identified the HTML elements that contained the article content and metadata (title, date and byline), then formulated the Xpath code that would match those elements. These Xpath code snippets were then included in the config file under the relevant site heading.

For some of the metadata (titles and dates), we identified that there were common HTML elements being used across many sites and included the matching Xpath codes as defaults, which could be overwritten by the config Xpaths upon inclusion. This saved time when adding additional sites.

The config file also specified which crawl strategy should be performed for each site, of which there were three kinds that we developed.
1.	The "Index page" strategy worked by iterating through index pages (those we identified by matching a particular url pattern) of a website and treating all links matching a given Xpath code as being article pages.
2.	The "Sitemap" strategy worked by treating all the links on a website’s sitemap as article pages.
3.	The "Scattergun" strategy worked by crawling all the links on a site. We used this strategy as a last resort for sites that lacked viable index pages or a sitemap.

Each of these strategies could be modified further for a particular site by placing constraints on the urls of pages to be considered articles appropriate for the dataset.

Over the duration of the project, in addition to adding new sites to the config, the crawler code was refined many times and sometimes new features had to be added in light of a site that couldn’t be crawled by the current version of the code.

One such modification was to use the Python package "Selenium" within the crawler’s middleware, which enabled it to "click" buttons from a list we compiled as we continued to update the crawler code to support additional sites. These buttons were often "Load more" buttons that some sites use on their index pages to reveal additional articles, but they also included subscribe popups that are encountered when visiting a site for the first time, which needed to be "clicked on" before the crawler could reach the main site pages.

Challenges
-----

One of the challenges we faced as we began to populate the database with articles extracted by the crawler was the "sliding window" effect created by the passing of time. Since the sites we crawled are active news sites, many of which publish daily, the complement of articles extracted each time the crawler is run is always different.

Some of the sites that we originally intended to crawl have since been taken offline and others still proved to be un-crawlable, due to the site authors implementing an anti-scraping measure, or because the sites were subscription only.

How to run code on GitHub
----

*Include specific instructions*

By cloning the GitHub project and replacing the config file with a custom one, it will be possible to create a new dataset.
