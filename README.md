# Misinformation crawler
Web crawler to collect snapshots of articles to web archive.

See [main project](https://github.com/alan-turing-institute/misinformation) for project board and issues.


## Prerequisites
- `chromedriver`
    - needed by Selenium. See [installation instructions](https://selenium-python.readthedocs.io/installation.html)
- `node.js`
    - needed both for some `ReadabiliPy` tests and also to avoid Cloudflare protections. See [installation instructions](https://nodejs.org/en/download/)
- (optional) Microsoft SQL drivers
    - Needed only if recording the crawl in the Azure database, not if writing output to a local file
    - See sections below on `Using pyodbc on macos` and `How to install Microsoft SQL Server drivers`

##### Using pyodbc on OSX
If you are not using the latest version of macos, you may get an `sql.h not found` error when installing the `pyodbc`
dependency via pip. This is because there is no compiled wheel for your version of OSX.

The options are to either (i) upgrade to the latest version of OSX or (ii) install the `unixodbc` driver libraries using `brew install unixodbc`.

##### How to install Microsoft SQL Server drivers on OSX
1. Install Homebrew is you have not already: `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
2. Add the Microsoft Tap: `brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release`
3. Update Homebrew: `brew update`
4. Install the Microsoft SQL ODBC driver: `brew install openssl msodbcsql17 mssql-tools`


## Installation
- Check out the code from `github`
- Install the Python dependencies for this package by running:
  - As a user of this project `pip install -r requirements.txt`
  - As a developer of this project `pip install -r requirements-dev.txt`
- Ensure that [`ReadabiliPy`](https://github.com/alan-turing-institute/ReadabiliPy) is installed by running:
    ```git submodule update --init --recursive```
  - Install the Python dependencies for `ReadabiliPy` by typing `pip install -r ReadabiliPy/requirements.txt`
  - (Optional) Install the `node.js` dependencies for `ReadabiliPy` by entering the `ReadabiliPy` directory and typing `npm install`



## Testing
To run tests, run `python -m pytest` from the repository root.


## Usage
Site configurations for 47 sites are included in `misinformation/site_configs.yml`

Usage: `python crawl_all.py -n=<max_articles_per_site>` (limit is optional and all articles will be crawled if left off)

Crawled articles are saved one file per site in `articles/`

The actual number of articles returned may be up to 16 higher due to number of parallel requests scrapy has open at any time.


## Developing
To update to the latest version of [ReadabiliPy](https://github.com/martintoreilly/ReadabiliPy/blob/features/14-plain-content-structure/README.md).
- Navigate to the `ReadabiliPy` folder with `cd ReadabiliPy`
- Ensure you are on the `master` branch with `git checkout master`
- Pull the latest version with `git pull`
- Install the dependencies with `pip install -r requirements.txt`


## Running the crawler with the Azure database backend
In order to run the crawler you will need to create a file at `secrets/db_config.yaml` inside the top-level `misinformation-crawler` directory. This should look like the following:

```
driver: ODBC Driver 17 for SQL Server
server: misinformation.database.windows.net
database: misinformation
user: database-crawler-user
password: <password>
```

where the password is obtained from the Azure keyvault for the database, using

```az keyvault secret show --vault-name misinformation-user --name database-crawler-user```

The crawler can then be run using `python crawl_all.py -e database`.

