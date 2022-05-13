import asyncio
import urllib
import os

from parser.parser import Parser
from playwright.async_api import Page
from pyquery import PyQuery as pq
from mods.logouter import Logouter
from mods.utils import extrat_extname, md5


class BaozimhParser(Parser):

    @property
    def name(self):
        return 'Baozimh'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)

        html = await page.content()
        doc = pq(html)

        comic_name = doc('h1.comics-detail__title').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = doc('h2.comics-detail__author').text()
        intro = doc('p.comics-detail__desc').text()
        cover_url = doc(f'img[alt="{comic_name}"]').attr('src')

        for cpt in doc('#chapters_other_list>div>a').items():

            url = urllib.parse.urljoin(page.url, cpt.attr('href'))
            keystr = md5(url)
            title = cpt.text()

            if not chapters.get(keystr, None):
                chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)

        html = await page.content()
        doc = pq(html)

        els = doc('div.chapter-main.scroll-mode > section > amp-img')
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
