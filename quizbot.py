from slackclient import SlackClient
import time
import random
import os
import json
import sys
from statistics import mean
import logging

FORMAT = '%(asctime)s %(name)s %(levelname)5s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

#
# Config
#
OFFLINE = False  # Allow telnet interface to simulate chat
# Without this, we might hit a rate-limit on the Slack RTM
WEBSOCKET_READLOOP_SLEEP = 0.1  # Pauses between reads when no messages waiting

# Point increase when nobody has guessed for X seconds. Should mean the current question is hard
SECONDS_NO_GUESSES = 30
SECONDS_UNTIL_CLUE = 60  # Point decrease, and first clue offered
SECONDS_UNTIL_SECOND_CLUE = 90  # Point decrease, second, bigger clue offered
POINT_DEFAULT_WEIGHT = 1
GOLDEN_ANSWER_POINTS = 3
# Slack user Id of user who can issue commands
QUIZ_MASTER = os.environ['QUIZ_MASTER']
QUIZ_MASTER_DIRECT_CHAT = os.environ['QUIZ_MASTER_DIRECT_CHAT']
QUIZ_CHANNEL_ID = os.environ['QUIZ_CHANNEL_ID']  # The Quiz channel
# For quick debug to go straight to a fake results table.
CHEAT_TO_RESULTS = False
QUESTION_FILE = 'questions/qa_test.json'


# bot
slack_token = os.environ.get("SLACK_BOT_TOKEN", None)
if OFFLINE:
    import offline_simulator
    sc = offline_simulator.SocketServer()
else:
    sc = SlackClient(slack_token)


def clean_answer(text):
    for character in ['?', '!', ',', '.', '\\', '\'', ':', '-']:
        text = text.replace(character, "")
    return text.lower()


# Init some things. Should all go away with a future refactoring
QUIZ_MODE = ''
QUESTION_COUNT = 0
REMAINING_QUESTIONS = 0
POINT_ESCALATION_OFFERED = False
CLUES_OFFERED = 0

answers = []
answers_found = []
STARTING_ANSWER_COUNT = 0
golden_answers = []  # Only used by a list style quiz

last_question_time = 0.0
# Set the first correct answer time after the first question is asked.
last_correct_answer = 0.0

ANTIPABLO_SPACE = False
ANTIPABLO_LETTERS = False


def select_golden_answers():
    random.seed(os.urandom(1024))
    for _ in range(1, int(len(answers)/10)):
        golden_random = random.choice(answers)
        if golden_random not in golden_answers:
            golden_answers.append(golden_random)


# Load up the questions
with open(QUESTION_FILE, encoding='utf-8') as file:
    json_data = json.load(file)
    if json_data.get('mode') == 'QA':
        QUIZ_MODE = 'QA'
        CURRENT_QUESTION = 0
        QUESTION_COUNT = len(json_data['questions'])
        REMAINING_QUESTIONS = QUESTION_COUNT
    else:  # For now, just a list style quiz
        for answer in json_data['answers']:
            if answer != '':
                answers.append(clean_answer(
                    answer.strip().replace('&', '&amp;')))
        STARTING_ANSWER_COUNT = len(answers)
        select_golden_answers()

logger.info(answers)
logger.info('golden: {}'.format(golden_answers))


results_object = {}
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
    if OFFLINE:
        return user_id
    global sc
    response = sc.api_call(
        "users.info",
        user=user_id
    )
    return response['user']['profile']['display_name']


def ordinal(num):
    # Taken from https://codereview.stackexchange.com/questions/41298/producing-ordinal-numbers
    SUFFIXES = {1: 'st', 2: 'nd', 3: 'rd'}
    # Checking for 10-20 because those are the digits that
    # don't follow the normal counting scheme.
    if 10 <= num % 100 <= 20:
        suffix = 'th'
    else:
        # the second parameter is a default.
        suffix = SUFFIXES.get(num % 10, 'th')
    return str(num) + suffix


def podium_medal(position, total_player_results):
    if position == 1:
        return ':first_place_medal:'
    if position == 2:
        return ':second_place_medal:'
    if position == 3:
        return ':third_place_medal:'
    # Last place
    if position == len(total_player_results):
        return ':poop:'
    else:
        return ''


def quiz_results(client, results_object, forced=False):
    if forced:
        bot_say('Ok fine. You lot are useless! The results are...')
    else:
        bot_say('Quiz over! The results are...')

    result_output = ""
    for index, result in enumerate(Player.order_player_results()):
        score = result[0]
        user_id = result[1]
        player = Player.load_player(user_id)
        result_output += "{pos} {medal}) <@{user}>, score: {score:.1f}.".format(
            pos=ordinal(index+1),
            medal=podium_medal(index+1, Player.order_player_results()),
            user=user_id,
            score=score
        )
        if player.score > 0.0:
            result_output += " Correct answers: {answers} ({guess_percent:02.0f}% accuracy). Average time: {avg:.4f}s".format(
                answers=player.total_correct_answers,
                guess_percent=(
                    player.total_correct_answers /
                    player.total_guesses *
                    100),
                avg=player.average_answer_time
            )
        result_output += '\n'
    bot_say('{}'.format(result_output))
    logger.info('OUT: %s', result_output)
    fastest_time, fastest_user = Player.order_player_results(
        order_attribute='fastest_answer', reverse=False)[0]
    bot_say('Fastest anwswer time by <@{fastest_user}>: {fastest_time:.4f}s'.format(
        fastest_user=fastest_user, fastest_time=fastest_time))
    Player.dump_instances()
    logger.info('Players ordered by points: {}'.format(
        Player.order_player_results()))
    sys.exit(0)


def bot_say(msg, channel=QUIZ_CHANNEL_ID):
    if OFFLINE:
        logger.info('OUT: bot_say: {}'.format(msg))
        return
    if channel == QUIZ_CHANNEL_ID:
        logger.debug(f'OUT: {msg}')
    else:
        logger.debug(f'OUT(PM): {msg}')
    sc.rtm_send_message(channel, msg)


def goodbye():
    bot_say('I have been terminated. NO MORE QUIZ. :tired_face:')


def find_vowels(line):
    """ Find all the vowels in the answer, to use for clues """
    vowels = ['a', 'e', 'i', 'o', 'u']
    clue_list = []
    for letter in line.lower():
        if letter in vowels:
            clue_list.append(letter)
    return clue_list


def check_if_points_escalated():
    # We need to set this to check in a later read loop. Make global
    global POINT_ESCALATION_OFFERED, point_weight, CLUES_OFFERED

    if POINT_ESCALATION_OFFERED is False and CLUES_OFFERED is 0:
        point_weight = POINT_DEFAULT_WEIGHT
    if time.time()-last_correct_answer >= float(SECONDS_NO_GUESSES):
        if POINT_ESCALATION_OFFERED is False:
            point_weight = 2
            bot_say('There have not been any correct guesses in {} seconds. Next correct answer worth {} points!'.format(
                SECONDS_NO_GUESSES, point_weight))
            logger.info(
                'Point escalation')
            POINT_ESCALATION_OFFERED = True
    if time.time()-last_correct_answer >= float(SECONDS_UNTIL_CLUE) and CLUES_OFFERED == 0 and QUIZ_MODE == 'QA':
        point_weight = 0.5
        bot_say('There have not been any correct guesses in {} seconds. Next answer now worth {} points with a clue:'.format(
            SECONDS_UNTIL_CLUE, point_weight))

        if 'Anagrams' in json_data['title']:
            for question, answer in json_data['questions'][CURRENT_QUESTION].items():
                if question == 'parent':
                    # The question dict may have another key.
                    # TODO: Restructure the questions list to have a nested question dict and a clues dict?
                    continue
                first_letter = answer[0][0].upper()
                bot_say(
                    f'The first letter for *{question}* is *{first_letter}*')
        else:
            for question, answer in json_data['questions'][CURRENT_QUESTION].items():
                if question == 'parent':
                    # The question dict may have another key.
                    # TODO: Restructure the questions list to have a nested question dict and a clues dict?
                    continue
                vowels_clue_list = find_vowels(answer[0])
                vowels_clue = ' '.join(vowels_clue_list[0:2])

                bot_say('The first two vowels for *{question}* are: *{vowels}*'.format(
                    question=question,
                    vowels=vowels_clue.upper()
                ))
        logger.info('Clue offered')
        CLUES_OFFERED = 1
    if time.time()-last_correct_answer >= float(SECONDS_UNTIL_SECOND_CLUE) and CLUES_OFFERED == 1 and QUIZ_MODE == 'QA':
        point_weight = 0.1
        bot_say('You are all terrible. No correct guesses in {} seconds. Next answer now worth {} points with a big clue:'.format(
            SECONDS_UNTIL_SECOND_CLUE, point_weight))

        for question, answer in json_data['questions'][CURRENT_QUESTION].items():
            if question == 'parent':
                # The question dict may have another key.
                # TODO: Restructure the questions list to have a nested question dict and a clues dict?
                continue
            # There should only be one question object.
            answer = answer[0]

        bot_say('The *first half* of *{question}* is: *{clue}*'.format(
            question=question,
            clue=answer[0:round(len(answer)/2)].title()
        ))
        logger.info('Second Clue offered')
        CLUES_OFFERED = 2

    return point_weight


def toggle(var):
    if var == True:
        return False
    if var == False:
        return True


def parse_message(read_line_object):
    cleaned = clean_answer(read_line_object[0]['text'])
    user = read_line_object[0]['user']
    time_at = read_line_object[0]['ts']
    channel = read_line_object[0]['channel']
    event_ts = read_line_object[0].get('event_ts', None)
    # Check if direct message
    # print(f'C: {channel}, u: {user}')
    if (channel[0:2] == 'DC' or channel[0:2] == 'DD') and user == QUIZ_MASTER:
        logger.info(
            'IN: Private Message received from QUIZ_MASTER: {}'.format(cleaned))
        if cleaned == 'remaining':
            bot_say(str(answers), channel)
        if cleaned == 'space':
            global ANTIPABLO_SPACE
            ANTIPABLO_SPACE = toggle(ANTIPABLO_SPACE)
            logger.info(f'Setting ANTIPABLO_SPACE to {ANTIPABLO_SPACE}')
        if cleaned == 'letter':
            global ANTIPABLO_LETTERS
            ANTIPABLO_LETTERS = toggle(ANTIPABLO_LETTERS)
            logger.info(f'Setting ANTIPABLO_LETTERS to {ANTIPABLO_LETTERS}')
        if cleaned.startswith('say'):
            bot_say('<!here> ' + read_line_object[0]['text'][4:])

    logger.info("IN: {time_now} - At {time_msg} (event_ts: {event_ts}) User {user} says: '{orig}'. Cleaned: '{cleaned}'".format(
        user=user,
        time_now=time.time(),
        time_msg=time_at,
        orig=read_line_object[0]['text'],
        event_ts=event_ts,
        cleaned=cleaned
    ))
    return (user, time_at, cleaned)


class Player:
    instances = {}

    def __init__(self, user_id):
        self.user_id = user_id
        self.fastest_answer = 0.0
        self.answer_times = []
        self.average_answer_time = 0.0
        self.score = 0.0
        self.total_guesses = 0
        self.total_correct_answers = 0
        Player.instances[user_id] = self

    def inc_score(self, points):

        self.score += points
        self.total_correct_answers += 1

    def answer_time(self, time):
        self.answer_times.append(round(time, 4))
        # Update fastest and average. These should probably be computed when read instead.
        self.fastest_answer = min(self.answer_times)
        self.average_answer_time = mean(self.answer_times)

    @staticmethod
    def load_player(user_id):
        if user_id in Player.instances:
            # Return existing Player instance object
            return Player.instances[user_id]
        else:  # else make a new one
            return Player(user_id)

    @staticmethod
    def dump_instances():
        for user_id, player_instance in Player.instances.items():
            logger.info('User: {}. Vars: {}'.format(
                user_id, vars(player_instance)))

    @staticmethod
    def order_player_results(order_attribute='score', reverse=True):
        results_table = []
        for user_id, player_instance in Player.instances.items():
            if user_id != QUIZ_MASTER:
                if order_attribute == 'fastest_answer' and player_instance.fastest_answer == 0.0:
                    pass
                else:
                    results_table.append(
                        (getattr(player_instance, order_attribute), user_id)
                    )
        results_table.sort(reverse=reverse)
        return results_table


class Message:
    def __init__(self, read_msg):
        self.is_guess = False
        self.is_question = False
        self.time_at = 0.0
        self.event_ts = 0.0
        self.user = ''
        self.guess = ''  # message text after cleaning for quiz guess
        if read_msg.get('type') and read_msg.get('text'):
            self.is_guess = True
            (self.user, self.time_at,
                self.guess) = parse_message([read_msg])
            read_msg.get('event_ts', 0.0)
        # Slack responds with 'ok' when the bot sends a message.
        elif read_msg.get('ok', False):
            if read_msg.get('text').startswith('Question'):
                self.is_question = True
                self.time_at = float(read_msg.get('ts'))
                # Point escalation logic is based from last_correct_answer time.
                # Allow this to work with new Q+A format also, by re-setting it to
                # the time the question was offered.
                global last_question_time, last_correct_answer
                last_question_time = self.time_at
                last_correct_answer = last_question_time
                logger.info(
                    'Question asked at slack ts: {}'.format(self.time_at))


UNICODE_SWAPS = {
    "H": ["\u041D"],
    "T": ['\u0422'],
    'B': ['\u0412'],
    'K': ['\u039A'],
    'N': ['\u039D'],
    'M': ['\u041C'],
    'S': ['\u0405']
}


def check_for_pablo(question):
    if ANTIPABLO_SPACE:
        question = question.replace(' ', u'\u2005')
    if ANTIPABLO_LETTERS:
        unicode_available = []
        # Build list of letter suitable to replace
        for index, letter in enumerate(question):
            if letter in UNICODE_SWAPS:
                unicode_available.append((index, letter))
        if len(unicode_available) >= 1:
            pos, letter = random.choice(unicode_available)
            replacement = random.choice(UNICODE_SWAPS[letter])
            question = question[:pos] + replacement + question[pos+1:]
    return question


def bot_reaction(msg_timestamp, emoji):
    sc.api_call(
        "reactions.add",
        channel=QUIZ_CHANNEL_ID,
        name=emoji,
        timestamp=msg_timestamp
    )


def check_plural(num):
    if num == 1:
        return ''
    else:
        return 's'


def ask_question(question_id):
    global answers
    for question, answer in json_data['questions'][question_id].items():
        if question == 'parent':
            # The question object may have another key.
            # TODO: Restructure the questions list to have a nested question dict and a clues dict?
            continue
        bot_say('Question {i}) *{question}*'.format(
            i=question_id+1, question=check_for_pablo(question)))
        # Set global
        answers = [x.lower() for x in answer]
        logger.info('Asking question id {}. Listening for answer: {}'.format(
            question_id, answers))
        # PM QUIZ_MASTER (hardcoded channel for now)
        bot_say(
            f'Asked question {question} {get_answer_parent(question_id)} for answer: {answers}', QUIZ_MASTER_DIRECT_CHAT)

    if OFFLINE:
        # Normal flow is to set these times based on the confirmation response
        # from Slack when we ask the question. Keep simple and just force to now()
        global last_question_time, last_correct_answer
        last_question_time = time.time()
        last_correct_answer = last_question_time


def get_answer_parent(question_id):
    try:
        question_parent = json_data['questions'][question_id]['parent']
        for key, value in question_parent.items():
            # Assume only one item in "parent" key
            return f'({key}: {value})'
    except:
        return ''


if sc.rtm_connect(with_team_state=True):

    while sc.server.connected is False:
        logger.info('Waiting for connection..')
        time.sleep(1)
    if sc.server.connected is True:
        logger.info('Connected')
        # Without the sleep, connected seems to be true, but a message can't be sent?
        time.sleep(1)
        if QUIZ_MODE == 'QA':
            bot_say('<!here> Quiz starting. {title} - {description}.\n\nThere are *{total}* total questions.'.format(
                title=json_data['title'],
                total=QUESTION_COUNT,
                description=json_data['description']
            ))
            time.sleep(12)
            last_correct_answer = time.time()
            ask_question(CURRENT_QUESTION)
        else:
            bot_say('<!here> Quiz starting. *{title}* - {description}.\n\nThere are *{total}* total answers. *{goldens} golden answers* :tada: worth *{golden_points}* points :moneybag: each. Chosen at random.'.format(
                title=json_data['title'],
                total=STARTING_ANSWER_COUNT,
                description=json_data['description'],
                goldens=len(golden_answers),
                golden_points=GOLDEN_ANSWER_POINTS
            ))

    # Sample message from Slack
    # [{'type': 'message', 'user': 'UC7HXJ319', 'text': 'a', 'client_msg_id': 'a898be5b-2cdf-40f4-b9c9-220b8c81b431', 'team': 'TC75G1A3B', 'channel': 'CCAMPJ57E', 'event_ts': '1534609801.000200', 'ts': '1534609801.000200'}]

    # Main game loop

    while sc.server.connected is True:
        # End the quiz if no answers left
        if QUIZ_MODE == 'QA':
            if REMAINING_QUESTIONS == 0:
                quiz_results(sc, results_object)
        else:
            if len(answers) == 0:
                quiz_results(sc, results_object)

        # Set the points available for the next answer
        point_weight = check_if_points_escalated()

        msg_counter = 0
        for read_msg in sc.rtm_read():
            msg_counter += 1
            message = Message(read_msg)
            if not message.is_guess:
                continue  # Read next message

            # Quick hack to avoid more work after Message became a class. Awaiting refactor
            (user, time_at, guess) = (message.user, message.time_at, message.guess)

            player = Player.load_player(user)

            if 'results' in guess and user == QUIZ_MASTER:
                quiz_results(sc, results_object, forced=True)

            player.total_guesses += 1

            # Answer was right, but already found
            if guess in answers_found:
                bot_reaction(msg_timestamp=time_at,
                             emoji='snail')
            # Right answer
            if guess in answers:
                last_correct_answer = float(time_at)

                if guess in golden_answers:
                    bot_reaction(msg_timestamp=time_at, emoji='tada')
                    point_weight = GOLDEN_ANSWER_POINTS
                    bot_say('A Golden answer was found! "{}" :tada: by user <@{}>. {} points!'.format(
                        guess, user, point_weight))
                else:
                    bot_say('Answer found! "{guess}" {answer_parent} by <@{user}>. {points} point{plural}!'.format(
                        guess=guess,
                        user=user,
                        # TODO: Refactor with Question class:
                        answer_parent=get_answer_parent(CURRENT_QUESTION),
                        points=point_weight,
                        plural=check_plural(point_weight)
                    ))

                player.inc_score(point_weight)
                player.answer_time(last_correct_answer-last_question_time)

                bot_reaction(msg_timestamp=time_at,
                             emoji='heavy_check_mark')

                # Not the best way if the list is huge? Or if there's dupes?
                answers.remove(guess)
                answers_found.append(guess)
                if QUIZ_MODE != 'QA':
                    bot_say("There are {} answers left".format(len(answers)))

                # Reset point offer increase
                POINT_ESCALATION_OFFERED = False
                CLUES_OFFERED = 0
                point_weight = POINT_DEFAULT_WEIGHT

                if QUIZ_MODE == 'QA':
                    CURRENT_QUESTION = CURRENT_QUESTION+1
                    REMAINING_QUESTIONS = REMAINING_QUESTIONS-1
                    if REMAINING_QUESTIONS != 0:
                        time.sleep(5)
                        ask_question(CURRENT_QUESTION)
        # rtm_read() says it makes a list of multiple events, but only ever seems to have 1?
        # If it *was* 0, then pause before next read.
        if msg_counter == 0:
            # logger.debug('Found %d messages in websocket', msg_counter)
            # logger.debug('Ending websocket read loop. Sleeping %f',
            #              WEBSOCKET_READLOOP_SLEEP)
            time.sleep(WEBSOCKET_READLOOP_SLEEP)

else:
    print("Connection Failed")
