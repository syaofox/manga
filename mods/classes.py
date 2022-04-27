class Config:

    def __init__(self, parser_name, ccount=1, headless=False, checklogin=False) -> None:
        """_summary_

        Args:

            ccount (int, optional): 爬取线程数. Defaults to 1.
            dcount (int, optional): 下载线程数. Defaults to 1.
            headless (bool, optional): 无头模式. Defaults to False.
            szip (bool, optional): 跳过压缩. Defaults to False.
            fzip (bool, optional): 强制压缩. Defaults to False.           
        """

        self.parser_name = parser_name
        self.ccount = ccount

        self.headless = headless
        self.checklogin = checklogin