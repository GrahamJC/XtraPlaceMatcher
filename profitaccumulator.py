import sys
import datetime as dt
import re

from requests import Session, get, post
from requests.exceptions import RequestException
from contextlib import closing
from time import sleep

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from user_agent import generate_user_agent

from bs4 import BeautifulSoup

import settings
from models import Bookie, Event, BookieEvent, Runner, Checkpoint, Odds


class ProfitAccumulator:

    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'
    LOGON_URL = 'https://www.profitaccumulator.co.uk/wp-login.php'
    USERNAME = settings.PA_USERNAME
    PASSWORD = settings.PA_PASSWORD
    DASHBOARD_URL = 'https://www.profitaccumulator.co.uk/mydashboard'
    EXTRA_PLACE_CATCHER_URL = 'https://www.profitaccumulator.co.uk/extra-place-catcher'
    EXTRA_PLACE_CATCHER_DATA_URL = 'https://odds.profitaccumulator.co.uk/Home/ExtraPlaceMatcherData'

    def __init__(self):
        self.session = Session()
        self.session.headers.update({ 'user-agent': self.USER_AGENT })
        self.events = {}
        self.bookies = {}
        self.exchanges = {}
        pass

    def logon(self):

        # GET logon page which sets a test cookie that must be included with the POST
        self.session.get(self.LOGON_URL)

        # POST logon credentials
        form_data = {
            'log': self.USERNAME,
            'pwd': self.PASSWORD,
            'wp-submit': 'Log In',
            'redirect-to': self.DASHBOARD_URL,
            'testcookie': 1,
        }
        response = self.session.post(self.LOGON_URL, data = form_data, allow_redirects = True)
        html = BeautifulSoup(response.content, 'html.parser')
        if html.head.title.string.startswith('Log In'):
            div = html.find('div', id = 'login_error')
            if div:
                print(f"ERROR: {div.contents[1]}")
            return False
        
        # Logon Ok
        return True

    def logoff(self):

        # Get dashboard and parse to get logout URL
        response = self.session.get(self.DASHBOARD_URL)
        html = BeautifulSoup(response.content, 'html.parser')
        li = html.select('.topbar ul.list-inline li')[-1]
        if li and li.a:
            response = self.session.get(li.a['href'])


    def get_extra_place_info(self):

        # Get main page
        response = self.session.get(self.EXTRA_PLACE_CATCHER_URL)
        html = BeautifulSoup(response.content, 'html.parser')
        print(html.head.title.string)

        # Find <iframe> (selecting by id doesn't seem to work)
        iframe = html.iframe
        if iframe:

            # Get <iframe> content
            headers = {
                'referer': self.EXTRA_PLACE_CATCHER_URL,
            }
            response = self.session.get(iframe['src'], headers = headers)

            # Parse response
            html = BeautifulSoup(response.content, 'html.parser')

            # Get events
            for option in html.select('#events option'):
                id = option['data-id']
                s = option.string.split(' - ')
                course = s[0]
                date_time = dt.datetime.strptime(s[1], '%a, %d %b %Y %H:%M')
                self.events[id] = {
                    'course': course,
                    'date_time': date_time,
                }

            # Get bookies
            for label in html.select('#bookiename ul li label'):
                match = re.compile(r'CheckBookmaker\(this,(\d+)\)').match(label.input['onclick'])
                if match:
                    id = match.group(1)
                    name = label.input['data-filter']
                    title = label.contents[1].strip()
                    self.bookies[id] = {
                        'name': name,
                        'title': title,
                    }


            # Get exchanges
            for label in html.select('#exchangename ul li label'):
                match = re.compile(r'CheckExchanges\(this,(\d+)\)').match(label.input['onclick'])
                if match:
                    id = match.group(1)
                    name = label.input['data-filter']
                    title = label.contents[1].strip()
                    self.exchanges[id] = {
                        'name': name,
                        'title': title,
                    }


    def get_extra_place_data(self):

        form_data = {
            'tournamentId': 1095,
            'configId': 1017,
            'cr': ['{"BookMaker": 104, "Rate":2}', '{"BookMaker": 101, "Rate":5}', '{"BookMaker": 103, "Rate":0}','{"BookMaker": 102, "Rate":0}'],
            'bookies': [8, 2, 57, 24, 26, 40, 29, 34],
            'exchanges': [104, 101, 103, 102],
            'minRating': '',
            'maxRating': '',
            'minOdds': '',
            'maxOdds': '',
            'minImpOdds': '',
            'maxImpOdds': '',
            'ewStake': '',
            'userKey': 'dVY1Z1RhREEwVDcrdmZzd21KY2hqdz09OjpsS/ZKEapxiJ1b3OeuY/up',
        }
        response = self.session.post(self.EXTRA_PLACE_CATCHER_DATA_URL, data = form_data)
        return response.content


if __name__ == '__main__':

    pa = ProfitAccumulator()
    if pa.logon():
        pa.get_extra_place_info()
        print(pa.events)
        print(pa.bookies)
        print(pa.exchanges)
        #data = pa.get_extra_place_data()
        pa.logoff()
    sys.exit()