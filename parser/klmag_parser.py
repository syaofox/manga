import asyncio
import urllib
import lzstring
import time
import re
import os

from mods.zipper import Zipper
from parser.parser import Parser
from playwright.async_api import Page
from pyquery import PyQuery as pq
from mods.logouter import Logouter
from mods.utils import extrat_extname, md5


class KlmagParser(Parser):

    @property
    def name(self):
        return 'klmag'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)
        await page.wait_for_selector('div.col-md-4 > div.well.info-cover > img.thumbnail')

        html = await page.content()
        doc = pq(html)

        comic_name = doc('ul.manga-info>h3').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = ''
        intro = '[' + doc('ul.manga-info > li:nth-child(3)').text() + ']' + doc('h3:contains("Description")').siblings('p').text()
        cover_url = doc('div.col-md-4 > div.well.info-cover > img.thumbnail').attr('src')

        for cpt in doc('div.tab-text a.chapter').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.text()
            if not chapters.get(keystr, None):
                chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
        await page.wait_for_selector('div.chapter-content > p > img.chapter-img')

        html = await page.content()
        doc = pq(html)

        els = doc('div.chapter-content > p > img.chapter-img')
        page_count = len(els)
        Logouter.pic_total += page_count
        Logouter.crawlog()

        for i, el in enumerate(els.items()):
            purl = el.attr('data-aload').strip()
            urlmd5 = md5(purl)
            pic_fname = os.path.join(chapter_dir, f'{str(i).zfill(4)}.{extrat_extname(purl)}')

            self.save_image(urlmd5, pic_fname)

        return page_count
