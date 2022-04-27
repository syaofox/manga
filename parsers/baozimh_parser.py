import asyncio
import re
import urllib
import lzstring
import os
import math
from pyquery import PyQuery as pq
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname, extrat_fname, valid_filename
from mods.zipper import Zipper
from parsers.parser import Parser
from playwright.async_api import Page, Response, Error, BrowserContext
from mods.picchecker import PicChecker
from PIL import Image


class BaozimhParser(Parser):

    @property
    def name(self):
        return 'baozimh'

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
        name = doc('h1.comics-detail__title').text()
        if name is None:
            raise Exception('获取漫画名字失败')

        author = doc('h2.comics-detail__author').text()
        intro = doc('p.comics-detail__desc').text()

        cover_url = doc(f'img[alt="{name}"]').attr('src')

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

        Logouter.chapter_total = len(Comic.chapters)
        Logouter.crawlog()
        Comic.save_to_json()

    async def parse_chapter_page(self, browser: BrowserContext, page: Page, url, param=None):

        param['chapter_url'] = url
        categories_str = valid_filename(f'{param["categories"]}')
        chapter_str = valid_filename(f'{param["chapter"]}')
        chapter_dir = os.path.join(Comic.get_full_comicdir(), categories_str, chapter_str)

        param['chapter_dir'] = chapter_dir
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        param['pices_count'] = 0
        param['pices_datas'] = {}

        param['busy'] = True

        async def handle_response(response: Response):
            await response.finished()
            if response.ok:
                if (response.request.resource_type == "image"):

                    Logouter.pic_crawed += 1
                    Logouter.crawlog()

                    # 保存页面上的图像数据
                    imgdata = await response.body()
                    param['pices_datas'][md5(response.url)] = imgdata

        # 首次访问获得图片地址
        page.on("response", handle_response)
        await page.goto(url, wait_until='networkidle', timeout=100000)

        await page.keyboard.press("Home")
        await page.wait_for_load_state('networkidle')

        await page.wait_for_load_state('networkidle')
        html = await page.content()

        doc = pq(html)
        els = doc('div.chapter-main.scroll-mode > section > amp-img')
        param['pices_count'] = len(els)
        Logouter.pic_total += param['pices_count']
        Logouter.crawlog()

        cur_pos = 0

        # 判断是否所有图片都缓存到
        while True:
            allparsed = True
            for el in els.items():
                purl = el.attr('src').strip()
                keystr = md5(purl)
                if not keystr in param['pices_datas'].keys():
                    allparsed = False
                    break
            if allparsed:
                break

            cur_pos = min(param['pices_count'], cur_pos)
            await page.evaluate(f"window.scrollTo(0, {cur_pos*2000});")

            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(0.3)
            cur_pos += 1
            #

            if cur_pos >= param['pices_count']:
                cur_pos = 1

        await page.wait_for_load_state('networkidle')

        for i, el in enumerate(els.items()):
            purl = el.attr('src').strip()
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
