from slackclient import SlackClient
import time
import random
import os
import json
import sys
from statistics import mean
import logging
from html import unescape
from config import *
from misc_functions import *
from math import floor

FORMAT = '%(asctime)s %(name)s %(levelname)5s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

#
# Config
#
OFFLINE = False  # Allow telnet interface to simulate chat
# Without this, we might hit a rate-limit on the Slack RTM
WEBSOCKET_READLOOP_SLEEP = 0.1  # Pauses between reads when no messages waiting

# Slack user Id of user who can issue commands
QUIZ_MASTER = os.environ['QUIZ_MASTER']
QUIZ_MASTER_DIRECT_CHAT = os.environ['QUIZ_MASTER_DIRECT_CHAT']
QUIZ_CHANNEL_ID = os.environ['QUIZ_CHANNEL_ID']  # The Quiz channel


# bot
slack_token = os.environ.get("SLACK_BOT_TOKEN", None)
if OFFLINE:
    import offline_simulator
    sc = offline_simulator.SocketServer()
else:
    sc = SlackClient(slack_token)


def clean_answer(text):
    # TODO: Support full override of what chars are cleaned in the quiz json
    # This is True or False for now
    if not CLEAN_ANSWERS:
        return text

    # TODO: Maths quizes shouldn't clean '-'
    for character in ['?', '!', ',', '.', '\\', '\'', ':', '-']:
        text = text.replace(character, "")
    return text.lower()


# Init some things. Should all go away with a future refactoring
QUESTION_COUNT = 0
REMAINING_QUESTIONS = 0
POINT_ESCALATION_OFFERED = False
CLUES_OFFERED = 0
point_weight = 0

question_answered_correctly = False
question_asked = False

# Use a global for now until more refactoring. Later will be passed properly
# This will be set as a new 'Question' instance when ask_question() is invoked
# point escalation, game loop etc will use the global.
cur_question = ''

results_object = {}

answers = []
answers_found = []
STARTING_ANSWER_COUNT = 0
golden_answers = []  # Only used by a list style quiz

last_question_time = 0.0
# Set the first correct answer time after the first question is asked.
last_correct_answer = 0.0

ANTIPABLO_SPACE = False
ANTIPABLO_LETTERS = False

RESULTS_STREAKERS_MSG = ''

# Load up the questions
with open(QUESTION_FILE, encoding='utf-8') as file:
    json_data = json.load(file)
    if json_data.get('mode') in ['QA', 'MultiChoice']:
        CURRENT_QUESTION = 0
        QUESTION_COUNT = len(json_data['questions'])
        REMAINING_QUESTIONS = QUESTION_COUNT
    elif json_data.get('mode') in ['List']:  # For now, just a list style quiz
        for answer in json_data['answers']:
            if answer != '':
                answers.append(clean_answer(
                    answer.strip().replace('&', '&amp;')))
        STARTING_ANSWER_COUNT = len(answers)
        golden_answers = select_golden_answers(answers)


class Quiz():
    def __init__(self, quiz_json):
        self.mode = quiz_json.get('mode')
        self.tiebreaker = quiz_json.get('tiebreaker')
        self.shitlist = []

        if self.mode == 'QA':
            # Autogen all clues unless explicitly set to False
            # Ie, maths quizes
            self.autogen_clues = quiz_json.get('autogen_clues', True)
        elif self.mode == 'MultiChoice':
            self.multichoice = True
            self.autogen_clues = False
            global CLEAN_ANSWERS
            CLEAN_ANSWERS = False
        elif self.mode == 'List':
            pass
        else:
            logger.error(f'Unknown quiz mode: {self.mode}')
            raise Exception('Unknown quiz mode')


quiz = Quiz(json_data)

if quiz.mode in ['List']:
    logger.info(answers)
    logger.info('golden: {}'.format(golden_answers))


def get_username(user_id):
    if OFFLINE:
        return user_id
    global sc
    response = sc.api_call(
        "users.info",
        user=user_id
    )
    return response['user']['profile']['display_name']


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


def allocate_high_streak_bonus_points():
    global RESULTS_STREAKERS_MSG
    # Award points to the player(s) with the highest streak
    # If a tie, split the points evenly.

    def at_user(u):
        return f'<@{u}>'

    if Player.high_streakers:
        points_to_share = get_combo_breaker_points(Player.highest_streak) * 2
        high_streak_bonus = points_to_share / len(Player.high_streakers)

        for streaker in Player.high_streakers:
            player = Player.load_player(streaker)

            player.score += high_streak_bonus
            player.bonus_score += high_streak_bonus
            logger.debug(
                f'Highest streak bonus. {high_streak_bonus} to player {player.user_id}')

        RESULTS_STREAKERS_MSG = f'Highest streak of the game ({Player.highest_streak}) by: '
        RESULTS_STREAKERS_MSG += ', '.join(map(at_user, Player.high_streakers))
        RESULTS_STREAKERS_MSG += f'. {high_streak_bonus} bonus points'
        if len(Player.high_streakers) > 1:
            RESULTS_STREAKERS_MSG += ' each! :broken_heart:'
        else:
            RESULTS_STREAKERS_MSG += '! :dollar:'


def highest_streakers_emoji(player):
    if player.user_id in Player.high_streakers:
        return ' :gem:'
    else:
        return ''


def quiz_results(client, results_object, forced=False):
    allocate_high_streak_bonus_points()

    Player.dump_instances()

    if forced:
        bot_say('Ok fine. You lot are useless! The results are...')
    else:
        bot_say('Quiz over! The results are...')

    result_output = ""

    player_results_by_points = Player.order_player_results()

    users_tied = Player.test_if_tiebreaker(player_results_by_points)
    if quiz.tiebreaker and users_tied:
        bot_say('.... wait! There is a tie for first place!')
        bot_say(f'The following tiebreaker question is for '
                f'{users_tied[0]} and {users_tied[1]} only!')

    for index, result in enumerate(player_results_by_points):
        score = result[0]
        user_id = result[1]
        player = Player.load_player(user_id)

        # Include anyone who made a guess in the results table.
        result_output += "{pos} {medal}) <@{user}>, score: {score:.1f}{bonus}.".format(
            pos=ordinal(index+1),
            medal=podium_medal(index+1, player_results_by_points),
            user=user_id,
            score=score,
            bonus=check_for_bonus(player.bonus_score),
        )
        # But only include other stats if they actually got something right
        if player.score > 0.0:
            result_output += " Correct: {answers} ({guess_percent:d}% accuracy).".format(
                answers=player.total_correct_answers,
                guess_percent=(round(
                    player.total_correct_answers /
                    player.total_guesses *
                    100))
            )
            if quiz.mode != 'List':
                result_output += " Average time: {avg:.1f}s.".format(
                    avg=player.average_answer_time
                )

            result_output += " Streak: {streak}{streak_emoji}".format(
                streak=player.highest_score_streak,
                streak_emoji=highest_streakers_emoji(player)
            )

        result_output += '\n'

    bot_say('{}'.format(result_output))
    logger.info('OUT: %s', result_output)
    if quiz.mode != 'List':
        fastest_time, fastest_user = Player.order_player_results(
            order_attribute='fastest_answer', reverse=False)[0]
        bot_say('Fastest answer time by <@{fastest_user}>: {fastest_time:.4f}s'.format(
            fastest_user=fastest_user, fastest_time=fastest_time))
    if Player.high_streakers:
        bot_say(RESULTS_STREAKERS_MSG)
    logger.info(f'Players ordered by points: {player_results_by_points}')
    sys.exit(0)


def bot_say(msg, channel=QUIZ_CHANNEL_ID):
    if OFFLINE:
        logger.info('OUT: bot_say: {}'.format(msg))
        return
    if channel == QUIZ_CHANNEL_ID:
        logger.debug(f'OUT: {msg}')
    else:
        logger.debug(f'OUT(PM): {msg}')
    # Don't post to slack if we're being invoked from a tester script
    if __name__ == '__main__':
        sc.rtm_send_message(channel, msg)


class Question():
    # json_data should be read in future from a Quiz class?
    def __init__(self, q_id):
        logger.info(
            f'New question loaded. question_id: {q_id}. Points: {POINT_DEFAULT_WEIGHT}')
        self.has_clues = False  # Flip if we find a clue, or autogen_clues is on
        self.autogen_clues = False
        self.has_parent = False
        self.points = POINT_DEFAULT_WEIGHT  # read from global for now
        self.original_points = POINT_DEFAULT_WEIGHT
        self.incorrect_guesses = []
        # build this up when looping through the choices
        self.possible_incorrect_answers = []

        # Slack module currently doesn't support setting mrkdown:false in the message
        self.disable_markdown = False  # Set to true if markdown chars detected in text

        if quiz.mode == 'List':
            pass

        if quiz.mode == 'QA':
            # TODO: Allow override in quiz json.
            # TODO: Also allow curated clues in each question?
            if quiz.autogen_clues:
                self.autogen_clues = True
                self.has_clues = True

        if quiz.mode == 'MultiChoice':
            self.has_parent = False

            q_object = json_data['questions'][q_id]
            key, value = [x for x in q_object.items()][0]
            self.question = safe_embolden(key)
            multiple_choices = value
            correct_choice = multiple_choices[0]
            random.shuffle(multiple_choices)
            self.num_choices = len(multiple_choices)

            # What do we do with more than 5 choices?
            #choice_letters = ['j', 'k', 'l', ';', '\'']
            #choice_letters = ['a', 's', 'd', 'f', 'g']
            #choice_letters = ['1', '2', '3', '4', '5']
            #choice_letters = ['a', 'b', 'c', 'd', 'e']
            #random_letter_selection = string.printable
            # letter_blacklist = ['I','O','0','l','\','*', '_', '~', '`','#','@',':','/']
            random_letter_selection = \
                '123456789abcdefghijkmnopqrstuvwxyz' \
                'ABCDEFGHJKLMNPQRSTUVWXYZ' \
                '!"$%&()+,-.;<=>?[]^{|}'
            choice_letters = random.sample(
                random_letter_selection, self.num_choices)
            for i in range(self.num_choices):
                choice_letter = choice_letters[i]
                choice = f'\n{choice_letter}) {multiple_choices[i]}'
                self.question += choice
                if multiple_choices[i] == correct_choice:
                    # Legacy hangup: answers is still a list of one.
                    self.answers = [choice_letter]
                    self.real_answer = choice.lstrip('\n')
                else:
                    self.possible_incorrect_answers.append(choice_letter)

        if quiz.mode == 'QA':
            for key, value in json_data['questions'][q_id].items():
                if key != "parent":
                    self.question = safe_embolden(key)
                    self.answers = [x.lower() for x in value]
                    self.real_answer = value

            try:
                question_parent = json_data['questions'][q_id]['parent']
                for key, value in question_parent.items():
                    # Assume only one item in "parent" key
                    self.parent_key = key
                    self.parent_value = value
                    self.has_parent = True
            except:
                self.has_parent = False

        if self.autogen_clues:
            # The type should really be an attribute forced in the quiz json. Or per Q
            if 'Anagram' in json_data['title']:
                # First letter of first answer
                self.first_clue = self.answers[0][0].upper()
                self.first_clue_text = f'The first letter for {self.question} is *{self.first_clue}*'

            else:  # Only NO VOWELS for now
                vowels_clue_list = find_vowels(self.answers[0])
                vowels_clue = ' '.join(vowels_clue_list[0:2]).upper()
                self.first_clue_text = f'The first two vowels for {self.question} are: *{vowels_clue}*'

            # First half of the first answer
            answer = self.answers[0]
            self.second_clue = answer[0:round(len(answer) / 2)].title()
            self.second_clue_text = f'The *first half* of {self.question} is: *{self.second_clue}*'

    def get_answer_parent(self):
        if self.has_parent:
            return f'({self.parent_key}: {self.parent_value})'
        else:
            return ''

    def update_points(self, points):
        self.points = points

    def check_multi_choice_spam_guess(self, guess):
        if quiz.mode != 'MultiChoice':
            return
        # TODO: move from global to Question property
        if question_answered_correctly:
            return
        if guess in self.answers:
            return
        if (
            MULTICHOICE_PENALISE_SPAM_GUESS
            and len(guess) == 1
            and guess not in self.possible_incorrect_answers
            and guess not in self.incorrect_guesses
        ):
            return True

    def check_multi_choice_guess(self, guess):
        if quiz.mode != 'MultiChoice':
            return
        # TODO: move from global to Question property
        if question_answered_correctly:
            return
        if guess in self.answers:
            return
        if guess in self.possible_incorrect_answers:
            self.incorrect_guesses.append(guess)
            self.possible_incorrect_answers.remove(guess)

            penalty = floor(self.num_choices /
                            (len(self.possible_incorrect_answers) + 1))
            if self.points > 1.0:
                self.update_points(self.original_points - penalty)
            return penalty


def check_if_points_escalated():
    # We need to set this to check in a later read loop. Make global
    global POINT_ESCALATION_OFFERED, point_weight, CLUES_OFFERED

    if POINT_ESCALATION_OFFERED is False and CLUES_OFFERED is 0:
        point_weight = POINT_DEFAULT_WEIGHT
    if (
        time.time() - last_correct_answer >= float(SECONDS_NO_GUESSES)
        and not POINT_ESCALATION_OFFERED
    ):
        point_weight = point_weight * POINT_INCREASE_MULTIPLE_1
        cur_question.update_points(point_weight)

        logger.info(f'Point escalation to {point_weight}')
        bot_say(
            'There have not been any correct guesses in {} seconds. '
            'Next correct answer worth {} points!'.format(
                SECONDS_NO_GUESSES, point_weight
            )
        )
        POINT_ESCALATION_OFFERED = True
    elif (
        time.time() - last_correct_answer >= float(SECONDS_UNTIL_CLUE)
        and CLUES_OFFERED == 0
        and quiz.mode == 'QA'
        and cur_question.has_clues
    ):
        point_weight = 0.5
        cur_question.update_points(point_weight)

        logger.info(f'First Clue offered. {point_weight} points')
        bot_say(
            'There have not been any correct guesses in {} seconds. '
            'Next answer now worth {} points with a clue:'.format(
                SECONDS_UNTIL_CLUE, point_weight
            )
        )
        bot_say(cur_question.first_clue_text)
        CLUES_OFFERED = 1
    elif (
        time.time() - last_correct_answer >= float(SECONDS_UNTIL_SECOND_CLUE)
        and CLUES_OFFERED == 1
        and quiz.mode == 'QA'
        and cur_question.has_clues
    ):
        point_weight = 0.1
        cur_question.update_points(point_weight)

        logger.info(f'Second Clue offered. {point_weight} points')
        bot_say(
            'You are all terrible. No correct guesses in {} seconds. '
            'Next answer now worth {} points with a big clue:'.format(
                SECONDS_UNTIL_SECOND_CLUE, point_weight
            )
        )
        bot_say(cur_question.second_clue_text)
        CLUES_OFFERED = 2

    return point_weight


def parse_message(read_line_object):
    # Sample message from Slack
    # [
    #     {
    #         'type': 'message',
    #         'user': 'UC7HXJ319'
    #         'text': 'a',
    #         'client_msg_id': 'a898be5b-2cdf-40f4-b9c9-220b8c81b431',
    #         'team': 'TC75G1A3B',
    #         'channel': 'CCAMPJ57E',
    #         'event_ts': '1534609801.000200',
    #         'ts': '1534609801.000200'
    #     }
    # ]

    # Answers have & as &amp; Full unescape might be overkill
    orig_msg = unescape(read_line_object[0]['text'])

    cleaned = clean_answer(orig_msg)
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
        if 'block' in cleaned:
            bad_user=cleaned.split(' ')[1].upper()
            logger.info(f'Shitlisting user {bad_user}')
            bot_say(f'<!here> Spammer detected! :angry: Shitlisting <@{bad_user}> for the rest of the quiz :poop:')
            quiz.shitlist.append(bad_user)


        if cleaned.startswith('say'):
            bot_say('<!here> ' + orig_msg[4:])

    logger.info(
        f"IN: {time.time()} - At {time_at} (event_ts: {event_ts}) "
        f"User {user} says: '{orig_msg}'. Cleaned: '{cleaned}'"
    )
    return (user, time_at, cleaned)


def get_combo_breaker_points(streak_broken):
    points = COMBO_BREAKER_BONUS_POINTS.get(streak_broken)
    if points:
        return points
    else:
        return COMBO_BREAKER_BONUS_POINTS_DEFAULT


class Player:
    instances = {}
    has_streak = ''
    last_correct = ''
    highest_streak = 0
    high_streakers = []

    def __init__(self, user_id):
        logger.info(f'New player seen. Adding {user_id}')
        self.user_id = user_id
        self.fastest_answer = 0.0
        self.answer_times = []
        self.average_answer_time = 0.0
        self.score = 0.0
        self.total_guesses = 0
        self.total_correct_answers = 0
        self.highest_score_streak = 0
        self.score_streak = 0
        self.bonus_score = 0.0
        self.multi_choice_spam_penalty = MULTICHOICE_SPAM_GUESS_POINT_RANGE[0]
        # TODO: async fetch the user fullname and populate for later use
        Player.instances[user_id] = self

    def inc_score(self, points):
        self.inc_streak()
        self.score += points
        self.total_correct_answers += 1
        logger.info(
            f'Answer correct by {self.user_id}. '
            f'Adding {points} points. Total: {self.score}. '
            f'Answered: {self.total_correct_answers}'
        )

    def dec_score(self, points):
        self.score -= points
        logger.info(
            f'Score penalty for {self.user_id}. -{points} points'
        )

    def apply_spam_penalty(self):
        penalty = self.multi_choice_spam_penalty
        self.dec_score(penalty)
        bot_say(
            f'<@{self.user_id}> loses {penalty} point{check_plural(penalty)} for guessing a terrible guess!')

        # Increment for next time
        penalty += MULTICHOICE_SPAM_GUESS_POINT_INCREMENT
        limit = MULTICHOICE_SPAM_GUESS_POINT_RANGE[1]
        if penalty >= limit:
            penalty = limit
        self.multi_choice_spam_penalty = penalty

    @staticmethod
    def save_streak_record(user_id, streak):
        if streak > Player.highest_streak:
            Player.high_streakers = [user_id]
            Player.highest_streak = streak
        elif streak == Player.highest_streak:
            if user_id not in Player.high_streakers:
                Player.high_streakers.append(user_id)
        else:
            pass

    def inc_streak(self):
        # self is breaking someone else's combo
        if Player.last_correct and Player.last_correct != self.user_id:
            prev = Player.load_player(Player.last_correct)
            logger.debug(
                f'Current streak of {prev.score_streak} - {prev.user_id} '
                f'broken by {self.user_id}')

            # This probably shouldn't be in the Player class. Not sure where to put it
            # Only trigger a breaker if the streak was bigger than threshold
            if prev.score_streak >= STREAK_BONUS_THRESHOLD:
                logger.debug(f'Combo breaker!')
                bonus_points = get_combo_breaker_points(prev.score_streak)
                bot_say(
                    f":zap: C-C-C-COMBO BREAKER! :zap: <@{prev.user_id}>'s "
                    f"streak :cut_of_meat: of {prev.score_streak} has been broken! :sob: "
                    f"{bonus_points} bonus point{check_plural(bonus_points)} "
                    f"to <@{self.user_id}> :tada:"
                )
                self.score += bonus_points
                self.bonus_score += bonus_points

            prev.score_streak = 0  # Reset the previous player's streak now that it's broken

        Player.last_correct = self.user_id  # Set last correct as current Player instance

        # Increase the Player's streak count
        self.score_streak += 1
        if self.score_streak > self.highest_score_streak:
            self.highest_score_streak = self.score_streak

        if self.score_streak >= STREAK_BONUS_THRESHOLD:
            Player.save_streak_record(self.user_id, self.score_streak)
            bot_say(
                f'<@{self.user_id}> just hit a streak of {self.score_streak} correct answers :fire:')

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
            logger.info('Dump User: {}. Vars: {}'.format(
                user_id, vars(player_instance)))

    @staticmethod
    def order_player_results(order_attribute='score', reverse=True):
        # TODO: Make better secondary ordering if two players have the same score
        # Perhaps by accuracy or most correct answers?
        results_table = []
        for user_id, player_instance in Player.instances.items():
            if user_id == QUIZ_MASTER and SKIP_QUIZ_MASTER_IN_RESULTS:
                pass
            else:
                if order_attribute == 'fastest_answer' and player_instance.fastest_answer == 0.0:
                    pass
                else:
                    results_table.append(
                        (getattr(player_instance, order_attribute), user_id)
                    )
        results_table.sort(reverse=reverse)
        return results_table

    @staticmethod
    def tiebreaker():
        pass

    @staticmethod
    def test_if_tiebreaker(results):
        if len(Player.instances) < 2:
            return False
        # Each tuple in the results list is (0.0, 'PLAYER_ID')
        p1 = Player.load_player(results[0][1])
        p2 = Player.load_player(results[1][1])
        if p1.score == p2.score:
            logger.info(
                f'Tie found ({p1.score}) between {p1.user_id} and {p2.user_id}')
            return (p1.user_id, p2.user_id)
        else:
            return False


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
                global last_question_time, last_correct_answer, question_asked
                last_question_time = self.time_at
                last_correct_answer = last_question_time
                question_asked = True
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


def ask_question(question_id):
    global answers, question_asked, question_answered_correctly, cur_question
    # Needs to be global to reset after a question timeout
    global POINT_ESCALATION_OFFERED, point_weight, CLUES_OFFERED
    question_answered_correctly = False

    # Instantiate question object, set global. Pass properly with later refactor
    cur_question = Question(question_id)
    q = cur_question

    bot_say('Question {i}) {question}'.format(
        i=question_id+1, question=check_for_pablo(q.question)))
    # Set global
    answers = q.answers
    logger.info('Asking question id {}. Listening for answer: {}'.format(
        question_id, q.answers))
    # PM QUIZ_MASTER (hardcoded channel for now)
    bot_say(
        f'{q.answers} - {q.get_answer_parent()} for question {q.question}',
        QUIZ_MASTER_DIRECT_CHAT
    )

    if OFFLINE:
        # Normal flow is to set these times based on the confirmation response
        # from Slack when we ask the question. Keep simple and just force to now()
        global last_question_time, last_correct_answer
        last_question_time = time.time()
        last_correct_answer = last_question_time

    POINT_ESCALATION_OFFERED = False
    point_weight = POINT_DEFAULT_WEIGHT
    CLUES_OFFERED = 0


#    _________    __  _________   __    ____  ____  ____
#   / ____/   |  /  |/  / ____/  / /   / __ \/ __ \/ __ \
#  / / __/ /| | / /|_/ / __/    / /   / / / / / / / /_/ /
# / /_/ / ___ |/ /  / / /___   / /___/ /_/ / /_/ / ____/
# \____/_/  |_/_/  /_/_____/  /_____/\____/\____/_/


def game_loop():
    # Yuck!
    global CURRENT_QUESTION, REMAINING_QUESTIONS, point_weight, answers, \
        last_correct_answer, question_answered_correctly, question_asked, \
        POINT_ESCALATION_OFFERED, CLUES_OFFERED, answers_found, cur_question, \
        last_question_time

    if sc.rtm_connect(with_team_state=True):

        while sc.server.connected is False:
            logger.info('Waiting for connection..')
            time.sleep(1)

        # Post starting messages when first connected
        if sc.server.connected is True:
            logger.info('Connected')
            # Without the sleep, connected seems to be true, but a message can't be sent?
            time.sleep(1)
            if quiz.mode in ['QA', 'MultiChoice']:
                bot_say(
                    '<!here> Quiz starting. {title} - {description}.\n\n'
                    'There are *{total}* total questions.'.format(
                        title=safe_embolden(json_data['title']),
                        total=QUESTION_COUNT,
                        description=json_data['description']
                    )
                )
                bot_say(
                    'Quiz starting! - {}'.format(json_data['title']),
                    QUIZ_MASTER_DIRECT_CHAT
                )
                time.sleep(PAUSE_BEFORE_FIRST_QUESTION)
                last_correct_answer = time.time()
                # Makes new question instance in global cur_question
                ask_question(CURRENT_QUESTION)
            elif quiz.mode == 'List':
                bot_say(
                    '<!here> Quiz starting. {title} - {description}.\n\n'
                    'There are *{total}* total answers. *{goldens} golden answers*'
                    ':tada: worth *{golden_points}* points :moneybag: each. '
                    'Chosen at random.'.format(
                        title=safe_embolden(json_data['title']),
                        total=STARTING_ANSWER_COUNT,
                        description=json_data['description'],
                        goldens=len(golden_answers),
                        golden_points=GOLDEN_ANSWER_POINTS
                    )
                )
                cur_question = Question(0)

        # Main game loop

        while sc.server.connected is True:
            # End the quiz if no answers left
            if quiz.mode in ['QA', 'MultiChoice']:
                if REMAINING_QUESTIONS == 0:
                    quiz_results(sc, results_object)
            elif quiz.mode in ['List']:
                if len(answers) == 0:
                    quiz_results(sc, results_object)

            # Set the points available for the next answer
            if question_asked:
                point_weight = check_if_points_escalated()

            # If we hit the question timeout, give up and move on to the next question
            if (
                question_asked
                and (time.time() - last_question_time >= float(QUESTION_TIMEOUT))
                and quiz.mode in ['QA', 'MultiChoice']
            ):
                logger.info(
                    f'Question timeout ({QUESTION_TIMEOUT}) reached. Giving up waiting.')
                # Pretend a question was answered to fool the rest of the loop
                question_answered_correctly = True
                question_asked = False
                last_correct_answer = time.time()

                bot_say(
                    f':cold_sweat: :dizzy_face: Too hard or am I broken:interrobang:  '
                    f'The answer was: {safe_embolden(cur_question.real_answer)} {cur_question.get_answer_parent()}. '
                    f'Moving on to next question...'
                )
                timedout_answers = answers  # Save to check for cheaky guesses
                answers = ''  # Clear, so a player can't guess after we've hit the timeout

            # Check if we've waited SECONDS_BETWEEN_ANSWER_AND_QUESTION before asking next Q
            if (
                quiz.mode in ['QA', 'MultiChoice']
                and question_answered_correctly
                and not question_asked
                and (last_correct_answer + float(SECONDS_BETWEEN_ANSWER_AND_QUESTION)) <= time.time()
            ):
                logger.debug(
                    f'Waited {SECONDS_BETWEEN_ANSWER_AND_QUESTION} seconds after correct answer'
                )
                CURRENT_QUESTION = CURRENT_QUESTION+1
                REMAINING_QUESTIONS = REMAINING_QUESTIONS-1
                if REMAINING_QUESTIONS != 0:
                    answers_found=[]
                    ask_question(CURRENT_QUESTION)

            msg_counter = 0
            for read_msg in sc.rtm_read():
                msg_counter += 1
                message = Message(read_msg)
                if not message.is_guess:
                    continue  # Read next message

                # Quick hack to avoid more work after Message became a class. Awaiting refactor
                (user, time_at, guess) = (
                    message.user, message.time_at, message.guess)

                player = Player.load_player(user)
                if user == 'USLACKBOT':
                    logger.info('Skipping slackbot message')
                    continue
                if user in quiz.shitlist:
                    logger.info(f'Skipping shitlist {user} message')
                    continue
                if 'results' in guess and user == QUIZ_MASTER:
                    quiz_results(sc, results_object, forced=True)

                if 'skip' in guess and user == QUIZ_MASTER:
                    last_question_time -= (QUESTION_TIMEOUT + 500.0)

                player.total_guesses += 1

                try:
                    if guess in timedout_answers:
                        bot_reaction(msg_timestamp=time_at, emoji='angry')
                except:
                    pass
                # Answer was right, but already found
                if guess in answers_found and quiz.mode != 'MultiChoice':
                    bot_reaction(msg_timestamp=time_at,
                                 emoji='snail')

                # MultiChoice check
                if quiz.mode in ['MultiChoice']:
                    if cur_question.check_multi_choice_spam_guess(guess):
                        player.apply_spam_penalty()
                    point_penalty = cur_question.check_multi_choice_guess(
                        guess)
                else:
                    point_penalty = False
                if point_penalty:
                    bot_reaction(msg_timestamp=time_at,
                                 emoji='negative_squared_cross_mark')
                    bot_say('<@{user}> loses {point_penalty} point{plural_p}!'
                            ' Question now worth {p} point{plural_q}! :man-golfing:'.format(
                                user=user,
                                point_penalty=point_penalty,
                                p=cur_question.points,
                                plural_p=check_plural(point_penalty),
                                plural_q=check_plural(cur_question.points)
                            )
                            )

                    player.dec_score(point_penalty)

                # Right answer
                if guess in answers:
                    last_correct_answer = float(time_at)
                    question_answered_correctly = True
                    question_asked = False
                    logger.info(
                        f'Answer found. Waiting for {SECONDS_BETWEEN_ANSWER_AND_QUESTION} '
                        'seconds before asking next'
                    )

                    if guess in golden_answers:
                        bot_reaction(msg_timestamp=time_at, emoji='tada')
                        point_weight = GOLDEN_ANSWER_POINTS
                        bot_say(
                            f'A Golden answer was found! "{guess}" :tada: by user <@{user}>. '
                            f'{point_weight} points!'
                        )
                    else:
                        real_answer = guess  # TODO: Read original formatted answer
                        if quiz.mode == 'MultiChoice':
                            real_answer = cur_question.real_answer

                        answer_parent = cur_question.get_answer_parent()
                        if answer_parent:
                            answer_parent = answer_parent + ' '
                        bot_say(
                            'Answer found! "{real_answer}" {answer_parent}by <@{user}>. '
                            '{points} point{plural}!'.format(
                                real_answer=safe_embolden(real_answer),
                                user=user,
                                # TODO: Refactor with Question class:
                                answer_parent=answer_parent,
                                points=cur_question.points,
                                plural=check_plural(cur_question.points)
                            )
                        )

                    player.inc_score(cur_question.points)
                    player.answer_time(last_correct_answer-last_question_time)

                    bot_reaction(msg_timestamp=time_at,
                                 emoji='heavy_check_mark')

                    # Not the best way if the list is huge? Or if there's dupes?
                    answers.remove(guess)
                    answers_found.append(guess)
                    if quiz.mode in ['List']:
                        bot_say("There are {} answers left".format(len(answers)))

                    # Reset point offer increase
                    POINT_ESCALATION_OFFERED = False
                    CLUES_OFFERED = 0
                    point_weight = POINT_DEFAULT_WEIGHT

            # rtm_read() says it makes a list of multiple events, but only ever seems to have 1?
            # If it *was* 0, then pause before next read.
            if msg_counter == 0:
                # logger.debug('Found %d messages in websocket', msg_counter)
                # logger.debug('Ending websocket read loop. Sleeping %f',
                #              WEBSOCKET_READLOOP_SLEEP)
                time.sleep(WEBSOCKET_READLOOP_SLEEP)

    else:
        print("Connection Failed")


if __name__ == '__main__':
    game_loop()
