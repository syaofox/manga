import asyncio
import urllib
import time
import re
import os

from mods.zipper import Zipper
from parser.parser import Parser
from playwright.async_api import Page
from pyquery import PyQuery as pq
from mods.logouter import Logouter
from mods.utils import extrat_extname, md5


class XmanhuaParser(Parser):

    @property
    def name(self):
        return 'xmanhua'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)

        html = await page.content()
        doc = pq(html)

        comic_name = doc('p.detail-info-title').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = doc('p.detail-info-tip > span:nth-child(1) > a').text()
        intro = doc('p.detail-info-content').text()
        cover_url = urllib.parse.urljoin(page.url, doc('body > div.detail-info-1 > div > div > img.detail-info-cover').attr('src'))

        els = doc('#chapterlistload > a')

        for el in els.items():
            url = urllib.parse.urljoin(page.url, el.attr('href'))
            keystr = md5(url)

            chapterdata = chapters.get(keystr, None)
            if not chapterdata:
                title = el.text()
                chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        start_time = time.time()

        purls = {}
        cur_idx = -1

        while True:
            if cur_idx < 0:
                await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
            else:
                await page.locator('#cp_image').click()
                # 等待图片加载完成
            await page.wait_for_selector('#imgLoading', state='hidden')
            await page.wait_for_selector('#cp_image')

            html = await page.content()
            doc = pq(html)

            count_info = doc('body > div.reader-bottom > div > a').text()  #'頁碼 1/22'
            idxs = re.search(r'頁碼 (\d+)/(\d+)', count_info)
            cur_idx = int(idxs.group(1))
            page_count = int(idxs.group(2))

            if cur_idx == 1:
                Logouter.pic_total += page_count
                Logouter.crawlog()

            purl = doc('#cp_image').attr('src')
            # purl = urllib.parse.quote(purl, safe="[];/?:@&=+$,%")
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

        cost_time = time.time() - start_time
        await asyncio.sleep(5 - cost_time)
        return page_count
