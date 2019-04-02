s = input('Question:')

for c in s:
    print(ord(c))

if ' ' in s:
    print('Space detected')