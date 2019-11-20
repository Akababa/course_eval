import requests, lxml.html, json, os
import pandas as pd

COURSE_EVAL_URL = "https://mathsoc.uwaterloo.ca/university/evaluations/"
SALARY_URL = "https://uwaterloo.ca/about/accountability/salary-disclosure"


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


sess = uw_cas_login(COURSE_EVAL_URL, "m9pang", "MYPASSWORD")


def getcourse(num):
    url = f"{COURSE_EVAL_URL}{num}/"
    r = sess.get(url)
    return r


def parse_course(r):
    rt = lxml.html.fromstring(r.text)
    _, course_code, instructor = rt.xpath(r"//h1[@class='my-4']")[0].text.split(' - ')
    course_code = course_code[:-12]
    evaluation = []
    for question, answers in zip(rt.xpath(r"//strong"), rt.xpath(r"//ol")):
        anss = []
        for answer in answers.xpath(".//li"):
            anss.append(answer.text)
        evaluation.append([question.text, anss])

    return course_code, instructor, evaluation


def dump_course(num, term):
    filename = f"scraped_data/{term}_{num}.json"
    if os.path.exists(filename):
        print(f"{num} exists, skipping")
        return False
    r = getcourse(num)
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


def dump_all_courses(all_courses=None):
    if all_courses is None:
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
        print(f"{year} exists, skipping")
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


### UNCOMMENT THESE
# dump_all_courses()
# for year in range(2011, 2019):
#     dump_all_salaries(year)
