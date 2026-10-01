# -*- coding: utf-8 -*-
"""
Build a grep-able API reference for the Java classes these scripts actually use.

This runs on a DESKTOP Python 3, not inside ResSim.

    python data/scripts/_reference/build_api_reference.py

Why this exists
---------------
data/javaDocs holds the full HEC-ResSim javadocs: 1187 files, about 621,000
lines of HTML. Nothing can read that, and grepping raw HTML returns tag soup.
This pulls the method signatures for the ~60 classes named in
_migration/java_classes.txt into one plain text file that greps cleanly.

    grep -A40 "CLASS hec.rss.model.OpValue" data/scripts/_reference/ressim_api.txt

Rerun it if the javadocs are replaced with a different ResSim version.
"""

import os
import re
import html

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(SCRIPTS))

JAVADOCS = os.path.join(REPO, "data", "javaDocs")
CLASS_LIST = os.path.join(SCRIPTS, "_migration", "java_classes.txt")
OUTPUT = os.path.join(HERE, "ressim_api.txt")

# Classes worth including even if no script imports them by name, because they
# are what the entry-point arguments actually are.
ALWAYS = [
    "hec.rss.model.ScriptOpRule",     # what currentRule is
    "hec.rss.model.RssSystem",        # what network is
    "hec.model.RunTimeStep",          # what currentRuntimestep is
    "hec.rss.model.Element",
    "hec.rss.model.ReservoirElement",
    "hec.rss.model.DiversionElement",
    "hec.rss.model.OpValue",
    "hec.rss.model.OpRule",
    "hec.heclib.util.HecTime",
    "hec.model.TSRecord",
]


def stripTags(fragment):
    """HTML fragment -> one line of readable text."""
    text = re.sub(r"<[^>]+>", "", fragment)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def shortenTypes(text):
    """java.lang.String -> String, so signatures fit on one line."""
    return re.sub(r"\b(?:[a-z][\w]*\.)+([A-Z]\w*)", r"\1", text)


def readClassPage(className):
    """Path to a class's javadoc page, or None if it is not there."""
    path = os.path.join(JAVADOCS, *className.split(".")) + ".html"
    if not os.path.exists(path):
        return None
    handle = open(path, encoding="utf-8", errors="replace")
    try:
        return handle.read()
    finally:
        handle.close()


def extractRows(page, summaryTitle):
    """
    Pull (returnType, signature) pairs out of one javadoc summary table.

    Javadoc 17 lays each row out as a pair of divs, col-first holding the
    return type and col-second holding the name and arguments.
    """
    block = re.search(
        r'<section class="%s"[^>]*>(.*?)</section>' % summaryTitle, page, re.S)
    if block is None:
        return []
    body = block.group(1)
    rows = []
    pattern = re.compile(
        r'<div class="col-first[^"]*">(.*?)</div>\s*'
        r'<div class="col-second[^"]*">(.*?)</div>', re.S)
    for first, second in pattern.findall(body):
        returnType = shortenTypes(stripTags(first))
        signature = shortenTypes(stripTags(second))
        if not signature or signature.lower() in ("method", "field", "constructor"):
            continue
        # Drop the modifiers javadoc puts in col-first for fields
        returnType = returnType.replace("static ", "").replace("final ", "").strip()
        rows.append((returnType, signature))
    return rows


def describeClass(className):
    """One class as a block of plain text, or None if it has no javadoc page."""
    page = readClassPage(className)
    if page is None:
        return None

    out = ["CLASS %s" % className]

    heading = re.search(r'<h1 title="[^"]*"[^>]*>(.*?)</h1>', page, re.S)
    declaration = re.search(r'<div class="type-signature">(.*?)</div>', page, re.S)
    if declaration:
        out.append("  %s" % shortenTypes(stripTags(declaration.group(1))))
    elif heading:
        out.append("  %s" % stripTags(heading.group(1)))

    summary = re.search(r'<div class="block">(.*?)</div>', page, re.S)
    if summary:
        text = stripTags(summary.group(1))
        if text:
            out.append("  %s" % text[:300])

    fields = extractRows(page, "field-summary")
    if fields:
        out.append("  FIELDS")
        for fieldType, signature in fields:
            out.append("    %-14s %s" % (fieldType, signature))

    methods = extractRows(page, "method-summary")
    if methods:
        out.append("  METHODS")
        for returnType, signature in methods:
            out.append("    %-14s %s" % (returnType, signature))

    if not fields and not methods:
        out.append("  (no members listed -- probably an interface alias or a package)")

    return "\n".join(out)


def wantedClasses():
    """Classes from the import catalog, plus the entry-point argument types."""
    names = set(ALWAYS)
    handle = open(CLASS_LIST)
    try:
        for line in handle:
            name = line.split("\t")[0].strip()
            if name and "." in name:
                names.add(name)
    finally:
        handle.close()
    return sorted(names)


def main():
    if not os.path.isdir(JAVADOCS):
        raise SystemExit("No javadocs at %s. Nothing to build." % JAVADOCS)

    blocks = []
    missing = []
    for className in wantedClasses():
        block = describeClass(className)
        if block is None:
            missing.append(className)
        else:
            blocks.append(block)

    header = [
        "HEC-ResSim Java API, for the classes these scripts use.",
        "",
        "GENERATED from data/javaDocs by scripts/_reference/build_api_reference.py",
        "Do not edit by hand.",
        "",
        "Look a class up with:",
        '    grep -A40 "CLASS hec.rss.model.OpValue" scripts/_reference/ressim_api.txt',
        "Find which class has a method with:",
        '    grep -B60 "getReservoirElement" scripts/_reference/ressim_api.txt | grep CLASS | tail -1',
        "",
        "Package names are shortened in signatures: java.lang.String reads as String.",
        "",
    ]
    if missing:
        header.append("No javadoc page for: %s" % ", ".join(missing))
        header.append("")
    header.append("=" * 70)
    header.append("")

    handle = open(OUTPUT, "w")
    try:
        handle.write("\n".join(header))
        handle.write("\n\n".join(blocks))
        handle.write("\n")
    finally:
        handle.close()

    print("Wrote %s" % OUTPUT)
    print("  %d classes, %d lines" % (len(blocks), len(open(OUTPUT).read().splitlines())))
    if missing:
        print("  no javadoc page for %d: %s" % (len(missing), ", ".join(missing)))


if __name__ == "__main__":
    main()
