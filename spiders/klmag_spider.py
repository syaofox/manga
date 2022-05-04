import os
import re
import urllib
import lzstring
from playwright.async_api import Response
from mods.logouter import Logouter
from mods.utils import extrat_extname, md5, valid_filename
from pyquery import PyQuery as pq
from mods.zipper import Zipper
from spiders.wspider import WSpider


class KlmagSpider(WSpider):

    @property
    def name(self):
        return 'klmang'

    async def fetch_comic_info_sub(self, page):
        await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)
        await page.wait_for_selector('div.col-md-4 > div.well.info-cover > img.thumbnail')

        html = await page.content()
        doc = pq(html)

        self.comic_name = doc('ul.manga-info>h3').text()
        if self.comic_name is None:
            raise Exception('获取漫画名字失败')
        self.author = ''
        self.intro =  '[' + doc('ul.manga-info > li:nth-child(3)').text()\
            + ']' +doc('h3:contains("Description")').siblings('p').text()

        self.cover_url = doc('div.col-md-4 > div.well.info-cover > img.thumbnail').attr('src')

    async def fetch_chapters(self, page):
        await super().fetch_chapters(page)

        html = await page.content()
        doc = pq(html)

        for cpt in doc('div.tab-text a.chapter').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.text()
            if not self.chapters.get(keystr, None):
                self.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(self.chapters)
        Logouter.crawlog()

    async def fetch_pices_sub(self, chapter, chapter_dir):

        async def handle_response(response: Response):
            if response.ok:
                if (response.request.resource_type == "image"):
                    # 保存页面上的图像数据
                    await response.finished()
                    imgdata = await response.body()
                    self.pices_data[md5(response.url)] = imgdata

        page = await self.get_page()
        page.on("response", handle_response)
        await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)

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
