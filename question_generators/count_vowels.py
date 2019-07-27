vowels = ['a', 'e', 'i', 'o', 'u']

with open('list_to_remove_vowels.txt') as file:
    for line in file:
        count=0
        answer = line.rstrip()
        line = answer.lower().replace(' ', '')
        for letter in line:
            if letter in vowels:
                count+=1
        print('{} {}'.format(count,line))