# -*- coding: utf-8 -*-
"""
Import smoke test. Run this under ResSim's Jython with ResSim's jars on the
classpath -- see run_smoketest.ps1. No watershed is opened and nothing is
computed, so nothing else in the model gets a chance to fail first.

Two phases:
    1. every Java class the ResSim-side code imports
    2. every ResSim-side module, which exercises those imports for real

Anything that fails prints the exception. Everything that passes prints nothing,
so the output is the list of problems.
"""

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def readList(fileName):
    """[(first column, second column or "")] from a tab separated list file."""
    handle = open(os.path.join(HERE, fileName), "r")
    try:
        rows = []
        for line in handle.readlines():
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) == 1:
                parts.append("")
            rows.append((parts[0].strip(), parts[1].strip()))
        return rows
    finally:
        handle.close()


def tryImport(name):
    """None if the import worked, otherwise the error text."""
    try:
        __import__(name)
        return None
    except:
        info = sys.exc_info()
        return "%s: %s" %(info[0].__name__, info[1])


def tryLoadFile(path):
    """
    Import a file directly, for scripts that are not importable as modules --
    a folder with a space in its name, or one with no __init__.py. ResSim runs
    those perfectly well, so they still need testing.
    """
    import imp
    full = os.path.join(SCRIPTS, path.replace("/", os.sep))
    name = "smoketest_" + str(abs(hash(path)))
    try:
        handle = open(full, "r")
        try:
            imp.load_source(name, full, handle)
        finally:
            handle.close()
        return None
    except:
        info = sys.exc_info()
        return "%s: %s" %(info[0].__name__, info[1])


def phaseJava(rows):
    """
    Java classes. A name marked optional is one arm of a try/except, so the
    other arm covering it is the expected result, not a failure.
    """
    print("")
    print("=== Java classes (%d) ===" %len(rows))
    failures = []
    skipped = 0
    for name, flag in rows:
        problem = tryImport(name)
        if problem is None:
            continue
        if flag == "optional":
            skipped = skipped + 1      # the alternative import is the live one
            continue
        failures.append((name, problem))
        print("  FAIL %s" %name)
        print("       %s" %problem)
    if len(failures) == 0:
        print("  all %d required classes imported cleanly" %(len(rows)-skipped))
    if skipped > 0:
        print("  (%d optional alternatives absent, which is expected)" %skipped)
    return failures


def phaseModules(rows):
    """ResSim-side modules, by name where possible and by file where not."""
    print("")
    print("=== ResSim-side modules (%d) ===" %len(rows))
    failures = []
    for name, path in rows:
        problem = tryImport(name)
        if problem is not None and path:
            problem = tryLoadFile(path)     # not importable as a module
        if problem is not None:
            failures.append((name, problem))
            print("  FAIL %s" %name)
            print("       %s" %problem)
    if len(failures) == 0:
        print("  all %d imported cleanly" %len(rows))
    return failures


def main():
    print("Jython %s" %sys.version)
    try:
        import java.lang.System as System
        print("Java    %s" %System.getProperty("java.version"))
    except:
        print("Java    could not be determined")

    javaFailures = phaseJava(readList("java_classes.txt"))
    moduleFailures = phaseModules(readList("ressim_modules.txt"))

    handle = open(os.path.join(HERE, "smoketest_results.txt"), "w")
    try:
        handle.write("Jython %s\n" %sys.version)
        for label, failures in [("JAVA", javaFailures), ("MODULE", moduleFailures)]:
            for name, problem in failures:
                handle.write("%s\t%s\t%s\n" %(label, name, problem))
    finally:
        handle.close()

    total = len(javaFailures) + len(moduleFailures)
    print("")
    print("%d failure(s). Written to smoketest_results.txt" %total)


main()
