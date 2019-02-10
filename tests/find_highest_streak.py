import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from quizbot import *
print(WEBSOCKET_READLOOP_SLEEP)

player1 = Player('AAAA')
player1.total_guesses += 1
player1.answer_time(1.0)
player1.inc_score(1)
player1.inc_score(1)
player1.inc_score(1)
# player1.inc_score(1)

player2 = Player('BBBB')
player2.total_guesses += 2
player2.answer_time(1.5)
player2.inc_score(1)
player2.inc_score(2)
# player2.inc_score(1)
# player2.inc_score(1)


logger.info(Player.dump_instances())

# print(Player.find_high_streak_players())
quiz_results('', '')
