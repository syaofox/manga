import asyncio
import os
import urllib

from mods.logouter import Logouter
from mods.utils import extrat_extname, md5
from pyquery import PyQuery as pq
from mods.zipper import Zipper
from spiders.spider import Spider


class BaozimhSpider(Spider):

    @property
    def name(self):
        return 'Baozimh'

    async def fetch_comic_info_sub(self, page):
        await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)

        html = await page.content()
        doc = pq(html)

        self.comic_name = doc('h1.comics-detail__title').text()
        if self.comic_name is None:
            raise Exception('获取漫画名字失败')
        self.author = doc('h2.comics-detail__author').text()
        self.intro = doc('p.comics-detail__desc').text()
        self.cover_url = doc(f'img[alt="{self.comic_name}"]').attr('src')

    async def fetch_chapters(self, page):
        await super().fetch_chapters(page)

        html = await page.content()
        doc = pq(html)

        for cpt in doc('#chapters_other_list>div>a').items():

            url = urllib.parse.urljoin(page.url, cpt.attr('href'))
            keystr = md5(url)
            title = cpt.text()

            if not self.chapters.get(keystr, None):
                self.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(self.chapters)
        Logouter.crawlog()

    async def fetch_pices_sub(self, chapter, chapter_dir):

        page = await self.get_page()

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
                    Logouter.pic_crawed += 1
                    downlaoded += 1
                    Logouter.crawlog()
                    if self.pices_data.get(urlmd5, None):
                        self.pices_data.pop(urlmd5)
                    purls.pop(urlmd5)

            current_pos += 1
            await page.evaluate(f"var q=document.documentElement.scrollTop={current_pos * incer}")
            await asyncio.sleep(0.2)

            if current_pos * incer > (page_heigh - incer):
                current_pos = 0

            if downlaoded == page_count:
                break

        downloaded_count = Zipper.count_dir(chapter_dir)
        if downloaded_count == page_count:
            Zipper.zip(chapter_dir)
            self.chapters[md5(chapter['url'])]['status'] = 1
            Logouter.chapter_successed += 1
            Logouter.crawlog()
            self.save_base_info()
