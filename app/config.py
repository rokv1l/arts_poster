import os

from loguru import logger

app_name = 'Arts poster'
app_size = '1800x1000'
appdata = os.getenv('APPDATA')
files_path = f'{appdata}\\{app_name}'

PIXIV_LOGIN = os.getenv('PIXIV_LOGIN')
PIXIV_PASSWORD = os.getenv('PIXIV_PASSWORD')
USER_ID = os.getenv('USER_ID')

GROUP_ID = os.getenv('GROUP_ID')
VK_TOKEN = os.getenv('VK_TOKEN')

REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')

request_delay = 4
arts_delay = 60*60*24*30
post_limit = 9

base_width = 170
base_height = 180
bg_color = '#4a4a4a'

base_pack_len = 8

posts_list = []
