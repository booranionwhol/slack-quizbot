# These functions should really be in an appropriate Class
# They are all generic and not related to the Bot, Results, or Questions for now


def select_golden_answers():
    random.seed(os.urandom(1024))
    for _ in range(1, int(len(answers)/10)):
        golden_random = random.choice(answers)
        if golden_random not in golden_answers:
            golden_answers.append(golden_random)


def find_vowels(line):
    """ Find all the vowels in the answer, to use for clues """
    vowels = ['a', 'e', 'i', 'o', 'u']
    clue_list = []
    for letter in line.lower():
        if letter in vowels:
            clue_list.append(letter)
    return clue_list


def toggle(var):
    if var == True:
        return False
    if var == False:
        return True


def check_plural(num):
    if num == 1:
        return ''
    else:
        return 's'


def check_for_bonus(points):
    if points > 0.0:
        return f' (Bonus: {points})'
    else:
        return ''


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


def check_for_markdown(string):
    # If any of these chars exist in the loaded question string. Disable slack markdown
    SPECIAL_MARKDOWN_CHARS = ['*', '_', '~', '`']

    for char in SPECIAL_MARKDOWN_CHARS:
        if char in string:
            return True


def safe_embolden(string):
    # URLs get parsed by slack
    if '*' in string or 'http' in string:
        return string
    else:
        return f'*{string}*'
