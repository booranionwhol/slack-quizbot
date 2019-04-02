r = {
    "N": ["n","b"],
    "T": ["T","x"]
    
}

s = 'teNstxxNx'
import random
print(random.choice(s))
unicode_available=[]
# Build list of letter suitable to replace
for index,letter in enumerate(s):
    if letter in r:
        unicode_available.append((index,letter))
#         if letter not in unicode_available:
#             unicode_available.append(letter)
# replace_me=random.choice(unicode_available)

print(unicode_available)