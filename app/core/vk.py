import requests
import re
import datetime
import os
from time import sleep
from vk_api import VkApi

from loguru import logger
from src.utils import get_grouped_open_images, del_dir
from config import VK_TOKEN, GROUP_ID

SESSION = VkApi(token=VK_TOKEN, api_version='5.107')
API = SESSION.get_api()


def gen_publish_timestamp():
    time_now = datetime.datetime.now()
    time = datetime.datetime(
        year=time_now.year,
        month=time_now.month,
        day=time_now.day,
        hour=time_now.hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    publish_time = int(datetime.datetime.timestamp(time)) + 3600
    offset = 0
    while True:
        postpone = API.wall.get(owner_id=f'-{GROUP_ID}', filter='postponed', offset=offset)
        offset += 20
        postpone_times = [post.get('date') for post in postpone['items']]
        for _ in postpone_times:
            if publish_time in postpone_times:
                publish_time += 3600
            else:
                return publish_time
        if not postpone_times:
            return publish_time


def del_postpone_wall():
    offset = 0
    postpone = API.wall.get(owner_id=f'-{GROUP_ID}', filter='postponed', offset=offset)
    while postpone['items']:
        offset += 20
        for post in postpone['items']:
            API.wall.delete(owner_id=f'-{GROUP_ID}', post_id=post['id'])
        postpone = API.wall.get(owner_id=f'-{GROUP_ID}', filter='postponed', offset=offset)


def create_new_posts(text):
    upload_url = API.photos.getWallUploadServer(group_id=GROUP_ID)['upload_url']
    post_attachments = get_grouped_open_images()
    for post_images in post_attachments:
        attachments = ''
        for index, file in enumerate(post_images):
            upload_response = requests.post(url=upload_url, files={'file' + str(index + 1): file}).json()
            file.close()
            os.remove(file.name)
            upload_response['group_id'] = GROUP_ID
            if upload_response['photo'] in ['[]', '']:
                continue

            save_server_response = API.photos.saveWallPhoto(**upload_response)
            attachments += f'photo{save_server_response[0]["owner_id"]}_{save_server_response[0]["id"]},'

        post_timestamp = gen_publish_timestamp()
        logger.info(datetime.datetime.fromtimestamp(post_timestamp))
        copyright_link = 'https://www.pixiv.net'        

        if text == 0 or text == '0':
            text = 'ᅠ'

        API.wall.post(
            owner_id=f'-{GROUP_ID}',
            from_group=1,
            v='5.107',
            message=text,
            attachments=attachments,
            publish_date=post_timestamp,
            copyright=copyright_link
        )
        logger.info(f'Post posted with attachments count {len(post_images)} and time {datetime.datetime.fromtimestamp(post_timestamp)}')
