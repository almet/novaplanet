# -*- coding: utf-8 -*-
import codecs
import datetime
import os.path
import sys
import time
from operator import attrgetter
from urllib.parse import urljoin

from pyquery import PyQuery as pq
from jinja2 import Environment, FileSystemLoader
import requests

HERE = os.path.dirname(os.path.abspath(__file__))


class Track(object):
    def __init__(self, artist, title, ts, picture):
        self.artist = artist.replace('"', "'")
        self.title = title.replace('"', "'")
        self.date = datetime.datetime.fromtimestamp(float(ts))
        self.ts = ts
        self.picture = picture


class NovaScrapper(object):

    url = 'http://www.nova.fr/radionova/radio-nova'

    def __init__(self, start, end):
        self.tracks = {}  # Let's store data indexed by their timestamp

        # Alter start because the nova page will give us too much info
        # otherwise.
        self.start = start
        self.end = end

        start = start + datetime.timedelta(minutes=50)
        self.scrap_page(start)

        while self.max_date < end:
            start = self.max_date + datetime.timedelta(minutes=50)
            self.scrap_page(start)

    @property
    def max_date(self):
        return datetime.datetime.fromtimestamp(self.max_ts)

    @property
    def max_ts(self):
        if self.tracks:
            return float(max(self.tracks.keys()))
        return 0

    def scrap_page(self, date):
        """Scrap a page, put the results in the self.tracks attribute."""
        # First, we need to get the form build ID.
        form = pq(url=self.url)
        form_build_id = form.find('input[name=form_build_id]')[0].value
        # Now, get the form answer
        resp = requests.post(self.url, data={
            'form_id': 'cqctform',
            'form_build_id': form_build_id,
            'year': date.year,
            'month': date.month,
            'day': date.day,
            'hour': date.hour,
            'minutes': date.minute
        })
        print('#')
        d = pq(resp.text)
        for item in d.find('.square-item>a').items():
            artist = item('.title>.name').text().capitalize()

            title = item('.title>.description').text().capitalize()
            picture = urljoin(self.url, item('img')[0].get('src'))
            hour, minute = map(int, item('time').text().split(':'))
            if hour > 6:
                continue
            title_datetime = datetime.datetime(
                year=date.year,
                month=date.month,
                day=date.day,
                hour=hour,
                minute=minute)
            ts = time.mktime(title_datetime.timetuple())

            if ts not in self.tracks:
                print('.')
                track = Track(artist=artist, title=title, ts=ts, picture=picture)
                self.tracks[ts] = track


def render_tracks(date, tracks, output_path):
    """Render a list of tracks objects into an HTMl page using a Jinja
    template.

    :param date: the date of today, used to generate the filename of the
                 output.
    :param tracks: the list of tracks objects.
    :param output_path: the path where to output the .html file.
    """
    filename = '%s.html' % date.strftime('%Y-%m-%d')
    render_template('tracks.html', filename, date=date, tracks=tracks)
    render_template('index.html', 'index.html', date=date)


def render_template(tpl_name, filename, **options):
    env = Environment(loader=FileSystemLoader(HERE))
    template = env.get_template(tpl_name)
    output = template.render(**options)

    full_path = os.path.join(output_path, filename)

    with codecs.open(full_path, 'w+', encoding='utf-8') as f:
        f.write(output)


def parse_nova_lanuit(start, end):

    scrapper = NovaScrapper(start, end)

    tracks = list(scrapper.tracks.values())
    tracks.sort(key=attrgetter('date'))

    return [t for t in tracks if t.date > start and t.date < end]

if __name__ == '__main__':
    output_path = sys.argv[1] if len(sys.argv) > 1 else '.'

    now = datetime.datetime.now() - datetime.timedelta(days=10)
    start = datetime.datetime(year=now.year, month=now.month,
                              day=now.day, hour=0, minute=00)

    end = datetime.datetime(year=now.year, month=now.month, day=now.day,
                            hour=6, minute=0)
    tracks = parse_nova_lanuit(start, end)
    render_tracks(start, tracks, output_path)
