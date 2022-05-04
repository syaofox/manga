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


class ManhuaguiSpider(WSpider):

    @property
    def name(self):
        return 'manhuagui'

    async def fetch_comic_info_sub(self, page):
        await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)

        html = await page.content()
        doc = pq(html)

        self.comic_name = doc('div.book-title>h1').text()
        if self.comic_name is None:
            raise Exception('获取漫画名字失败')
        self.author = doc('div.book-detail.pr.fr > ul> li:nth-child(2)>span:nth-child(2)> a').text()
        self.intro = doc('#intro-cut').text()
        self.cover_url = urllib.parse.urljoin(page.url, doc('p.hcover > img').attr('src'))

    async def fetch_chapters(self, page):

        html = await page.content()
        doc = pq(html)

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

                chapterdata = self.chapters.get(keystr, None)
                if not chapterdata:
                    title = f"{el.attr('title')}({el('span>i').text()})"
                    self.chapters[keystr] = {'categories': categories, 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(self.chapters)
        Logouter.crawlog()

    async def fetch_pices_sub(self, chapter):
        categories_str = valid_filename(f'{chapter["categories"]}')
        chapter_str = valid_filename(f'{chapter["title"]}')
        chapter_dir = os.path.join(self.full_comic_path, categories_str, chapter_str)
        test_zip_file = f'{chapter_dir}.zip'

        if os.path.exists(test_zip_file):
            chapter['status'] = 1

        if chapter['status'] == 1:
            Logouter.chapter_successed += 1
            Logouter.crawlog()
            return

        chapter_dir = os.path.join(self.full_comic_path, valid_filename(f'{chapter["categories"]}'), valid_filename(f'{chapter["title"]}'))
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        async def handle_response(response: Response):
            if response.ok:
                if (response.request.resource_type == "image"):
                    # 保存页面上的图像数据
                    await response.finished()
                    imgdata = await response.body()
                    self.pices_data[md5(response.url)] = imgdata

        page = await self.get_page()
        page.on("response", handle_response)
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
            purl = urllib.parse.quote(purl, safe="[];/?:@&=+$,%")
            purls[md5(purl)] = os.path.join(chapter_dir, f'{str(cur_idx).zfill(4)}.{extrat_extname(purl)}')

            for urlmd5, pic_fname in purls.copy().items():
                if self.save_image(urlmd5, pic_fname):
                    Logouter.pic_crawed += 1
                    Logouter.crawlog()
                    self.pices_data.pop(urlmd5)
                    purls.pop(urlmd5)

            if cur_idx >= page_count:  # len(purls) >= page_count:
                downloaded_count = Zipper.count_dir(chapter_dir)
                if downloaded_count >= page_count:
                    break
                else:
                    cur_idx = 1
                    await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)

        downloaded_count = Zipper.count_dir(chapter_dir)
        if downloaded_count == page_count:
            Zipper.zip(chapter_dir)
            self.chapters[md5(chapter['url'])]['status'] = 1
            Logouter.chapter_successed += 1
            Logouter.crawlog()
            self.save_base_info()
