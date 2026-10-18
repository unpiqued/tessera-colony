"""Convert the generated Swift level data (LevelData*.swift) into Web/data/levels.json.

Usage: python3 convert_levels.py ../../TesseraColony.swiftpm ../data/levels.json
Keeps every field of LevelDefinition. 64-bit golden hashes are stored as 16-digit hex strings.
"""
import json, re, sys, pathlib

src = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
files = ["LevelData.swift", "LevelDataCollection.swift", "LevelDataLiterature.swift",
         "LevelDataDiscovery.swift", "LevelDataSeasons.swift"]

palette = None
levels = {}
order = []
block_re = re.compile(r"static let (\w+) = LevelDefinition\((.*?)\n    \)\n", re.S)


def field(body, name, pat):
    m = re.search(r"\n\s+" + name + r":\s*" + pat, body, re.S)
    return m.group(1) if m else None


for fn in files:
    text = (src / fn).read_text()
    if palette is None and "enum GeneratedPalette" in text:
        names = json.loads(re.search(r"familyNames: \[String\] = (\[.*?\])", text).group(1))
        tones = [[int(h, 16) for h in re.findall(r"0x([0-9A-F]{6})", row)]
                 for row in re.findall(r"\[(0x[^\]]*)\]", re.search(r"static let tones: \[\[UInt32\]\] = \[(.*?)\n    \]", text, re.S).group(1))]
        consts = {k: int(re.search(r"static let " + k + r": UInt32 = 0x([0-9A-F]+)", text).group(1), 16)
                  for k in ("grout", "soil", "soilDark")}
        palette = {"names": names, "tones": tones, **consts}
    for m in block_re.finditer(text):
        var, body = m.group(1), m.group(2)
        lv = {
            "id": json.loads(field(body, "id", r'(".*?")')),
            "title": json.loads(field(body, "title", r'(".*?(?<!\\)")')),
            "subtitle": json.loads(field(body, "subtitle", r'(".*?(?<!\\)")')),
            "art": json.loads("[" + field(body, "art", r"\[(.*?)\]").strip().rstrip(",") + "]"),
            "tunnels": [[[int(a), int(b)] for a, b in re.findall(r"TeamSpec\((\d+), (\d+)\)", row)]
                        for row in re.findall(r"\[(TeamSpec[^\]]*)\]", field(body, "tunnels", r"\[(.*?)\n        \],"))],
            "chambersGentle": int(field(body, "chambersGentle", r"(\d+)")),
            "chambersClassic": int(field(body, "chambersClassic", r"(\d+)")),
            "chambersExpert": int(field(body, "chambersExpert", r"(\d+)")),
            "solution": json.loads(field(body, "solution", r"(\[.*?\])")),
            "goldenClaimsPerMove": json.loads(field(body, "goldenClaimsPerMove", r"(\[.*?\])")),
            "goldenClaimsHash": field(body, "goldenClaimsHash", r"0x([0-9A-F]+)").rjust(16, "0"),
            "goldenFinalStateHash": field(body, "goldenFinalStateHash", r"0x([0-9A-F]+)").rjust(16, "0"),
            "carelessWins": json.loads(field(body, "carelessWins", r"(\[.*?\])")),
            "greedyWins": json.loads(field(body, "greedyWins", r"(\[.*?\])")),
        }
        ch = field(body, "isChallenge", r"(true|false)")
        lv["isChallenge"] = ch == "true"
        pk = field(body, "pack", r'"(.*?)"')
        lv["pack"] = pk or "main"
        assert field(body, "palette", r"([\w.]+)") == "GeneratedPalette.builtIn", var
        assert all(len(r) == len(lv["art"][0]) for r in lv["art"]), var
        levels[var] = lv
        order.append(var)

assert len(levels) == 193, len(levels)
out.write_text(json.dumps({"palette": palette, "levels": levels}, separators=(",", ":")))
print(f"{len(levels)} levels, {out.stat().st_size // 1024} KB")
