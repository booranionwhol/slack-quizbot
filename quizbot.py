from slackclient import SlackClient
import time
import random
import os
import json

# bot
slack_token = os.environ["SLACK_BOT_TOKEN"]
sc = SlackClient(slack_token)

# channels = slack_api.api_call(
#     "channels.list"
# )

# general: CC7EWCEAY
# quiz: CCAMPJ57E

def clean_answer(text):
    for character in ['?', '!', ',', '.','\\']:
        text = text.replace(character, "")
    return text.lower()
    
answers = []
with open('questions/four_letter_countries.json') as file:
    json_data = json.load(file)
    for answer in json_data['answers']:
        if answer != '':
            answers.append(clean_answer(answer.strip().replace('&','&amp;')))

STARTING_ANSWER_COUNT = len(answers)
random.seed(os.urandom(1024))
golden_answers = []
for i in range(1, int(len(answers)/10)):
    golden_random = random.choice(answers)
    if golden_random not in golden_answers:
        golden_answers.append(golden_random)
# rand=random.randint(0, len(answers)-1)
print(answers)
print('golden: {}'.format(golden_answers))
# print(len(answers),rand,answers[rand])

# raise SystemExit
WEBSOCKET_READLOOP_SLEEP = 0.2
POINT_ESCALATION_OFFERED = False
MINUTES_NO_GUESSES = 1
# As soon as the quiz starts, set the timer before there's a real guess.
last_correct_answer = time.time()
POINT_DEFAULT_WEIGHT = 1
QUIZ_MASTER = os.environ['QUIZ_MASTER']
GOLDEN_ANSWER_POINTS = 3
QUIZ_CHANNEL_ID = os.environ['QUIZ_CHANNEL_ID']

results_object = {}
CHEAT_TO_RESULTS = False
if CHEAT_TO_RESULTS:
    answers = []
    results_object = {
        "UC7HXJ319": {
            "score": 9,
            "total_correct_answers": 7
        },
        "UCDFY00HE": {
            "score": 8,
        },
        "UCDFZPDHN": {
            "score": 2,
            "total_correct_answers": 1
        }

    }




def get_username(user_id):
    global sc
    response = sc.api_call(
        "users.info",
        user=user_id
    )
    return response['user']['profile']['display_name']


# Taken from https://codereview.stackexchange.com/questions/41298/producing-ordinal-numbers
SUFFIXES = {1: 'st', 2: 'nd', 3: 'rd'}


def ordinal(num):
    # Checking for 10-20 because those are the digits that
    # don't follow the normal counting scheme.
    if 10 <= num % 100 <= 20:
        suffix = 'th'
    else:
        # the second parameter is a default.
        suffix = SUFFIXES.get(num % 10, 'th')
    return str(num) + suffix


def podium_medal(position):
    if position == 1:
        return ':first_place_medal:'
    if position == 2:
        return ':second_place_medal:'
    if position == 3:
        return ':third_place_medal:'
    # Last place
    if position == len(results_object):
        return ':poop:'
    else:
        return ''


def quiz_results(client, results_object, forced=False):
    if forced:
        bot_say('Ok fine. You lot are useless! The results are...')
    else:
        bot_say('Quiz over! The results are...')

    results_to_sort = []
    for user_id in results_object.keys():
        # Make a set with (score, user_id). So the list of sets can be sorted.
        results_to_sort.append((results_object[user_id]['score'], user_id))
    result_output = ""
    for index, result in enumerate(sorted(results_to_sort, reverse=True)):
        score = result[0]
        user_id = result[1]
        result_output += "{pos} {medal}) <@{user}>, score: {score}. Correct answers: {answers}\n".format(
            pos=ordinal(index+1),
            medal=podium_medal(index+1),
            user=user_id,
            score=score,
            answers=results_object[user_id]['total_correct_answers']
        )
    bot_say('{}'.format(result_output))
    quit('Finished!')


def bot_say(msg):
    sc.rtm_send_message('#quiz', msg)


def check_if_points_escalated():
    # We need to set this to check in a later read loop. Make global
    global POINT_ESCALATION_OFFERED, point_weight

    if POINT_ESCALATION_OFFERED is False:
        point_weight = POINT_DEFAULT_WEIGHT
    if time.time()-last_correct_answer >= float(MINUTES_NO_GUESSES*60):
        if POINT_ESCALATION_OFFERED is False:
            point_weight = 2
            bot_say('There have not been any correct guesses in {} minutes. Next correct answer worth {} points!'.format(
                MINUTES_NO_GUESSES, point_weight))
            POINT_ESCALATION_OFFERED = True

    return point_weight


def logger(msg):
    print(msg)


def parse_message(read_line_object):
    cleaned = clean_answer(read[0]['text'])
    user = read[0]['user']
    time_at = read[0]['ts']
    logger('{time_now} - At {time_msg} User {user} says: {orig}. Cleaned: {cleaned}'.format(
        user=user,
        time_now=time.time(),
        time_msg=time_at,
        orig=read[0]['text'],
        cleaned=cleaned
    ))
    return (user, time_at, cleaned)


def bot_reaction(msg_timestamp, emoji):
    sc.api_call(
        "reactions.add",
        channel=QUIZ_CHANNEL_ID,
        name=emoji,
        timestamp=msg_timestamp
    )


def check_plural(num):
    if num > 1:
        return 's'
    else:
        return ''


if sc.rtm_connect(with_team_state=True):
    # sc.api_call(
    #     "chat.postMessage",
    #     channel='general',
    #     text='sdasd'
    # )

    while sc.server.connected is False:
        print('Waiting for connection..')
        time.sleep(1)
    if sc.server.connected is True:
        print('Connected')
        # Without the sleep, connected seems to be true, but a message can't be sent?
        time.sleep(1)
        bot_say('<!here> Quiz starting. *{title}* - {description}.\n\nThere are *{total}* total answers. *{goldens} golden answers* :tada: worth *{golden_points}* points :moneybag: each. Chosen at random.'.format(
            title=json_data['title'],
            total=STARTING_ANSWER_COUNT,
            description=json_data['description'],
            goldens=len(golden_answers),
            golden_points=GOLDEN_ANSWER_POINTS
        ))

    # Returns "not_allowed_token_type". Apparently bots can't join channels, but have to be invited?
    # r=sc.api_call(
    #     "channels.join",
    #     name="#quiz"
    # )
    # print(r)

    # [{'type': 'message', 'user': 'UC7HXJ319', 'text': 'a', 'client_msg_id': 'a898be5b-2cdf-40f4-b9c9-220b8c81b431', 'team': 'TC75G1A3B', 'channel': 'CCAMPJ57E', 'event_ts': '1534609801.000200', 'ts': '1534609801.000200'}]
    i = 0

    # Main game loop

    while sc.server.connected is True:
        read = sc.rtm_read()

        point_weight = check_if_points_escalated()

        if len(read) is 0:
            time.sleep(WEBSOCKET_READLOOP_SLEEP)
            continue

        if 'type' in read[0]:
            if read[0]['type'] == 'user_typing':
                time.sleep(WEBSOCKET_READLOOP_SLEEP)
                continue

            if read[0]['type'] == 'message' and 'text' in read[0]:
                (user, time_at, guess) = parse_message(read)

                if 'results' in guess and user == QUIZ_MASTER:
                    quiz_results(sc, results_object, forced=True)

                # Right answer
                if guess in answers:
                    last_correct_answer = float(time_at)

                    if guess in golden_answers:
                        point_weight = GOLDEN_ANSWER_POINTS
                        bot_say('A Golden answer was found! "{}" :tada: by user <@{}>. {} points!'.format(
                            guess, user, point_weight))
                    else:
                        bot_say('Answer found! "{}" by <@{}>. {} point{plural}!'.format(
                            guess, user, point_weight, plural=check_plural(point_weight)))
                    if user not in results_object:
                        results_object[user] = {}
                        results_object[user]['score'] = point_weight
                        results_object[user]['total_correct_answers'] = 1
                    else:
                        results_object[user]['score'] += point_weight
                        results_object[user]['total_correct_answers'] += 1

                    bot_reaction(msg_timestamp=time_at,
                                 emoji='heavy_check_mark')

                    if guess in golden_answers:
                        bot_reaction(msg_timestamp=time_at, emoji='tada')

                    # Not the best way if the list is huge? Or if there's dupes?
                    answers.remove(guess)
                    sc.rtm_send_message(
                        "#quiz", "There are {} answers left".format(len(answers)))

                    # Reset point offer increase
                    POINT_ESCALATION_OFFERED = False
                    point_weight = POINT_DEFAULT_WEIGHT
        else:
            print(read)
        i += 1
        # if i < 10:
        #     sc.rtm_send_message("#quiz", "test {}".format(i))

        if len(answers) == 0:
            quiz_results(sc, results_object)

else:
    print("Connection Failed")
