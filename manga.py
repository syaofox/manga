import fire
import json
import os

from mods.classes import Config
from mods.logouter import Logouter
from mods.settings import DOWNLOADS_DIR
from spiders.baozimh_spider import BaozimhSpider
from spiders.comic18_spider import Comic18Spider
from spiders.klmag_spider import KlmagSpider
from spiders.manhuagui_spider import ManhuaguiSpider
from spiders.rawdevart_spider import RawdevartSpider
from spiders.senmanga_spider import SenmangaSpider


def parse_start_url(start_url):
    comic_url = start_url
    maindir = DOWNLOADS_DIR
    comic_dir_name = ''
    chapters = {}

    if start_url.endswith('json'):
        with open(start_url, 'r', encoding='utf-8') as load_f:
            jdata = json.load(load_f)

            comic_url = jdata.get('url', None)
            maindir = os.path.dirname(os.path.dirname(start_url))
            comic_dir_name = os.path.basename(os.path.dirname(start_url))
            chapters = jdata.get('chapters', {})

    return comic_url, maindir, comic_dir_name, chapters


def start_craw(start_url, headless=False, szip=False):

    comic_url, maindir, comic_dir_name, chapters = parse_start_url(start_url)
    if not comic_url:
        Logouter.red(f'起始地址错误={comic_url}')
        return

    config = Config(comic_url, maindir, comic_dir_name, chapters, ccount=1, headless=headless)

    if ('manhuagui' in comic_url) or ('mhgui' in comic_url):
        spider = ManhuaguiSpider(config=config)
    elif '18comic' in comic_url:
        spider = Comic18Spider(config=config)
    elif ('klmag' in comic_url) or ('klmanga' in comic_url):
        spider = KlmagSpider(config=config)
    elif 'baozimh' in comic_url:
        spider = BaozimhSpider(config=config)
    elif 'senmanga' in comic_url:
        spider = SenmangaSpider(config=config)
    elif 'rawdevart' in comic_url:
        spider = RawdevartSpider(config=config)

    spider.run()


if __name__ == "__main__":
    fire.Fire(start_craw)
