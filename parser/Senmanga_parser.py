import os

from mods.zipper import Zipper
from parser.parser import Parser
from playwright.async_api import Page
from pyquery import PyQuery as pq
from mods.logouter import Logouter
from mods.utils import extrat_extname, md5


class SenmangaParser(Parser):

    @property
    def name(self):
        return 'senmanga'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)
        await page.wait_for_selector('div.series-desc > div.desc > h1.series')

        html = await page.content()
        doc = pq(html)

        comic_name = doc('div.series-desc > div.desc > h1.series').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = doc('div.series-desc > div.desc > div.info > div:nth-child(3) > a').text()
        intro = doc('div.series-desc > div.desc > div.alt-name').text()
        cover_url = doc('div.series-desc > div.thumbook > div.cover > img').attr('src')

        for el in doc('ul.chapter-list > li > a').items():
            categories = '连载'
            url = el.attr('href')
            keystr = md5(url)

            chapterdata = chapters.get(keystr, None)
            if not chapterdata:
                title = el.text()
                chapters[keystr] = {'categories': categories, 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        purls = {}
        cur_idx = -1

        while True:
            if cur_idx < 0:
                await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
            else:
                # await page.locator('text=Next Page').click()
                await page.keyboard.press('ArrowRight')
                # 等待图片加载完成

            await page.wait_for_selector('body > div.reader.text-center > a > img')

            html = await page.content()
            doc = pq(html)

            page_els = doc('select[name="page"]')
            for page_el in page_els.items():

                cur_idx = int(page_el('option[selected]').text())
                page_count = len(page_el('option'))
                break

            if cur_idx == 1:
                Logouter.pic_total += page_count
                Logouter.crawlog()

            purl = doc('body > div.reader.text-center > a > img').attr('src')

            purls[md5(purl)] = os.path.join(chapter_dir, f'{str(cur_idx).zfill(4)}.{extrat_extname(purl)}')

            for urlmd5, pic_fname in purls.copy().items():
                if self.save_image(urlmd5, pic_fname):
                    purls.pop(urlmd5)

            if cur_idx >= page_count:  # len(purls) >= page_count:
                downloaded_count = Zipper.count_dir(chapter_dir)
                if downloaded_count >= page_count:
                    break
                else:
                    cur_idx = 1
                    await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
        return page_count
