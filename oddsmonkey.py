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


class OddsMonkey:

    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'
    LOGON_URL = 'https://www.oddsmonkey.com/oddsmonkeyLogin.aspx?returnurl=%2f'
    USERNAME = settings.OM_USERNAME
    PASSWORD = settings.OM_PASSWORD
    DASHBOARD_URL = 'https://www.oddsmonkey.com/Dashboard.aspx'
    EXTRA_PLACE_MATCHER_URL = 'https://www.oddsmonkey.com/Tools/Matchers/ExtraPlaceMatcher.aspx'

    BOOKIE_IMAGES = {
        '/desktopModules/arbmonitor/images/bookies/10bet_h.gif'                 : '10Bet',
        '/desktopModules/arbmonitor/images/bookies/888sport_h.gif'              : '888Sport',
        '/desktopModules/arbmonitor/images/bookies/bet365_h.gif'                : 'Bet365',
        '/desktopModules/arbmonitor/images/bookies/betfairsportsbook_h.gif'     : 'BetfairSportsbook',
        '/desktopModules/arbmonitor/images/bookies/betfred_h.gif'               : 'BetFred',
        '/desktopModules/arbmonitor/images/bookies/betstars_h.gif'              : 'BetStars',
        '/desktopModules/arbmonitor/images/bookies/betvictor_h.gif'             : 'BetVicotr',
        '/desktopModules/arbmonitor/images/bookies/boylesports_h.gif'           : 'BoyleSports',
        '/desktopModules/arbmonitor/images/bookies/coral_h.gif'                 : 'Coral',
        '/desktopModules/arbmonitor/images/bookies/betstars_h.gif'              : 'FansBet',
        '/desktopModules/arbmonitor/images/bookies/ladbrokes_h.gif'             : 'Ladbrokes',
        '/desktopModules/arbmonitor/images/bookies/moplay_h.gif'                : 'MoPlay',
        '/desktopModules/arbmonitor/images/bookies/paddypower_h.gif'            : 'PaddyPower',
        '/desktopModules/arbmonitor/images/bookies/redarmybet_h.gif'            : 'RedArmyBet',
        '/desktopModules/arbmonitor/images/bookies/redsbet_h.gif'               : 'RedsBet',
        '/desktopModules/arbmonitor/images/bookies/skybet_h.gif'                : 'SkyBet',
        '/desktopModules/arbmonitor/images/bookies/totesport_h.gif'             : 'ToteSport',
        '/desktopModules/arbmonitor/images/bookies/unibet_h.gif'                : 'UniBet',
        '/desktopModules/arbmonitor/images/bookies/virginbet_h.gif'             : 'VirginBet',
        '/desktopModules/arbmonitor/images/bookies/willhill_h.gif'              : 'WilliamHill',
    }

    EXCHANGE_IMAGES = {
        '/desktopModules/arbmonitor/images/bookies/betfair_h.gif'               : 'Betfair',
        '/desktopModules/arbmonitor/ExtraPlaceMatcher/images/betfair_h.gif'     : 'Betfair',
        '/desktopModules/arbmonitor/images/bookies/smarkets_h.gif'              : 'SMarkets',
        '/desktopModules/arbmonitor/ExtraPlaceMatcher/images/smarkets_h.gif'    : 'SMarkets',
        '/desktopModules/arbmonitor/images/bookies/matchbook_h.gif'             : 'MatchBook',
        '/desktopModules/arbmonitor/ExtraPlaceMatcher/images/matchbook_h.gif'   : 'MatchBook',
        '/desktopModules/arbmonitor/images/bookies/betdaq_h.gif'                : 'BetDAQ',
        '/desktopModules/arbmonitor/ExtraPlaceMatcher/images/betdaq_h.gif'      : 'BetDAQ',
    }

    def __init__(self):
        self.session = Session()
        self.session.headers.update({ 'user-agent': self.USER_AGENT })
        self.events = {}
        self.bookies = {}
        self.exchanges = {}
        pass

    def logon(self):

        # GET logon page and parse form fields
        response = self.session.get(self.LOGON_URL)
        form_data = {}
        html = BeautifulSoup(response.content, 'html.parser')
        for input_ in html.form.find_all('input'):
            if 'name' in input_.attrs:
                name = input_['name']
                if name.endswith('txtUsername'):
                    form_data[name] = self.USERNAME
                elif name.endswith('txtPassword'):
                    form_data[name] = self.PASSWORD
                else:
                    form_data[name] = input_.attrs.get('value', '')
    
        # Set __EVENTTARGET
        form_data['__EVENTTARGET'] = 'dnn$ctr433$Login$Login_DNN$cmdLogin'

        # POST form
        headers = {
            'referer': self.LOGON_URL,
            'request-context': 'appId=cid-v1:c3b1d5f9-3835-4a4b-8569-c2bea254bcaa',
            'request-id': '|TjvPd.MhoU4',
        }
        response = self.session.post(self.LOGON_URL, data = form_data)

        # Parse response and check title to see if logon has succeeded
        html = BeautifulSoup(response.content, 'html.parser')
        title = html.head.title.string.strip() 
        if not title.startswith('Dashboard'):
            print(title)
            return False

        # Logon Ok
        return True

    def logoff(self):

        # Get dashboard and parse to get logout URL
        response = self.session.get(self.DASHBOARD_URL)
        html = BeautifulSoup(response.content, 'html.parser')
        a = html.find('a', title = 'Logout')
        if a:
            response = self.session.get(a['href'])

    def convert_to_float(self, value):

        try:
            return float(value.strip('£'))
        except ValueError:
            return None 

    def get_extra_place_event_data(self, html):

        # Collect event details in a dictionary
        data = {}

        # Get selected event details
        option = html.select_one('#races select option[selected]')
        if option and 'value' in option.attrs:

            # Get course and date/time
            value_list = option['value'].split('|')
            time_regex = re.compile('\d\d:\d\d')
            if not time_regex.match(value_list[0][-5:]):
                return None
            data['course'] = value_list[0][:-6]
            data['date_time'] = dt.datetime.strptime(value_list[1], '%a %d %b %Y %H:%M')

            # Get bookie details
            bookies = {}
            try:
                table = html.select('#divFilter .row')[1].table
                for span in table.select('span.cb-element'):
                    name = self.BOOKIE_IMAGES.get(span.find('img')['src'])
                    if name:
                        bookies[name] = {
                            'id': span.find('input')['value'],
                            'places': span.find('small').string[1],
                        }
            except:
                print(f"Bookies: {sys.exc_info()[0]}")                
            data['bookies'] = bookies

            # Get exchange details
            exchanges = {}
            try:
                table = html.select('#divFilter .row')[2].table
                for span in table.select('span.cb-element'):
                    name = self.EXCHANGE_IMAGES.get(span.find('img')['src'])
                    if name:
                        exchanges[name] = {
                            'id': span.find('input')['value'],
                        }
            except:
                print(f"Exchanges: {sys.exc_info()[0]}")                
            data['exchanges'] = exchanges

            # Get runners
            runners = {}
            try:
                for tr in html.select('#divRaceRepeater table tbody tr:not(.hide)'):
                    name = tr.find_all('td')[1].find('span').string
                    runners[name] = {
                        'back_ew_stake': self.convert_to_float(tr.find_all('td')[2].find('input')['value']),
                        'back_bookie': self.BOOKIE_IMAGES.get(tr.find_all('td')[3].find('img')['src']),
                        'back_win_odds': self.convert_to_float(tr.find_all('td')[4].find('input')['value']),
                        'back_place_terms': tr.find_all('td')[5].find('span').string,
                        'back_place_odds': self.convert_to_float(tr.find_all('td')[6].find('span').string),
                        'lay_win_exchange': self.EXCHANGE_IMAGES.get(tr.find_all('td')[7].find('img')['src']),
                        'lay_win_odds': self.convert_to_float(tr.find_all('td')[8].find('input')['value']),
                        'lay_win_commission': self.convert_to_float(tr.find_all('td')[9].find('span').string),
                        'lay_win_stake': self.convert_to_float(tr.find_all('td')[9].find('input')['value']),
                        'lay_place_exchange': self.EXCHANGE_IMAGES.get(tr.find_all('td')[11].find('img')['src']),
                        'lay_place_odds': self.convert_to_float(tr.find_all('td')[12].find('input')['value']),
                        'lay_place_commission': self.convert_to_float(tr.find_all('td')[13].find('span').string),
                        'lay_place_stake': self.convert_to_float(tr.find_all('td')[13].find('input')['value']),
                        'rate': self.convert_to_float(tr.find_all('td')[15].find('input')['value']),
                        'implied_odds': self.convert_to_float(tr.find_all('td')[16].find('input')['value']),
                        'qual_loss': self.convert_to_float(tr.find_all('td')[17].find('input')['value']),
                        'xplace_profit': self.convert_to_float(tr.find_all('td')[18].find('input')['value']),
                    }
            except:
                print(f"Runners: {sys.exc_info()[0]}")                
            data['runners'] = runners

        # Return event data
        return data

    def get_extra_place_events(self):

        # Get extra place matcher
        response = self.session.get(self.EXTRA_PLACE_MATCHER_URL)

        # Parse to get list of events
        event_list = []
        current_event = None
        html = BeautifulSoup(response.content, 'html.parser')
        for option in html.select('#races select option'):
            value = option['value']
            date_time = dt.datetime.strptime(value.split('|')[1], '%a %d %b %Y %H:%M')
            if date_time.date() == dt.date.today():
                event_list.append(value)
                if 'selected' in option.attrs:
                    current_event = option['value']

        # Get data for each event
        for event in event_list:

            # If not currently selected event POST a new request
            if event != current_event:
                form_data = {}
                for input_ in html.form.find_all('input'):
                    if 'name' in input_.attrs:
                        form_data[input_['name']] = input_.attrs.get('value', '')
                race_select = html.select('#races select')[0]
                form_data[race_select['name']] = event
                form_data['__EVENTTARGET'] = race_select['name']
                headers = {
                    'referer': self.EXTRA_PLACE_MATCHER_URL,
                    'request-context': 'appId=cid-v1:c3b1d5f9-3835-4a4b-8569-c2bea254bcaa',
                    'request-id': '|I0rEM.sKYwK',
                }
                response = self.session.post(self.EXTRA_PLACE_MATCHER_URL, data = form_data)
                html = BeautifulSoup(response.content, 'html.parser')

            # Get event data and look for good matches
            event_data = self.get_extra_place_event_data(html)
            if event_data:
                runners = len(event_data['runners'])
                print(f"{event_data['course']} {event_data['date_time']:%H:%M} ({runners} runners)")
                for name, runner in event_data['runners'].items():
                    if runner['back_win_odds'] <= 40 and runner['implied_odds'] >= runners:
                        print(f"  {runner['implied_odds']} {name} : {runner['back_bookie']}@{runner['back_win_odds']}/{runner['back_place_odds']}, {runner['lay_win_exchange']}@{runner['lay_win_odds']}, {runner['lay_place_exchange']}@{runner['lay_place_odds']}")


if __name__ == '__main__':

    om = OddsMonkey()
    if om.logon():
        print(f"===== {dt.datetime.now():%H:%M:%S} =====")
        om.get_extra_place_events()
        om.logoff()
    sys.exit(0)