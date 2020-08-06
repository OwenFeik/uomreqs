import asyncio
import json
import re

import bs4
import requests

URL_BASE = 'https://handbook.unimelb.edu.au'
INHERENT = [line.replace('\n', '') for line in open('inherent.txt', 'r')]

async def get(url):
    return requests.get(url).content.decode()

def parse_subject_table(table):
    # columns = []
    # for th in table.select('thead')[0].select('th'):
    #     columns.append(th.string)
    # if columns[0] != 'Code':
    #     raise ValueError('No subject table.')

    subjects = []
    for tr in table.select('table > tr'):
        code = tr.select('td')[0].string
        subjects.append(code)

    return subjects

def parse_requisites_element(children):
    aliases = {
        'Prerequisites': 'prereqs',
        'Corequisites': 'coreqs',
        'Non-allowed subjects': 'antireqs',
        'Inherent requirements (core participation requirements)': 'inherent',
        'Recommended background knowledge': 'background'
    }

    info = {}
    heading = ''
    content = []
    alias = lambda h: aliases[h] if h in aliases else h
    for child in children:
        if child.name == 'h3':
            if heading:
                info[alias(heading)] = content
            heading = child.string
            content = []
        elif child.name == 'p':
            text = re.sub(r'<[^<>]*>', '', str(child)).strip()
            if text:
                content.append(text)
        elif child.name == 'table':
            content.append(parse_subject_table(child))
        elif child.name == 'div':
            break
    info[alias(heading)] = content

    if 'inherent' in info:
        info['inherent'] = [i for i in info['inherent'] if i not in INHERENT]
    return info

async def get_requirements_href(href):
    if 'eligibility-and-requirements' in href:
        return href
    
    soup = bs4.BeautifulSoup(await get(URL_BASE + href), features='lxml')
    return soup.find(name='a', text='Eligibility and requirements')['href']

async def get_subject_requirements(href):
    href = await get_requirements_href(href)
    soup = bs4.BeautifulSoup(await get(URL_BASE + href), features='lxml')

    body = soup.select('.course__body__inner > .sidebar-tabs__panel')[0]

    info = {'updated': body.select('p.last-updated')[0].string}
    children = list(body.children)
    prerequisites = body.select('div#prerequisites')[0]
    children.remove(prerequisites)

    info.update(parse_requisites_element(list(prerequisites.children)))
    info.update(parse_requisites_element(children))
    
    return info

async def get_n_pages():
    return 5

    search_url = URL_BASE + '/search?types[]=subject'
    soup = bs4.BeautifulSoup(await get(search_url), features='lxml')
    div = soup.select('.search-results__paginate')[0] 
    return int(div.select('span')[0].string[3:]) # '<span>of 313</span>'

async def parse_search_result_page(url):
    soup = bs4.BeautifulSoup(await get(url), features='lxml')
    subject_divs = soup.select('.search-result-item__anchor')
    subjects = []
    for div in subject_divs:
        href = div['href']
        header = div.select('.search-result-item__header')[0].select(
            '.search-result-item__name')[0]
        title = header.select('h3')[0].string
        code = header.select('span.search-result-item__code')[0].string
        
        footer = div.select('.search-result-item__meta')[0]
        period = footer.select('.search-result-item__meta-primary')[0].select(
            'p')[0].string
        level = footer.select('.search-result-item__meta-secondary')[0].select(
            'p')[0].string

        subjects.append({
            'href': href,
            'title': title,
            'code': code,
            'period': period,
            'level': level
        })

    return subjects

async def add_requirement_info(subject):
    subject.update(await get_subject_requirements(subject['href']))
    print(subject)
    return subject

async def get_page_of_subjects(n):
    subjects = await parse_search_result_page(
        URL_BASE + '/search?types[]=subject&page=' + str(n))

    tasks = [asyncio.create_task(add_requirement_info(subject)) \
        for subject in subjects]
        
    return await asyncio.gather(*tasks)

# Will take a while; there are 6000+ subjects, across 300+ pages.
async def get_all_subjects():
    n = await get_n_pages()

    tasks = [asyncio.create_task(get_page_of_subjects(i + 1)) \
        for i in range(n)]

    return await asyncio.gather(*tasks)

loop = asyncio.get_event_loop()
subjects = loop.run_until_complete(get_all_subjects())
with open('out.json', 'w') as f:
    json.dump(subjects, f, indent=4)
