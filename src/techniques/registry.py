from src.techniques import t1, t2, t3, t4


TECHNIQUES = {
    "T1": t1.run,
    "T2": t2.run,
    "T3": t3.run,
    "T4": t4.run,
}


def run_technique(name, config):
    if name not in TECHNIQUES:
        raise ValueError(f"Unknown technique {name}")
    return TECHNIQUES[name](config)
