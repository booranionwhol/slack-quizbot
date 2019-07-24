# Copy this file from config-example.py to config.py

PAUSE_BEFORE_FIRST_QUESTION = 25

# Point increase when nobody has guessed for X seconds. Should mean the current question is hard
SECONDS_NO_GUESSES = 20
SECONDS_UNTIL_CLUE = 100  # Point decrease, and first clue offered
SECONDS_UNTIL_SECOND_CLUE = 150  # Point decrease, second, bigger clue offered
QUESTION_TIMEOUT = 200  # Give up and move to the next question
# Non-blocking wait between a correct answer and next q
SECONDS_BETWEEN_ANSWER_AND_QUESTION = 10

POINT_DEFAULT_WEIGHT = 1
STREAK_BONUS_THRESHOLD = 3
GOLDEN_ANSWER_POINTS = 3  # For list style quizes

# Matrix of points awarded for breaking a streak
# key: value = streak_broken_size: points_awarded
COMBO_BREAKER_BONUS_POINTS = {1: 0, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6}
COMBO_BREAKER_BONUS_POINTS_DEFAULT = 5  # Awarded if beyond the above matrix
# HIGHEST_STREAK_BONUS_POINTS = x # For now use the COMBO_BREAKER_MATRIX? See what happens

QUESTION_FILE = 'questions/capital_cities3.json'
CLEAN_ANSWERS = True  # Disable for typing challenge and maths style quizes

SKIP_QUIZ_MASTER_IN_RESULTS = True  # Set to False for easier testing
