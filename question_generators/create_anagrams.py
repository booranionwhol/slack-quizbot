import random
import json

qa_dict = []
with open('capital_cities.txt') as f:
    lines = f.read().splitlines()

# random.shuffle(lines)

for line in lines:
    parent, city = line.split(',')
    line = city
    # TODO: Reshuffle the question if a space is placed at start or end
    s = ''.join(random.sample(line.lower(), len(line)))
    print(f'{s} - {line}')
    question_dict = {s: [line], 'parent': {'Country': parent}}
    qa_dict.append(question_dict)

# TODO: split in to multiple quiz rounds when over X questions
print(json.dumps(qa_dict))
