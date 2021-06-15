#coding=utf-8
import config
import logging
import mysql.connector.pooling as ms
import requests
import time
import datetime

logger = logging.getLogger('Pharmbot')
logger.setLevel(logging.ERROR)
fh = logging.FileHandler("errors.txt")
fh.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

string_quotes = lambda string: '"' + string + '"'

mspool = ms.MySQLConnectionPool(pool_name='Pharmbot', **config.dbconfig, use_unicode=True)

headers = {'Authorization': f'Bearer {config.moysklad_token}', 'Content-Type': 'application/json'}

organization = 'https://online.moysklad.ru/api/remap/1.2/entity/organization/f334f078-95f1-11eb-0a80-07a5002a3c88'

class QueryMethod:
    
    def __init__(self, table):
        self.table = table
        
    def query(self, method, **kwargs):
        db = mspool.get_connection()
        cursor = db.cursor()
        method = method.upper()
        condition = ''
        cursor.execute('SET NAMES utf8mb4')
        cursor.execute("SET CHARACTER SET utf8mb4")
        cursor.execute("SET character_set_connection=utf8mb4")        
        
        if 'columns' in kwargs:
            cols = ', '.join(kwargs['columns'])
        if 'condition' in kwargs:
            condition = f'WHERE {kwargs["condition"]}'
            
        try:
            if method == "INSERT":
                values = []
                for value in kwargs['values']:
                    if isinstance(value, str):
                        values.append(string_quotes(value))
                    elif value == None:
                        values.append('NULL')
                    else:
                        values.append(str(value))
                vals = ', '.join(values)
                cursor.execute(f'INSERT INTO {self.table} ({cols}) VALUES ({vals});')
                db.commit()
                cursor.close()
                db.close()
                return 1
            elif method == "SELECT":
                cursor.execute(f"SELECT {cols} FROM {self.table} " + condition)
                if not kwargs['fetchall']:
                    result = cursor.fetchone()
                    while cursor.fetchone() != None:
                        cursor.fetchone()
                else:
                    result = cursor.fetchall()
                cursor.close()
                db.close()
                return result
            elif method == 'UPDATE':
                cursor.execute(f'UPDATE {self.table} SET {kwargs["to_update"]} ' + condition)
                db.commit()
                cursor.close()
                db.close()
                return 1
            elif method == "DELETE":
                cursor.execute(f'DELETE FROM {self.table} ' + condition)
                db.commit()
                cursor.close()
                db.close()
                return 1
        except Exception as e:
            logger.exception(e)
            cursor.close()
            db.close()
            return False
        
base_url = 'https://online.moysklad.ru/api/remap/1.2'
product_folder_link = 'https://online.moysklad.ru/api/remap/1.2/entity/productfolder/4945624d-36e8-11eb-0a80-00030015c55c'

class MoySkladQuery:
    
    def _get_product_name(self, link, chat_id, product_name):
        user_lang = get_text(chat_id, get_user_language=True)
        expanded_product_info = requests.get(link, headers=headers).json()
        if 'attributes' in expanded_product_info:
            for alt_name in expanded_product_info['attributes']:
                if alt_name['name'] == user_lang:
                    return alt_name['value']
        return product_name
    
    def get_stock(self, chat_id, name=None, get_names=False):
        try:
            c = 0
            result = [] if get_names else {}
            rows = requests.get(base_url + "/report/stock/all?limit=1000&filter=quantityMode=all", headers=headers).json()['rows']
            for i in rows:
                if i['folder']['name'] == 'Ингредиенты':
                    continue
                if get_names:
                    if i['folder']['name'] == name:
                        product_name = self._get_product_name(i['meta']['href'], chat_id, i['name'])
                        if c % 2 == 0:
                            result.append([product_name])
                        else:
                            result[len(result)-1].append(product_name)
                        c += 1
                elif i['folder']['name'] == name or name == None:
                    product_name = self._get_product_name(i['meta']['href'], chat_id, i['name'])
                    result[product_name] = i
                
            return result
        except Exception as e:
            logger.exception(e)
            return False
    
    def send_order(self, agent_link, positions):
        body = {
            "applicable": True,
            "vatEnabled": False,
            'agent': {
                'meta': {
                    'href': agent_link,
                    'type': 'counterparty',
                    "mediaType": 'application/json'
                }
             },
            'organization': {
                'meta': {
                    'href': organization,
                    'type': 'organization',
                    'mediaType': 'application/json'
                }
            },
            'state': {
                'meta': {
                    'href': 'https://online.moysklad.ru/api/remap/1.2/entity/customerorder/metadata/states/f352f4e6-95f1-11eb-0a80-07a5002a3cad',
                    'type': 'state',
                    "mediaType": "application/json"
                }
            },
            'positions': positions
        }
        return requests.post('https://online.moysklad.ru/api/remap/1.2/entity/customerorder', headers=headers, json=body)
        
    def create_counterparty(self, chat_id, **kwargs):
        body = {}       
        for arg in kwargs:
            body[arg] = kwargs[arg]
        return requests.post('https://online.moysklad.ru/api/remap/1.2/entity/counterparty', headers=headers, json=body).json()['meta']['href']
    
    def _get_counterparty_link(self, chat_id):
        return users.query('select', columns=['agent_link'], condition=f'telegram_id={chat_id}', fetchall=0)[0]
    
    def get_counterparty(self, chat_id):
        agent_link = self._get_counterparty_link(chat_id)
        counterparty = requests.get(agent_link, headers=headers).json()
        counterparty_info = {}
        txts = get_text(chat_id)
        required = {'name': txts['fullname'], 'phone': txts['my_phone'], 'actualAddress': txts['delivery_address']}
        if 'name' not in counterparty:
            return {}
        for requirement in required:
            if requirement in counterparty:
                counterparty_info[required[requirement]] = counterparty[requirement]
            else:
                counterparty_info[required[requirement]] = None
        return counterparty_info
    
    def edit_counterparty(self, chat_id, **kwargs):
        agent_link = self._get_counterparty_link(chat_id)
        body = {}
        for arg in kwargs:
            body[arg] = kwargs[arg]
        return requests.put(agent_link, headers=headers, json=body)

users = QueryMethod('users')
texts = QueryMethod('texts')
cart = QueryMethod('cart')
moysklad = MoySkladQuery()

def get_text(chat_id, rus_version=False, non_user=False, get_user_language=False):
    q = texts.query('select', columns=['*'], fetchall=1)
    user_info = users.query("SELECT", columns=["language"], condition=f'telegram_id={chat_id}', fetchall=0)
    result = {'uz': {}, 'en': {}, 'ru': {}}
    for i in q:
        result['uz'][i[0]] = i[1]
        result['ru'][i[0]] = i[2]
    if rus_version:
        return result['ru']
    if non_user:
        return result
    if get_user_language:
        return user_info[0]
    return result[user_info[0]]

def get_cart(chat_id, ordered=0):
    return cart.query("SELECT", columns=['*'], condition=f"telegram_id={chat_id} AND ordered={ordered}", fetchall=1)

def get_users():
    telegram_ids = []
    got_telegram_id = users.query('select', columns=['telegram_id'], fetchall=1)
    for telegram_id in got_telegram_id:
        telegram_ids.append(telegram_id[0])
    return telegram_ids