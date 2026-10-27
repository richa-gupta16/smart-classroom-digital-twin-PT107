import pandas as pd

# Lecture slots on weekdays: (start hour, end hour)
SLOTS = [(9, 10), (10, 11), (11, 12), (14, 15), (15, 16)]


def is_scheduled(ts):
    if ts.weekday() >= 5:  # Saturday and Sunday
        return False
    return any(start <= ts.hour < end for start, end in SLOTS)


def build_week(start="2026-09-07"):
    times = pd.date_range(start, periods=7 * 24, freq="h")
    df = pd.DataFrame({"timestamp": times})
    df["scheduled"] = df["timestamp"].apply(is_scheduled)
    return df


if __name__ == "__main__":
    week = build_week()
    print(week["scheduled"].sum(), "scheduled hours out of", len(week))
    week.to_csv("simulation/week_timetable.csv", index=False)