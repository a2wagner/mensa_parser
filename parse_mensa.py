#!/usr/bin/env python3

from sys import exit, argv
import requests

type = 1
if len(argv) > 1:
    if argv[1] in 'week':
        type = 2

result = requests.get("https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=1&display_type=%d" % type)
if result.status_code is not 200:
    exit('Error')


from bs4 import BeautifulSoup
import re

content = result.content
soup = BeautifulSoup(content, 'html.parser')

days = []
if type is 2:
    days = soup.find_all("div", "speiseplan_date")


def get_counters_scrubbed(soup):
    pattern = re.compile('Veg..').search
    [v.parent.find('span').insert_before(' [%s]' % m.group(0)) for v in soup.find_all("div", "vegan_icon") for i in v.find_all('img') for m in [pattern(i.get('src'))] if m]

    # get all contents of the different counters, remove parentheses
    dishes = [re.sub('\(.+?\)', '', line.strip()) for counter in soup.find_all('div', 'counter_box') for line in counter.stripped_strings]
    # remove empty lines, | spacings, and kJ values etc.
    dishes[:] = [re.sub(r'\|', '\n', line) for line in filter(None, dishes) if not line.lower().startswith(('kj', 'menü'))]
    # remove strange artifacts like multiple spaces, dash for menu counter, and non-breaking spaces
    dishes[:] = [re.sub('\s\s+', ' ', line.rstrip('-').replace(u'\xa0', u' ')) for line in dishes]

    return dishes

def format_day(dishes_list, day_string=''):
    menu = ''
    if day_string:
        menu = '\n \n# %s\n' % day_string
    else:
        menu = '# Die Mensa empfiehlt:\n'

    menu += ' '.join(dishes_list)
    menu = re.sub(r'\s*(Ausgabe\s\d)', r'\n \n## \1\n', menu)
    menu = re.sub(r'\n\s', r'\n', menu)
    menu = re.sub(r'\[(Veg.*)\]', r'![\1](http://www.studierendenwerk-mainz.de/fileadmin/templates/images/speiseplan/\1.png)', menu)
    # if Salatbuffet doesn't start in a separate line
    menu = re.sub(r'\)\sSalat', r')\nSalat', menu)

    return menu

def extract_days(soup):
    plan = soup.find('div', 'speiseplan')
    days = {}
    day = ''
    tags = None
    # loop over children: days followed by counters
    for child in plan.children:
        # only interested in divs containing the menu
        if child.name and child.name in 'div':
            # if this div contains a string, it's only the date
            if child.string:
                # if we find a day string and have collected tags already, start a new day and store info in dict
                if tags:
                    days.update({day: tags})
                    tags = None
                day = child.string
            # if it contains no string but more, all following tags are the dishes of this day
            else:
                if tags:
                    tags.append(child)
                else:
                    tags = child
    # don't forget to add the last day
    days.update({day: tags})
    #days = dict([('day', get_counters_scrubbed(day)) for day in days])

    return days

week = {}
if type is 2 and len(days) > 1:
    week = extract_days(soup)

menu = ''
if week:
    menu = '# Wochenplan Mensa:\n'
    for day, lst in week.items():
        dishes = get_counters_scrubbed(lst)
        menu += format_day(dishes, day)
else:
    dishes = get_counters_scrubbed(soup)
    menu = format_day(dishes)

print(menu)

