import arrow
import json
from logger import log

import redis

from settings import (REDIS_HOST, REDIS_PORT, REDIS_DB,
                      REDIS_SOCKET_TIMEOUT, REDIS_SOCKET_CONNECT_TIMEOUT)


def get_redis_client():
    redis_client = redis.StrictRedis(
                        host=REDIS_HOST,
                        port=REDIS_PORT,
                        db=REDIS_DB,
                        retry_on_timeout=False,
                        socket_keepalive=False,
                        socket_timeout=REDIS_SOCKET_TIMEOUT,
                        socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT)
    return redis_client


def get_member_info(client=None):
    user_list = client.api_call("users.list")
    user_info = {user['id']: {'number': user['profile'].get('phone', None),
                              'is_bot': user['is_bot'],
                              'is_app_user': user['is_app_user'],
                              'presence': None,
                              'name': user['name']}
                 for user
                 in user_list['members']}
    log.debug(json.dumps({
        "message": "Got {} member details (including bots).".format(
            len(user_info))}))
    return user_info


def build_user_name_map(user_info):
    name_map = {info['name']: user_id
                for user_id, info
                in user_info.iteritems()
                if not info['is_bot']}
    name_map.pop('slackbot')
    log.debug(json.dumps(
        {"message": "Found {} users.".format(len(name_map)),
         "user_ids": name_map}))
    return name_map


def get_user_presence(user_id, client=None):
    presence = client.api_call("users.getPresence", user=user_id)
    log.debug(json.dumps({
        "message": "Got {} presence".format(user_id),
        "presence": presence}))
    return presence['presence']


def get_channel_info(channel_id, client=None):
    resp = client.api_call(
        "channels.info", channel=channel_id)
    if not resp.get(u'ok'):
        log.error(json.dumps({
            "message": "failed to get channel info",
            "resp": resp}))
        raise Exception("Error retrieving channel info")
    else:
        log.info(json.dumps({
            "message": "succeeded getting channel info"}))
    return {channel_id: {"last_read": str(arrow.get()),
                         "name": resp['channel']["name"]}}


def get_team_info(client=None):
    resp = client.api_call("team.info")
    log.debug({"team_info_resp": resp})
    if not resp.get(u'ok'):
        log.error(json.dumps({
            "message": "failed to get team info",
            "resp": resp}))
        raise Exception("Error retrieving team info")
    else:
        log.info(json.dumps({
            "message": "succeeded getting team info"}))
    return {"team_id": resp['team']['id'],
            "team_domain": resp['team']['domain'],
            "team_name": resp['team']['name']}


def respond(err, res=None):
    resp = {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }
    return resp
