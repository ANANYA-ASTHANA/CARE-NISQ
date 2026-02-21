from src.config import build_configs_for_main_grid

def run():
    configs = build_configs_for_main_grid(
        base_cfg_path="configs/base.yaml",
        main_cfg_path="configs/experiments_main.yaml",
        calibration_json_path="results/calibration.json",
    )
    print(f"Loaded {len(configs)} configs for main grid.")
    # Next step: loop configs and dispatch techniques
