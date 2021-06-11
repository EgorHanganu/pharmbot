import os

telegram_token = os.getenv('TELEGRAM_TOKEN')
moysklad_token = os.getenv('MOYSKLAD_TOKEN')

dbconfig = {
    'host': os.getenv('HOST_DB'),
    'user': os.getenv('USER_DB'),
    'password' : os.getenv('PASSWORD_DB'),
    'port' : 3306 , 
    'database': os.getenv('DATABASE_NAME')
}