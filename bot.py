#coding=utf-8
import config
import keyboards
import telebot
import requests
import logging
import time
import re
import datetime
import json
import os
from utils import *

bot = telebot.TeleBot(config.telegram_token)

bot.enable_save_next_step_handlers(delay=1)

users = QueryMethod('users')
texts = QueryMethod('texts')
cart = QueryMethod('cart')
moysklad = MoySkladQuery()

def cart_handler(message):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    if message.text == '/start':
        return bot.send_message(chat_id, txts['main_menu'], reply_markup=keyboards.main_menu(chat_id))
    if message.text == txts['back']:
        bot.register_next_step_handler(message, handle_category)
        return bot.send_message(chat_id, txts['choose_category'], reply_markup=keyboards.order_list(chat_id))
    if message.text == txts['clear_cart']:
        cart.query('delete', condition=f'telegram_id={chat_id} AND ordered=0')
        return bot.send_message(chat_id, txts['cart_cleared'], reply_markup=keyboards.main_menu(chat_id), parse_mode='Markdown')
    if message.text[:2] == '❌ ':
        cart.query('delete', condition=f'telegram_id={chat_id} AND product_name="{message.text[2:]}" AND ordered=0')
        cart_keyboard, cart_content = keyboards.get_cart_keyboard(chat_id)
        if len(cart_keyboard.keyboard) > 2:
            bot.register_next_step_handler(message, cart_handler)
            return bot.send_message(chat_id, cart_content, reply_markup=cart_keyboard, parse_mode='Markdown')
        return bot.send_message(chat_id, txts['cart_cleared'], reply_markup=keyboards.main_menu(chat_id), parse_mode='Markdown')
    if message.text == txts['checkout']:
        positions = []
        for pos in cart.query('select', columns=['query_dict'], condition=f'telegram_id={chat_id} AND ordered=0', fetchall=1):
            positions.append(json.loads(pos[0].replace("'", '"')))
        cart.query('update', to_update=f'ordered=1, _date="{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"', condition=f'telegram_id={chat_id} AND ordered=0')
        res = moysklad.send_order(moysklad._get_counterparty_link(chat_id), positions)
        return bot.send_message(chat_id, txts['thank_you'], reply_markup=keyboards.main_menu(chat_id))

def get_cart(message, prev_keyboard, *args):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    cart_details = cart.query('select', columns=['*'], condition=f'telegram_id={chat_id} AND ordered=0', fetchall=1)
    if not len(cart_details):
        bot.register_next_step_handler(message, *args)
        return bot.send_message(chat_id, txts['empty_cart'], reply_markup=prev_keyboard)
    bot.register_next_step_handler(message, cart_handler)
    cart_keyboard, cart_content = keyboards.get_cart_keyboard(chat_id)
    return bot.send_message(chat_id, cart_content, reply_markup=cart_keyboard, parse_mode='Markdown')

def count_handler(message, metaentity, group, price):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    _NORMALS = {'Для красоты': txts['for_beauty'], 'Для волос': txts['for_hair']}   
    if message.text == '/start':
        return bot.send_message(chat_id, txts['main_menu'], reply_markup=keyboards.main_menu(chat_id))
    bot.send_message(chat_id, txts['pending'])
    product_keyboard = keyboards.get_products_keyboard(chat_id, group)
    if message.text == txts['back']:
        if product_keyboard:
            bot.register_next_step_handler(message, handle_product, group, product_keyboard)
            return bot.send_message(chat_id, _NORMALS[group], reply_markup=product_keyboard)
        bot.register_next_step_handler(message, handle_category)
        return bot.send_message(chat_id, txts['temporarily_unavailable'], reply_markup=keyboards.order_list(chat_id))
    if message.text == txts['cart']:
        return get_cart(message, keyboards.get_product_counter_keyboard(chat_id), count_handler, metaentity, group, price)
    if message.text.replace(' ', '').isdigit() and int(message.text.replace(' ', '')) <= 20 and int(message.text.replace(' ', '')) > 0:
        existed_prod = cart.query('select', columns=['query_dict'], condition=f'telegram_id={chat_id} AND ordered=0 AND product_name_sys="{metaentity["name"]}"', fetchall=0)
        if not existed_prod:
            quantity = int(message.text.replace(' ', ''))
            meta = {'quantity': quantity, 'reserve': quantity, 'price': price*100, 'vat': 0, 'discount': 0, 'assortment': {'meta': metaentity['meta']}}
            cart.query('insert', columns=['telegram_id', 'product_name_sys', 'query_dict', 'product_name', 'ordered'], values=[chat_id, metaentity['name'], str(meta), metaentity['name'], 0])
        else:
            entity = json.loads(existed_prod[0].replace("'", '"'))
            quantity = int(message.text.replace(' ', '')) + entity['quantity']
            if quantity > 20:
                bot.register_next_step_handler(message, count_handler, metaentity, group, price)
                return bot.send_message(chat_id, txts['no_more_than_20'])
            entity['quantity'] = quantity
            cart.query('update', to_update=f'query_dict="{str(entity)}"', condition=f'telegram_id={chat_id} AND ordered=0 AND product_name_sys="{metaentity["name"]}"')
        if product_keyboard:
            bot.register_next_step_handler(message, handle_product, group, product_keyboard)
            return bot.send_message(chat_id, txts['added_success'], reply_markup=product_keyboard)
        bot.register_next_step_handler(message, handle_category)
        return bot.send_message(chat_id, txts['temporarily_unavailable'], reply_markup=keyboards.order_list(chat_id))
    elif message.text.replace(' ', '').isdigit() and int(message.text.replace(' ', '')) > 20:
        bot.send_message(chat_id, txts['no_more_than_20'])
    else:
        bot.send_message(chat_id, txts['invalid_format_product'])
    bot.register_next_step_handler(message, count_handler, metaentity, group, price)

def handle_product(message, group, this_keyboard):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    if message.text == '/start':
        return bot.send_message(chat_id, txts['main_menu'], reply_markup=keyboards.main_menu(chat_id))      
    if message.text == txts['back']:
        bot.register_next_step_handler(message, handle_category)
        return bot.send_message(chat_id, txts['choose_category'], reply_markup=keyboards.order_list(chat_id))
    if message.text == txts['cart']:
        return get_cart(message, this_keyboard, handle_product, group, this_keyboard)
    bot.send_message(chat_id, txts['pending'])
    stock = moysklad.get_stock(chat_id, group)
    if message.text in stock:
        msg_to_send = '*'+ message.text + '*\n\n'
        product_info = requests.get(stock[message.text]['meta']['href'], headers=headers).json()
        if 'description' in product_info:
            msg_to_send += product_info['description'] + '\n\n'
        price = int(product_info['salePrices'][1]['value'] // 100)
        msg_to_send += txts['price'] + str(price) + txts['currency_sum']
        if 'image' in stock[message.text]:
            image = requests.get(stock[message.text]['image']['meta']['href'], headers=headers).content
            bot.send_photo(chat_id, image, caption=msg_to_send, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, msg_to_send, parse_mode='markdown')
        bot.register_next_step_handler(message, count_handler, stock[message.text], group, price)
        return bot.send_message(chat_id, txts['product_counter'], reply_markup=keyboards.get_product_counter_keyboard(chat_id), parse_mode='markdown')
    bot.register_next_step_handler(message, handle_product, group, this_keyboard)

def handle_category(message):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    if message.text == '/start':
        return bot.send_message(chat_id, txts['main_menu'], reply_markup=keyboards.main_menu(chat_id))
    order_list_texts = keyboards.order_list(chat_id, True)
    if message.text in order_list_texts:
        bot.send_message(chat_id, txts['pending'])
        _NORMALS = {'for_beauty': 'Для красоты', 'for_hair': 'Для волос'}
        destination = order_list_texts[message.text]
        if destination == 'GET_BACK_MAIN_MENU':
            return bot.send_message(chat_id, txts['main_menu'], reply_markup=keyboards.main_menu(chat_id))
        if destination == 'CART':
            return get_cart(message, keyboards.order_list(chat_id), handle_category)
        if destination in _NORMALS:
            product_keyboard = keyboards.get_products_keyboard(chat_id, _NORMALS[destination])
            if product_keyboard:
                bot.register_next_step_handler(message, handle_product, _NORMALS[destination], product_keyboard)
                return bot.send_message(chat_id, message.text, reply_markup=product_keyboard)
            bot.register_next_step_handler(message, handle_category)
            return bot.send_message(chat_id, txts['temporarily_unavailable'])
    bot.register_next_step_handler(message, handle_category)

def get_phone(message, name, address):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    if message.text == '/start':
        bot.register_next_step_handler(message, get_phone, name, address)
        return bot.send_message(chat_id, txts['get_phone'], reply_markup=keyboards.get_phone(chat_id))        
    if message.content_type == 'contact':
        phone_num = message.contact.phone_number.replace('+', '')
    elif message.content_type == 'text':
        phone_num = message.text.strip().replace('+', '').replace(' ', '')
    else:
        return bot.register_next_step_handler(message, get_phone, name, address)
        
    if (phone_num[:3] == '998' and len(phone_num) == 12 and phone_num.isdigit()) or phone_num == '37368765347':
        agent_link = moysklad.create_counterparty(chat_id, name=name, actualAddress=address, phone='+' + phone_num)
        users.query('UPDATE', to_update=f'agent_link="{agent_link}"', condition=f'telegram_id={chat_id}')
        bot.send_message(chat_id, txts['welcome'], reply_markup=keyboards.main_menu(chat_id))
    else:
        return bot.register_next_step_handler(message, get_phone, name, address)

def get_address(message, name):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    if message.text == '/start' or message.content_type != 'text':
        bot.register_next_step_handler(message, get_address, name)
        return bot.send_message(chat_id, txts['get_address'])        
    address = message.text.strip().replace('"', '').replace("'", '')
    if len(address) > 200:
        bot.register_next_step_handler(message, get_address)
        return bot.send_message(chat_id, txts['address_not_more'])
    bot.register_next_step_handler(message, get_phone, name, address)
    return bot.send_message(chat_id, txts['get_phone'], reply_markup=keyboards.get_phone(chat_id))    

def get_name(message):
    chat_id = message.chat.id
    txts = get_text(chat_id)
    if message.text == '/start' or message.content_type != 'text':
        bot.register_next_step_handler(message, get_name)
        return bot.send_message(chat_id, txts['get_name'])
    name = message.text.strip().replace('"', '').replace("'", '')
    if len(name) > 100:
        bot.register_next_step_handler(message, get_name)
        return bot.send_message(chat_id, txts['name_not_more'])
    bot.register_next_step_handler(message, get_address, name)
    return bot.send_message(chat_id, txts['get_address'])

def get_language(message):
    chat_id = message.chat.id
    if message.text in keyboards.languages:
        bot.register_next_step_handler(message, get_name)
        users.query('INSERT', columns=['telegram_id', 'language'], values=[chat_id, keyboards.languages[message.text]])
        txts = get_text(chat_id)
        return bot.send_message(chat_id, txts['get_name'], reply_markup=keyboards.remove_keyboard)
    bot.register_next_step_handler(message, get_language)
    bot.send_message(chat_id, "🇺🇿 Iltimos, o'z tilingizni tanlang\n🇷🇺 Пожалуйста, выберите ваш язык", reply_markup=keyboards.get_languages())

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if chat_id < 0:
        return False    
    if chat_id not in get_users():       
        bot.register_next_step_handler(message, get_language)
        bot.send_message(chat_id, "🇺🇿 Iltimos, o'z tilingizni tanlang\n🇷🇺 Пожалуйста, выберите ваш язык", reply_markup=keyboards.get_languages())
    elif not moysklad._get_counterparty_link(chat_id):
        bot.register_next_step_handler(message, get_name)
        txts = get_text(chat_id)
        return bot.send_message(chat_id, txts['get_name'], reply_markup=keyboards.remove_keyboard)        
    else:
        bot.send_message(chat_id, get_text(chat_id)['main_menu'], reply_markup=keyboards.main_menu(chat_id))

@bot.message_handler(content_types=['text'])
def text_handler(message):
    chat_id = message.chat.id
    try:
        txts = get_text(chat_id)
        menu_texts = keyboards.main_menu(chat_id, True)
    except:
        return start(message)
    if message.text in menu_texts:
        destination = menu_texts[message.text]
        if destination == 'VACANCIES':
            return bot.send_message(chat_id, 'Link on vacancies')
        if destination == 'ABOUT_US':
            return bot.send_message(chat_id, txts['about_us_info'], parse_mode='Markdown')
        if destination == 'PRICE_LIST':
            bot.send_message(chat_id, txts['pending'])
            mts = ''
            stock = moysklad.get_stock(chat_id)
            for i in stock:
                prod_name = i
                price = int(requests.get(stock[i]['meta']['href'], headers=headers).json()['salePrices'][1]['value'] // 100)
                mts += prod_name + ': ' + str(price) + txts['currency_sum'] + '\n'
            if mts:
                return bot.send_message(chat_id, mts)
        if destination == 'MAKE_ORDER':
            bot.register_next_step_handler(message, handle_category)
            return bot.send_message(chat_id, txts['choose_category'], reply_markup=keyboards.order_list(chat_id))

bot.load_next_step_handlers()

while True:    
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.exception(e)
        time.sleep(5)