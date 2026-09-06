"""Create independent runtime folders for official harness comparisons."""

import argparse
import json
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode", choices=["classical", "neural", "hybrid", "phase"], default="classical"
    )
    p.add_argument("--style", type=int, default=0)
    p.add_argument("--opening-style", choices=["none", "alien", "alien-selective"], default="none")
    p.add_argument("--alien-cp", type=int, default=15)
    p.add_argument("--model", type=Path, default=Path("models/value.npz"))
    p.add_argument("--player-policy", type=Path)
    p.add_argument("--policy-cp", type=int, default=20)
    p.add_argument("--root-value", action="store_true")
    p.add_argument("--root-value-cp", type=int, default=5)
    p.add_argument("--adaptive-time", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.root_value and (a.mode != "classical" or not a.player_policy):
        p.error("Root value requires classical mode and a player policy")
    if a.out.exists():
        raise ValueError("Use a fresh variant path to preserve prior builds")
    a.out.mkdir(parents=True)
    shutil.copy2("agent.py", a.out / "agent.py")
    shutil.copytree("engine", a.out / "engine", ignore=shutil.ignore_patterns("__pycache__"))
    if a.mode != "classical" or a.root_value:
        (a.out / "models").mkdir()
        shutil.copy2(a.model, a.out / "models/value.npz")
    if a.player_policy:
        (a.out / "models").mkdir(exist_ok=True)
        shutil.copy2(a.player_policy, a.out / "models/player-policy.npz")
    (a.out / "runtime.json").write_text(
        json.dumps(
            {
                "mode": a.mode,
                "style_tolerance": a.style,
                "opening_style": a.opening_style,
                "player_policy": bool(a.player_policy),
                "policy_cp": a.policy_cp,
                "alien_cp": a.alien_cp,
                **({"root_value": True, "root_value_cp": a.root_value_cp} if a.root_value else {}),
                **({"adaptive_time": True} if a.adaptive_time else {}),
            }
        )
    )


if __name__ == "__main__":
    main()
