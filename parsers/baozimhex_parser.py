import asyncio
import urllib
import os

from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname
from mods.zipper import Zipper

from parsers.parserex import ParserEx


class BaozimhexParser(ParserEx):

    def __init__(self) -> None:
        self.semaphore_down = asyncio.Semaphore(10)

    @property
    def name(self):
        return 'baozimhex'

    async def fetch_chapters(self, page, doc):
        await page.locator('#button_show_all_chatper').click()

        for el in doc('#chapter-items>div>a').items():
            url = urllib.parse.urljoin(page.url, el.attr('href'))
            title = el.text()
            keystr = md5(url)
            if not Comic.chapters.get(keystr, None):
                Comic.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        for el in doc('#chapters_other_list>div>a').items():
            url = urllib.parse.urljoin(page.url, el.attr('href'))
            title = el.text()
            keystr = md5(url)
            if not Comic.chapters.get(keystr, None):
                Comic.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

    def getch_comic_info(self, doc):
        name = doc('h1.comics-detail__title').text()
        if name is None:
            raise Exception('获取漫画名字失败')

        author = doc('h2.comics-detail__author').text()
        intro = doc('p.comics-detail__desc').text()

        cover_url = doc(f'img[alt="{name}"]').attr('src')
        return name, author, intro, cover_url

    async def fetch_pices(self, browser, url, chapter_dir, doc, html):
        els = doc('div.chapter-main.scroll-mode > section > amp-img')
        pices_total_num = len(els)
        Logouter.pic_total += pices_total_num
        Logouter.crawlog()

        down_tasks = []

        for i, el in enumerate(els.items()):
            purl = el.attr('src').strip()
            pic_fname = os.path.join(chapter_dir, f'{str(i).zfill(4)}.{extrat_extname(purl)}')
            pic = {'url': purl, 'fname': pic_fname}

            down_task = asyncio.create_task(self.down(pic, browser))
            down_tasks.append(down_task)

        await asyncio.gather(*down_tasks)

        downloaded_count = Zipper.count_dir(chapter_dir)
        if downloaded_count == pices_total_num:
            Zipper.zip(chapter_dir)
            Comic.chapters[md5(url)]['status'] = 1
            Comic.save_to_json()
