
from asyncio.log import logger
import os
import asyncio
from time import sleep

from tkinter.ttk import Scrollbar
from turtle import width
from uuid import uuid4
from PIL import Image, ImageTk
from tkinter import Tk, Button, Frame, Entry, Label, Canvas, Menu, StringVar, IntVar, messagebox, Text

import config
from core import vk, pixiv

delimiters = []
cache = {}
areas = list()


def run_coroutine(coroutine, args):
    """Универсальная функция для вызова корутин"""
    async def func():
        tasks = list()
        task = asyncio.create_task(coroutine(**args))
        tasks.append(task)
        await asyncio.gather(*tasks)
        sleep(0.5)
    asyncio.run(func())


def main():
    window = Tk()
    window.title(config.app_name)
    window.geometry(config.app_size)
    window.resizable(width=0, height=0)
    cache['window'] = window
    
    global buffer_size
    buffer_size = StringVar()
    global selected_tag
    selected_tag = StringVar()
    global selected_user
    selected_user = StringVar()
    
    menu = Menu(tearoff=0)
    menu.add_command(label="Открыть", command=open_full_art)
    menu.add_command(label="Удалить", command=delete_art)
    cache['menu'] = menu
    
    draw_arts_area(window)
    draw_settings_areas(window)
    window.mainloop()
    

def draw_arts_area(window):
    packs_main_frame = Frame(window, width=1750, height=780, bg=config.bg_color)
    packs_main_frame.pack(side='top', fill='both', expand=1)
    cache['packs_main_frame'] = packs_main_frame
    
    packs_canvas = Canvas(packs_main_frame, bg=config.bg_color)
    cache['packs_canvas'] = packs_canvas
    packs_canvas.pack(side='left', fill='both', expand='yes')
    
    packs_scroll = Scrollbar(packs_main_frame, orient='vertical', command=packs_canvas.yview)
    packs_scroll.pack(side='right', fill='y')
    
    packs_canvas.configure(yscrollcommand=packs_scroll.set)
    packs_canvas.bind('<Configure>', lambda x: packs_canvas.configure(scrollregion=packs_canvas.bbox('all')))
    packs_canvas.bind_all('<MouseWheel>', on_mousewheel)
    
    packs_area = Frame(packs_canvas, bg=config.bg_color)
    packs_canvas.create_window((0, 0),  window=packs_area, anchor='nw', width=1750, height=10000)
    cache['packs_area'] = packs_area
    draw_arts(packs_area)


def draw_arts(packs_area):
    pack_lenth = 0
    x = 35
    y = 10
    config.posts_list.append(list())
    for art in os.listdir(config.files_path):
        if pack_lenth >= config.base_pack_len:
            pack_lenth = 0
            x = 35
            y += config.base_height + 10
            config.posts_list.append(list())
            
        path = f'{config.files_path}\\{art}'
        image  = Image.open(path)
        wpercent = (config.base_width/float(image.size[0]))
        h_size = int((float(image.size[1])*float(wpercent)))
        image = image.resize((config.base_width,h_size), Image.ANTIALIAS)
        ph = ImageTk.PhotoImage(image=image)
        name = art
        art = Label(packs_area, image=ph, height=170)
        art.name = name
        art.place(x=x, y=y, height=170)
        art.image = ph
        art.bind('<Button-1>', drag_start)
        art.bind('<B1-Motion>', drag_motion)
        art.bind('<ButtonRelease-1>', drop)
        art.bind('<Button-3>', open_full_art)
        art.bind('<Button-2>', delete_art)
        
        config.posts_list[-1].append((path, art))
        x += config.base_width + 10
        pack_lenth += 1
        
    y += config.base_height + 10
    del_empty_area()
    draw_delimiters()

    
def draw_settings_areas(window):
    settings_area = Frame(window, width=1750, height=185, bg='#9c9c9c')
    cache['settings_area'] = settings_area
    settings_area.pack_propagate(0)
    settings_area.pack(padx=0, pady=0, fill='both')
    settings_areas = list()
    for i in range(5):
        area = Frame(settings_area, width=225, height=180, bg='#9c9c9c')
        area.pack_propagate(0)
        area.pack(side='left', padx=5, pady=5)
        settings_areas.append(area)
        
    Label(settings_areas[1], text=f'{" "*12}Фильтр :', name=f'text_{uuid4().hex[:6]}', bg='#9c9c9c').place(x=10, y=30)
    Label(settings_areas[1], text=f'Сделать чекпоинт для фильтра', name=f'text_{uuid4().hex[:6]}', bg='#9c9c9c').place(x=10, y=60)
    Label(settings_areas[0], text=f'Размер буфера:\n\n{" "*21}Тег:\n\n{" "*18}Текст :', name=f'text_{uuid4().hex[:6]}', bg='#9c9c9c').place(x=10, y=30)
    
    Entry(settings_areas[0], textvariable=buffer_size).place(x=110, y=30, width=100)
    Entry(settings_areas[0], textvariable=selected_tag).place(x=110, y=60, width=100)
    text = Text(settings_area)
    text.place(x=115, y=95, width=335, height=50)
    cache['text_field'] = text
    
    Entry(settings_areas[1]).place(x=110, y=30, width=100)

    Button(settings_areas[2], text='Очистить отложенные посты', command=del_postpone_wall_wrap, bg='red').place(x=10, y=27, width=200)
    Button(settings_areas[2], text='Запостить', command=create_new_posts_wrap, bg='green').place(x=10, y=57, width=200)
    Button(settings_areas[2], text='Заполнить из подписок', command=download_by_user_b_handler).place(x=10, y=87, width=200)
    Button(settings_areas[2], text='Заполнить по тегу', command=download_by_tag_b_handler).place(x=10, y=117, width=200)
    Button(settings_areas[3], text='Обновить данные подписок', command=following_demon_wrap).place(x=10, y=27, width=200)


def following_demon_wrap():
    try:
        pixiv.following_demon()
        messagebox.showinfo("Успешно", 'Обновление данных завершено')
    except Exception as e:
        logger.exception(e)
        messagebox.showinfo("Ошибка", e)


def del_postpone_wall_wrap():
    try:
        answer = messagebox.askyesno('Подтверждение', 'Действительно удалить ВСЕ отложенные посты в группе вк?')
        if answer:
            vk.del_postpone_wall()
            messagebox.showinfo("Успешно", 'Отложенные посты удалены')
        else:
            messagebox.showinfo("Отмена", 'Удаление отменено')
    except Exception as e:
        logger.exception(e)
        messagebox.showinfo("Ошибка", e)
    

def create_new_posts_wrap():
    try:
        vk.create_new_posts(cache['text_field'].get(1.0, 'end'))
        del_all_arts()
        draw_arts(cache['packs_area'])
        messagebox.showinfo("Успешно", 'Посты созданы')
    except Exception as e:
        logger.exception(e)
        messagebox.showinfo("Ошибка", e)


def del_all_arts():
    for post in config.posts_list:
        for art in post:
            art[1].destroy()
    
    config.posts_list = []


def download_by_tag_b_handler():
    try:
        if not buffer_size.get().isdigit():
            messagebox.showwarning('Предупреждение', 'В поле "Размер буфера" введены неверные данные, это должно быть число')
            return
        
        run_coroutine(pixiv.download_arts_by_tag, {
                    'tag': selected_tag.get(),
                    'pack_num': buffer_size.get()
                })
        del_all_arts()
        draw_arts(cache['packs_area'])
        messagebox.showinfo("Успешно", 'Загрузка артов завершена')
    except Exception as e:
        logger.exception(e)
        messagebox.showinfo("Ошибка", e)
    

def download_by_user_b_handler():
    try:
        pixiv.download_following(buffer_size.get())
        del_all_arts()
        draw_arts(cache['packs_area'])
        messagebox.showinfo("Информация", 'Загрузка успешно завершена')
    except Exception as e:
        logger.exception(e)
        messagebox.showinfo("Ошибка", e)


def open_full_art(event):
    width = int(config.app_size.split('x')[0])
    height = int(config.app_size.split('x')[1])
    art_frame = Frame(width=width, height=height)
    art_frame.place(x=0, y=0, width=width, height=height)
    arts = []
    for pack in config.posts_list:
        arts.extend(pack)
    
    for art in arts:
        if event.widget.name in art[0]:
            path = art[0]
            break
        
    image  = Image.open(path)
    if image.size[0] > width and image.size[1] > height:
        if image.size[0] < image.size[1]: # ширина > высота
            hpercent = (height/float(image.size[1]))
            w_size = int((float(image.size[0])*float(hpercent)))
            if w_size > width:
                wpercent = (width/float(image.size[0]))
                h_size = int((float(image.size[1])*float(wpercent)))
                image = image.resize((width, h_size), Image.ANTIALIAS)
                ph = ImageTk.PhotoImage(image=image)
            else:
                image = image.resize((w_size, height), Image.ANTIALIAS)
                ph = ImageTk.PhotoImage(image=image)
        else:
            wpercent = (width/float(image.size[0]))
            h_size = int((float(image.size[1])*float(wpercent)))
            if h_size > height:
                hpercent = (height/float(image.size[1]))
                w_size = int((float(image.size[0])*float(hpercent)))
                image = image.resize((w_size, height), Image.ANTIALIAS)
                ph = ImageTk.PhotoImage(image=image)
            else:
                image = image.resize((width, h_size), Image.ANTIALIAS)
                ph = ImageTk.PhotoImage(image=image)
        
    elif image.size[0] > width:
        wpercent = (width/float(image.size[0]))
        h_size = int((float(image.size[1])*float(wpercent)))
        if h_size > height:
            hpercent = (height/float(image.size[1]))
            w_size = int((float(image.size[0])*float(hpercent)))
            image = image.resize((w_size, height), Image.ANTIALIAS)
            ph = ImageTk.PhotoImage(image=image)
        else:
            image = image.resize((width, h_size), Image.ANTIALIAS)
            ph = ImageTk.PhotoImage(image=image)
            
    elif image.size[1] > height:
        hpercent = (height/float(image.size[1]))
        w_size = int((float(image.size[0])*float(hpercent)))
        if w_size > width:
            wpercent = (width/float(image.size[0]))
            h_size = int((float(image.size[1])*float(wpercent)))
            image = image.resize((width, h_size), Image.ANTIALIAS)
            ph = ImageTk.PhotoImage(image=image)
        else:
            image = image.resize((w_size, height), Image.ANTIALIAS)
            ph = ImageTk.PhotoImage(image=image)
            
    else:
        ph = ImageTk.PhotoImage(image=image)
    
    art = Label(art_frame, image=ph, bg=config.bg_color)
    art.pack(side='bottom')
    art.image = ph
    art_frame.bind('<Button-1>', close_full_art)
    art.bind('<Button-1>', close_full_art)
    cache['full_art_wrap'] = art_frame
    cache['full_art'] = art


def close_full_art(event):
    cache['full_art'].destroy()
    cache['full_art_wrap'].destroy()
    del cache['full_art']
    del cache['full_art_wrap']


def delete_art(event):
    for pack in config.posts_list:
        for art in pack:
            if event.widget.name in art[0]:
                pack.remove(art)
                art[1].destroy()
                os.remove(art[0])
                del_empty_area()
                draw_delimiters()
                return
            
            
def drag_start(event):
    widget = event.widget
    widget.startX = event.x
    widget.startY = event.y


def drag_motion(event):
    widget = event.widget
    x = widget.winfo_x() - widget.startX + event.x
    y = widget.winfo_y() - widget.startY + event.y
    widget.place(x=x, y=y)


def drop(event):
    widget = event.widget
    x = widget.winfo_x()
    y = widget.winfo_y()
    escape = False
    for post_index, arts in enumerate(config.posts_list):
        for art_data in arts:
            if widget.name in art_data[0]:
                escape = True
                break
        if escape:
            break
        
    x = 35
    config.posts_list[post_index].remove(art_data)
    for i in config.posts_list[post_index]:
        i[1].place(x=x, y=i[1].winfo_y(), height=170)
        x += config.base_width + 10
        
    for index, art in enumerate(config.posts_list):
        if widget.winfo_y() < (config.base_height * index + 10) + config.base_height and len(config.posts_list[index]) < config.post_limit:
            x = (config.base_width * len(config.posts_list[index])) + (len(config.posts_list[index]) * 10) + 35
            y = (config.base_height * index + 35) + 5
            config.posts_list[index].append(art_data)
            break
    else:
        create_new_area(art_data)
        del_empty_area()
        draw_delimiters()
        return
    
    widget.place(x=x, y=y)
    del_empty_area()
    draw_delimiters()


def draw_delimiters():
    global delimiters
    for delimiter in delimiters:
        delimiter.destroy()

    delimiters = []
    y = 20
    for _ in config.posts_list:
        delimiters.append(Label(cache['packs_area'], width=int(config.app_size.split('x')[0]), bg='white'))
        delimiters[-1].place(x=0, y=y + config.base_height - 12, height=4)
        y += config.base_height + 10


def create_new_area(art_data):
    x = 35
    y = (config.base_height * len(config.posts_list) + 35) + config.base_height
    config.posts_list.append(list())
    config.posts_list[-1].append(art_data)
    art_data[1].place(x=x, y=y, height=170)


def del_empty_area():
    initial_lenth = len(config.posts_list)
    for i, post in enumerate(config.posts_list):
        if not post:
            config.posts_list.remove(post)
    
    if initial_lenth != config.posts_list:
        y = 10
        for post in config.posts_list:
            x = 35
            for art_data in post:
                art_data[1].place(x=x, y=y, height=170)
                x += config.base_width + 10
                
            y += config.base_height + 10


def on_mousewheel(event):
    cache['packs_canvas'].yview_scroll(int(-1*(event.delta/120)), "units")
    
    
if __name__ == '__main__':
    main()
