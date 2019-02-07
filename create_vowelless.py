import json

qa_dict = []
vowels = ['a', 'e', 'i', 'o', 'u', ' ', '.', '\'']
with open('tourist_destinations_seed.txt') as file:
    lines = file.read().splitlines()

    for line in lines:
        answer, parent = line.split('|')
        answer = answer.lower()
        for vowel in vowels:
            answer = answer.replace(vowel, '')
        if len(answer) > 10:
            split_size = 4
        if len(answer) <= 10:
            split_size = 3
        result = []
        for i in range(0, len(answer), split_size):
            result.append(answer[i:i+split_size])
        # A letter on its own looks weird. Merge it to the previous block if found
        # TODO:
        # If the first word is 'The'. Merge the 'Th' to the right a bit randomly?
        if len(result[-1]) == 1 and len(result) >= 2:
            last_block = result.pop(-1)
            result[-1] = result[-1]+last_block

        cryptic = ' '.join(result).upper()
        # print(cryptic)
        #print('{"{}}": ["{}}"]},'.format(cryptic,answer))
        question_dict = {cryptic: [answer], 'parent': {'Location': parent}}
        qa_dict.append(question_dict)
print(json.dumps(qa_dict))
