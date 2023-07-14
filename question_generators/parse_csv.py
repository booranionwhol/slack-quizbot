import json

"""
Parse a CSV with fields:
question,answer
"""

qa_dict = []
with open('file.csv') as f:
    lines = f.read().splitlines()

# random.shuffle(lines)

for line in lines:
    question, answer = line.split(',')
    question_dict = {question: [answer]}
    qa_dict.append(question_dict)

# TODO: split in to multiple quiz rounds when over X questions
print(json.dumps(qa_dict))
