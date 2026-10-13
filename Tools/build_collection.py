"""Build the collection packs' levels (resumable): each finished level is saved on its own, so an
interrupted run picks up where it stopped. Then merge them into a report and export LevelData.swift.

  python3 build_collection.py build OUT_DIR [workers] [key,key,...]
  python3 build_collection.py merge OUT_DIR REPORT_IN.json REPORT_OUT.json OUT.swift
"""
import json
import os
import sys
from multiprocessing import Pool

from art_packs import collection_jobs
from generate_levels import job, export_swift

ORDER = {"master": 0, "challenge": 1, "gentle": 2}


def run(spec):
    lv, rep = job(spec)
    return lv, rep


def build(out, workers, only=None):
    os.makedirs(out, exist_ok=True)
    todo = [j for j in collection_jobs() if not os.path.exists(os.path.join(out, j[3] + ".json"))
            and (only is None or j[3] in only)]
    todo.sort(key=lambda j: ORDER[j[1]])
    print("to build:", len(todo), flush=True)
    with Pool(workers) as pool:
        for lv, rep in pool.imap_unordered(run, todo):
            json.dump({"level": lv, "report": rep}, open(os.path.join(out, lv["key"] + ".json"), "w"))
            print("saved", lv["key"], rep.get("tier"), rep["rating_gentle_classic_expert"],
                  rep["careless_win_gentle_classic_expert"], rep["one_step_player_wins_gentle_classic_expert"],
                  rep.get("lookahead_player_wins_gentle_classic_expert"), rep.get("build", ""), flush=True)


def merge(out, rep_in, rep_out, swift_out):
    base = json.load(open(rep_in))
    keys = [j[3] for j in collection_jobs()]
    levels = [lv for lv in base["levels"] if lv["key"] not in keys]
    report = {k: v for k, v in base["report"].items() if k not in keys}
    for k in keys:
        d = json.load(open(os.path.join(out, k + ".json")))
        lv = d["level"]
        lv.pop("challenge", None)      # collection levels are not Challenge-pack levels (badge colour)
        levels.append(lv)
        report[k] = d["report"]
    json.dump({"levels": levels, "report": report}, open(rep_out, "w"), indent=1)
    export_swift(levels, swift_out)
    print("merged", len(levels), "levels")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        only = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None
        build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2, only)
    else:
        merge(*sys.argv[2:6])
