from parser.parser import Parser
from playwright.async_api import Page
from pyquery import PyQuery as pq
import urllib
import lzstring

from mods.logouter import Logouter
from mods.utils import extrat_extname, md5


class ManhuaguiParser(Parser):

    @property
    def name(self):
        return 'manhuagui'

    async def parse_comic_info(self, comic_url, page: Page, chapters):

        await page.goto(comic_url, wait_until='networkidle', timeout=100000)

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
