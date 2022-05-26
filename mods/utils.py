import os
import re
import hashlib


def md5(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def valid_filename(file_name):
    """删除字符串内不合法的文件名字符（windows）
        """

    if not file_name:
        return file_name

    rstr = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_file_name = re.sub(rstr, "_", file_name)  # 替换为下划线
    return new_file_name


def extrat_fname(url):
    try:
        return re.search(r'.+/(.*?\.gif|.*?\.png|.*?\.jpg|.*?\.jpeg|.*?\.webp|.*?\.bmp)', url, re.IGNORECASE).group(1)
    except (TypeError, AttributeError):
        return ''


def extrat_extname(url):
    try:
        return re.search(r'.*(jpeg|jpg|png|webp|gif|bmp)', url, re.IGNORECASE).group(1)
    except (TypeError, AttributeError):
        return ''


def findJsonFile(base):
    flist = []
    for root, ds, fs in os.walk(base):
        for f in fs:
            if f.endswith('json'):
                flist.append(os.path.join(root, f))

    return flist
