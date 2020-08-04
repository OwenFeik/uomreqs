import asyncio

import bs4
import requests

async def get_n_pages():
    search_url = 'https://handbook.unimelb.edu.au/search'
    html = requests.get(search_url).content.decode()
    soup = bs4.BeautifulSoup(html, features='lxml')
    div = soup.select('.search-results__paginate')[0] 
    return int(div.select('span')[0].string[3:]) # '<span>of 348</span>'

async def get_page_of_subjects(n):
    url_base = 'https://handbook.unimelb.edu.au/search?types[]=subject&page='
    html = requests.get(url_base + str(n)).content.decode()
    soup = bs4.BeautifulSoup(html, features='lxml')
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

        subjects.append((href, title, code, period, level))
    return subjects

# Will take a while; there are 6000+ subjects, across 300+ pages.
async def get_all_subjects():
    n = await get_n_pages()

    loop = asyncio.get_event_loop()
    tasks = [asyncio.create_task(get_page_of_subjects(i + 1)) \
        for i in range(n)]

    return await asyncio.gather(*tasks)

loop = asyncio.get_event_loop()
print(loop.run_until_complete(get_all_subjects()))
