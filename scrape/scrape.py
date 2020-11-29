import asyncio
import concurrent.futures
import json
import re
import time

import bs4
import requests

URL_BASE = 'https://handbook.unimelb.edu.au'
INHERENT = [line.replace('\n', '') for line in open('inherent.txt', 'r')]

def get(url):
    return requests.get(url).content.decode()

def element_text(el):
    return re.sub(r'<[^<>]*>', '', str(el)).strip()

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

def parse_list(ul):
    entries = []
    for li in ul.select('li'):
        entries.append(element_text(li))

    return entries

def parse_requisites_element(children):
    aliases = {
        'Prerequisites': 'prereqs',
        'Corequisites': 'coreqs',
        'Non-allowed subjects': 'antireqs',
        'Additional Entry Requirements': 'addreqs',
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
        elif child.name == 'table':
            content.append(parse_subject_table(child))
        elif child.name == 'ul':
            content.append(parse_list(child))
        elif child.name == 'div':
            break
        elif child.name == 'h2':
            pass
        else:
            text = element_text(child)
            if text:
                content.append(text)
    info[alias(heading)] = content

    if 'inherent' in info:
        info['inherent'] = [i for i in info['inherent'] if i not in INHERENT]
    return info

def get_requirements_href(href):
    if 'eligibility-and-requirements' in href:
        return href
    
    soup = bs4.BeautifulSoup(get(URL_BASE + href), features='lxml')
    return soup.find(name='a', text='Eligibility and requirements')['href']

def get_subject_requirements(href):
    href = get_requirements_href(href)
    soup = bs4.BeautifulSoup(get(URL_BASE + href), features='lxml')

    body = soup.select('.course__body__inner > .sidebar-tabs__panel')[0]

    info = {'updated': body.select('p.last-updated')[0].string}
    children = list(body.children)
    prerequisites = body.select('div#prerequisites')[0]
    children.remove(prerequisites)

    info.update(parse_requisites_element(list(prerequisites.children)))
    info.update(parse_requisites_element(children))
    
    return info

def get_n_pages():
    search_url = URL_BASE + '/search?types[]=subject'
    soup = bs4.BeautifulSoup(get(search_url), features='lxml')
    div = soup.select('.search-results__paginate')[0] 
    return int(div.select('span')[0].string[3:]) # '<span>of 313</span>'

def parse_search_result_page(url):
    soup = bs4.BeautifulSoup(get(url), features='lxml')
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

def add_requirement_info(subject):
    try:
        subject.update(get_subject_requirements(subject['href']))
        print(subject['code'])
    except Exception as e:
        print(f'Failed to get info for subject {subject}: {e}')
    return subject

async def get_page_of_subjects(n):
    try:
        subjects = parse_search_result_page(
            URL_BASE + '/search?types[]=subject&page=' + str(n))
    except Exception as e:
        print(f'Failed to get page {n} of subjects: {e}')
        return []

    loop = asyncio.get_event_loop()

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [loop.run_in_executor(executor, add_requirement_info, s) \
            for s in subjects]
        return await asyncio.gather(*futures)

# Will take a while; there are 6000+ subjects, across 300+ pages.
async def get_all_subjects():
    n = get_n_pages()

    tasks = [asyncio.create_task(get_page_of_subjects(i + 1)) \
        for i in range(n)]

    subjects = []
    _ = [subjects.extend(s) for s in await asyncio.gather(*tasks)]
    return subjects

def main():
    start = time.time()
    loop = asyncio.get_event_loop()
    subjects = loop.run_until_complete(get_all_subjects())
    with open('out.json', 'w') as f:
        json.dump(subjects, f, indent=4)
    print(f'Downloaded requisite information for {len(subjects)} ' + \
        f'subjects in {time.time() - start} seconds.')

if __name__ == '__main__':
    main()
