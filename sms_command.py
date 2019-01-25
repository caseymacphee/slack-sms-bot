from base64 import b64decode
import copy
import json
import re
from urlparse import parse_qs

import arrow
from FlowrouteMessagingLib.Controllers.APIController import APIController
from FlowrouteMessagingLib.Models.Message import Message
import emoji
from slackclient import SlackClient

from common import (get_user_presence, get_member_info, build_user_name_map,
                    get_team_info, get_channel_info,
                    respond, get_redis_client)
from logger import log
from settings import (slack_client_token, slack_verification_token,
                      FLOWROUTE_NUMBER, FLOWROUTE_ACCESS_KEY,
                      FLOWROUTE_SECRET_KEY, REDIS_KEY_EXPIRE_TIME)


COMMAND_WORD = '/sms'
MESSAGE_TEMPLATE = "[Slack from {user}@{team} in #{channel}]\n{body}"
PROMPT_MESSAGE = '1 or more of the users you mentioned are not online.'
PROMPT_ATTACHMENTS = [
        {
            'text': 'Do you want to SMS them also?',
            'fallback': 'Sorry, unable to send the text message.',
            'callback_id': None,
            'color': '#3AA3E3',
            'attachment_type': 'default',
            'actions': [
                {
                    'name': 'Yes',
                    'text': 'Yes',
                    'type': 'button',
                    'value': 'yes'
                },
                {
                    'name': 'No',
                    'text': 'No',
                    'type': 'button',
                    'value': 'no'
                }
            ]
        }
    ]

FIND_MENTIONS = '<@(.+?)>'

TEAM_INFO = {}
USER_INFO = {}
NAME_MAP = {}
PUBLIC_CHANNELS_INFO = {}

sc = None
sms_controller = None
redis_client = None


class SlackError(Exception):
    pass


def check_for_challenge(event_event_body):
    return event_event_body.get('challenge')


def look_for_mentions(text):
    return re.findall(FIND_MENTIONS, text)


def store_event_context(event_id, channel, sender, recipients, timestamp, message, client=None):
    payload = json.dumps(
        {'channel': channel,
         'sender': sender,
         'recipients': recipients,
         'timestamp': timestamp,
         'message': message})
    client.set(event_id, payload, ex=REDIS_KEY_EXPIRE_TIME)
    return


def unpack_token(event_body):
    try:
        token = event_body['token']
    except KeyError:
        token = None
    if type(token) == list:
        token = token[0]
    return token


def send_message_prompt(cb_id, user, channel, attachment_template=PROMPT_ATTACHMENTS, client=None):
    attachment_template = copy.deepcopy(attachment_template)
    attachment_template[0]['callback_id'] = cb_id
    try:
        resp = sc.api_call(
            "chat.postEphemeral",
            channel=channel,
            text=PROMPT_MESSAGE,
            attachments=attachment_template,
            user=user)
    except Exception as e:
        log.error(json.dumps({"message": "Failed to post prompt to {}".format(user),
                              "exc": e}))
        raise e
    else:
        try:
            assert resp['ok'] == True
        except (KeyError, AssertionError):
            log.error(json.dumps({"message": "Failed to post prompt to {}".format(user),
                "resp": resp}))
            raise SlackError("Failed to post to channel")
        else:
            return


def lambda_handler(event, context):
    global TEAM_INFO
    global USER_INFO
    global NAME_MAP
    global PUBLIC_CHANNELS_INFO
    global sc
    global sms_controller
    global redis_client
    if not sc:
        sc = SlackClient(slack_client_token)
    if not USER_INFO:
        USER_INFO = get_member_info(client=sc)
        NAME_MAP = build_user_name_map(USER_INFO)
        if not USER_INFO:
            log.error(json.dumps({"message": "unable to retrieve user info from slack api"}))
    if not sms_controller:
        sms_controller = APIController(username=FLOWROUTE_ACCESS_KEY,
                                       password=FLOWROUTE_SECRET_KEY)
    event_body = parse_qs(event['body'])
    if not event_body:
        event_body = json.loads(event['body'])
    log.debug(json.dumps({"message": "the event body from slack",
        "event_body": event_body}))
    challenge = check_for_challenge(event_body)
    if challenge:
        return respond(None, challenge)
    token = unpack_token(event_body)
    if not token:
        event_body = json.loads(event_body['payload'][0])
        token = event_body['token']
    if token != slack_verification_token:
        log.error("Request token (%s) does not match expected", token)
        return respond(Exception('Invalid request token'))
    if 'command' in event_body:
        # It's a slash command
        command = event_body['command'][0]
        if command != COMMAND_WORD:
            return
        else:
            log.debug(json.dumps({
                "message": "User triggered {} command, retrieving customer contact info.".format(
                    COMMAND_WORD)}))
        user = event_body['user_name'][0]
        channel = event_body['channel_name'][0]
        command_text = unicode(event_body['text'][0])
        user_id = event_body['user_id']
        team_domain = event_body['team_domain'][0]
        # TODO get team id and channel id to load them into the cache
        try:
            recipient, text = command_text.split('@', 1)[1].split(' ', 1)  # FIXME support multiple recipients
        except[IndexError, KeyError]:
            log.error(json.dumps({"message": "Could not parse the {} command".format(COMMAND_WORD)}))
            return respond(None, "Could not parse the command")
        try:
            recipient_number = USER_INFO[NAME_MAP[recipient]]['number']
            if not recipient_number:
                raise KeyError('number')
        except KeyError:
            log.error(json.dumps({
                "message": "Unable to find contact number for user {}. Refreshing global contact info before returning.".format(
                    recipient)}))
            USER_INFO = get_member_info(client=sc)
            NAME_MAP = build_user_name_map(USER_INFO)
            return respond(None, "Could not find a phone number listed for that user. Please try again once they update their profile.")
        else:
            log.info(json.dumps(
                {"message": "Found contact info for {}. Attempting SMS send.".format(recipient)}))
            content = MESSAGE_TEMPLATE.format(
                user=user,
                team=team_domain,
                channel=channel,
                body=emoji.emojize(text, use_aliases=True))
            message = Message(
                to=recipient_number,
                from_=FLOWROUTE_NUMBER,
                content=content)
            try:
                sms_controller.create_message(message)
            except Exception as e:
                log.error(json.dumps({"message": "Failed to send SMS",
                    "exc": e}))
                return respond(None, "Unable to send SMS, please try again.")
            else:
                log.info(json.dumps(
                    {"message": "Successfully sent SMS to {}".format(recipient)}))
                return respond(None, "Successfully sent SMS!")
    if event_body['type'] == 'interactive_message':
        log.info(json.dumps(
                {"message": ("Received interactive message event with callback_id {}."
                             " Retrieving message context.").format(event_body['callback_id'])}))
        user_response = event_body['actions'][0].get('value')
        if user_response == 'no':
            return respond(None, "Ok, you can always message them with '/sms' if you change your mind later.")
        else:
            if not redis_client:
                log.debug(json.dumps({"message": "Getting redis client connection", "timestamp": str(arrow.get())}))
                redis_client = get_redis_client()
                log.debug(json.dumps({"message": "Got redis client connection", "timestamp": str(arrow.get())}))
            try:
                message_context = redis_client.get(event_body['callback_id'])
            except Exception as e:
                log.error(json.dumps({"message": "Failed to get event from Redis",
                                      "exc": e}))
                return respond(None, 'Something went wrong, please try again.')
            if not message_context:
                log.error(json.dumps({"message": "Callback id {} not found in Redis".format(
                    event_body['callback_id'])}))
                return respond(None, 'Session not found. Sorry!')
            else:
                event_context = json.loads(message_context)
                log.debug(json.dumps({"message": "interactive event context",
                                      "context": event_context}))
                sender_id = event_context['sender']
                channel_id = event_context['channel']
                for recipient in event_context['recipients']:
                    try:
                        recipient_number = USER_INFO[recipient]['number']
                        recipient_name = USER_INFO[recipient]['name']
                    except KeyError:
                        log.warning(json.dumps({
                            "message": "Unable to find contact number for user {}. Refreshing global contact info before returning.".format(
                                recipient)}))
                        USER_INFO = get_member_info(client=sc)
                        NAME_MAP = build_user_name_map(USER_INFO)
                        try:
                            recipient_number = USER_INFO[recipient]['number']
                            recipient_name = USER_INFO[recipient]['name']
                        except KeyError:
                            log.debug(json.dumps({"message": "unable to find contact number for user",
                                                  "recipient_id": recipient,
                                                  "user_info": USER_INFO,
                                                  "name_map": NAME_MAP,
                                                  "context": event_context}))
                            log.error(json.dumps({
                                "message": "Unable to find contact number for user {}. Returning now.".format(
                                    recipient)}))
                            return(None, "Could not find a contact number for that user.")
                    if not recipient_number:
                        log.info(json.dumps({"message": "Could not find a contact number for {}".format(recipient_name)}))
                        return (None, "Could not find a contact number for that user on their profile.") 
                    try:
                        sender_info = USER_INFO.get(sender_id)
                        if not sender_info:
                            log.debug(json.dumps({"message": "unable to find contact number for user",
                                                  "channel_id": channel_id,
                                                  "sender_id": sender_id,
                                                  "user_info": USER_INFO,
                                                  "name_map": NAME_MAP,
                                                  "context": event_context}))
                            return (None, "Could not find info for that user. Please try again.")
                        else:
                            sender_name = sender_info['name']
                        team_domain = TEAM_INFO.get('team_domain')
                        if not team_domain:
                            TEAM_INFO = get_team_info(client=sc)
                            team_domain = TEAM_INFO['team_domain']
                        channel_info = PUBLIC_CHANNELS_INFO.get(channel_id)
                        if not channel_info:
                            PUBLIC_CHANNELS_INFO.update(get_channel_info(
                                channel_id, client=sc))
                            channel_name = PUBLIC_CHANNELS_INFO[channel_id]['name']
                        else:
                            channel_name = PUBLIC_CHANNELS_INFO[channel_id]['name']
                    except Exception as e:
                        log.error(json.dumps({"message": "unable to get information",
                                              "channel_id": channel_id,
                                              "sender_id": sender_id,
                                              "user_info": USER_INFO,
                                              "name_map": NAME_MAP,
                                              "channel_info": PUBLIC_CHANNELS_INFO,
                                              "team_info": TEAM_INFO,
                                              "context": event_context,
                                              "exc": str(e)}))
                        raise e

                    log.info(json.dumps(
                        {"message": "Found contact info for {}. Attempting SMS send.".format(recipient_name)}))
                    human_readable_message = event_context['message'].replace('<@{}>'.format(recipient), "@{}".format(recipient_name))
                    log.debug(json.dumps({"message": "sms message", "sms": human_readable_message}))
                    content = MESSAGE_TEMPLATE.format(
                        user=sender_name,
                        team=team_domain,
                        channel=channel_name,
                        body=emoji.emojize(human_readable_message, use_aliases=True))
                    message = Message(
                        to=recipient_number,
                        from_=FLOWROUTE_NUMBER,
                        content=content)
                    try:
                        sms_controller.create_message(message)
                    except Exception as e:
                        log.error(json.dumps({"message": "Failed to send SMS",
                            "exc": str(e)}))
                        return respond(None, "Unable to send SMS, please try again.")
                    else:
                        log.info(json.dumps(
                            {"message": "Successfully sent SMS to {}".format(recipient)}))
                return respond(None, "Successfully sent!")        
    elif event_body['type'] == 'event_callback':
        log.debug(json.dumps({"message": "event callback body",
            "body": event_body}))
        # It's a channel message event
        event = event_body['event']
        # TODO make sure this isn't a duplicate request
        event_id = event_body['event_id']

        if event['type'] == 'message':
            if event_body.get('subtype') == 'message_changed' and event.get('hidden') == True:
                # This is the ephemeral message change that 
                # was just posted back.
                return
            try:
                text = event['text']
            except Exception as e:
                log.info(json.dumps({"message": "unknown message event with no text",
                    "body": event_body}))
                return
            # lookup channel, team, and user

            channel = event['channel']
            sender = event['user']
            timestamp = event['ts']
            mentioned_users = look_for_mentions(text)
            if mentioned_users:
                away_users = []
                for user_id in mentioned_users:
                    presence = get_user_presence(user_id, client=sc)
                    log.debug(json.dumps(
                        {"message": "Found mentioned user {} in '{}' public channel message with status {}.".format(
                            user_id, channel, presence)}))
                    if presence != 'active':
                        away_users.append(user_id)
            else:
                log.debug(json.dumps({"message": "Found no mentioned users in '{}' public channel message".format(
                    channel)}))
                return
            if away_users:
                users_have_numbers = False
                for recipient in away_users:
                    try:
                        recipient_number = USER_INFO[recipient]['number']
                        recipient_name = USER_INFO[recipient]['name']
                    except KeyError:
                        log.warning(json.dumps({
                            "message": "Unable to find contact number for user {}. Refreshing global"
                                       " contact info before returning.".format(recipient)}))
                        USER_INFO = get_member_info(client=sc)
                        NAME_MAP = build_user_name_map(USER_INFO)
                    else:
                        if recipient_number:
                            log.debug(json.dumps({
                                "message": "Found number of away users",
                                "user_id": recipient,
                                "number": recipient_number}))
                            users_have_numbers = True
                if not users_have_numbers:
                    log.info({"message": "None of the away users mentioned have phone numbers listed."})
                    return
                log.info(json.dumps(
                    {"message": "Found {} non-active users in '{}' public channel message. Sending message prompt.".format(
                        len(away_users), channel),
                     "users": away_users}))
                if not redis_client:
                    log.debug(json.dumps({"message": "Getting redis client connection", "timestamp": str(arrow.get())}))
                    redis_client = get_redis_client()
                    log.debug(json.dumps({"message": "Got redis client connection", "timestamp": str(arrow.get())}))
                store_event_context(
                     event_id, channel, sender, away_users, timestamp, text, client=redis_client)
                send_message_prompt(event_id, sender, channel, client=sc)
                log.info(json.dumps({"message": "Successfully posted ephemeral prompt to {} in channel {}".format(
                    sender, channel),
                                     "callback_id": event_id}))
                return respond(None, 'Successfully sent prompt')
            else:
                log.debug(json.dumps({"message": "Found no away users in '{}' public channel message mentions."}))
                return
