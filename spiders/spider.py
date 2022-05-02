import asyncio
import os
from playwright.async_api import Error, async_playwright, BrowserContext, Response

from mods.classes import Config
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.settings import CHROMIUM_USER_DATA_DIR
from mods.utils import valid_filename


class Spider:

    def __init__(self, config, parser) -> None:
        self.config: Config = config
        self.parser = parser
        self.semaphore_crawl = asyncio.Semaphore(self.config.ccount)

    def run(self):
        Logouter.blue(f'开始爬取任务,引擎:{self.parser.name}')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start_crawl_task())
        Logouter.blue('信息爬取完成!')

    async def parse_chapters(self, chapter, context):
        async with self.semaphore_crawl:
            # 爬取每个章节图片
            categories_str = valid_filename(f'{chapter["categories"]}')
            chapter_str = valid_filename(f'{chapter["title"]}')

            chapter_dir = os.path.join(Comic.get_full_comicdir(), categories_str, chapter_str)
            test_zip_file = f'{chapter_dir}.zip'

            if os.path.exists(test_zip_file):
                chapter['status'] = 1
                Logouter.chapter_successed += 1
                Logouter.crawlog()

            if chapter['status'] == 0:

                #{'categories': '單話', 'title': '第13話(19p)', 'url': 'https://tw.manhuagui.com/comic/36962/550128.html', 'status': 0}
                await self.fetch_page(chapter['url'], context, self.parser.parse_chapter_page, param={'url': chapter['url'], 'categories': categories_str, 'chapter': chapter_str})

                Logouter.chapter_successed += 1
                Logouter.crawlog()

    async def start_crawl_task(self):

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(user_data_dir=CHROMIUM_USER_DATA_DIR, headless=self.config.headless, accept_downloads=True, args=['--disable-blink-features=AutomationControlled'])

            # 首页爬取章节
            try:
                if self.config.checklogin:
                    await self.fetch_page(Comic.main_url, browser, self.parser.login, param={})

                await self.fetch_page(Comic.main_url, browser, self.parser.parse_main_page, param={})

                # 日志
                Logouter.comic_name = Comic.gen_comicdir()
                Logouter.crawlog()

                async_tasks = []

                for _, chapter in Comic.chapters.items():
                    async_task = asyncio.create_task(self.parse_chapters(chapter, browser))
                    async_tasks.append(async_task)

                await asyncio.gather(*async_tasks)

            finally:
                Comic.save_to_json()
                await browser.close()

    async def fetch_page(self, url, browser: BrowserContext, parse_method, retry=0, param=None):

        # pages = len(browser.pages)

        # if pages > 0:
        #     page = browser.pages[0]
        # else:
        page = await browser.new_page()

        try:
            await parse_method(browser, page, url, param)

        except (Error, AttributeError) as e:

            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{url}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_page(url, browser=browser, parse_method=parse_method, retry=nretry, param=param)
            else:
                Logouter.red(e.message)
                Logouter.red(f'页面{url}打开错误,重试超过最大次数')

        finally:
            await page.close()