import json
import random

qa_dict=[]

with open('questions/townlist1-shuf.txt') as f:
    lines = f.read().splitlines()

# random.shuffle(lines)

for town in lines:
    town=town.lower()
    cryptic=''.join(random.sample(town,len(town)))
    print(f'{cryptic} - {town}')
            # cryptic=' '.join(result).upper()
    question_dict={cryptic:[town]}
    qa_dict.append(question_dict)
print(json.dumps(qa_dict))
