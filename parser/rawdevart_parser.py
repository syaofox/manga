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


class RawdevartParser(Parser):

    @property
    def name(self):
        return 'rawdevart'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)
        await page.wait_for_selector('div.manga-top-info > h1.title')

        html = await page.content()
        doc = pq(html)

        comic_name = doc('div.manga-top-info > h1.title').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = ''
        intro = doc('div.row.manga-body.pb-2 > div.col-lg-3.manga-body-left > table > tbody > tr:nth-child(2)').text()
        cover_url = doc('div.row.manga-top > div.col-lg-3.manga-top-img > a > img').attr('src')

        for cpt in doc('div.list-group>div.list-group-item>a').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.attr('title')
            if not chapters.get(keystr, None):
                chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)

        html = await page.content()
        doc = pq(html)

        els = doc('#img-container > div > img')
        page_count = len(els)
        Logouter.pic_total += page_count
        Logouter.crawlog()

        # await page.keyboard.press('End')
        await page.evaluate("document.querySelectorAll('#img-container > div > img[data-src]').length == 0")

        for i, el in enumerate(els.items()):
            purl = el.attr('src').strip()
            urlmd5 = md5(purl)
            pic_fname = os.path.join(chapter_dir, f'{str(i).zfill(4)}.{extrat_extname(purl)}')

            self.save_image(urlmd5, pic_fname)

        return page_count
