import asyncio
import os
import json
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Response
from mods.classes import Config
from mods.logouter import Logouter
from mods.picchecker import PicChecker
from mods.settings import CHROMIUM_USER_DATA_DIR
from mods.utils import extrat_extname, md5, valid_filename


class Spider:

    def __init__(self, config) -> None:
        self.config: Config = config
        self.semaphore_crawl = asyncio.Semaphore(self.config.ccount)
        self.browser: Optional[BrowserContext] = None
        self.pices_data: dict = {}
        self.cover_imgdatas: dict = {}

        self.comic_name = ''
        self.author = ''
        self.intro = ''
        self.cover_url = ''
        self.chapters: dict = {}

    @property
    def name(self):
        return 'spider'

    @property
    def full_comic_path(self):
        return os.path.join(self.config.maindir, self.config.comic_dir_name)

    async def get_page(self):
        pages = len(self.browser.pages)

        if pages > 0:
            page = self.browser.pages[0]
        else:
            page = await self.browser.new_page()
        return page

    def save_image(self, urlmd5, pic_name):

        if os.path.exists(pic_name):
            if PicChecker.valid_pic(pic_name):
                return True
            else:
                os.remove(pic_name)

        imgdata = self.pices_data.get(urlmd5, None)

        if not imgdata:
            return False

        with open(pic_name, 'wb') as f:
            f.write(imgdata)

        if not PicChecker.valid_pic(pic_name):
            os.remove(pic_name)
            raise Exception(f'下载失败！下载图片不完整={pic_name}')

        return True

    def save_base_info(self):
        if not self.config.comic_dir_name:
            self.config.comic_dir_name = valid_filename(f'[{self.author}]{self.comic_name}' if self.author else self.comic_name)

        # self.full_comic_path = os.path.join(self.config.maindir, self.config.comic_dir_name)

        if not os.path.exists(self.full_comic_path):
            os.makedirs(self.full_comic_path)

        fjson = os.path.join(self.full_comic_path, f'{self.name}.json')

        data = {
            'comic': self.comic_name,
            'url': self.config.comic_url,
            'author': self.author,
            'intro': self.intro,
            'chapters': self.chapters,
        }

        with open(fjson, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def run(self):
        Logouter.blue(f'开始爬取任务,引擎:{self.name}')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start_crawl_task())
        Logouter.blue('信息爬取完成!')

    async def start_crawl_task(self):

        async with async_playwright() as p:
            self.browser = await p.chromium.launch_persistent_context(user_data_dir=CHROMIUM_USER_DATA_DIR, headless=self.config.headless, accept_downloads=True, args=['--disable-blink-features=AutomationControlled'])

            # 首页爬取章节
            try:

                # 爬取基本信息和章节
                page = await self.fetch_comic_info()
                await self.fetch_chapters(page)

                #保存基本信息
                self.save_base_info()

                #下载封面
                cover_fname = os.path.join(self.full_comic_path, f'cover.{extrat_extname(self.cover_url)}')
                self.save_image(md5(self.cover_url), cover_fname)

                # 设置日志
                Logouter.comic_name = self.config.comic_dir_name

                # 爬取各个章节
                async_tasks = []
                for _, chapter in self.chapters.items():
                    async_task = asyncio.create_task(self.fetch_pices(chapter))
                    async_tasks.append(async_task)

                await asyncio.gather(*async_tasks)

            finally:
                self.save_base_info()
                await self.browser.close()

    async def handle_response(self, response: Response):
        if response.ok and response.status == 200 and (response.request.resource_type == "image"):

            try:
                # await response.finished()
                imgdata = await response.body()
                self.pices_data[md5(response.url)] = imgdata
            except Exception as e:
                pass
                # Logouter.red(f'response error{e}={response}')

    async def fetch_comic_info(self, retry=0):
        try:

            page = await self.get_page()
            page.on("response", self.handle_response)
            await self.fetch_comic_info_sub(page)

            return page

        except Exception as e:
            Logouter.yellow(e)
            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{page.url}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_comic_info(retry=nretry)
            else:
                Logouter.red(e)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                Logouter.red(f'页面{page.url}打开错误,重试超过最大次数')

    async def fetch_comic_info_sub(self, page):
        pass

    async def fetch_chapters(self, page):
        self.chapters = self.config.chapters

    async def fetch_pices(self, chapter, retry=0):

        try:
            async with self.semaphore_crawl:
                # 爬取每个章节图片
                categories_str = valid_filename(f'{chapter["categories"]}')
                chapter_str = valid_filename(f'{chapter["title"]}')
                chapter_dir = os.path.join(self.full_comic_path, categories_str, chapter_str)
                test_zip_file = f'{chapter_dir}.zip'

                if chapter['status'] == 1:
                    Logouter.chapter_successed += 1
                    Logouter.crawlog()
                    return

                if os.path.exists(test_zip_file):
                    chapter['status'] = 1
                    return

                chapter_dir = os.path.join(self.full_comic_path, valid_filename(f'{chapter["categories"]}'), valid_filename(f'{chapter["title"]}'))
                if not os.path.exists(chapter_dir):
                    os.makedirs(chapter_dir)

                return await self.fetch_pices_sub(chapter, chapter_dir)

        except Exception as e:
            Logouter.yellow(e)
            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{chapter["url"]}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_pices(chapter, retry=nretry)
            else:
                Logouter.red(e)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                Logouter.red(f'页面{chapter["url"]}打开错误,重试超过最大次数')

    async def fetch_pices_sub(self, chapter):
        pass
