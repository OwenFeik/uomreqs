import json
import re

RE_ANY = r'[ \w\-():;,]+'
RE_END = r'(?=\.|$)'
RE_SBJ = r'[a-zA-Z]{4}\d{5}'

def min_len_any_str(options, divider='|'):
    l = min(len(o) for o in options)
    return divider.join(o[-l:] for o in options)

def match_pref_clean_suff(item, prefs, suffs, needs_suff=False):
    """
    finds a substring of item beginning with any of prefs and ending at
    any of suffs followed by string end or full stop, then cleans off any of
    suffs from the end of a found string
    """

    ending = rf'(?={min_len_any_str(suffs)})' if needs_suff else RE_END
    regex = rf'(?<={min_len_any_str(prefs)}){RE_ANY}{ending}'

    match = re.search(
        regex,
        item,
        flags=re.IGNORECASE
    )

    if match is None:
        return None

    poss_suffix_string = '|'.join(suffs)
    return re.sub(
        rf'({poss_suffix_string})$',
        '',
        match.group(0),
        flags=re.IGNORECASE
    )

def parse_major_requirement(item):
    major = match_pref_clean_suff(
        item,
        [
            'only available to students in the ',
            'enrolled in the '
        ],
        [
            ' major within the',
            ' major of the'
        ],
        needs_suff=True
    )
    if major is not None:
        return 'MAJOR', major
    else:
        return None

def parse_course_requirement(item):
    course = match_pref_clean_suff(
        item, 
        [
            'entry into the ',
            'enrolled in the ',
            ' points of the ',
            'admission to the '
            'major within the ',
            'major of the '
        ],
        [
            ' to complete this subject',
            ' to enrol in this capstone subject'
        ]
    )

    if course is None:
        return course

    degree_types = [
        'Advanced',
        'Associate',
        'Bachelor',
        'Diploma',
        'Doctor',
        'Graduate',
        'Master'
    ]
    degree_prefix_string = '|'.join(d[:6] for d in degree_types)

    course = [c.strip() for c in re.split(
        rf' or |, (?={degree_prefix_string})',
        course,
        flags=re.IGNORECASE
    )]

    return 'COURSE', course

def parse_points_requirement(item):
    match = re.search(
        r'must be in the (last|final) (?P<n>[\d]+)',
        item,
        re.IGNORECASE
    )
    if match is not None:
        return 'POINTS', 'FINAL', match.group('n')

def parse_subject_requirement(item):
    match = re.search(
        r'have completed a minimum of (?P<n>\w+) (?P<y>\d)(nd|rd|th) year '
        rf'units in (?P<fields>{RE_ANY}){RE_END}',
        item
    )

    if match is None:
        return None

    try:
        n = {
            'one': 1,
            'two': 2,
            'three': 3,
            'four': 4,
            'five': 5,
            'six': 6,
            'seven': 7,
            'eight': 8,
            'nine': 9,
            'ten': 10
        }[match.group('n')]
    except KeyError:
        print(f'Failed to parse subject requirements for: {item}')
        return None

    y = int(match.group('y'))
    fields = re.sub(
        r', or equivalent$',
        '',
        match.group('fields'),
        flags=re.IGNORECASE
    )

    return 'FIELD', n, y, fields

def clean_subj_list(item):
    removals = []
    replacements = []
    for s in item:
        if len(s) != 7:
            removals.append(s)

            match = re.search(RE_SBJ, s)
            if match is None:
                print(f'Strange subject format: {s}')
                replacements.append(None)
            else:
                replacements.append(match.group(0))

    for rem, rep in zip(removals, replacements):
        item.remove(rem)
        if rep is not None:
            item.append(rep)

def parse_prereq_info(subj):
    constraints = []

    defaults = {
        'prereqs': (0, False),
        'coreqs': (0, True),
        'antireqs': (-1, False)
    }

    for req in defaults:
        qty, conc = defaults[req]    
        for item in subj[req]:
            if type(item) == list:
                clean_subj_list(item)
                constraints.append(('SUBJECTS', qty, item, conc))
                qty, conc = defaults[req]
            elif type(item) != str:
                print('WTF' + item)
            else:
                subjects = re.findall(
                    RE_SBJ,
                    item,
                    flags=re.IGNORECASE
                )
                if subj['code'] in subjects:
                    subjects.remove(subj['code'])
                if subjects != []:
                    constraints.append(('SUBJECTS', qty, subjects, conc))
                    qty, conc = defaults[req]

                for func in [
                    parse_course_requirement,
                    parse_points_requirement,
                    parse_subject_requirement,
                    parse_major_requirement
                ]:
                    c = func(item)
                    if c is not None:
                        constraints.append(c)

                if item != 'None':
                    print(item)

                lower = item.lower()

                qty_map = {
                    'one of': 1,
                }

                for s in qty_map:
                    if s in lower:
                        qty = qty_map[s]

                conc_map = {
                    'may be taken concurrently': True
                }

                for s in conc_map:
                    if s in lower:
                        conc = conc_map[s]

    if 'addreqs' in subj:
        constraints.append(('ADDITIONAL', '\n'.join(subj['addreqs'])))

    return constraints

    # ('SUBJECTS', qty, subjects, concurrent)
    # qty of 0 -> all subjects required
    # qty of -1 -> disallowed subjects
    # e.g. (0, [comp10002], False) implies that comp10002 is a requirement
    # e.g. (2, [comp10002, comp20005], False) implies that both subj required
    # e.g. (1, [MAST10005, MAST10006], True) implies that either subj must be
    #    done before or simultaneously.
    #
    # ('COURSE', course) -> must be in course (may be a list)
    # ('FIELD', n, year, fields) -> must have taken n yearth subjects in fields
    # ('ADDITIONAL', reqstr) -> an additional request (e.g. audition, etc)

def clean_scraped(file='out.json'):
    with open(file, 'r') as f:
        subjs = json.load(f)

    for s in subjs:
        s['level'], s['points'] = \
            s['level'].replace('credit points', '').strip().split(', ')
        s['constraints'] = parse_prereq_info(s)
        for entry in ['prereqs', 'coreqs', 'addreqs', 'antireqs']:
            if entry in s:
                del s[entry]
    
    with open('cleaned.json', 'w') as f:
        json.dump(subjs, f, indent=4)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        clean_scraped(file=sys.argv[1])
    else:
        clean_scraped()
