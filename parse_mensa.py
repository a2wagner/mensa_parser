#!/usr/bin/env python3

from sys import argv
import re
from collections import OrderedDict

try:
    import requests
except ImportError:
    exit('Unable to import requests, package installed?')
try:
    from bs4 import BeautifulSoup
except ImportError:
    exit('Unable to import BeautifulSoup 4, package installed?')


class Fmt:
    """
    Class which stores escape codes for formatted terminal output
    """
    red = r'\033[92m'
    green = r'\033[91m'
    bold = r'\033[1m'
    underlined = r'\033[4m'
    reset = r'\033[0m'

def query_mensa_page(querytype=1, building=1, language=0):
    """
    Query the Mensa page and return the retrieved content,
    exit with error if HTTP status code is not okay
    """
    result = requests.get("https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=%d&display_type=%d&L=%d" % (building, querytype, language))
    if result.status_code != 200:
        msg = 'Konnte Mensa-Infos nicht abrufen'
        if language == 3:
            msg = "Couldn't retrieve Mensa information"
        exit(msg)

    return result.content

def has_menu(soup):
    """
    Check if the queried contents contain meaningful values inside the 'speiseplan' div
    """
    if not soup.find('div', 'speiseplan').text.strip():
        return False
    return True

def get_counters_scrubbed(soup, mensaria=False):
    """
    Turn the HTML code into a list of strings.
    vegan/veggi icons are preserved, injected in the code via [veg*] tag
    which will get replaced in the formatting method by the image.
    Some other artifacts and unwanted stuff is removed as well.
    """
    pattern = re.compile('Veg..').search
    any(v.parent.insert_after(' [%s]' % m.group(0)) for v in soup.find_all("div", "vegan_icon") for i in v.find_all('img') for m in [pattern(i.get('src'))] if m and v.parent['class'][0] in 'menuspeise')

    # insert a pipe (will be replaced with newline) before every food item (due to changed syntax)
    any([v.find('div').insert_before('|') for v in soup.find_all('div', 'menuspeise') if v.find('div')])
    # get all contents of the different counters, remove parentheses
    dishes = [re.sub(r'\(.+?\)', '', line.strip()) for counter in soup.find_all('div', 'counter_box') for line in counter.stripped_strings]

    # in case of Mensaria, include additional meals offered as Snack etc.
    if mensaria:
        # Mensaria doesn't have the vegan_icon div, img directly in spmenuname div; take this into account assuming the price div is the last one in the spmenuename parent container
        any(v.parent.find('div', 'price').insert_after(' [%s]' % m.group(0)) for v in soup.find_all("div", "spmenuname") for i in v.find_all('img') for m in [pattern(i.get('src'))] if m)
        # insert markdown headline syntax before meal type string as well as a pipe after it which becomes a linebreak
        any(v.find('span').insert_before('|### ') for v in soup.find_all("div", "specialcounter"))
        any(v.find('span').insert_after('|') for v in soup.find_all("div", "specialcounter"))
        special = soup.find('div', 'specialbox')
        dishes += ['\n'] + [re.sub(r'\(.+?\)', '', line.strip()) for line in special.stripped_strings]

    # remove empty lines, | spacings, and kJ values etc.
    dishes[:] = [re.sub(r'\|', '\n', line) for line in filter(None, dishes) if not line.lower().startswith(('kj', 'menü', 'menu'))]
    # remove strange artifacts like multiple spaces, dash for menu counter, and non-breaking spaces
    dishes[:] = [re.sub(r'\s\s+', ' ', line.rstrip('-').replace(u'\xa0', u' ')) for line in dishes]

    return dishes

def format_day(dishes_list, day_string='', markdown_img=True, terminal=False, language='German'):
    """
    Format a list of strings containing Mensa dishes into Markdown formatted code
    """
    menu = ''
    if day_string:
        menu = '\n \n# %s\n' % day_string
    else:
        menu = '# Die %s empfiehlt:\n'
        if language == 'English':
            menu = '# Today in the %s:\n'
    if terminal:
        menu = re.sub(r'#(.*)\n', r'#%s\1%s\n' % (Fmt.bold, Fmt.reset), menu)

    menu += ' '.join(dishes_list)
    counter_string = 'Ausgabe'
    if language == 'English':
        counter_string = 'Counter'
    if terminal:
        menu = re.sub(r'\s*(' + counter_string + '\s\d)', r'\n \n## %s\1%s' % (Fmt.underlined, Fmt.reset), menu)
    else:
        menu = re.sub(r'\s*(' + counter_string + '\s\d)', r'\n \n## \1', menu)
    menu = re.sub(r'\n\s', r'\n', menu)
    if markdown_img:
        menu = re.sub(r'\[(Veg.*)\]', r'![\1](http://www.studierendenwerk-mainz.de/fileadmin/templates/images/speiseplan/\1.png)', menu)
    elif terminal:
        menu = re.sub(r'\[(Veggi)\]', r'[%s\1%s]' % (Fmt.red, Fmt.reset), menu)
        menu = re.sub(r'\[(Vegan)\]', r'[%s\1%s]' % (Fmt.green, Fmt.reset), menu)
    # fix that Salatbuffet doesn't start in a separate line
    menu = re.sub(r'\s+Salatbuffet', r'\nSalatbuffet', menu)

    return menu

def extract_days(soup):
    """
    Parse the HTML code for a complete week and create a dict from the contents.
    The day shown on the Mensa page is the key, the corresponding menu gets merged in a bs4 tag
    which then can be parsed by the get_counters_scrubbed method.
    """
    plan = soup.find('div', 'speiseplan')
    days = OrderedDict()
    day = ''
    tags = None
    # loop over children: days followed by counters
    for child in plan.children:
        # only interested in divs containing the menu
        if child.name and child.name in 'div':
            # if this div contains a string, it's only the date
            if child['class'][0] in 'speiseplan_date':
                # if we find a day string and have collected tags already, start a new day and store info in dict
                if tags:
                    days.update({day: tags})
                    tags = None
                day = child.string
            # skip the building name
            elif child['class'][0] in 'speiseplan_bldngall_name':
                continue
            # if it contains no string but more, all following tags are the dishes of this day
            else:
                if tags:
                    tags.append(child)
                else:
                    tags = child
    # don't forget to add the last day
    days.update({day: tags})

    return days

def find_dish(soup, dish, mensaria=False, detail=False):
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

    from datetime import datetime
    import locale
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')  # set locale for time to German since the month names are in German
    time = datetime.strptime(re.search(r'\d+. \w+ \d+', day).group(0) + ' 16:00', '%d. %B %Y %H:%M')
    now = datetime.today()
    days = (time - now).days
    hours = (time - now).seconds / 3600
    print('Treffer %s!' % ('in %d Tagen' % days if days else 'heute'))
    day = day.split()[0] + time.strftime(' %d.%m.')
    when = 'Am %s ' % day
    if not days and hours < 16:
        when = 'Heute '

    if mensaria:
        return when + "gibt's %s in der Mensaria" % dish

    counter = match.parent.parent.find(string=re.compile('Ausgabe')).string.strip()
    return when + "gibt's %s an %s" % (dish, counter)

def parse_arguments():
    """
    Uses the argv list and checks the arguments for known options.
    Returns the matched parameters or exits when there are unknown options.
    """
    check = None
    query = 1
    building = 1
    language = 0  # 0 (and 1 and 2) German, 3 English
    tmrw = False
    md_img = True
    detail = True
    term = False
    args = [arg.lower() for arg in argv[1:]]
    if args:
        if '--no-img' in args:
            md_img = False
            args.remove('--no-img')
        if '--no-detail' in args:
            detail = False
            args.remove('--no-detail')
        if '--terminal' in args:
            term = True
            args.remove('--terminal')
            if md_img:
                print('[WARN] --terminal specified but not --no-img. Assume no Markdown image inclusion.\n')
                md_img = False
        if '--german' in args:
            language = 0
            args.remove('--german')
        if '--english' in args:
            language = 3
            args.remove('--english')
        if 'week' in args:
            query = 2
            args.remove('week')
        if 'next' in args:
            query = 3
            args.remove('next')
        if 'morgen' in args:
            query = 2
            tmrw = True
            args.remove('morgen')
        if 'tomorrow' in args:
            query = 2
            tmrw = True
            args.remove('tomorrow')
        if 'mensaria' in args:
            building = 7
            args.remove('mensaria')
        if args and args[0] in 'check':
            if len(args) > 1:
                check = args[1]
                args.remove(check)
            else:
                check = 'käsespätzle'
            args.remove('check')
        # all known options checked and removed; if there are still arguments, the arguments are unknown or the query type was wrong
        if args:
            exit('Unknown options: ' + ', '.join(args))

    return check, query, building, language, tmrw, md_img, detail, term


def main():
    """main function"""
    types = {1: 'aktueller Tag', 2: 'aktuelle Woche', 3: 'nächste Woche'}
    types_en = {1: 'current day', 2: 'current week', 3: 'next week'}
    buildings = {1: 'Mensa', 7: 'Mensaria'}
    languages = {0: 'German', 3: 'English'}

    check, query, building, language, tmrw, md_img, detail, term = parse_arguments()

    if check:
        if detail:
            print('Checking for', check.title(), 'in', buildings[building])
        # first check the current week
        this_week = query_mensa_page(2, building)
        soup = BeautifulSoup(this_week, 'html.parser')
        time = None  # set time to None, prevents error if check is run on e.g. a Sunday when there's no menu
        if has_menu(soup):
            time = find_dish(soup, check, building == 7, detail)
        if not time:
            # if we have no match in the current week, check the next week
            next_week = query_mensa_page(3, building)
            soup = BeautifulSoup(next_week, 'html.parser')
            if has_menu(soup):
                time = find_dish(soup, check, building == 7, detail)
        if not time:
            print('No %s in the next time... :-(' % check.title())
            exit(1)
        else:
            print(time)
        return

    content = query_mensa_page(query, building, language)
    soup = BeautifulSoup(content, 'html.parser')

    # check if the found menu contains anything
    if not has_menu(soup):
        exit('Leerer Speiseplan, Mensa geschlossen?')

    week = {}
    # check if the query type was for a week and we have more than one day in the returned HTML code
    if query > 1 and len(soup.find_all("div", "speiseplan_date")) > 1:
        week = extract_days(soup)

    if tmrw:
        if not week:
            exit('Konnte keinen Wochenplan ermitteln... Bereits Wochenende?')
        else:
            dishes = get_counters_scrubbed(list(week.values())[1], building == 7)
            string = 'Morgen in der'
            if language == 3:
                string = 'Tomorrow in the'
            menu = format_day(dishes, '%s %s:' % (string, buildings[building]), md_img, term, language=languages[language])
            print(menu.lstrip())
            return

    menu = ''
    if week:
        menu = '# Wochenplan %s (%s):\n' % (buildings[building], types[query])
        if language == 3:
            menu = '# Week plan %s (%s):\n' % (buildings[building], types_en[query])
        if term:
            menu = re.sub(r'#(.*)\n', r'#%s\1%s\n' % (Fmt.bold, Fmt.reset), menu)
        for day, lst in week.items():
            dishes = get_counters_scrubbed(lst, building == 7)
            menu += format_day(dishes, day, md_img, term, language=languages[language])
    else:
        dishes = get_counters_scrubbed(soup, building == 7)
        menu = format_day(dishes, markdown_img=md_img, terminal=term, language=languages[language]) % buildings[building]

    print(menu)


if __name__ == '__main__':
    main()
