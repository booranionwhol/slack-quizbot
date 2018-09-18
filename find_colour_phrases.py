import re
from collections import Counter

colours = [
    'redXX',
    'green',
    'blue',
    'orange',
    'black',
    'white',
    'purple',
    'indigo',
    'violet',
    'yellow',
    'pink',
    'cyan',
    'magenta',
    'grey',
    'brown',
    'navy'
]
colours = [
    'cat',
    'dog',
    'horse',
    'fox',
    'mouse',
    'snake',
    'cow',
    'pig',
    'chicken',
    'sheep',
    'bird',
    'elk',
    'deer',
    'lemur',
    'impala',
    'rat',
    'frog',
    'toad',
    'fly',
    'bee',
    'wasp',
    'fish',
    'crow',
    'raven',
    'robin',
    'eagle',
    'monkey',
    'ape',
    'tiger',
    'lion',
]
# Previously checked, remove from list to not waste time on retries
colours_dont_exist=[
    'horse',
    'pig',
    'chicken',
    'sheep',
    'bird',
    'impala',
    'frog',
    'fish',
    'crow',
    'monkey',
    'tiger'
]
colours_too_common=[
    'ape',
    'bee',
    'rat'
]
# Make the list shorter
for remove in colours_dont_exist+colours_too_common:
    colours.remove(remove)
counter=[]
strip_chars = ['\'', ':', ';', '-', '.', '!', '?']
BACKWARDS = False
with open('shakespeare_complete.txt', encoding='utf-8') as file:
    for line in file:
        answers = []
        question = line.strip()
        if len(question) <= 15:
            continue
        question_cleaned = question
        for char in strip_chars:
            question_cleaned = question_cleaned.replace(char, '')

        if BACKWARDS:
            question_backwards = question_cleaned.replace(' ', '')
            question_cleaned = ''
            for letter in reversed(question_backwards):
                # Build up the string again, reversed
                question_cleaned = question_cleaned + letter
        for colour in colours:
            if BACKWARDS:
                pattern = colour
                # for letter in reversed(colour):
                #     pattern = pattern + letter
            else:
                # Construct a pattern that matches an optional space after each letter
                pattern = ' ?'.join(colour)
                # Eg: 'r ?e ?d'
            re_pattern = re.compile(pattern, re.IGNORECASE)
            results = re.findall(re_pattern, question_cleaned)
            for result in results:
                # Only include the match if it has only one space
                # And has not already been added to the answers
                if result.count(' ') == 1 and colour not in answers:
                    answers.append(colour)
                # If we're searching backwards, we're ignoring spaces
                if BACKWARDS and colour not in answers:
                    answers.append(colour)
        if len(answers) >= 1:
            for answer in answers:
                counter.append(answer)
            print(question, answers)
print(Counter(counter).most_common())