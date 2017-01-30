import re
import os
import glob
import aiohttp
import argparse
import asyncio
import requests
import itertools
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()

# https://docs.python.org/3/library/argparse.html#the-add-argument-method
parser = argparse.ArgumentParser(description='jenkins image downloader beta')
parser.add_argument("-l", "--login", required=True, type=str, help="Login")
parser.add_argument("-p", "--password", required=True, type=str, help="Password")
parser.add_argument("-u", "--url", required=True, type=str, help="url")
# parser.add_argument("--debug", action='store_true', help="Debug")
args = parser.parse_args()

password = args.password
login = args.login
url = args.url
last_build_log = 'last_downloaded_build.log'
download_folder = '/home/apalii/downloads'


def get_content_length(direct_url_on_image):
    res = requests.head(
        direct_url_on_image, verify=False, auth=HTTPBasicAuth(login, password)
    )
    return int(res.headers["Content-Length"])


def get_build_version(link):
    pattern = re.compile(r'rc(\d{4})')
    match = re.search(pattern, link)
    return int(match.group(1))


def get_latest_build(url_with_images):
    res = requests.get(url_with_images,
                       verify=False,
                       auth=HTTPBasicAuth(login, password)
                       )

    soup = BeautifulSoup(res.text, 'html.parser')
    a_tags = soup.findAll('a')
    aio_latest_build = [
        i.get('href') for i in a_tags if re.search('USM_All-in-One_dev', i.get('href'))
        ]
    file_name = aio_latest_build[0].split('/')[-1]
    return get_build_version(aio_latest_build[0]), aio_latest_build[0], file_name


def get_downloaded_build(newest=True):
    if newest:
        newest = max(glob.iglob(download_folder + '/*.zip'), key=os.path.getctime)
        return get_build_version(newest), newest
    oldest = min(glob.iglob(download_folder + '/*.zip'), key=os.path.getctime)
    return get_build_version(oldest), oldest


async def download(url, parts, size):
    conn = aiohttp.TCPConnector(verify_ssl=False)
    my_auth = aiohttp.BasicAuth(login, password)

    async def get_partial_content(u, i, start, end):
        headers = {
            "Range": "bytes={}-{}".format(start, end - 1 if end else "")
        }
        # print(i, format(start, ',d'), format(end, ',d'))
        print(i, start, end)
        with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(u, headers=headers, auth=my_auth) as _resp:
                return i, await _resp.read()

    ranges = list(range(0, size, size // parts))

    res, _ = await asyncio.wait(
        [get_partial_content(url, i, start, end) for i, (start, end) in
         enumerate(itertools.zip_longest(ranges, ranges[1:], fillvalue=""))]
    )

    sorted_result = sorted(task.result() for task in res)
    # return b"".join(data for _, data in sorted_result)
    print("All the parts are downloaded")
    return sorted_result


if __name__ == '__main__':

    last_build = get_latest_build(url)
    last_downloaded_build = get_downloaded_build(newest=True)

    if last_build[0] > last_downloaded_build[0]:
        image_size = get_content_length(last_build[1])

        print(image_size)
        loop = asyncio.get_event_loop()
        bs = loop.run_until_complete(download(last_build[1], 5, image_size))

        with open(last_build[2], "wb") as fi:
            for _, data in bs:
                fi.write(data)
    else:
        print("Ne kachaem")
