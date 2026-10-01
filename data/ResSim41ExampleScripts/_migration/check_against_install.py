# -*- coding: utf-8 -*-
"""
Cross-reference the catalogued imports against a real ResSim installation.

This answers "does this class still exist in 4.1?" by looking inside the jars
that ship with the program, so it needs no knowledge of what HEC changed. Point
it at 4.1 alone to find what is missing, or at both versions to get a diff of
exactly what went away.

    python check_against_install.py "C:\\Program Files\\HEC\\HEC-ResSim\\4.1"
    python check_against_install.py "...\\4.1" --baseline "...\\3.5"

Run it from a desktop Python 3. It only reads files.

A jar is a zip, so this reads each jar's entry list and turns
hec/rss/model/OpRule.class into hec.rss.model.OpRule. Names that resolve to a
field rather than a class (hec.script.Constants.TRUE) fall back to their parent.
"""

import os
import sys
import csv
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "import_catalog.csv")

# Roots that ship with the application. java/javax come from the JRE, which is a
# separate question, so they are reported but not failed.
APP_ROOTS = ("hec", "hec2", "rma", "jxl", "com", "org")
JRE_ROOTS = ("java", "javax")


def wantedNames():
    """{fully qualified name: set of files importing it} from the catalog."""
    wanted = {}
    handle = open(CATALOG, "r")
    try:
        for row in csv.DictReader(handle):
            if row["category"] != "java" or row["runsUnder"] != "ressim":
                continue
            module, names = row["module"], row["imports"]
            targets = []
            if not names:
                targets.append(module)
            else:
                for name in names.replace("(", "").replace(")", "").split(","):
                    name = name.strip().split(" as ")[0].strip()
                    if name and name != "*":
                        targets.append(module + "." + name)
                    elif name == "*":
                        targets.append(module)
            for target in targets:
                wanted.setdefault(target, set()).add(row["file"])
    finally:
        handle.close()
    return wanted


def classesInInstall(installDir):
    """Every class name found in every jar under installDir."""
    classes = set()
    jarCount = 0
    jythonJars = []
    for dirPath, dirNames, fileNames in os.walk(installDir):
        for fileName in fileNames:
            low = fileName.lower()
            if not low.endswith(".jar"):
                continue
            full = os.path.join(dirPath, fileName)
            if "jython" in low:
                jythonJars.append(fileName)
            try:
                archive = zipfile.ZipFile(full)
            except Exception:
                continue
            jarCount += 1
            try:
                for entry in archive.namelist():
                    if entry.endswith(".class"):
                        classes.add(entry[:-6].replace("/", ".").replace("$", "."))
            finally:
                archive.close()
    return classes, jarCount, jythonJars


def resolve(name, classes):
    """True if the name is a class, or a member of one."""
    if name in classes:
        return True
    if "." in name and name.rsplit(".", 1)[0] in classes:
        return True          # a field or nested member, e.g. Constants.TRUE
    # A bare package import such as "import hec.heclib.grid"
    prefix = name + "."
    for candidate in classes:
        if candidate.startswith(prefix):
            return True
    return False


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    target = argv[1]
    baseline = None
    if "--baseline" in argv:
        baseline = argv[argv.index("--baseline") + 1]
    if not os.path.isdir(target):
        print("Not a directory: %s" % target)
        return 2

    wanted = wantedNames()
    print("Scanning %s ..." % target)
    targetClasses, jarCount, jythonJars = classesInInstall(target)
    print("  %d jars, %d classes" % (jarCount, len(targetClasses)))
    if jythonJars:
        print("  Jython jar(s): %s" % ", ".join(sorted(set(jythonJars))))
    else:
        print("  NO jython jar found by name -- check how this version runs scripts")

    baselineClasses = None
    if baseline:
        print("Scanning baseline %s ..." % baseline)
        baselineClasses, baseJars, baseJython = classesInInstall(baseline)
        print("  %d jars, %d classes" % (baseJars, len(baselineClasses)))
        if baseJython:
            print("  Jython jar(s): %s" % ", ".join(sorted(set(baseJython))))

    missing = []
    jreNames = []
    for name in sorted(wanted):
        root = name.split(".")[0]
        if root in JRE_ROOTS:
            jreNames.append(name)
            continue
        if root not in APP_ROOTS:
            continue
        if not resolve(name, targetClasses):
            wasThere = ""
            if baselineClasses is not None:
                wasThere = "present in baseline" if resolve(name, baselineClasses) \
                    else "absent in baseline too"
            missing.append((name, sorted(wanted[name]), wasThere))

    outPath = os.path.join(HERE, "missing_in_target.csv")
    handle = open(outPath, "w")
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["missingClass", "numFiles", "baseline", "files"])
    for name, files, wasThere in missing:
        writer.writerow([name, len(files), wasThere, "; ".join(files)])
    handle.close()

    print("\n%d of %d application classes did NOT resolve:"
          % (len(missing), len([n for n in wanted
                                if n.split(".")[0] in APP_ROOTS])))
    for name, files, wasThere in missing:
        note = (" (%s)" % wasThere) if wasThere else ""
        print("  %-48s %d file(s)%s" % (name, len(files), note))
    if not missing:
        print("  none -- every imported class still exists")
    print("\nWritten to %s" % outPath)
    print("%d java/javax names were skipped; those come from the JRE, not ResSim."
          % len(jreNames))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
