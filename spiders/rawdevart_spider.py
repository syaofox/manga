import os
import urllib

from mods.logouter import Logouter
from mods.utils import extrat_extname, md5
from pyquery import PyQuery as pq
from mods.zipper import Zipper
from spiders.spider import Spider


class RawdevartSpider(Spider):

    @property
    def name(self):
        return 'rawdevart'

    async def fetch_comic_info_sub(self, page):
        await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)
        await page.wait_for_selector('div.manga-top-info > h1.title')

        html = await page.content()
        doc = pq(html)

        self.comic_name = doc('div.manga-top-info > h1.title').text()
        if self.comic_name is None:
            raise Exception('获取漫画名字失败')
        self.author = ''
        self.intro = doc('div.row.manga-body.pb-2 > div.col-lg-3.manga-body-left > table > tbody > tr:nth-child(2)').text()
        self.cover_url = doc('div.row.manga-top > div.col-lg-3.manga-top-img > a > img').attr('src')

    async def fetch_chapters(self, page):
        await super().fetch_chapters(page)

        html = await page.content()
        doc = pq(html)

        for cpt in doc('div.list-group>div.list-group-item>a').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.attr('title')
            if not self.chapters.get(keystr, None):
                self.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(self.chapters)
        Logouter.crawlog()

    async def fetch_pices_sub(self, chapter, chapter_dir):

        page = await self.get_page()

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

            if self.save_image(urlmd5, pic_fname):
                Logouter.pic_crawed += 1
                Logouter.crawlog()
                if self.pices_data.get(urlmd5, None):
                    self.pices_data.pop(urlmd5)

        downloaded_count = Zipper.count_dir(chapter_dir)
        if downloaded_count == page_count:
            Zipper.zip(chapter_dir)
            self.chapters[md5(chapter['url'])]['status'] = 1
            Logouter.chapter_successed += 1
            Logouter.crawlog()
            self.save_base_info()
