import itertools

import requests, lxml.html, json, os
import pandas as pd

COURSE_EVAL_URL = "https://mathsoc.uwaterloo.ca/university/evaluations/"
SALARY_URL = "https://uwaterloo.ca/about/accountability/salary-disclosure"
CATALOG_URL = "http://www.adm.uwaterloo.ca/cgi-bin/cgiwrap/infocour/salook.pl"


def uw_cas_login(service, username, password):
    s = requests.session()

    ### Here, we're getting the login page and then grabbing hidden form
    ### fields.  We're probably also getting several session cookies too.
    login = s.get(service)
    login_html = lxml.html.fromstring(login.text)
    all_inputs = login_html.xpath(r'//form//input')
    form = {x.attrib["name"]: x.attrib["value"] for x in all_inputs}
    # print(form, login_html)

    ### Now that we have the form fields, let's add in our
    ### username and password.
    form['username'] = username  # Enter an email here.  Not mine.
    form['password'] = password  # I'm definitely not telling you my password.
    s.post("https://cas.uwaterloo.ca" + login_html.forms[0].action,
           data=form,
           headers={"Referer": login.url})
    return s


def get_course(num):
    url = f"{COURSE_EVAL_URL}{num}/"
    r = sess.get(url)
    return r


def parse_course(r):
    rt = lxml.html.fromstring(r.text)
    _, course_code, instructor = rt.xpath(r"//h1[@class='my-4']")[0].text.split(' - ')
    course_code, sec = course_code[:-12], course_code[-3:]
    evaluation = []
    for question, answers in zip(rt.xpath(r"//strong"), rt.xpath(r"//ol")):
        anss = []
        for answer in answers.xpath(".//li"):
            anss.append(answer.text)
        evaluation.append([question.text, anss])

    return course_code, sec, instructor, evaluation


def dump_course(num, term):
    filename = f"scraped_data/{term}_{num}.json"
    if os.path.exists(filename):
        print(f"{filename} exists, skipping")
        return False
    r = get_course(num)
    if r.status_code != 200:
        print(f"{num} got status code {r.status_code}, skipping")
        return False
    json.dump([*parse_course(r), term], open(filename, "x"))
    print(f"{term}_{num} dumped to json")
    return True


def get_all_courses():
    r = sess.get(COURSE_EVAL_URL)
    rt = lxml.html.fromstring(r.text)
    allcourses = rt.xpath("//script[@type='text/javascript']")[0].text.split("\n")[1].strip()[
                 len("var term_survey_map = "):-1]
    return json.loads(allcourses)


def dump_all_courses():
    all_courses = get_all_courses()
    dumped = set()
    for term_code, courses in all_courses.items():
        print(f"Found {len(courses)} courses in term {term_code}")
        for course in courses:
            end_eval_id, num_responses = int(course["evaluate_id"]), int(course["completed_surveys"])
            dump_course(end_eval_id, term_code)
            dumped.add(end_eval_id)
    # for start_eval_id in range(0, 100000, 50):
    #     if start_eval_id in dumped:
    #         continue
    #     if dump_course(start_eval_id, "0000"):
    #         break
    # for end_eval_id in range(10000, 0, -50):
    #     if end_eval_id in dumped:
    #         continue
    #     if dump_course(end_eval_id, "0000"):
    #         break
    # for eval_id in range(start_eval_id - 100, end_eval_id + 100):
    #     if eval_id not in dumped:
    #         dump_course(eval_id, "0000")
    #         dumped.add(end_eval_id)


def dump_all_salaries(year):
    filename = f"salaries/{year}.csv"
    if os.path.exists(filename):
        print(f"{filename} exists, skipping")
        return False
    url = SALARY_URL
    if year == 2013:
        url = "https://uwaterloo.ca/about/what-we-stand/accountability/salary-disclosure-2013"
    elif year != 2018:
        url += f"-{year}"
    r = sess.get(url)
    if r.status_code != 200:
        print(f"{year} got status code {r.status_code}, skipping")
        return False

    rt = lxml.html.fromstring(r.text)
    table = rt.xpath("//table[@class='tablesaw tablesaw-stack']/tbody/tr")
    # headers = list(map(lambda x: x.text, table[0].xpath(".//th")))
    headers = ["name", "title", "salary", "benefits"]
    df = pd.DataFrame(columns=headers)
    for entry in table[1:]:
        row = entry.text_content().strip().split("\n")
        row = [x.strip() for x in row if x.strip() != '']
        lastname, firstname, title, salary, benefits = row
        salary = float(salary.replace('$', '').replace(',', ''))
        try:
            benefits = float(benefits.replace('$', '').replace(',', ''))
        except:
            benefits = 0
        fullname = firstname.split()[0].title() + " " + lastname.title()
        df.loc[len(df.index)] = [fullname, title, salary, benefits]

    df.to_csv(filename, index=False)

    print(f"{len(df.index)} salaries scraped from {r.url} and dumped to {filename}")


import concurrent.futures


def dump_catalog(terms):
    subjects = ['ACTSC', 'AMATH', 'CS', 'PMATH', 'PHYS', 'CO', 'QIC', 'COMM',
                'ECE', 'CM', 'MATBUS', 'MATH', 'MTHEL', 'STAT', 'SYDE', 'EARTH',
                'SE', 'BIOL', 'ACC', 'ENGL']
    levels = ["under", "grad"]
    url = CATALOG_URL + "?sess={}&subject={}&level={}"
    for term in terms:
        filename = f"catalog/{term}.csv"
        if os.path.exists(filename):
            print(f"{filename} exists, skipping")
            continue

        df = pd.DataFrame(columns=["term", "ccode", "section", "enrolled"])
        urls = []
        for subject, level in itertools.product(subjects, levels):
            url_f = url.format(term, subject, level)
            urls.append(url_f)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            responses = executor.map(sess.get, urls)

        for r, url_f, (subject, level) in zip(responses, urls, itertools.product(subjects, levels)):
            # r = sess.get(url_f)
            if r.status_code != 200:
                print(f"{url_f} got status code {r.status_code}, skipping")
                continue

            rt = lxml.html.fromstring(r.text)
            try:
                bigtab = rt.xpath("//table[@border=2]")[0]
            except:
                print(f"{url_f} got no results, skipping")
                continue
            courses = bigtab.xpath(f"./tr/td[starts-with(.,'{subject}')]/..")
            print(f"{url_f} got {len(courses)} results")
            for course in courses:
                cnumber = course.xpath("./td[2]")[0].text.strip()
                table = course.xpath("./following-sibling::tr[./td[@colspan=3]][1]/td[2]/table")[0]
                xp = "./tr/td[{}]/..".format(' or '.join(f"starts-with(.,'{sym} ')" for sym in ["LEC", "SEM", "RDG"]))
                for row in table.xpath(xp):
                    row = row.xpath("./td")
                    sec = row[1].text[4:7]
                    enro = int(row[7].text)
                    # instr = row[13].text.split(",", 1)[0].strip()
                    df.loc[len(df.index)] = [term, f"{subject} {cnumber}", sec, enro]
        if len(df.index) > 0:
            df.to_csv(filename, index=False)
            print(f"{len(df.index)} courses dumped to {filename}")


sess = uw_cas_login(COURSE_EVAL_URL, "m9pang", "MYPASSWORD")
### UNCOMMENT THESE
# dump_all_courses()
# for year in range(2011, 2019):
#     dump_all_salaries(year)
dump_catalog([x * 10 + y for x in range(113, 124) for y in [1, 5, 9]])
