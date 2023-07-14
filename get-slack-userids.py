from slackclient import SlackClient
import os
from time import sleep

os.environ['QUIZ_CHANNEL_ID']  # The Quiz channel

slack_token = os.environ.get("SLACK_BOT_TOKEN", None)
sc = SlackClient(slack_token)

r=sc.api_call('channels.info',channel=QUIZ_CHANNEL_ID)
members=r['channel']['members']
def get_username(user_id):
    global sc
    response = sc.api_call(
        "users.info",
        user=user_id
    )
    user_obj=response['user']
    return [user_obj['profile']['display_name'], user_obj['name'], user_obj['real_name']]
for member in members:
    name =get_username(member)
    print(f'{member}  {name}')
    sleep(1)
