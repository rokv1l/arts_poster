import os
import aiohttp
import asyncio
from sys import stderr
from time import sleep
from threading import Thread
from loguru import logger

import requests
from sqlalchemy import and_
from pixivpy3 import AppPixivAPI as SyncApi
from pixivpy3.utils import JsonDict
from pixivpy_async import PixivClient, AppPixivAPI
from aiohttp.client_exceptions import ServerDisconnectedError

import config
from config import REFRESH_TOKEN
from src.database import session_maker, Art


def download_disconnect_handle(function):
    async def inner(session, url, file_name):
        try:
            await function(session, url, file_name)
        except ServerDisconnectedError:
            logger.error(f'Server closed connection with {url}, download failed\n')
    return inner


@download_disconnect_handle
async def download_data(session, url, file_name):
    logger.info(f'Downloading file {url}')
    sleep(0.1)
    async with session.get(url, headers={'Referer': 'https://app-api.pixiv.net/'}) as response:
        data = await response.read()
        with session_maker() as session:
            art_id = url.split('/')[-1].split('.')[0]
            if 'ugoira' in art_id:
                logger.info(f'Download failed {url}')
                return
            try:
                art_id, art_num = int(art_id.split('_p')[0]) if '_p' in art_id else int(art_id), 0
            except Exception as e:
                logger.error(f'Something went wrong {e}')
                return
            if session.query(Art).filter(Art.url == url).first():
                logger.info(f'Art already exists {url}')
                return
            art = Art(
                pixiv_id=art_id,
                art_num=art_num,
                url=url,
                posted=True
            )

            try:
                session.add(art)
                session.commit()
            except:
                return
        path = f'{config.appdata}\\{config.app_name}\\{file_name}'
        with open(path, 'wb') as image_file:
            image_file.write(data)
            image_file.close()
    logger.info(f'Success downloaded {url}')


# modification for for search with bookmarks filter
async def search_illust_mod(
        app_api_,
        word: str,
        search_target: str = 'partial_match_for_tags',
        sort: str = 'date_desc',
        duration: str = None,
        filter: str = 'for_ios',
        offset: int = None,
        req_auth: bool = True,
        start_date=None,
        end_date=None,
        bookmark_num_min=None,
        bookmark_num_max=None
):
    method, url = app_api_.api.search_illust
    if bookmark_num_min is not None:
        params = app_api_.set_params(
            word=word,
            search_target=search_target,
            sort=sort,
            filter=filter,
            duration=duration,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            bookmark_num_min=bookmark_num_min,
            bookmark_num_max=bookmark_num_max,
        )
    else:
        params = app_api_.set_params(
            word=word,
            search_target=search_target,
            sort=sort,
            filter=filter,
            duration=duration,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )
    return await app_api_.requests_(method=method, url=url, params=params, auth=req_auth)


def make_dir(dir_name):
    path = f'images/{dir_name}/'
    if not os.path.exists(path):
        os.mkdir(path)

    return path


async def make_arts_pack(data):
    arts_pack = []
    if not data.get('illusts'):
        return arts_pack
    for illust_data in data['illusts']:
        if illust_data['meta_single_page']:
            arts_pack.append(illust_data['meta_single_page']['original_image_url'])
        elif illust_data['meta_pages']:
            for art_urls in illust_data['meta_pages']:
                arts_pack.append(art_urls['image_urls']['original'])
    return arts_pack


async def download_arts_by_tag(tag, pack_num, min_bookmark=0, max_bookmark=0):
    async with PixivClient() as client:
        api = AppPixivAPI(client=client)
        await api.login(refresh_token=REFRESH_TOKEN)
        next_pack = {
            "word": tag,
            "search_target": "partial_match_for_tags",
            "sort": "date_desc",
            "filter": "for_ios",
            "bookmark_num_min": min_bookmark,
            "bookmark_num_max": max_bookmark,
            "offset": 0
        }
        download_queue = []
        while int(pack_num) > len(download_queue):
            if next_pack == {}:
                break
            data = await search_illust_mod(api, **next_pack)
            arts_pack = await make_arts_pack(data)
            for art_url in arts_pack:
                if len(download_queue) >= int(pack_num):
                    break
                with session_maker() as session:
                    if not session.query(Art).filter(Art.url == art_url).first():
                        download_queue.append(art_url)

            next_pack = api.parse_qs(data.next_url) if api.parse_qs(data.next_url) else {}

        async with aiohttp.ClientSession() as session:
            tasks = list()
            for art in download_queue:
                tasks.append(asyncio.create_task(download_data(session=session, url=art, file_name=art.split('/')[-1])))
            await asyncio.gather(*tasks)


# --------------------------------------------


def following_demon() -> None:
    logger.info('following_demon started')
    api = SyncApi()
    api.auth(refresh_token=REFRESH_TOKEN)
    next_users_pack = {
        'restrict': 'public',
        'user_id': config.USER_ID,
        'offset': 0
    }
    while next_users_pack:
        user_following_json = api.user_following(**next_users_pack)
        if not user_following_json.user_previews:
            next_users_pack = None
            break
        users_handler(api, user_following_json)
        next_users_pack = api.parse_qs(user_following_json.next_url)
        sleep(config.request_delay)
        print(next_users_pack['offset'])
    logger.info('following_demon end')


def users_handler(api: SyncApi, users: JsonDict) -> None:
    for user_data in users.user_previews:
        next_arts_pack = {
            'user_id': user_data.user.id,
            'filter': 'for_ios',
            'type': 'illust',
            'offset': 0
        }
        while next_arts_pack:
            response = api.user_illusts(**next_arts_pack)
            if not response.illusts:
                next_arts_pack = None
                break
            for art_data in response.illusts:
                save_art_url(art_data)
            next_arts_pack = api.parse_qs(response.next_url)
            sleep(config.request_delay)


def save_art_url(art_data: JsonDict) -> None:
    try:
        if art_data.meta_pages:
            if art_data.type != 'illust':
                return
            for meta_page in art_data.meta_pages:
                with session_maker() as session:
                    art_id = meta_page.image_urls.original.split('/')[-1].split('.')[0]
                    try:
                        art_id, art_num = int(art_id.split('_p')[0]) if '_p' in art_id else int(art_id), 0
                    except Exception as e:
                        logger.error(f'Something went wrong {e}')
                        continue
                    if session.query(Art).filter(Art.url == meta_page.image_urls.original).first():
                        continue
                    art = Art(
                        pixiv_id=art_id,
                        art_num=art_num,
                        url=meta_page.image_urls.original,
                        posted=False,
                        author_id=art_data.user.id
                    )
                    session.add(art)
                    session.commit()
                    session.close()

        elif art_data.meta_single_page:
            with session_maker() as session:
                if not art_data.meta_single_page.original_image_url or art_data.type != 'illust':
                    return
                art_id = art_data.meta_single_page.original_image_url.split('/')[-1].split('.')[0]
                try:
                    art_id, art_num = int(art_id.split('_p')[0]) if '_p' in art_id else int(art_id), 0
                except Exception as e:
                    logger.error(f'Something went wrong {e}')
                    return
                if session.query(Art).filter(Art.url == art_data.meta_single_page.original_image_url).first():
                    return

                art = Art(
                    pixiv_id=art_id,
                    art_num=art_num,
                    url=art_data.meta_single_page.original_image_url,
                    posted=False,
                    author_id=art_data.user.id
                )
                session.add(art)
                session.commit()
                del art
                session.close()
    except Exception:
        logger.info(art_data)
        raise


def download_following(pack_size: int) -> None:
    with session_maker() as session:
        arts = session.query(Art).filter(Art.posted!=True).order_by(Art.pixiv_id.desc()).limit(pack_size).all()
        queue = [Thread(target=download_file, args=(art.url, )) for art in arts]
        for thread in queue:
            sleep(2)
            thread.start()
        for thread in queue:
            thread.join()


def download_file(url: str) -> None:
    with session_maker() as session:
        logger.info(f'Downloading file {url}')
        response = requests.get(url, headers={'Referer': 'https://app-api.pixiv.net/'})
        session.query(Art).filter(Art.url == url).update({'posted': True})
        session.commit()
        path = f'{config.appdata}\\{config.app_name}\\{url.split("/")[-1]}'
        with open(path, 'wb') as image_file:
            image_file.write(response.content)
        logger.info(f'Success downloaded {url}')
