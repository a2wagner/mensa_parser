# Parser for the Mensa menu of the Uni Mainz
 
Written with [node.js](https://nodejs.org/).
Python version using [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

## Node

### Requirements:

  * request
  * cheerio

`npm install request cheerio`

### Usage

Run with `node parse_mensa.js`


## Python

### Requirements:

  * requests
  * beautifulsoup4

`pip install requests beatifulsoup4`

### Usage

Run it with `./parse_mensa.py` or `python parse_mensa.py`

## Mensa Alarm

The shell script `mensa_alarm.sh` calls the Python script mentioned above to check for certain meals. If there's a match, it will be send to the desktop environment as a notification.

Käsespätzle is assumed by default. A different meal can be passed as an argument to the script.

To run it as a weekly cron job, e.g. every Monday at 11, create a new cron job with
`crontab -e`
and add the following line:

`0 11 * * 1 /path/to/mensa_alarm.sh (dish)`

The dish argument is optional. Make sure both the shell script and the Python script are executable.
