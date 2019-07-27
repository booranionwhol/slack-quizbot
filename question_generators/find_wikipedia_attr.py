import requests
import json
from bs4 import BeautifulSoup

def main(url):

    questions_attribs = []

    r = requests.get(url)
    # print(r.headers)
    content = r.content.decode('utf-8', 'ignore')

    json_result = json.loads(content)
    html = json_result['parse']['text']['*']

    soup = BeautifulSoup(html, 'html.parser')
    info = soup.find(name='table', attrs={'class': 'infobox geography vcard'})
    if not info:
        print("Couldn't find infobox card")
        return None
    # print(str(info))
    # info=BeautifulSoup("""
    # <tr class="mergedtoprow"><th colspan="2" style="text-align:center;text-align:left">Area<span style="font-weight:normal"></span></th></tr>
    # <tr class="mergedrow"><th scope="row"> • <a href="/wiki/City" title="City">City</a></th><td>363 km<sup>2</sup> (140 sq mi)</td></tr>
    # <tr class="mergedrow"><th scope="row"> • Metro<span style="font-weight:normal"></span></th><td>1,190 km<sup>2</sup> (460 sq mi)</td></tr>
    # <tr class="mergedtoprow"><th scope="row">Highest elevation<span style="font-weight:normal"></span></th><td>424 m (1,391 ft)</td></tr>
    # """,'html.parser')
    # print(info)
    parent_attrib = None

    accepted_parents = ['Area', 'Population']
    accepted_attribs = [
        'Parish',
        'Established',
        'Named for',
        'Founded',
        'Elevation',
        'Highest elevation',
        'Lowest elevation',
        'Demonym(s)',
        'GDP',
        'GDP per capita',
        'Area code(s)',
        'Postal code'
    ]


    def remove_reference_links(data):
        for sup in data.find_all(name='sup', attrs={'class': 'reference'}):
            sup.extract()
        return data


    def replace_attrib_image(data):
        # Example: Population - Total in Minsk
        img_tag = data.find('img')
        if img_tag:
            if len(img_tag.attrs.get('alt')) >= 1:
                data.img.replace_with(img_tag.attrs.get('alt'))
        return data


    for row in info.find_all(name='tr'):
        # print(f"row: {row}")

        # We have hit a new block, which may not have a sub-category
        # Clear the parent_attrib
        # class attr is a list.
        try:
            if "mergedtoprow" in row.attrs.get('class'):
                parent_attrib = None
        except:
            pass

        leftcell = row.find('th')
        if leftcell:
            # Córdoba, Argentina had an odd blank row in the Population
            if len(leftcell.get_text()) <= 2:
                continue
            if leftcell.attrs.get('colspan') == '2':
                # next row will be a sub category
                leftcell = remove_reference_links(leftcell)
                parent_attrib = leftcell.get_text().strip()
                print(f'parent_attrib {parent_attrib}')
            else:
                attrib = leftcell.get_text().strip()
                # Strips superscript etc.
                rightcell = row.find('td')
                if leftcell.get_text() != 'Country':
                    # This still messes up the original. Should it make a deepcopy first?
                    rightcell_orig = replace_attrib_image(rightcell)
                rightcell_orig = rightcell.get_text().strip()
                rightcell = remove_reference_links(rightcell)
                rightcell = rightcell.get_text().strip()
                if parent_attrib in accepted_parents or attrib in accepted_attribs or str(parent_attrib).startswith('Population'):
                    # Some cells have newlines. Eg. GDP for Dhaka, Bangladesh
                    if 'Ethnic' not in attrib and '\n' not in rightcell:
                        if parent_attrib:
                            question=parent_attrib + ' - ' + attrib
                        else:
                            question=attrib
                        print(
                            f"{parent_attrib} - {attrib}: '{rightcell}' ({rightcell_orig})")
                        questions_attribs.append({"question": question, "answers":[rightcell,rightcell_orig]})

    return questions_attribs
if __name__ == "__main__":
    url = 'https://en.wikipedia.org/w/api.php?action=parse&page=Chi%C5%9Fin%C4%83u&format=json'
    main(url)