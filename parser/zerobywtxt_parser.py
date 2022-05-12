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


class ZerobywtxtParser(Parser):

    @property
    def name(self):
        return 'zerobywtxt'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)
        # await page.wait_for_selector('div.manga-top-info > h1.title')

        html = await page.content()
        doc = pq(html)

        # 检测是否登录
        await page.wait_for_selector("a:text-is('退出')", timeout=300000)

        comic_name = doc('#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-expand > div > ul.uk-switcher.uk-margin.pl0.mt5 > li > h3').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = doc(
            '#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-expand > div > ul.uk-switcher.uk-margin.pl0.mt5 > li > div:nth-child(2) > a:nth-child(1)'
        ).text().replace('作者:', '')

        intro = doc(
            '#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-expand > div > ul.uk-switcher.uk-margin.pl0.mt5 > li > div.uk-alert.xs2.mt5.mb5.pt5.pb5'
        ).text()
        cover_url = doc('#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-medium.uk-first-column > img').attr('src')

        for cpt in doc('#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div.uk-grid-collapse.uk-child-width-1-4.uk-grid > div > a').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.text()
            if not chapters.get(keystr, None):
                chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        await page.goto(chapter['url'], wait_until='networkidle', timeout=500000)

        html = await page.content()
        doc = pq(html)

        els = doc('#jameson_manhua > div.uk-zjimg.uk-text-center.uk-padding.uk-margin-top.uk-margin-bottom.uk-inline.xiala2 > div > img')
        if not els:
            els = doc('#jameson_manhua > div.uk-margin-top > div.uk-zjimg.uk-text-center.uk-padding.uk-margin-top.uk-margin-bottom.uk-inline > div > img')
        page_count = len(els)
        Logouter.pic_total += page_count
        Logouter.crawlog()

        purls = {}

        for i, el in enumerate(els.items()):
            purl = el.attr('src').strip()
            urlmd5 = md5(purl)
            pic_fname = os.path.join(chapter_dir, f'{str(i).zfill(4)}.{extrat_extname(purl)}')
            purls[urlmd5] = pic_fname

        downlaoded = 0
        page_heigh = await page.evaluate('document.body.scrollHeight')

        current_pos = 0
        incer = 1000

        while True:
            for urlmd5, pic_fname in purls.copy().items():
                if self.save_image(urlmd5, pic_fname):
                    downlaoded += 1
                    purls.pop(urlmd5)

            current_pos += 1
            await page.evaluate(f"var q=document.documentElement.scrollTop={current_pos * incer}")
            await asyncio.sleep(0.2)

            if current_pos * incer > (page_heigh - incer):
                current_pos = 0

            if downlaoded == page_count:
                break

        return page_count
