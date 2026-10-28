import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

short = pd.read_csv("simulation/short_holdoff_sweep.csv")
main = pd.read_csv("simulation/energy_results.csv")

fig, ax = plt.subplots(figsize=(7, 5))
for label, prefix, marker in [("PIR only", "PIR only", "o"),
                              ("Model + PIR override", "Model + PIR", "s")]:
    d = short[short["strategy"].str.startswith(prefix)].copy()
    d["hold"] = d["strategy"].str.extract(r"hold (\d+)").astype(int)
    d = d.sort_values("hold")
    ax.plot(d["saving_vs_fixed_%"], d["occupied_time_lights_off_%"], marker=marker, label=label)
    for _, r in d.iterrows():
        ax.annotate(f"{r['hold']} min", (r["saving_vs_fixed_%"], r["occupied_time_lights_off_%"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)

fixed = main[main["strategy"].str.contains("fixed")].iloc[0]
ax.scatter([0], [fixed["occupied_time_lights_off_%"]], marker="x", color="k", label="Fixed 08:00-18:00")
ax.set_xlabel("Energy saving vs. fixed schedule (%)")
ax.set_ylabel("Occupied time with lights off (%)")
ax.set_title("Energy saving vs. comfort cost (simulation, 87 h of data)")
ax.legend()
ax.grid(alpha=0.3)
plt.savefig("docs/tradeoff.png", dpi=150, bbox_inches="tight")
print("Saved docs/tradeoff.png")