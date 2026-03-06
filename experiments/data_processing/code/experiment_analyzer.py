from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ------------------------
# Configuration
# ------------------------

WEIGHT_MAP = {
    1: 10,
    2: 20,
    3: 50,
    4: 100,
    5: 200,
    6: 500,
}

SAMPLING_INTERVAL = 0.5  # seconds

# ------------------------
# Dataclasses
# ------------------------

@dataclass
class Measurement:
    weight_g: int
    resistance: pd.Series
    sampling_interval: float = SAMPLING_INTERVAL

    @property
    def time(self) -> pd.Series:
        # time = interval * (measurement - 1)
        return self.resistance.index * self.sampling_interval


@dataclass
class LoadUnloadPair:
    load: Measurement
    unload: Measurement

    @property
    def difference(self) -> pd.Series:
        return self.load.resistance - self.unload.resistance


@dataclass
class Experiment:
    pairs: dict[int, LoadUnloadPair]  # key = weight (g)

# ------------------------
# Data loading utilities
# ------------------------

def load_measurement(csv_path: Path, weight: int) -> Measurement:
    """
    Reads CSV, removes columns 2 and 4,
    keeps 'No.' and 'Z[ohm]'.
    """

    df = pd.read_csv(csv_path)

    # Keep only column 1 ("No.") and column 3 ("Z[ohm]")
    df = df.iloc[:, [0, 2]]
    df.columns = ["No", "Z_ohm"]

    # Type conversion
    df["No"] = df["No"].astype(int)
    df["Z_ohm"] = df["Z_ohm"].astype(float)

    # Index = measurement - 1
    df.index = df["No"] - 1

    return Measurement(
        weight_g=weight,
        resistance=df["Z_ohm"]
    )


def load_experiment(folder: str) -> Experiment:
    folder = Path(folder)
    pairs = {}
    zero_weight_file = folder / "0g_unload.csv"
    zero_weight_meas = load_measurement(zero_weight_file, 0)
    for i, weight in WEIGHT_MAP.items():
        load_file = folder / f"{weight}g_load.csv"
        unload_file = folder / f"{weight}g_unload.csv"

        load_meas = load_measurement(load_file, weight)
        unload_meas = load_measurement(unload_file, weight)

        pairs[weight] = LoadUnloadPair(load_meas, unload_meas)

    return Experiment(pairs)

# ------------------------
# Plotting functions
# ------------------------

def plot_load_unload(pair: LoadUnloadPair):
    plt.figure()
    plt.plot(pair.load.time, pair.load.resistance, label="Load")
    plt.plot(pair.unload.time, pair.unload.resistance, label="Unload")

    plt.xlabel("Time (s)")
    plt.ylabel("Resistance (Ω)")
    plt.title(f"{pair.load.weight_g} g — Load vs Unload")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"load_unload_{pair.load.weight_g}g.png")


def plot_difference(pair: LoadUnloadPair):
    plt.figure()
    plt.plot(pair.load.time, pair.difference)

    plt.xlabel("Time (s)")
    plt.ylabel("ΔResistance (Ω)")
    plt.title(f"{pair.load.weight_g} g — Load − Unload")
    plt.grid(True)
    plt.savefig(f"difference_{pair.load.weight_g}g.png")


def plot_all_loads(experiment: Experiment):
    plt.figure()
    zero_weight_file = folder / "0g_unload.csv"
    zero_weight_meas = load_measurement(zero_weight_file, 0)
    for weight, pair in experiment.pairs.items():
        plt.plot(pair.load.time, pair.load.resistance, label=f"{weight} g")
    plt.plot(
        zero_weight_meas.time,
        zero_weight_meas.resistance,
        label="0 g",)


    plt.xlabel("Time (s)")
    plt.ylabel("Resistance (Ω)")
    plt.title("Load Curves — All Weights")
    plt.legend()
    plt.grid(True)
    plt.savefig("all_loads.png")


# ------------------------
# Main
# ------------------------
# ------------------------
# Multi-experiment plotting
# ------------------------

def plot_load_unload_compare(
    exp_a: Experiment,
    exp_b: Experiment,
    label_a: str,
    label_b: str,
):
    for weight in exp_a.pairs.keys():
        pair_a = exp_a.pairs[weight]
        pair_b = exp_b.pairs[weight]

        plt.figure()

        # Load
        plt.plot(
            pair_a.load.time,
            pair_a.load.resistance,
            label=f"{label_a} Load",
            linestyle="-",
        )
        plt.plot(
            pair_b.load.time,
            pair_b.load.resistance,
            label=f"{label_b} Load",
            linestyle="--",
        )

        # Unload
        plt.plot(
            pair_a.unload.time,
            pair_a.unload.resistance,
            label=f"{label_a} Unload",
            linestyle="-.",
        )
        plt.plot(
            pair_b.unload.time,
            pair_b.unload.resistance,
            label=f"{label_b} Unload",
            linestyle=":",
        )

        plt.xlabel("Time (s)")
        plt.ylabel("Resistance (Ω)")
        plt.title(f"{weight} g — Load / Unload Comparison")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"compare_load_unload_{weight}g.png")
        plt.close()


def plot_difference_compare(
    exp_a: Experiment,
    exp_b: Experiment,
    label_a: str,
    label_b: str,
):
    for weight in exp_a.pairs.keys():
        pair_a = exp_a.pairs[weight]
        pair_b = exp_b.pairs[weight]

        plt.figure()

        plt.plot(
            pair_a.load.time,
            pair_a.difference,
            label=f"{label_a}",
            linestyle="-",
        )
        plt.plot(
            pair_b.load.time,
            pair_b.difference,
            label=f"{label_b}",
            linestyle="--",
        )

        plt.xlabel("Time (s)")
        plt.ylabel("ΔResistance (Ω)")
        plt.title(f"{weight} g — Load − Unload Difference")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"compare_difference_{weight}g.png")
        plt.close()


def plot_all_loads_compare(
    exp_a: Experiment,
    exp_b: Experiment,
    label_a: str,
    label_b: str,
):
    plt.figure()

    for weight, pair in exp_a.pairs.items():
        plt.plot(
            pair.load.time,
            pair.load.resistance,
            label=f"{label_a} {weight} g",
            linestyle="-",
        )

    for weight, pair in exp_b.pairs.items():
        plt.plot(
            pair.load.time,
            pair.load.resistance,
            label=f"{label_b} {weight} g",
            linestyle="--",
        )

    plt.xlabel("Time (s)")
    plt.ylabel("Resistance (Ω)")
    plt.title("All Load Curves — Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig("compare_all_loads.png")
    plt.close()


def plot_all_loads_compare_log(
    exp_a: Experiment,
    exp_b: Experiment,
    label_a: str,
    label_b: str,
):
    plt.figure()
    for weight, pair in exp_a.pairs.items():
        plt.plot(
            pair.load.time,
            np.log10(pair.load.resistance),
            label=f"{label_a} {weight} g",
            linestyle="-",
        )
    
    for weight, pair in exp_b.pairs.items():
        plt.plot(
            pair.load.time,
            np.log10(pair.load.resistance),
            label=f"{label_b} {weight} g",
            linestyle="--",
        )
    plt.xlabel("Time (s)")
    plt.ylabel("Resistance (Ω) - log scale")
    plt.title("All Load Curves — Comparison in log")
    plt.yscale("log")
    plt.legend()
    plt.grid(True)
    plt.savefig("compare_all_loads_log.png")
    plt.close()
#
# if __name__ == "__main__":
#     folder = input("Enter folder containing CSV files: ").strip()
#
#     exp = load_experiment(folder)
#
#     # Example plots
#     for weight, pair in exp.pairs.items():
#         plot_load_unload(pair)
#         plot_difference(pair)
#
#     plot_all_loads(exp)

if __name__ == "__main__":
    folder_a = input("Enter first folder: ").strip()
    folder_b = input("Enter second folder: ").strip()

    label_a = Path(folder_a).name
    label_b = Path(folder_b).name

    exp_a = load_experiment(folder_a)
    exp_b = load_experiment(folder_b)

    plot_all_loads_compare_log(exp_a, exp_b, label_a, label_b)

