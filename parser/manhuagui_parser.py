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


class ManhuaguiParser(Parser):

    @property
    def name(self):
        return 'manhuagui'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)

        await page.wait_for_selector("a:text-is('註銷')", timeout=300000)

        html = await page.content()
        doc = pq(html)

        comic_name = doc('div.book-title>h1').text()
        if comic_name is None:
            raise Exception('获取漫画名字失败')
        author = doc('div.book-detail.pr.fr > ul> li:nth-child(2)>span:nth-child(2)> a').text()
        intro = doc('#intro-cut').text()
        cover_url = urllib.parse.urljoin(page.url, doc('p.hcover > img').attr('src'))

        if await page.query_selector('#__VIEWSTATE'):
            lzstrings = doc('#__VIEWSTATE').attr('value')
            deslzstring = lzstring.LZString().decompressFromBase64(lzstrings)
            doc = pq(deslzstring)
            chapter_divs = doc('div.chapter-list')
            heads = [el.text() for el in doc('h4').items()]
        else:
            await page.wait_for_selector('div.chapter>div.chapter-list')
            chapter_divs = doc('div.chapter>div.chapter-list')
            heads = [el.text() for el in doc('body > div.w998.bc.cf> div.fl.w728 > div.chapter.cf.mt16 > h4').items()]

        for i, chapter_div in enumerate(chapter_divs.items()):
            els = chapter_div('li>a')
            categories = heads[i] if heads else ''

            for el in els.items():
                url = urllib.parse.urljoin(page.url, el.attr('href'))
                keystr = md5(url)

                chapterdata = chapters.get(keystr, None)
                if not chapterdata:
                    title = f"{el.attr('title')}({el('span>i').text()})"
                    chapters[keystr] = {'categories': categories, 'title': title, 'url': url, 'status': 0}

        return comic_name, author, intro, cover_url

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        await super().parse_chapter_pices(page, chapter, chapter_dir)

        # 点击显示成人内容
        if await page.query_selector('#checkAdult'):
            await page.click('#checkAdult')

        start_time = time.time()

        purls = {}
        cur_idx = -1

        while True:
            if cur_idx < 0:
                await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
            else:
                await page.locator('#next').click()
                # 等待图片加载完成
            await page.wait_for_selector('#imgLoading', state='hidden')

            html = await page.content()
            doc = pq(html)

            count_info = doc('body > div.w980.title > div:nth-child(2) > span').text()
            idxs = re.search(r'\((\d+)/(\d+)\)', count_info)
            cur_idx = int(idxs.group(1))
            page_count = int(idxs.group(2))

            if cur_idx == 1:
                Logouter.pic_total += page_count
                Logouter.crawlog()

            purl = doc('#mangaFile').attr('src')

            #https://i.hamreus.com/ps1/t/tunshirenjian/origin90(下)/14.jpg.webp?e=1654878550&m=6yu3viVowUUstmQOZ_heBg
            purl = urllib.parse.quote(purl, safe="[];/?:@&=+$,%()")

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
