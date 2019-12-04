import numpy as np
import os
import pandas as pd


def fixall():
    names = pd.read_csv("averages.csv", usecols=["instructor"]).instructor.unique()
    names = {n.lower(): n for n in names}
    fixes = {
        "Joseph West": "Joe West",
        "Zhiyong Liu": "Michael Liu",
        "Hany Fahmy": "Hamy Fahmy",
        "David Tompkins": "Dave Tompkins",
        "Troy Vasiga": "Troy Michael Vasiga",
        "Sandra Graham": "Sandy Graham",
        "John-Paul Pretti": "J. P. Pretti",
        "Steven Furino": "Steve Furino",
        "Ruodu Wang": "Ruodo Wang",
        "William Cook": "Bill Cook",
        "James Munro": "J Ian Munro",
        "Lap Lau": "Lap Chi Lau",
        "B. Park": "Douglas Park",
    }
    for a, b in fixes.items():
        assert a.lower() not in names
        names[a.lower()] = b

    def fix(name):
        name_l = name.lower()
        if name_l in names:
            fixed_name = names[name_l]
            if name not in fixes and name != fixed_name:
                fixes[name] = fixed_name
            return fixed_name

        firsts, last = name_l.rsplit(" ", 1)
        for i in range(len(firsts), 1, -1):
            partialname = f"{firsts[:i]} {last}"
            if partialname in names:
                fixed_name = names[partialname]
                fixes[name] = fixed_name
                names[name_l] = fixed_name
                return fixed_name
        print(f"Can't fix {name}")
        return name

    for filename in os.listdir("salaries"):
        df = pd.read_csv(f"salaries/{filename}")
        df = df[df.title.isin(["Professor", "Associate Professor", "Assistant Professor", "Lecturer"])]
        df["name"] = df.name.apply(fix)
        df.to_csv(f"salaries/p_{filename}", index=False)

    for name, fixed_name in fixes.items():
        print(f"Fixed {name} to {fixed_name}")


fixall()
