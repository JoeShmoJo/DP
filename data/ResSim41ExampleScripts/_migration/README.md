# ResSim 3.5 -> 4.1 import audit

Tooling to find which imports break in the upgrade. All three scripts read files only; none of them opens a watershed or computes
anything.

**If you do not have Python installed**, you do not need it. Everything here
also runs under the Jython that ships with ResSim, via `run_with_jython.ps1`.
Each step below gives both forms.

## Scope

Only code **ResSim actually loads** is assessed. That set is derived, not
assumed: a file is in scope if it defines a ResSim entry point
(`initRuleScript`, `runRuleScript`, `initStateVariable`, `computeStateVariable`,
`runStateVariable`, `cleanupStateVariable`) or is reachable by imports from one
that does. Headless batch runners, plotting utilities and DSS download tooling
are Jython in places but ResSim never loads them, so they are out of scope.

As of this audit: **142 .py files, of which 39 are in scope.**

**Known gap:** a script run by hand from ResSim's Scripts pane has no entry point
to detect -- it is just a module that runs top to bottom. `DP_Menu.py` is one of
these, and the detector missed it. Treat 39 as a floor. If you run other scripts
from the Scripts pane, name them and they can be checked directly. Of NWDJyLib's 25
modules, 10 are reachable.

## Step 1 - build the catalog

```powershell
python data/scripts/_migration/catalog_imports.py
```

or, with no Python installed:

```powershell
cd data\scripts\_migration
.\run_with_jython.ps1 -Install "C:\Program Files\HEC\HEC-ResSim\4.1" -Script catalog_imports.py
```

Writes `import_catalog.csv` (one row per import, with a `runsUnder` column of
`ressim` / `other-jython` / `cpython`) and `import_summary.csv` (one row per
module, ResSim scope only).

## Step 2 - check against a real installation

```powershell
python data/scripts/_migration/check_against_install.py "C:\Program Files\HEC\HEC-ResSim\4.1"
```

or:

```powershell
.\run_with_jython.ps1 -Install "C:\Program Files\HEC\HEC-ResSim\4.1" -Script check_against_install.py -ScriptArgs "C:\Program Files\HEC\HEC-ResSim\4.1"
```

Add a baseline to get a true diff of what went away between versions:

```powershell
python data/scripts/_migration/check_against_install.py "C:\Program Files\HEC\HEC-ResSim\4.1" --baseline "C:\Program Files\HEC\HEC-ResSim\3.5"
```

It reads the class list out of every `.jar` in the install, so it needs no
knowledge of what HEC changed. Writes `missing_in_target.csv`, naming each
unresolved class and every file that imports it.

It also reports the **Jython jar version** found in each install. That answers
the question everything else depends on: if both versions ship Jython 2.7, this
is a Java API problem only. If the interpreter changed, the language itself is
in scope and the job is much larger.

## Step 3 - import smoke test, still with no watershed

Static jar checking proves a class exists. It does not prove a module imports.
`smoketest_imports.py` runs under ResSim's own Jython with ResSim's jars on the
classpath, imports every Java class and every ResSim-side module, and reports
what fails.

```powershell
.\run_with_jython.ps1 -Install "C:\Program Files\HEC\HEC-ResSim\4.1"
```

It opens no watershed and computes nothing, so no other script gets a chance to
fail first and mask the result. Run it once per install to compare versions.
It prints the Jython and Java versions it actually ran on, and writes
`smoketest_results.txt`.

The classpath is built by finding every `.jar` under the install directory and
handing Java wildcard entries, so it does not depend on the jar layout staying
the same between versions.

## Only then, a watershed

By the time these three steps are clean, what is left is runtime behavior rather
than imports. That is the point at which a stripped-down watershed with one
reservoir and one rule is worth building.

## Re-run after changing code

Both steps are safe to re-run; step 1 regenerates the catalog from the tree.


## Model output checks moved

`catalog_dss.py` and `extract_dss.py` now live in `model_check/` at the root of
the repository, with the diagnostics that use their output.
