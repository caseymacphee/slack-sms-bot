import pytest


from test_fixtures import (member_detail_resp, sms_command_event, channel_msg_event, presence_resp,
  interactive_message_resp)
import sms_command

FAKE_USER_INFO = {u'U06GTFGG0': {'is_app_user': False,
  'is_bot': False,
  'name': u'casey',
  'number': u'12069928996',
  'presence': None},
 u'U06KHKY4D': {'is_app_user': False,
  'is_bot': False,
  'name': u'connor',
  'number': None,
  'presence': None},
 u'USLACKBOT': {'is_app_user': False,
  'is_bot': False,
  'name': u'slackbot',
  'number': None,
  'presence': None}}

FAKE_NAME_MAP = {u'casey': u'U06GTFGG0', u'connor': u'U06KHKY4D'}


class MockSMSController(object):
    def __init__(self, **kwargs):
        pass

    def create_message(self, message):
        return


class FakeSlackClient(object):
    def __init__(self, **kwargs):
        pass

    def api_call(self, api_endpoint, **kwargs):
        if api_endpoint == 'chat.postEphemeral':
          return {u'message_ts': u'1510960572.000319', u'ok': True}
        elif api_endpoint == 'users.list':
          return member_detail_resp
        elif api_endpoint == 'users.getPresence':
          return presence_resp
        else:
          return None


class FakeRedisClient(object):
  def __init__(*args, **kwargs):
    pass

  def set(*args, **kwargs):
    return

  def get(*args, **kwargs):
    return {}


@pytest.fixture
def fake_globals(monkeypatch):
    monkeypatch.setattr(sms_command, 'sc', FakeSlackClient())
    monkeypatch.setattr(sms_command, 'USER_INFO', FAKE_USER_INFO)
    monkeypatch.setattr(sms_command, 'NAME_MAP', FAKE_NAME_MAP)
    monkeypatch.setattr(sms_command, 'sms_controller', MockSMSController())
    monkeypatch.setattr(sms_command, 'redis_client', FakeRedisClient())
    monkeypatch.setattr(sms_command, 'slack_verification_token', 'laTZQsNEyOvOfII13xqkBj20')
    

def test_sms_command_success(monkeypatch, fake_globals):
    res = sms_command.lambda_handler(sms_command_event, None)
    assert res == {'body': '"Successfully sent SMS!"', 'headers': {'Content-Type': 'application/json'}, 'statusCode': '200'}


def test_mention_message_success(monkeypatch, fake_globals):
    res = sms_command.lambda_handler(channel_msg_event, None)
    assert res == {'body': '"Successfully sent prompt"', 'headers': {'Content-Type': 'application/json'}, 'statusCode': '200'}

def test_message_prompt_response_success(monkeypatch, fake_globals):
  res = sms_command.lambda_handler(interactive_message_resp, None)
  assert res is not None
