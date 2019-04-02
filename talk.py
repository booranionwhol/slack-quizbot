from slackclient import SlackClient
import time
import random
import os
import json

# bot
slack_token = os.environ.get("SLACK_BOT_TOKEN", None)
sc = SlackClient(slack_token)

QUIZ_MASTER = os.environ['QUIZ_MASTER']
QUIZ_CHANNEL_ID = os.environ['QUIZ_CHANNEL_ID']


button_test = {
    "text": "Would you like to play a game?",
    "attachments": [
        {
            "text": "Choose a game to play",
            "fallback": "You are unable to choose a game",
            "callback_id": "wopr_game",
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [
                {
                    "name": "game",
                    "text": "Chess",
                    "type": "button",
                    "value": "chess"
                },
                {
                    "name": "game",
                    "text": "Falken's Maze",
                    "type": "button",
                    "value": "maze"
                },
                {
                    "name": "game",
                    "text": "Thermonuclear War",
                    "style": "danger",
                    "type": "button",
                    "value": "war",
                    "confirm": {
                        "title": "Are you sure?",
                        "text": "Wouldn't you prefer a good game of chess?",
                        "ok_text": "Yes",
                        "dismiss_text": "No"
                    }
                }
            ]
        }
    ]
}


def bot_say(msg, channel=QUIZ_CHANNEL_ID):
    sc.rtm_send_message(channel, msg)


def buttons(channel=QUIZ_CHANNEL_ID):
    r = sc.api_call('chat.postMessage', channel=channel,
                    text=button_test['text'], attachements=button_test['attachments'])
    print(r)


if sc.rtm_connect(with_team_state=True):
    while sc.server.connected is False:
        print('Waiting for connection..')
        time.sleep(1)
    if sc.server.connected is True:
        time.sleep(1)

        bot_say(u'Bo\u0422oTx\u041DxH\u0412xBx\u039AxKx\u039DxNx\u041CxMx\u0405xSp!')
        buttons()
        for read_msg in sc.rtm_read():
            print(read_msg)
            time.sleep(0.1)
