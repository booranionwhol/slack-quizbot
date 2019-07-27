
import json

j = json.load(open('questions/capital_cities2.json'))
with open('capital_cities.txt') as file:
    lines = file.read().splitlines()

d = {}
fixed = []
for line in lines:
    country, capital = line.split(',')
    d[capital] = country
for q in j['questions']:
    for key, value in q.items():
        d2 = {key: value, 'parent': {'Country': d[value[0]]}}
        fixed.append(d2)

print(json.dumps(fixed))
# for q in
