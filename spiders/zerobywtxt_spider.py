import asyncio
import os
import urllib

from mods.logouter import Logouter
from mods.utils import extrat_extname, md5
from pyquery import PyQuery as pq
from mods.zipper import Zipper
from spiders.spider import Spider
from playwright.async_api import Page


class ZerobywtxtSpider(Spider):

    @property
    def name(self):
        return 'zerobywtxt'

    # def islogin(self, doc: pq):
    #     return not doc('a:contains("退出")')

    async def fetch_comic_info_sub(self, page: Page):
        await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)
        # await page.wait_for_selector('div.manga-top-info > h1.title')

        html = await page.content()
        doc = pq(html)

        # 检测是否登录
        await page.wait_for_selector("a:text-is('退出')", timeout=300000)

        self.comic_name = doc('#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-expand > div > ul.uk-switcher.uk-margin.pl0.mt5 > li > h3').text()
        if self.comic_name is None:
            raise Exception('获取漫画名字失败')
        self.author = doc(
            '#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-expand > div > ul.uk-switcher.uk-margin.pl0.mt5 > li > div:nth-child(2) > a:nth-child(1)'
        ).text().replace('作者:', '')

        self.intro = doc(
            '#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-expand > div > ul.uk-switcher.uk-margin.pl0.mt5 > li > div.uk-alert.xs2.mt5.mb5.pt5.pb5'
        ).text()
        self.cover_url = doc('#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div:nth-child(1) > div.uk-width-medium.uk-first-column > img').attr('src')

    async def fetch_chapters(self, page):
        await super().fetch_chapters(page)

        html = await page.content()
        doc = pq(html)

        for cpt in doc('#jameson_manhua > div.bofangwrap.rootcate.uk-margin-top.uk-grid-collapse.uk-grid > div.uk-width-expand.uk-first-column > div.uk-grid-collapse.uk-child-width-1-4.uk-grid > div > a').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.text()
            if not self.chapters.get(keystr, None):
                self.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(self.chapters)
        Logouter.crawlog()

    async def fetch_pices_sub(self, chapter, chapter_dir):

        page = await self.get_page()

        await page.goto(chapter['url'], wait_until='networkidle', timeout=500000)

        html = await page.content()
        doc = pq(html)

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
