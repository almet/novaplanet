# -*- coding: utf-8 -*-
import argparse
import codecs
import datetime
import os.path
import shutil
import time

from operator import attrgetter
from urllib.parse import urljoin

import podcats
import requests
from jinja2 import Environment, FileSystemLoader
from pyquery import PyQuery as pq

THEME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'theme')


class Track(object):
    def __init__(self, artist, title, ts, picture, links):
        self.artist = artist.replace('"', "'")
        self.title = title.replace('"', "'")
        self.date = datetime.datetime.fromtimestamp(float(ts))
        self.ts = ts
        self.picture = picture
        self.links = links


class NovaScrapper(object):

    url = 'http://www.nova.fr/radionova/radio-nova'

    def __init__(self, start, end, delay=None):
        self.tracks = {}  # Let's store data indexed by their timestamp
        self.delay = delay

        # Alter start because the nova page will give us too much info
        # otherwise.
        self.start = start
        self.end = end

        start = start + datetime.timedelta(minutes=50)
        self.scrap_page(start)

        tries = 0
        while self.max_date < end:
            start = self.max_date + datetime.timedelta(minutes=50)
            old_count = len(self.tracks)
            self.scrap_page(start)
            if old_count == len(self.tracks):
                tries = tries + 1
            if tries >= 3:
                break
        print("!")

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
        print('#', end='', flush=True)
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

            if self.delay:
                title_datetime = title_datetime + self.delay

            ts = time.mktime(title_datetime.timetuple())
            links = {link.get('class').split('-')[1]: link.get('href')
                     for link in item.siblings()('a')}
            if ts not in self.tracks:
                print('.', end='', flush=True)
                track = Track(artist=artist, title=title, ts=ts, picture=picture,
                              links=links)
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
    render_template(output_path, 'tracks.html', filename, date=date, tracks=tracks)
    render_template(output_path, 'index.html', 'index.html', date=date)


def render_template(output_path, tpl_name, filename, **options):
    env = Environment(loader=FileSystemLoader(THEME_PATH))
    template = env.get_template(tpl_name)
    output = template.render(**options)

    full_path = os.path.join(output_path, filename)

    with codecs.open(full_path, 'w+', encoding='utf-8') as f:
        f.write(output)


def copy(source, destination):
    """Recursively copy source into destination.

    Taken from pelican.

    If source is a file, destination has to be a file as well.
    The function is able to copy either files or directories.
    :param source: the source file or directory
    :param destination: the destination file or directory
    """
    source_ = os.path.abspath(os.path.expanduser(source))
    destination_ = os.path.abspath(os.path.expanduser(destination))

    if os.path.isfile(source_):
        dst_dir = os.path.dirname(destination_)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        shutil.copy2(source_, destination_)

    elif os.path.isdir(source_):
        if not os.path.exists(destination_):
            os.makedirs(destination_)
        if not os.path.isdir(destination_):
            return

        for src_dir, subdirs, others in os.walk(source_):
            dst_dir = os.path.join(destination_,
                                   os.path.relpath(src_dir, source_))

            if not os.path.isdir(dst_dir):
                # Parent directories are known to exist, so 'mkdir' suffices.
                os.mkdir(dst_dir)

            for o in others:
                src_path = os.path.join(src_dir, o)
                dst_path = os.path.join(dst_dir, o)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)


def download(url, output_path):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    filename = url.split('/')[-1]
    resp = requests.get(url, stream=True)
    if resp.status_code == 200:
        file_path = os.path.join(output_path, filename)
        with open(file_path, 'wb') as f:
            resp.raw.decode_content = True
            shutil.copyfileobj(resp.raw, f)
    return filename


def parse_nova_lanuit(start, end, delay):
    print('Night of the %s' % start.isoformat())
    print('Scrapping nova website for track names', end='', flush=True)
    delay = datetime.timedelta(minutes=int(delay))
    scrapper = NovaScrapper(start, end, delay)
    tracks = list(scrapper.tracks.values())
    tracks.sort(key=attrgetter('date'))

    return [t for t in tracks if t.date > start and t.date < end]


def download_pictures(tracks, output_path):
    print('Downloading pictures', end='', flush=True)
    for track in tracks:
        new_url = download(track.picture, os.path.join(output_path, 'pictures'))
        track.picture = 'pictures/%s' % new_url
        print('.', end='', flush=True)


def generate_archive(day, output_path, delay):
    start = datetime.datetime(year=day.year, month=day.month,
                              day=day.day, hour=0, minute=00)

    end = datetime.datetime(year=day.year, month=day.month, day=day.day,
                            hour=6, minute=0)
    tracks = parse_nova_lanuit(start, end, delay)
    download_pictures(tracks, output_path)
    render_tracks(start, tracks, output_path)


def copy_assets(output_path):
    copy(os.path.join(THEME_PATH, 'fonts'), os.path.join(output_path, 'fonts'))
    copy(os.path.join(THEME_PATH, 'assets'), os.path.join(output_path, 'assets'))


def generate_podcast(url, output_path):
    podcast = podcats.Channel(
        root_dir=output_path,
        root_url=url,
        host=None,
        port=443,
        title='Nova la nuit',
        link=None,
    )

    full_path = os.path.join(output_path, 'podcast.xml')
    with codecs.open(full_path, 'w+', encoding='utf-8') as f:
        f.write(podcast.as_xml())


def parse_args():
    def valid_date(s):
        try:
            return datetime.datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            msg = "Not a valid date: '{0}'.".format(s)
            raise argparse.ArgumentTypeError(msg)

    parser = argparse.ArgumentParser(description='Generate nova archive pages.')
    parser.add_argument('--output', dest='output_path',
                        default='output',
                        help='Path where to output the generated files')
    parser.add_argument('--delay', type=int, dest='delay',
                        default=3,
                        help='Delay between the .ogg file and the nova website')

    parser.add_argument('--start-date', type=valid_date, dest='start_date',
                        default=datetime.date.today(),
                        help='Date to create the archive for. If not specified, '
                             'current day will be used')

    parser.add_argument('--end-date', type=valid_date,
                        default=None,
                        help='If specified, all dates between start-date and '
                             'end-date will be scrapped')
    parser.add_argument('--url', dest='url',
                        default='https://nova.notmyidea.org',
                        help='URL of the served files')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.end_date:
        delta = args.end_date - args.start_date
        for i in range(delta.days + 1):
            generate_archive(
                args.start_date + datetime.timedelta(days=i),
                args.output_path,
                args.delay,
            )
            print('')
    else:
        generate_archive(args.start_date, args.output_path, args.delay)
    copy_assets(args.output_path)
    generate_podcast(args.url, args.output_path)
    print('')
