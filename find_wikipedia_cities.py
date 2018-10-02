import requests
import json
from bs4 import BeautifulSoup

# url = 'https://en.wikipedia.org/w/api.php?action=parse&page=List_of_countries_by_national_capital%2C_largest_and_second-largest_cities&format=json'

# r = requests.get(url)
# content = r.content.decode('utf-8', 'ignore')

# json = json.loads(content)
# html = json['parse']['text']['*']

# soup = BeautifulSoup(html, 'html.parser')
# country_list_table = soup.find(name='table', attrs={'class': 'wikitable sortable'})
# print(str(info))
country_list_table = BeautifulSoup("""
<table class="wikitable sortable">
<tbody><tr><th rowspan="4">Country or territory</th>
<th rowspan="4">Capital</th><th colspan="2"><a href="/wiki/City_proper" title="City proper">City proper</a></th><th rowspan="4">Source</th></tr>
<tr><th>Largest</th><th>Second largest</th></tr>
<tr><th colspan="2"><a href="/wiki/Metropolitan_area" title="Metropolitan area">Metropolitan area</a> (if different)</th></tr>
<tr><th>Largest</th>
<th>Second largest</th></tr>
<tr>
<td><i><span class="flagicon"><img alt="" class="thumbborder" data-file-height="300" data-file-width="600" height="12" src="//upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Flag_of_the_Republic_of_Abkhazia.svg/23px-Flag_of_the_Republic_of_Abkhazia.svg.png" srcset="//upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Flag_of_the_Republic_of_Abkhazia.svg/35px-Flag_of_the_Republic_of_Abkhazia.svg.png 1.5x, //upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Flag_of_the_Republic_of_Abkhazia.svg/46px-Flag_of_the_Republic_of_Abkhazia.svg.png 2x" width="23"/> </span><a href="/wiki/Abkhazia" title="Abkhazia">Abkhazia</a></i>
(Georgia)</td>
<td colspan="2"><a href="/wiki/Sukhumi" title="Sukhumi">Sukhumi</a></td><td><a href="/wiki/Gagra" title="Gagra">Gagra</a></td>
<td><sup class="reference" id="cite_ref-Sokhumi_1-0"><a href="#cite_note-Sokhumi-1">[1]</a></sup></td></tr>
<tr>
<td><span class="flagicon"><img alt="" class="thumbborder" data-file-height="300" data-file-width="450" height="15" src="//upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Flag_of_Afghanistan.svg/23px-Flag_of_Afghanistan.svg.png" srcset="//upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Flag_of_Afghanistan.svg/35px-Flag_of_Afghanistan.svg.png 1.5x, //upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Flag_of_Afghanistan.svg/45px-Flag_of_Afghanistan.svg.png 2x" width="23"/> </span><a href="/wiki/Afghanistan" title="Afghanistan">Afghanistan</a></td>
<td colspan="2"><a href="/wiki/Kabul" title="Kabul">Kabul</a></td>
<td><a href="/wiki/Kandahar" title="Kandahar">Kandahar</a></td>
<td><sup class="noprint Inline-Template Template-Fact" style="white-space:nowrap;">[<i><a href="/wiki/Wikipedia:Citation_needed" title="Wikipedia:Citation needed"><span title="This claim needs references to reliable sources. (October 2013)">citation needed</span></a></i>]</sup>
</td></tr>
<tr>
<td><i><span class="flagicon"><img alt="" src="//upload.wikimedia.org/wikipedia/commons/thumb/8/87/Flag_of_American_Samoa.svg/23px-Flag_of_American_Samoa.svg.png" width="23" height="12" class="thumbborder" srcset="//upload.wikimedia.org/wikipedia/commons/thumb/8/87/Flag_of_American_Samoa.svg/35px-Flag_of_American_Samoa.svg.png 1.5x, //upload.wikimedia.org/wikipedia/commons/thumb/8/87/Flag_of_American_Samoa.svg/46px-Flag_of_American_Samoa.svg.png 2x" data-file-width="1000" data-file-height="500">&nbsp;</span><a href="/wiki/American_Samoa" title="American Samoa">American Samoa</a></i> (US)
</td>
<td><a href="/wiki/Pago_Pago" title="Pago Pago">Pago Pago</a>
</td>
<td><a href="/wiki/Tafuna,_American_Samoa" title="Tafuna, American Samoa">Tafuna</a></td>
<td><a href="/wiki/Nu%27uuli,_American_Samoa" title="Nu'uuli, American Samoa">Nu'uuli</a></td>
<td><sup id="cite_ref-world-gazetteer2_4-0" class="reference"><a href="#cite_note-world-gazetteer2-4">[4]</a></sup>
</td></tr>
</tbody>
</table>
""", 'html.parser')
table_body = country_list_table.find(name='tbody')

# print(info)
parent_attrib = None


def remove_reference_links(data):
    for sup in data.find_all(name='sup', attrs={'class': 'reference'}):
        sup.extract()
    return data


for row in table_body.find_all(name='tr'):
    if row.contents[0].name == 'th':
        continue

    # Get first cell, then navigate sideways
    country_cell = row.find(name='td')
    country_link = country_cell.a['href']
    country_text = country_cell.a.get_text()

    capital_cell = country_cell.find_next_sibling('td')
    capital_link = capital_cell.a.get('href', None)
    capital_text = capital_cell.a.get_text()

    if capital_cell.attrs.get('colspan') == '2':
        largest_city_link = capital_link
        largest_city_text = capital_text
        second_city_cell = capital_cell.find_next_sibling('td')
    else:
        largest_city_cell = capital_cell.find_next_sibling('td')
        largest_city_link = largest_city_cell.a.get('href', None)
        largest_city_text = largest_city_cell.a.get_text()
        second_city_cell = largest_city_cell.find_next_sibling('td')

    second_city_link = second_city_cell.a.get('href', None)
    second_city_text = second_city_cell.a.get_text()

    print(
        f'Cap: {capital_text} Large: {largest_city_text} Second: {second_city_text}')
