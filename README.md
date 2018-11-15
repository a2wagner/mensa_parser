# Parser for the Mensa menu of the Uni Mainz
 
Written with [node.js](https://nodejs.org/).
Python version using [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

## Node

NOTE: Outdated as of ~13.11.2018, syntax of the mensa code changed, only Python version has been updated

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

#### Examples

Markdown output of Mensa for current day:

`./parse_mensa.py`

Output better suited for terminals:

`./parse_mensa.py --no-img --terminal`

Mensaria for the next day:

`parse_mensa.py mensaria morgen`

Week plan for the (next) week:

`./parse_mensa.py (next) week`

Check for a certain dish (in the Mensaria), Käsespätzle will be used if dish is not passed:

`./parse_mensa.py (mensaria) check (dish)`

You might want to add the following aliases to your `.bashrc`:

    alias mensa='~/parse_mensa.py --no-img --terminal'
    alias mensaria='~/parse_mensa.py --no-img --terminal mensaria'

## Mensa Alarm

The shell script `mensa_alarm.sh` calls the Python script mentioned above to check for certain meals. If there's a match, it will be send to the desktop environment as a notification.

Käsespätzle is assumed by default. A different meal can be passed as an argument to the script.

To run it as a weekly cron job, e.g. every Monday at 11, create a new cron job with
`crontab -e`
and add the following line:

`0 11 * * 1 /path/to/mensa_alarm.sh (dish)`

The dish argument is optional. Make sure both the shell script and the Python script are executable and your cron job daemon is activated (systemctl status/enable cronie).
