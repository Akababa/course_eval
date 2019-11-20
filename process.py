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
        columns=["ccode", "instructor", "organization", "expl_lvl", "q_treatment", "visual", "oral", "help",
                 "interesting", "overall", "attendance", "assign_helpful", "printed_notes", "textbook", "new_material",
                 "assign_amount", "hours_outside", "num_responses", "term"])
    for filename in os.listdir("scraped_data"):
        cc, instr, evaluation, term = load_course(filename)

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

            df.loc[len(df.index)] = [cc, instr, *[avg(qa[1]) for qa in evaluation], num_resp, term]
            print(f"{cc} - {instr} - {term} processed successfully")

    return df


def dump_averages_csv(filename):
    # if os.path.exists(filename):
    #     print(f"{filename} found, loading")
    #     return pd.read_csv(filename)
    print(f"{filename} not found, generating and saving")
    df = make_df()
    df.to_csv(filename, index=False)
    return df


# dump_averages_csv("averages.csv")
