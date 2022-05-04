class Config:

    def __init__(self, comic_url, maindir, comic_dir_name, chapters, ccount=1, headless=False, checklogin=False) -> None:
        """_summary_

        Args:

            ccount (int, optional): 爬取线程数. Defaults to 1.
            dcount (int, optional): 下载线程数. Defaults to 1.
            headless (bool, optional): 无头模式. Defaults to False.
            szip (bool, optional): 跳过压缩. Defaults to False.
            fzip (bool, optional): 强制压缩. Defaults to False.           
        """

        self.ccount = ccount

        self.headless = headless
        self.checklogin = checklogin
        self.comic_url = comic_url
        self.maindir = maindir
        self.comic_dir_name = comic_dir_name
        self.chapters = chapters
