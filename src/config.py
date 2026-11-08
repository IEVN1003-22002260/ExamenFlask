class DevelopmentConfig():
    DEBUG=True
    MYSQL_HOST='localhost'
    MYSQL_USER='camila'
    MYSQL_PASSWORD='root'
    MYSQL_DB='pizzeria'
    MYSQL_CURSORCLASS='Cursor'

config={
    'development': DevelopmentConfig
}