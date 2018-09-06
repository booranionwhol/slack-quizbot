vowels = ['a', 'e', 'i', 'o', 'u', ' ']
with open('list_to_remove_vowels.txt') as file:
    for line in file:
        line = line.rstrip()
        for vowel in vowels:
            line = line.replace(vowel, '')
        if len(line) > 10:
            split_size = 4
        if len(line) <= 10:
            split_size = 3
        result = []
        for i in range(0, len(line), split_size):
            result.append(line[i:i+split_size])
        # A letter on its own looks weird. Merge it to the previous block if found
        # TODO:
        # If the first word is 'The'. Merge the 'Th' to the right a bit randomly?
        if len(result[-1]) == 1:
            last_block = result.pop(-1)
            result[-1] = result[-1]+last_block

        print(' '.join(result))
