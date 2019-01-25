import os


slack_client_token = os.environ.get(
    'SLACK_CLIENT_TOKEN', "")
slack_verification_token = os.environ.get(
    "SLACK_VERIFICATION_TOKEN", "")
FLOWROUTE_SECRET_KEY = os.environ.get(
    'FLOWROUTE_SECRET_KEY', '')
FLOWROUTE_ACCESS_KEY = os.environ.get(
    'FLOWROUTE_ACCESS_KEY', '')
FLOWROUTE_NUMBER = os.environ.get(
    'FLOWROUTE_NUMBER', '')
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB_NAME', 0))
REDIS_KEY_EXPIRE_TIME = int(os.environ.get('REDIS_KEY_EXPIRE_TIME', 10800))
MAX_REDIS_RECONNECT_ALLOWED = int(os.environ.get('MAX_REDIS_RECONNECT_ALLOWED',
                                                 3))
REDIS_SOCKET_TIMEOUT = int(os.environ.get('REDIS_SOCKET_TIMEOUT', 3))
REDIS_SOCKET_CONNECT_TIMEOUT = int(os.environ.get(
    'REDIS_SOCKET_CONNECT_TIMEOUT', 3))
