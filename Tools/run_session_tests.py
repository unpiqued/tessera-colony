"""Run only the play-session checks (tests.session_tests) and merge them into an existing results file
(the other checks are untouched: no rule or level data changed with the crash fixes of 3 Oct).
Usage: python3 run_session_tests.py <levels_report.json> <test_results.json>"""
import json
import sys
import time

import tests


def main():
    rep = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    old = json.load(open(out))
    metrics = old.get("metrics", {})
    t0 = time.time()
    tests.session_tests(rep, metrics)
    new = [r for r in tests.RESULTS if r["name"].startswith("session:")]
    kept = [r for r in old["results"] if not r["name"].startswith("session:")]
    old["results"] = kept + new
    old["metrics"] = metrics
    old["seconds"] = round(old.get("seconds", 0) + time.time() - t0, 1)
    json.dump(old, open(out, "w"), indent=1)
    failed = [r for r in old["results"] if not r["passed"]]
    print("%d checks in %s (%d new session checks), %d failed" % (len(old["results"]), out, len(new), len(failed)))


if __name__ == "__main__":
    main()
