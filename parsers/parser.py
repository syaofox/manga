"""
截获浏览器页面图片请求
"""
import os

from pyquery import PyQuery as pq
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.picchecker import PicChecker
from mods.utils import extrat_extname, extrat_fname, valid_filename
from playwright.async_api import Page, Error, Response


class Parser:

    @property
    def name(self):
        return 'base'

    async def login(self, page: Page, url, param=None):
        pass
