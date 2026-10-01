# -*- coding: utf-8 -*-
"""
Catalog every import in the scripts tree and classify it for the ResSim
3.5 -> 4.1 move.

Runs on a DESKTOP Python 3, not inside ResSim:
    python data/scripts/_migration/catalog_imports.py

Writes:
    _migration/import_catalog.csv   one row per (file, imported name)
    _migration/import_summary.csv   one row per imported name, with file count

The split that matters is which interpreter a file runs under. A file that runs
under CPython (the plotting and CWMS-download tooling) is untouched by a ResSim
upgrade. A file that runs under ResSim's Jython is exposed to both the Java API
changes and any Jython version change.
"""

import os
import re
import csv
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)

# _migration is excluded because this file lists the ResSim entry point names it
# searches for, which makes it match itself.
SKIP_DIRS = ("__pycache__", ".git", "_migration")

# Imports that only ever exist in CPython. Any file using one of these is not a
# ResSim script, whatever directory it sits in.
CPYTHON_ONLY = set([
    "pandas", "numpy", "plotly", "matplotlib", "pydsstools", "requests",
    "urllib3", "cwms", "typing", "pathlib", "__future__", "multiprocessing",
    "importlib", "dataclasses", "cProfile", "DBAPI",
])

# Java package roots. These are the ones a version move can rename or remove.
JAVA_ROOTS = set(["hec", "hec2", "rma", "java", "javax", "com", "org", "jxl"])

# Shipped with Jython itself; safe unless the Jython version changes.
STDLIB = set([
    "os", "sys", "time", "datetime", "math", "re", "csv", "string", "copy",
    "pickle", "shutil", "glob", "json", "logging", "traceback", "threading",
    "decimal", "bisect", "calendar", "fnmatch", "tempfile", "subprocess",
    "webbrowser", "io", "array", "imp", "xml", "timeit", "ConfigParser",
    "configparser", "StringIO", "collections", "itertools", "functools",
    "operator", "random", "socket", "struct", "types", "warnings", "zipfile",
])

JYTHON_ONLY = set(["jarray"])

IMPORT_RE = re.compile(
    r"^[ \t]*(?:from[ \t]+([A-Za-z_][\w.]*)[ \t]+import[ \t]+(.+)"
    r"|import[ \t]+([A-Za-z_][\w.]*(?:[ \t]*,[ \t]*[A-Za-z_][\w.]*)*))")


def localPackages():
    """Top-level names that are directories or modules inside scripts/."""
    names = set()
    for entry in os.listdir(SCRIPTS):
        full = os.path.join(SCRIPTS, entry)
        if os.path.isdir(full) and not entry.startswith("."):
            names.add(entry)
        elif entry.endswith(".py"):
            names.add(entry[:-3])
    return names


LOCAL = localPackages()


# A file runs in ResSim if it defines one of these entry points, or if it is
# reachable by imports from one that does. Everything else in the tree -- the
# headless batch runners, the plotting utilities, the DSS download tooling --
# may be Jython, but ResSim never loads it, so it is out of scope.
ENTRY_POINT_DEFS = [
    "def initRuleScript", "def runRuleScript",          # scripted rules
    "def initStateVariable", "def computeStateVariable",  # state variables
    "def runStateVariable", "def cleanupStateVariable",
]

# A script run by hand from ResSim's Scripts pane has no entry point to detect --
# it is a module that runs top to bottom. What it does carry is the header ResSim
# reads to build its menu, so that is the signature. Without this the Utilities
# scripts fall outside the audit, which is how seven un-migrated imports of
# hec.client.ManagerChooser survived the first pass.
ENTRY_POINT_HEADERS = [
    "# displayinmenu=", "#displayinmenu=",
    "# displaytouser=", "#displaytouser=",
    "# displayinselector=", "#displayinselector=",
]


def moduleToFile():
    """{dotted module name: path relative to scripts/} for local modules."""
    mapping = {}
    for dirPath, dirNames, fileNames in os.walk(SCRIPTS):
        dirNames[:] = [d for d in dirNames if d not in SKIP_DIRS]
        for fileName in fileNames:
            if not fileName.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirPath, fileName),
                                  SCRIPTS).replace("\\", "/")
            dotted = rel[:-3].replace("/", ".")
            mapping[dotted] = rel
            if dotted.endswith(".__init__"):
                mapping[dotted[:-9].rstrip(".")] = rel
    return mapping


def findEntryPoints():
    """Files that ResSim itself calls into."""
    entries = set()
    for dirPath, dirNames, fileNames in os.walk(SCRIPTS):
        dirNames[:] = [d for d in dirNames if d not in SKIP_DIRS]
        for fileName in fileNames:
            # The PasteIntoResSim .txt files ARE rules; they just live as text.
            if not (fileName.endswith(".py") or fileName.endswith(".txt")):
                continue
            full = os.path.join(dirPath, fileName)
            try:
                handle = open(full, "r", encoding="utf-8", errors="replace")
            except TypeError:
                handle = open(full, "r")
            try:
                text = handle.read()
            finally:
                handle.close()
            for marker in ENTRY_POINT_DEFS + ENTRY_POINT_HEADERS:
                if marker in text:
                    entries.add(os.path.relpath(full, SCRIPTS).replace("\\", "/"))
                    break
    return entries


def reachableFromEntryPoints(importsByFile):
    """Entry points plus everything they import, transitively."""
    mapping = moduleToFile()
    reached = set()
    queue = list(findEntryPoints())
    # .txt rules are entry points but carry no catalogued imports of their own;
    # they pull in the .py module, which the queue picks up below.
    while queue:
        rel = queue.pop()
        if rel in reached:
            continue
        reached.add(rel)
        for module, names, _lineNum, _optional in importsByFile.get(rel, []):
            candidates = [module]
            for name in names.replace("(", "").replace(")", "").split(","):
                name = name.strip().split(" as ")[0].strip()
                if name and name != "*":
                    candidates.append(module + "." + name)
            for candidate in candidates:
                target = mapping.get(candidate)
                if target is not None and target not in reached:
                    queue.append(target)
    return reached


def classify(root):
    if root in JAVA_ROOTS:
        return "java"
    if root in CPYTHON_ONLY:
        return "cpython-only"
    if root in JYTHON_ONLY:
        return "jython"
    if root in STDLIB:
        return "stdlib"
    if root in LOCAL:
        return "local"
    return "unknown"


def readImports(path):
    """[(module, namesImported, lineNumber)] for one file."""
    found = []
    try:
        handle = open(path, "r", encoding="utf-8", errors="replace")
    except TypeError:                       # Python 2 fallback
        handle = open(path, "r")
    try:
        for lineNum, line in enumerate(handle, 1):
            if "import" not in line:
                continue
            match = IMPORT_RE.match(line)
            if not match:
                continue
            fromMod, names, plainMods = match.group(1), match.group(2), match.group(3)
            # An indented import at module level is inside a try/except, which
            # means it is one of several alternatives. Only one has to resolve.
            optional = line[:1] in (" ", "\t")
            if fromMod:
                names = names.split("#")[0].strip().rstrip("\\").strip()
                found.append((fromMod, names, lineNum, optional))
            else:
                for mod in plainMods.split(","):
                    mod = mod.split("#")[0].strip()
                    if mod:
                        found.append((mod, "", lineNum, optional))
    finally:
        handle.close()
    return found


def main():
    importsByFile = {}
    for dirPath, dirNames, fileNames in os.walk(SCRIPTS):
        dirNames[:] = [d for d in dirNames if d not in SKIP_DIRS]
        for fileName in sorted(fileNames):
            if fileName.endswith(".py"):
                full = os.path.join(dirPath, fileName)
                rel = os.path.relpath(full, SCRIPTS).replace("\\", "/")
                importsByFile[rel] = readImports(full)

    inRessim = reachableFromEntryPoints(importsByFile)

    rows = []
    fileKinds = {}
    for rel in sorted(importsByFile):
            imports = importsByFile[rel]
            roots = set(m.split(".")[0] for m, _, _, _ in imports)
            if roots & CPYTHON_ONLY:
                kind = "cpython"          # cannot be a ResSim script
            elif rel in inRessim:
                kind = "ressim"           # ResSim loads this
            else:
                kind = "other-jython"     # Jython, but ResSim never loads it
            fileKinds[rel] = kind
            for module, names, lineNum, optional in imports:
                rows.append({
                    "file": rel,
                    "runsUnder": kind,
                    "module": module,
                    "root": module.split(".")[0],
                    "category": classify(module.split(".")[0]),
                    "imports": names,
                    "line": lineNum,
                    "optional": optional and "yes" or "no",
                })

    catalogPath = os.path.join(HERE, "import_catalog.csv")
    handle = open(catalogPath, "w")
    writer = csv.DictWriter(handle, fieldnames=[
        "file", "runsUnder", "module", "root", "category", "imports", "line",
        "optional"],
        lineterminator="\n")
    writer.writeheader()
    for row in sorted(rows, key=lambda r: (r["category"], r["module"], r["file"])):
        writer.writerow(row)
    handle.close()

    # Per-module summary, restricted to what ResSim actually runs.
    byModule = {}
    for row in rows:
        if row["runsUnder"] != "ressim":
            continue
        key = (row["category"], row["module"])
        byModule.setdefault(key, set()).add(row["file"])
    summaryPath = os.path.join(HERE, "import_summary.csv")
    handle = open(summaryPath, "w")
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["category", "module", "numJythonFiles", "exampleFile"])
    for (category, module) in sorted(byModule.keys()):
        files = sorted(byModule[(category, module)])
        writer.writerow([category, module, len(files), files[0]])
    handle.close()

    # Two plain lists for the in-ResSim smoke test to read. Kept as text so the
    # Jython side needs no csv parsing.
    modulePath = os.path.join(HERE, "ressim_modules.txt")
    handle = open(modulePath, "w")
    for rel in sorted(fileKinds):
        if fileKinds[rel] != "ressim":
            continue
        dotted = rel[:-3].replace("/", ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[:-9]
        # Path as well as name: a folder with a space in it, or one with no
        # __init__.py, is a perfectly good ResSim script but not an importable
        # module, so the smoke test loads those by file instead.
        handle.write(dotted + "\t" + rel + "\n")
    handle.close()

    javaPath = os.path.join(HERE, "java_classes.txt")
    javaNames = set()
    requiredNames = set()
    for row in rows:
        if row["runsUnder"] != "ressim" or row["category"] != "java":
            continue
        targets = []
        if row["imports"]:
            for name in row["imports"].replace("(", "").replace(")", "").split(","):
                name = name.strip().split(" as ")[0].strip()
                if name and name != "*":
                    targets.append(row["module"] + "." + name)
                elif name == "*":
                    targets.append(row["module"])
        else:
            targets.append(row["module"])
        for target in targets:
            javaNames.add(target)
            if row["optional"] != "yes":
                requiredNames.add(target)
    handle = open(javaPath, "w")
    for name in sorted(javaNames):
        flag = name in requiredNames and "required" or "optional"
        handle.write(name + "\t" + flag + "\n")
    handle.close()

    counts0 = {}
    for rel in fileKinds:
        counts0[fileKinds[rel]] = counts0.get(fileKinds[rel], 0) + 1
    print("%d .py files:" % len(fileKinds))
    for kind in sorted(counts0, key=lambda k: -counts0[k]):
        print("  %-14s %d" % (kind, counts0[kind]))
    print("%d import statements catalogued -> %s" % (len(rows), catalogPath))
    counts = {}
    for (category, module) in byModule:
        counts[category] = counts.get(category, 0) + 1
    print("\ndistinct modules imported by the ResSim side:")
    for category in sorted(counts, key=lambda c: -counts[c]):
        print("  %-14s %d" % (category, counts[category]))


if __name__ == "__main__":
    main()
