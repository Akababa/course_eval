import os, json
import pandas as pd
import numpy as np


def load_course(filename):
    filename = f"scraped_data/{filename}"
    if not os.path.exists(filename):
        print(f"{filename} doesn't exist, skipping")
        return
    info = json.load(open(filename))
    print(f"{filename} loaded successfully")
    return info


def make_df():
    df = pd.DataFrame(
        columns=["term", "ccode", "section", "instructor", "org", "expl_lvl", "q_treat", "visual", "oral",
                 "help", "interest", "overall", "attend", "assign", "notes", "textbook",
                 "new_mat", "assign_amt", "outside", "num_resp"])
    for filename in os.listdir("scraped_data"):
        cc, sec, instr, evaluation, term = load_course(filename)

        num_resp = 0
        for qa in evaluation:
            anss = []
            for ans in qa[1]:
                option, amt = ans.rsplit(": ", 1)
                amt = int(amt)
                if option not in ["No opinion", "Did not seek help", "No work assigned", "No printed notes",
                                  "No text required"]:
                    anss.append(amt)
            num_resp1 = sum(anss)
            qa[1] = anss
            if num_resp1 == 0:
                print(f"{num_resp1} responses for {qa[0]}, skipping row")
                break
            num_resp = max(num_resp, num_resp1)
        else:
            def avg(ans):
                return np.average(range(1, len(ans) + 1), weights=ans)

            df.loc[len(df.index)] = [term, cc, sec, instr, *[avg(qa[1]) for qa in evaluation], num_resp]
            print(f"{cc} - {instr} - {term} processed successfully")

    df = df.drop_duplicates()
    return df


def dump_averages_csv(filename):
    # if os.path.exists(filename):
    #     print(f"{filename} found, loading")
    #     return pd.read_csv(filename)
    print(f"{filename} not found, generating and saving")
    df = make_df()
    df.to_csv(filename, index=False)
    return df


def join_enrolment(filename, output):
    if not os.path.exists(filename):
        print(f"{filename} not found, aborting")
        return

    df = pd.read_csv(filename)  # .drop("enrolled", axis=1)
    df2 = pd.concat((pd.read_csv(f"catalog/{f}", dtype={"enrolled": int}) for f in os.listdir("catalog")))
    df["ccode"] = df["ccode"].str.split(" / ")
    df1 = df[["term", "ccode", "section"]].explode("ccode")
    df1['copy_index'] = df1.index
    df1 = df1.merge(df2, how="left").groupby("copy_index").agg({'enrolled': sum})
    # del df1.index.name
    assert df1.index.is_monotonic
    df["enrolled"] = df1.enrolled.astype(int)
    df["enrolled"] = df[["enrolled", "num_resp"]].max(axis=1)
    df["resp_rate"] = df.num_resp / df.enrolled
    # df["cc_sec"] = [f"{c} {a.split(' / ')[0]} - {b:03d}" for a, b, c in zip(df.ccode, df.section, df.term)]
    # df2["cc_sec"] = [f"{c} {a.split(' / ')[0]} - {b:03d}" for a, b, c in zip(df2.ccode, df2.section, df2.term)]

    # df = pd.merge(df, df2[["cc_sec", "enrolled"]], how="left", left_on="cc_sec", right_on="cc_sec")
    # df = df.drop("cc_sec", axis=1)
    print(df[df.isna().any(axis=1)])
    df = df.dropna()
    print(df)
    df.to_csv(output, index=False)
    return df


# dump_averages_csv("averages.csv")

join_enrolment("averages.csv", "averages_enrol.csv")
