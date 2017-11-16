#!/usr/bin/env python3

from sys import exit, argv
import re

try:
    import requests
except ImportError :
    exit('Unable to import requests, package installed?')
try:
    from bs4 import BeautifulSoup
except ImportError:
    exit('Unable to import BeautifulSoup 4, package installed?')


def query_mensa_page(querytype=1, building=1):
    """
    Query the Mensa page and return the retrieved content,
    exit with error if HTTP status code is not okay
    """
    result = requests.get("https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=%d&display_type=%d" % (building, querytype))
    if result.status_code is not 200:
        exit('Konnte Mensa-Infos nicht abrufen')

    return result.content

def get_counters_scrubbed(soup):
    """
    Turn the HTML code into a list of strings.
    vegan/veggi icons are preserved, injected in the code via [veg*] tag
    which will get replaced in the formatting method by the image.
    Some other artifacts and unwanted stuff is removed as well.
    """
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
    """
    Format a list of strings containing Mensa dishes into Markdown formatted code
    """
    menu = ''
    if day_string:
        menu = '\n \n# %s\n' % day_string
    else:
        menu = '# Die %s empfiehlt:\n'

    menu += ' '.join(dishes_list)
    menu = re.sub(r'\s*(Ausgabe\s\d)', r'\n \n## \1\n', menu)
    menu = re.sub(r'\n\s', r'\n', menu)
    menu = re.sub(r'\[(Veg.*)\]', r'![\1](http://www.studierendenwerk-mainz.de/fileadmin/templates/images/speiseplan/\1.png)', menu)
    # if Salatbuffet doesn't start in a separate line
    menu = re.sub(r'\)\sSalat', r')\nSalat', menu)

    return menu

def extract_days(soup):
    """
    Parse the HTML code for a complete week and create a dict from the contents.
    The day shown on the Mensa page is the key, the corresponding menu gets merged in a bs4 tag
    which then can be parsed by the get_counters_scrubbed method.
    """
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

    return days

def find_dish(soup, dish, detail=False):
    """
    Try to find a given dish in the parsed content of the Mensa site and return a string when it will be served if found.
    If detail is set to True the method returns the counter as well.
    """
    time = None
    week = extract_days(soup)
    match = None
    for day, dishes in week.items():
        match = next((elem.parent for elem in dishes(text=re.compile(dish, re.IGNORECASE))), None)
        if match:
            time = day
            if not detail:
                return 'There will be %s on %s' % (dish.title(), day)
            break

    if not detail or not match:
        return time

    dish = re.sub(r'\s?\(.*\)', '', match.string.strip())
    counter = match.parent.parent.find(string=re.compile('Ausgabe')).string.strip()

    return "Am %s gibt's %s an %s" % (day, dish, counter)


def main():

    types = {1: 'aktueller Tag', 2: 'aktuelle Woche', 3: 'nächste Woche'}
    buildings = {1: 'Mensa', 7: 'Mensaria'}

    #TODO: in case of Mensaria parse the special{box,counter} div as well

    check = None
    query = 1
    building = 1
    if len(argv) > 1:
        if 'next' in argv:
            query = 3
        elif 'week' in argv:
            query = 2
        if 'mensaria' in argv:
            building = 7
        elif argv[1] in 'check':
            if len(argv) is 3:
                check = str(argv[2]).lower()
            else:
                check = 'käsespätzle'
        # if query hasn't changed and the above if's didn't match, the option(s) provided are not known
        elif query is 1:
            exit('Unknown option')

    if check:
        print('Checking for', check.title())
        detail = True
        # first check the current week
        this_week = query_mensa_page(2)
        time = find_dish(BeautifulSoup(this_week, 'html.parser'), check, detail)
        if not time:
            # if we have no match in the current week, check the next week
            next_week = query_mensa_page(3)
            time = find_dish(BeautifulSoup(next_week, 'html.parser'), check, detail)
        if not time:
            print('No %s in the next time... :-(' % check.title())
        else:
            print(time)
        return

    content = query_mensa_page(query, building)
    soup = BeautifulSoup(content, 'html.parser')

    days = []
    if query > 1:
        days = soup.find_all("div", "speiseplan_date")


    week = {}
    if query > 1 and len(days) > 1:
        week = extract_days(soup)

    menu = ''
    if week:
        menu = '# Wochenplan %s (%s):\n' % (buildings[building], types[query])
        for day, lst in week.items():
            dishes = get_counters_scrubbed(lst)
            menu += format_day(dishes, day)
    else:
        dishes = get_counters_scrubbed(soup)
        menu = format_day(dishes) % buildings[building]

    print(menu)


if __name__ == '__main__':
    main()
