import pandas as pd

WINDOW = 10  # previous 10 readings, about 5 minutes

FEATURES = ["light", "sound", "co2", "co2_slope", "pir_1", "pir_2",
            "pir_any_roll", "sound_roll", "co2_roll", "light_roll"]


def add_features(df):
    """df must have these columns from the message format:
    timestamp (datetime), light, sound, co2, co2_slope, pir_1, pir_2.
    Rolling features use only past readings, inside each recording block."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["block"] = (df["timestamp"].diff() > pd.Timedelta(minutes=5)).cumsum()
    df["pir_any"] = ((df["pir_1"] + df["pir_2"]) > 0).astype(int)
    for col in ["pir_any", "sound", "co2", "light"]:
        df[col + "_roll"] = (df.groupby("block")[col]
                               .rolling(WINDOW, min_periods=1).mean()
                               .reset_index(level=0, drop=True))
    return df