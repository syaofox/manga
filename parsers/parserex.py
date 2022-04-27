"""
利用浏览器打开单张图片下载
"""

import asyncio
import urllib
import os
from numpy import arange

from pyquery import PyQuery as pq
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname, valid_filename
from mods.zipper import Zipper
from playwright.async_api import Page, Response, BrowserContext
from mods.picchecker import PicChecker


class ParserEx:

    def __init__(self) -> None:
        self.semaphore_down = asyncio.Semaphore(5)

    @property
    def name(self):
        return 'base'

    async def login(self, page: Page, url, param=None):
        pass

    def getch_comic_info(self, doc):
        pass

    async def fetch_chapters(self, page, doc):
        pass

    async def parse_main_page(self, browser: BrowserContext, page: Page, url, param=None):
        param['cover_imgdatas'] = {}

        async def handle_response(response: Response):
            await response.finished()
            if response.ok and (response.request.resource_type == "image"):
                imgdata = await response.body()
                Logouter.pic_crawed += 1
                Logouter.crawlog()

                imgdata = await response.body()
                param['cover_imgdatas'][md5(response.url)] = imgdata

        page.on("response", handle_response)
        await page.goto(url, wait_until='domcontentloaded', timeout=100000)
        await page.wait_for_load_state('networkidle')

        html = await page.content()
        doc = pq(html)

        # 基础信息
        name, author, intro, cover_url = self.getch_comic_info(doc)

        Comic.set_comic_name(name)
        Comic.set_author(author)
        Comic.main_url = page.url
        Comic.intro = intro
        Comic.save_to_json()

        if cover_url:
            keystr = md5(cover_url)
            imgdata = param['cover_imgdatas'].get(keystr, None)

            if not imgdata:
                Logouter.red(f'漏网{cover_url}')
                raise Exception(f'下载封面失败={cover_url}')

            cover_fname = os.path.join(Comic.get_full_comicdir(), f'cover.{extrat_extname(cover_url)}')

            with open(cover_fname, 'wb') as f:
                f.write(imgdata)

            if not PicChecker.valid_pic(cover_fname):
                os.remove(cover_fname)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                raise Exception(f'下载失败！下载图片不完整={cover_fname}')

        await self.fetch_chapters(page, doc)

        Logouter.chapter_total = len(Comic.chapters)
        Logouter.crawlog()
        Comic.save_to_json()

    async def parse_chapter_page(self, browser: BrowserContext, page: Page, url, param=None):

        await page.goto(url, wait_until='domcontentloaded', timeout=100000)

        categories_str = valid_filename(f'{param["categories"]}')
        chapter_str = valid_filename(f'{param["chapter"]}')
        chapter_dir = os.path.join(Comic.get_full_comicdir(), categories_str, chapter_str)
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        html = await page.content()
        doc = pq(html)

        await self.fetch_pices(browser, url, chapter_dir, doc, html)

    def down_done(self, fname, data):
        pass

    async def down(self, data, browser, retry=0):

        async with self.semaphore_down:

            fname = data.get('fname', None)
            furl = data.get('url', None)

            if os.path.exists(fname):
                if PicChecker.valid_pic(fname):
                    return
                else:
                    os.remove(fname)

            page: Page = await browser.new_page()
            try:

                response = await page.goto(furl, wait_until='networkidle', timeout=100000)
                status_code = response.status

                if status_code != 200:
                    raise Exception(f'下载失败！状态码={status_code},url={data}')

                imgdata = await response.body()

                with open(fname, 'wb') as fd:
                    fd.write(imgdata)

                if not PicChecker.valid_pic(fname):
                    os.remove(fname)
                    raise Exception(f'下载失败！下载图片不完整={fname}')

                self.down_done(fname=fname, data=data)

            except Exception as e:
                nretry = retry
                nretry += 1
                if nretry <= 5:
                    Logouter.yellow(f'错误:{e},重试={nretry}')
                    await asyncio.sleep(5)
                    await self.down(data, retry=nretry)

                else:
                    Logouter.red(f'错误:{e},重试超过最大次数，下载失败')
                    return

            finally:

                await page.close()