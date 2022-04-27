import asyncio
import re
import urllib
import lzstring
import os

from pyquery import PyQuery as pq
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname, extrat_fname, valid_filename
from mods.zipper import Zipper
from parsers.parser import Parser
from playwright.async_api import Page, Response, Error
from mods.picchecker import PicChecker


class KlmagPaser(Parser):

    @property
    def name(self):
        return 'klmag'

    async def parse_main_page(self, page: Page, url, param=None):
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
        await page.wait_for_selector('div.col-md-4 > div.well.info-cover > img.thumbnail')
        await page.wait_for_load_state('networkidle')

        html = await page.content()
        doc = pq(html)

        # 基础信息
        name = doc('ul.manga-info>h3').text()
        if name is None:
            raise Exception('获取漫画名字失败')

        author = ''
        intro = doc('h3:contains("Description")').siblings('p').text()
        cover_url = doc('div.col-md-4 > div.well.info-cover > img.thumbnail').attr('src')

        Comic.set_comic_name(name)
        Comic.set_author(author)
        Comic.main_url = page.url
        Comic.intro = intro
        Comic.save_to_json()

        # 注意comic获得信息后才允许
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

        for cpt in doc('div.tab-text a.chapter').items():

            url = cpt.attr('href')
            url = urllib.parse.urljoin(page.url, url)
            keystr = md5(url)

            title = cpt.text()
            if not Comic.chapters.get(keystr, None):
                Comic.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(Comic.chapters)
        Logouter.crawlog()
        Comic.save_to_json()

    async def parse_chapter_page(self, page: Page, url, param=None):
        param['chapter_url'] = url
        categories_str = valid_filename(f'{param["categories"]}')
        chapter_str = valid_filename(f'{param["chapter"]}')
        chapter_dir = os.path.join(Comic.get_full_comicdir(), categories_str, chapter_str)

        param['chapter_dir'] = chapter_dir
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        param['pices_count'] = 0
        param['pices_datas'] = {}

        async def handle_response(response: Response):
            await response.finished()
            if response.ok:
                if (response.request.resource_type == "image"):

                    Logouter.pic_crawed += 1
                    Logouter.crawlog()

                    # 保存页面上的图像数据
                    imgdata = await response.body()
                    param['pices_datas'][md5(response.url)] = imgdata

        page.on("response", handle_response)
        await page.goto(url, wait_until='networkidle', timeout=100000)
        await page.wait_for_load_state('networkidle')

        html = await page.content()
        doc = pq(html)

        els = doc('div.chapter-content > p > img.chapter-img')
        param['pices_count'] = len(els)
        Logouter.pic_total += param['pices_count']
        Logouter.crawlog()

        for i, el in enumerate(els.items()):
            purl = el.attr('data-aload').strip()
            pic_fname = os.path.join(param['chapter_dir'], f'{str(i).zfill(4)}.{extrat_extname(purl)}')
            if os.path.exists(pic_fname):
                if PicChecker.valid_pic(pic_fname):
                    continue
                else:
                    os.remove(pic_fname)

            keystr = md5(purl)
            imgdata = param['pices_datas'].get(keystr, None)
            if not imgdata:
                Logouter.red(f'漏网{purl}')
                continue

            with open(pic_fname, 'wb') as f:
                f.write(imgdata)

            if not PicChecker.valid_pic(pic_fname):
                os.remove(pic_fname)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                raise Exception(f'下载失败！下载图片不完整={pic_fname}')

        downloaded_count = Zipper.count_dir(param['chapter_dir'])
        if downloaded_count == param['pices_count']:
            Zipper.zip(param['chapter_dir'])
            Comic.chapters[md5(url)]['status'] = 1
            Comic.save_to_json()
