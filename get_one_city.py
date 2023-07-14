import requests
import json
from random import randint
import random
import find_wikipedia_attr
from bs4 import BeautifulSoup

list_of_countries=[
         {
                "country": 'Cayman Islands',
                "capital": 'AAA',
                "capital_link": '/wiki/George_Town,_Cayman_Islands',
                "largest_city": 'George Town',
                "largest_city_link": '/wiki/George_Town,_Cayman_Islands',
                "second_largest_city": 'George Town',
                "second_largest_city_link": '/wiki/George_Town,_Cayman_Island'
            }
        ]
questions_list=[]
for country in list_of_countries:
    print(country)
    country_text = country['country']
    # 20% chance of second largest city
    if random.random() <= 0.20:
        city = country['second_largest_city']
        city_link = country['second_largest_city_link']
        city_q = 'second largest'
        if city is None:
            city = country['largest_city']
            city_link = country['largest_city_link']
            city_q = 'largest'
    else:
        city = country['largest_city']
        city_link = country['largest_city_link']
        city_q = 'largest'

    print(city, city_link)
    city_link_page = city_link.replace('/wiki/', '')
    url = f'https://en.wikipedia.org/w/api.php?action=parse&page={city_link_page}&format=json'
    city_attribs = find_wikipedia_attr.main(url)
    if city_attribs is None or len(city_attribs) == 0:
        continue
    #attrib = random.choice(city_attribs)
    attrib = city_attribs[0]
    attrib_q = attrib['question']
    attrib_answers = attrib['answers']
    attrib_answers.append('CLUE'+city)
    question_text = u'In the {city_q} city of *{country_text}*. What is the *{attrib_q}*'.format(city_q=city_q,country_text=country_text,attrib_q=attrib_q)
    print(question_text)
    questions_list.append({question_text: attrib_answers})

print(json.dumps(questions_list))
with open('questions/city_output1.json','w+') as fp:
    json.dump(questions_list,fp,ensure_ascii=False)