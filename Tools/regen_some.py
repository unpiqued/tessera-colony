"""Rebuild only some levels and merge them into an existing report, then re-export LevelData.swift.

Usage: python3 regen_some.py ART.json REPORT_IN.json OUT.swift REPORT_OUT.json key1,key2,... [workers]

Uses exactly the same specs and seeds as generate_levels.py (MAIN_SPECS, CHALLENGE_SPECS and the
GARDEN / MASTER lists in art_packs.py), so the result equals a full regeneration. Levels in the
report whose key is no longer in any spec are dropped; the catalogue order follows the specs.
"""
import json
import sys
from multiprocessing import Pool

from art_packs import GARDEN, MASTER, art_for, master_kind, collection_jobs
from generate_levels import MAIN_SPECS, CHALLENGE_SPECS, job, export_swift


def job_key(j):
    return j[3] if j[0] == "pack" else j[1]


def all_jobs(art):
    jobs = []
    for key, title, sub, seed, nt, mw, mt, pw, art_key in MAIN_SPECS:
        jobs.append(("main", key, title, sub, seed, nt, mw, mt, pw, art[art_key]))
    for key, title, sub, seed, nt, art_key in CHALLENGE_SPECS:
        jobs.append(("challenge", key, title, sub, seed, nt, art[art_key]))
    for key, title, sub, gen, seed in GARDEN:
        jobs.append(("garden", key, title, sub, seed * 101 + 7, art_for(gen, seed)))
    for key, title, sub, gen, seed in MASTER:
        jobs.append((master_kind(key), key, title, sub, seed * 131 + 11, art_for(gen, seed)))
    jobs += collection_jobs()
    return jobs


def main():
    art = json.load(open(sys.argv[1]))
    old = json.load(open(sys.argv[2]))
    out_swift, out_report = sys.argv[3], sys.argv[4]
    keys = set(sys.argv[5].split(","))
    workers = int(sys.argv[6]) if len(sys.argv) > 6 else 2
    jobs = all_jobs(art)
    todo = [j for j in jobs if job_key(j) in keys]
    missing = keys - {job_key(j) for j in todo}
    assert not missing, "no spec for %s" % missing
    with Pool(workers) as pool:
        results = pool.map(job, todo, chunksize=1)
    fresh = {lv["key"]: (lv, rep) for lv, rep in results}
    old_levels = {lv["key"]: lv for lv in old["levels"]}
    levels, report = [], {}
    for j in jobs:
        k = job_key(j)
        if k in fresh:
            lv, rep = fresh[k]
        else:
            assert k in old_levels, "level %s is neither rebuilt nor in the old report" % k
            lv, rep = old_levels[k], old["report"][k]
        levels.append(lv)
        report[k] = rep
    for k in keys:
        rep = report[k]
        print(k, json.dumps({x: rep[x] for x in ("tiles", "teams", "rating_gentle_classic_expert",
                                                  "careless_win_gentle_classic_expert",
                                                  "one_step_player_wins_gentle_classic_expert",
                                                  "lookahead_player_wins_gentle_classic_expert") if x in rep}))
    export_swift(levels, out_swift)
    json.dump({"levels": levels, "report": report}, open(out_report, "w"), indent=1)


if __name__ == "__main__":
    main()
