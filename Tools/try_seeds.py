"""Build one Master level with several candidate seeds (same picture) and save each result, so the
best one can be chosen against the pack's bar.

Usage: python3 try_seeds.py OUT_DIR key:seed[,seed...] [key:seed...] [workers]
"""
import json
import os
import sys
from multiprocessing import Pool

from art_packs import MASTER, art_for, master_kind
from generate_levels import job


def run(args):
    key, seed = args
    spec = next(m for m in MASTER if m[0] == key)
    _, title, sub, scene, _ = spec
    lv, rep = job((master_kind(key), key, title, sub, seed * 131 + 11, art_for(scene)))
    return key, seed, lv, rep


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    tasks = []
    workers = 2
    for a in sys.argv[2:]:
        if ":" not in a:
            workers = int(a)
            continue
        key, seeds = a.split(":")
        tasks += [(key, int(s)) for s in seeds.split(",")]
    with Pool(workers) as pool:
        for key, seed, lv, rep in pool.imap_unordered(run, tasks):
            json.dump({"level": lv, "report": rep, "seed": seed}, open(os.path.join(out, "%s_%d.json" % (key, seed)), "w"))
            print(key, seed, json.dumps({k: rep[k] for k in ("careless_win_gentle_classic_expert",
                                                            "one_step_player_wins_gentle_classic_expert",
                                                            "lookahead_player_wins_gentle_classic_expert")}), flush=True)


if __name__ == "__main__":
    main()
