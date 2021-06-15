#coding=utf-8
import telebot.types as tbt
from utils import *
import datetime
import json

users = QueryMethod('users')
texts = QueryMethod('texts')
cart = QueryMethod('cart')
moysklad = MoySkladQuery()

languages = {"O'zbekcha 🇺🇿": 'uz', 'Русский 🇷🇺' : 'ru'}

remove_keyboard = tbt.ReplyKeyboardRemove()

def get_languages(enable_back=False, chat_id=None):
    select_language = tbt.ReplyKeyboardMarkup(True)
    select_language.row(*languages.keys())
    if enable_back:
        select_language.row(get_text(chat_id)['back'])
    return select_language

def main_menu(chat_id, get_texts=False):
    keyboard_texts = get_text(chat_id)
    make_order = keyboard_texts['order']
    products = keyboard_texts['products']
    about_us = keyboard_texts['about_us']
    vacancies = keyboard_texts['vacancies']
    if get_texts:
        return {make_order: 'MAKE_ORDER', products: "PRICE_LIST", about_us: "ABOUT_US", vacancies: "VACANCIES"}
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.row(make_order, products)
    keyboard.row(about_us, vacancies)
    return keyboard

def order_list(chat_id, get_texts=False):
    keyboard_texts = get_text(chat_id)
    beauty = keyboard_texts['for_beauty']
    hair = keyboard_texts['for_hair']
    cart = keyboard_texts['cart']
    menu = keyboard_texts['back']
    if get_texts:
        return {beauty: "for_beauty", hair: "for_hair", cart: "CART", menu: "GET_BACK_MAIN_MENU"}
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.row(beauty, hair)
    keyboard.row(cart, menu)
    return keyboard

def get_products_keyboard(chat_id, name):
    keyboard_values = moysklad.get_stock(chat_id, name, True)
    keyboard_texts = get_text(chat_id)
    cart = keyboard_texts['cart']
    back = keyboard_texts['back']
    if not keyboard_values:
        return None
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    for value in keyboard_values:
        keyboard.row(*value)
    keyboard.row(cart, back)
    return keyboard

def get_product_counter_keyboard(chat_id):
    keyboard_texts = get_text(chat_id)
    cart = keyboard_texts['cart']
    back = keyboard_texts['back']
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.row('1','2','3')
    keyboard.row('4', '5', '6')
    keyboard.row('7', '8', '9')
    keyboard.row(cart, back)
    return keyboard

def get_cart_keyboard(chat_id):
    keyboard_texts = get_text(chat_id)
    back = keyboard_texts['back']
    clear = keyboard_texts['clear_cart']
    checkout = keyboard_texts['checkout']
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    cart_info = cart.query('select', columns = ['product_name', 'query_dict'], fetchall=1, condition = f"telegram_id={chat_id} AND ordered=0")
    msg = keyboard_texts['cart_'] + ':\n\n'
    total = 0
    currency = keyboard_texts['currency_sum']
    for product in cart_info:
        qdict = json.loads(product[1].replace("'", '"'))
        keyboard.row("❌ " + product[0])
        quantity = qdict['quantity']
        price = int(qdict['price'] // 100)
        _total = int(price*quantity)
        msg += '*' + product[0] + '*\n' + str(quantity) + " x " + str(price) + ' = ' + str(_total) + currency + '\n'
        total += _total
    msg += f'\n*{keyboard_texts["total"]}*{total}{currency}'
    keyboard.row(back, clear)
    keyboard.row(checkout)
    return keyboard, msg

def back(chat_id):
    keyboard_texts = get_text(chat_id)
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.row(keyboard_texts['back'])
    return keyboard

def get_phone(chat_id):
    keyboard_texts = get_text(chat_id)
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.add(tbt.KeyboardButton(keyboard_texts['my_phone'], request_contact=True))
    return keyboard

def send_location(chat_id):
    keyboard_texts = get_text(chat_id)
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.add(tbt.KeyboardButton(keyboard_texts['send_location'], request_location=True))
    keyboard.add(tbt.KeyboardButton(keyboard_texts['back']))    
    return keyboard


def cancel(chat_id):
    txts = get_text(chat_id)
    keyboard = tbt.ReplyKeyboardMarkup(True, False)
    keyboard.row(txts['cancel_movement'])
    return keyboard