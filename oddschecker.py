import sys
import datetime as dt

from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from time import sleep

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from user_agent import generate_user_agent

from bs4 import BeautifulSoup

from models import Bookie, Event, BookieEvent, Runner, Checkpoint, Odds

class OCBookie:

    def __init__(self, name, ew_places = None, ew_divider = None):
        self.name = name
        self.ew_places = ew_places
        self.ew_divider = ew_divider

    def __str__(self):
        result = self.name
        if self.ew_places and self.ew_divider:
            result += f" ({self.ew_places} places @ 1/{self.ew_divider})"
        return result

    def __repr__(self):
        return f"OCBookie('{self.name}', {self.ew_places}, {self.ew_divider})"


class OCHorse:

    def __init__(self, name):
        self.name = name
        self.odds = {}

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"OCHorse({self.name})"

class OddsChecker:

    ROOT_URL = 'https://www.oddschecker.com'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    #USER_AGENT = generate_user_agent()


    def _http_get(self, url):

        try:
            headers = {
                'user-agent': self.USER_AGENT,
            }
            with closing(get(url, headers = headers, stream = True)) as resp:
                content_type = resp.headers['Content-Type'].lower()
                if (resp.status_code == 200  and content_type is not None and content_type.find('html') > -1):
                    return resp.content
                else:
                    return None
        except RequestException as e:
            return None
        
    def _get_bookies(self, html):

        bookies = []
        #for a in html.select('tr.eventTableHeader td.bookie-area a'):
        for a in html.select('#ew_bookie_content tr.ew_bookie_row td.bookie_column a'):
            bookies.append(OCBookie(a.attrs['title']))
        for idx, td in enumerate(html.select('#ew_bookie_content tr.eventTableFooter td[data-bk]')):
            bookies[idx].ew_places = td.attrs.get('data-ew-places')
            ew_div = td.attrs.get('data-ew-div')
            if ew_div == '1/4':
                bookies[idx].ew_divider = 4
            elif ew_div == '1/5':
                bookies[idx].ew_divider = 5
            else:
                bookies[idx].ew_divider = 1
        return bookies

    def _get_horses(self, html, bookies):
        horses = []
        if bookies:
            for tr in html.select('#oddsTableContainer table.eventTable tbody tr'):
                horse = OCHorse(tr.attrs['data-bname'])
                for idx, td in enumerate(tr.select('td[data-odig]')):
                    horse.odds[bookies[idx].name] = td.attrs['data-odig']
                horses.append(horse)
        return horses

    def get_racing_info(self, course, time, market = 'winner'):

        url = f"{self.ROOT_URL}/horse-racing/{course}/{time}/{market}"
        raw_html = self._http_get(url)
        while not raw_html:
            print(f"Retrying GET {url}")
            sleep(10)
            raw_html = self._http_get(url)
        html = BeautifulSoup(raw_html, 'html.parser')
        bookies = self._get_bookies(html)
        horses = self._get_horses(html, bookies)
        return {
            'bookies': bookies,
            'horses': horses,
        }

    def get_racing_events(self):

        url = f"{self.ROOT_URL}/horse-racing"
        raw_html = self._http_get(url)
        while not raw_html:
            print(f"Retrying GET {url}")
            sleep(10)
            raw_html = self._http_get(url)
        html = BeautifulSoup(raw_html, 'html.parser')
        result = {
            'courses': [],
        }
        for div in html.select('div.module.show-times[data-day="today"]:not(''.international-races'') div.race-details'):
            course = {
                'name': div.select('div.venue-details a')[0].string,
                'events': [],
            }
            for a in div.select('div.racing-time a'):
                event_dt = dt.datetime.strptime(a.attrs['data-time'], '%Y-%m-%d %H:%M:%S')
                event_url = a.attrs['href']
                course['events'].append({'date_time': event_dt, 'url': event_url})
            result['courses'].append(course)
        return result


def get_event_odds(db_session, db_event):

    # Get event info from OddsChecker web site
    oc = OddsChecker()
    info = oc.get_racing_info(event.course.lower().replace(' ', '-'), event.date_time.strftime('%H:%M'), 'winner')

    # Create checkpoint
    db_checkpoint = Checkpoint(event = event, date_time = dt.datetime.now(), source = 'OddsChecker')
    db_session.add(db_checkpoint)
    for bookie in info['bookies']:
        db_bookie = db_session.query(Bookie).filter_by(name = bookie.name).one_or_none()
        if not db_bookie:
            db_bookie = Bookie(name = bookie.name)
            db_session.add(db_bookie)
        db_bookie_event = db_session.query(BookieEvent).filter_by(event = db_event, bookie = db_bookie).one_or_none()
        if not db_bookie_event:
            db_bookie_event = BookieEvent(event = db_event, bookie = db_bookie, ew_places = bookie.ew_places or 0, ew_divider = bookie.ew_divider or 1)
            db_session.add(db_bookie_event)
    for horse in info['horses']:
        db_runner = db_session.query(Runner).filter_by(event = db_event, name = horse.name).one_or_none()
        if not db_runner:
            db_runner = Runner(event = db_event, name = horse.name)
            db_session.add(db_runner)
        for bookie, odds in horse.odds.items():
            db_bookie = db_session.query(Bookie).filter_by(name = bookie).one()
            db_odds = Odds(checkpoint = db_checkpoint, runner = db_runner, bookie = db_bookie, win = odds, place = 0)
            db_session.add(db_odds)
    db_session.commit()
    db_event.last_checkpoint = db_checkpoint
    db_session.commit()


SQLALCHEMY_URL = 'postgresql://xtraplace:barnum@localhost/xtraplace'

if __name__ == '__main__':

    db_engine = create_engine(SQLALCHEMY_URL)
    Session = sessionmaker(bind = db_engine)

    # Get todays events
    oc = OddsChecker()
    info = oc.get_racing_events()
    db_session = Session()
    for course in info['courses']:
        for event in course['events']:
            db_event = db_session.query(Event).filter(Event.course == course['name'], Event.date_time == event['date_time']).one_or_none()
            if not db_event:
                db_event = Event(course = course['name'], date_time = event['date_time'])
                db_session.add(db_event)
                print(f"Add {db_event.course} {db_event.date_time.time()} ({event['url']})")
    db_session.commit()

    # Get odds for todays events
    while True:
        db_session = Session()
        events = db_session.query(Event).filter(Event.date_time >= dt.datetime.now()).order_by(Event.date_time)
        if events.count() == 0:
            break
        for event in events:
            secs_to_off = (event.date_time - dt.datetime.now()).total_seconds()
            secs_since_check = (event.last_checkpoint.date_time - dt.datetime.now()).total_seconds() if event.last_checkpoint else 900
            if (secs_to_off <= 300 and secs_since_check >= 60) or (secs_to_off <= 1800 and secs_since_check >= 300) or (secs_since_check >= 900):
                print(f"{dt.datetime.now()}: Get odds for {event.course} at {event.date_time.time()}")
                get_event_odds(db_session, event)
        sleep(30)
    sys.exit()


