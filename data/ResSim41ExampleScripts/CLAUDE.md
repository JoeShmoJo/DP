# Writing Jython for HEC-ResSim

This folder is Jython that runs inside HEC-ResSim. It is not ordinary Python and
it cannot be run or tested the ordinary way. Read this before writing any of it.

The git rules in the repository root `CLAUDE.md` still apply. This file is only
about the code.

---

## The rule that matters most

**Copy what is already here.** This corpus is 147 `.py` files that are known to
work. Before using any construct, check whether it is already used.

```bash
grep -rn "the thing you want to use" --include='*.py' data/scripts/
```

If it returns nothing, do not use it. Find how the existing scripts solve that
problem and solve it the same way.

This is not a style preference. ResSim reports a syntax error as five words with
no line number, so an unfamiliar construct costs an hour. Matching the corpus
costs nothing.

When a rule below and an existing script disagree, the existing script wins.

---

## What you are writing for

| | |
|---|---|
| Language | Jython 2.7.3 — **Python 2 syntax** |
| Runs on | Java 21 |
| Inside | HEC-ResSim 4.1 (was 3.5) |

There has never been a Python 3 release of Jython. Do not write f-strings,
`print(...)` as the only form, type hints, `pathlib`, `subprocess.run`,
dict/set comprehensions, or anything else from Python 3.

There is no pip, no virtualenv, and no way to add a library. **If a module is
not imported by some script in this folder, assume it is not available.**

Across the 48 modules that actually run inside ResSim, the complete set of
non-Java imports is: `os`, `shutil`, `jarray`, `logging`, `bisect`, `sys`,
`math`, `datetime`, `fnmatch`, `json`, `calendar`, `array`, `io`, `csv`,
`glob`, `imp`, `copy`, `re`, `time`, `string`. That is the whole list.

`jarray` is Jython-only and is how you hand a Java method a primitive array.
Desktop-only packages such as `pandas`, `numpy` and `pathlib` do appear
elsewhere in this repo — in generator and audit scripts that run on ordinary
Python. Do not let them leak into a ResSim-side module.

`%` formatting only. Use `%s`, `%d`, `%.0f`. Not `.format()`, not f-strings.

---

## The three places code runs

**Scripted rules** operate a reservoir, diversion or reach.

```python
def initRuleScript(currentRule, network):
    return True                      # False halts the compute

def runRuleScript(currentRule, network, currentRuntimestep):
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MIN, 1200.0)
    return opValue                   # return None for no effect
```

**State variables** compute a number other rules read.

```python
def initStateVariable(currentVariable, network): ...
def computeStateVariable(currentVariable, network, currentRuntimestep): ...
def cleanupStateVariable(currentVariable, network): ...
```

**Scripts pane tools** are menu items, not part of a compute. They are marked by
a header comment ResSim reads:

```python
# displayinmenu=true
# displaytouser=true
# displayinselector=true
```

Tools can use Swing and dialogs. Rules and state variables cannot — they run
inside a compute and must never block.

---

## The two-file pattern

Never paste real logic into the ResSim editor. Paste a wrapper that imports the
real module from this folder.

```python
import sys

def initRuleScript(currentRule, network):
    modulePath = network.makeAbsolutePathFromWatershed("scripts")
    if not modulePath in sys.path:
        sys.path.append(modulePath)
    from externalRules import MyRule
    reload(MyRule)
    return MyRule.initRuleScript(currentRule, network)

def runRuleScript(currentRule, network, currentRuntimestep):
    from externalRules import MyRule
    return MyRule.runRuleScript(currentRule, network, currentRuntimestep)
```

`reload()` is the important line. ResSim keeps imported modules alive for the
whole session, so without it your edits do nothing until ResSim is restarted.

Save the wrapper next to the module as `<Name>_ScriptedRule_PasteIntoResSim.txt`
so it is obvious which text belongs in the editor.

---

## Finding out what an object can do

**First, `_reference/ressim_api.txt`.** Method signatures for the ~47 Java
classes these scripts use, pulled out of the javadocs.

```bash
grep -A40 "CLASS hec.rss.model.OpValue" data/scripts/_reference/ressim_api.txt
grep -B60 "getReservoirElement" data/scripts/_reference/ressim_api.txt | grep CLASS | tail -1
```

Inherited methods are listed on the parent, not the child. `ScriptOpRule` shows
nothing about elements; `OpRule`, its parent, is where `getReservoirElement()`
lives. Walk up when a method is missing.

**Second, ResSim itself.** The scripted rule editor has an APIs tree on the
right. Expanding `ScriptedRule` lists every method on `currentRule` for the
installed version, inherited ones included. That is the authority. Ask for a
screenshot rather than guessing.

**Third, a probe.** When neither settles it, write a throwaway rule that calls
the candidates inside `try/except` and prints what came back. See
`externalRules/DiversionElementProbe_PasteIntoResSim.txt`. Make it return `None`
from `runRuleScript` so it cannot affect the compute.

**Never invent a method name.** `network.getDiversionNames()` and
`network.findDiversion()` were invented in this repo once and neither exists.

---

## The API you will actually use

Counts are how many scripts here use each call — a good proxy for how safe it is.

### `currentRule` (a `ScriptOpRule`)

| Call | Notes |
|---|---|
| `getReservoirElement()` | The element this rule is on. **Works at diversions too** — it returns an `OperationsElement`, and `getOperationsElement()` is the same thing. 17 uses. |
| `varPut(name, value)` / `varGet(name)` / `varExists(name)` | Rule-scoped storage. 34 / 27 / 3 uses. |
| `getName()` | The **rule's** name, not the element's. |

Read an element's name defensively, because the two forms are both used here:

```python
element = currentRule.getReservoirElement()
try:
    return element._name
except:
    return element.toString()
```

### `network` (an `RssSystem`)

| Call | Uses |
|---|---|
| `makeAbsolutePathFromWatershed(relPath)` | 44 |
| `findReservoir(name)` / `getReservoirNames()` | 34 / 13 |
| `getTimeSeries(kind, name, group, param)` | 27 |
| `getStateVariable(name)` | 24 |
| `printMessage(msg)` / `printWarningMessage` / `printErrorMessage` | 17 / 7 / 6 |
| `getRssRun()` | 14 |
| `findJunction(name)` / `getJunctionNames()` | 10 / 3 |
| `getAlternative()` | 4 |

Useful specifics:

```python
# A reservoir's rule curve, straight as storage
network.getTimeSeries("Reservoir", "Foster", "Rule Curve", "Stor-ZONE")
# Cumulative local flow at a junction
network.getRssRun().getTSRecordByPathParts("Foster_IN", "FLOW-CUMLOC")
```

Time series answer `getCurrentValue(rts)` and `getPreviousValue(rts)`. Both can
return a DSS missing sentinel near 1e38 or a NaN, so filter before using:

```python
def _ok(v):
    try:
        f = float(v)
    except:
        return None
    if f != f:              # NaN is the only value not equal to itself
        return None
    if abs(f) > 1e30:       # DSS missing-value sentinels are around 1e38
        return None
    return f
```

### `OpValue` and `OpRule`

`OpRule` has exactly five rule types:

| Constant | Value | Means |
|---|---|---|
| `RULETYPE_FREE` | -1 | no constraint |
| `RULETYPE_MIN` | 0 | minimum flow |
| `RULETYPE_SPEC` | 1 | release exactly this |
| `RULETYPE_MAX` | 2 | maximum flow |
| `RULETYPE_DEMAND` | 3 | a demand |

```python
opValue = OpValue()
opValue.init(OpRule.RULETYPE_MIN, flow)
return opValue
```

`RULETYPE_DIVERSION` also appears in the javadocs. It is a display string on
`FirmYieldRuleRef` and has nothing to do with operating a diversion.

---

## Rule-scoped state

`varPut` / `varGet` persist across timesteps for the life of the rule. Use them
for anything expensive, like a parsed CSV.

Two traps:

`varPut(name, None)` goes through Java and does not behave like a Python `None`.
Do not store one. Ask `varExists(name)` instead.

ResSim caches rule variables across computes in the same session, so a rule
that reads its CSV only when `varExists` says it has not yet will never see an
edit. Read the CSV unconditionally in `initRuleScript`, which runs at the start
of every compute. Then an edit is picked up at the next compute.

**Do not check the file from `runRuleScript`.** A modified-time stamp compared
on every call costs two file-system calls per element per timestep. At the ~30
diversions that share `DiversionFromCSV.py` that adds up to millions of calls
in a long run, and far worse on a network or synced drive. Nobody edits a
config in the middle of a compute.

There are **two** independent caches. `reload()` in the wrapper handles stale
module code. Reading in init handles stale data. You need both.

---

## Time

Get a `HecTime` from a runtimestep with the helper, never by hand:

```python
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
hTime = getHecTimeFromRuntimestep(currentRuntimestep)
```

**Day of year is a trap.** Calling `dayOfYear()` on a real leap-year date shifts
everything after 28 February by one. Always project onto 2001 first:

```python
def _genericDayOfYear(hTime):
    month = hTime.month()
    day = hTime.day()
    if month == 2 and day == 29:
        day = 28
    probe = HecTime()
    probe.setYearMonthDay(2001, month, day, 1440)
    return int(probe.dayOfYear())
```

Volume conversion, used throughout:

```python
CFSDAY_TO_AF = (60*60*24)/43560.0            # about 1.98347
cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
```

Timestep length comes from `currentRuntimestep.getTimeStepMinutes()`. Never
assume daily.

---

## Config CSVs

Numbers that change belong in a CSV, not in the script. The house layout is one
row per day of a generic non-leap year:

```
# comments start with a hash and are stripped before parsing
Month,Day,Detroit,Hills Creek,Lookout Point
1,1,1200,400,1200
```

Column headers are element names exactly as ResSim spells them, spaces and all.
Read them with the repo's own helpers, not with `csv` directly:

```python
from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, \
    getCSVDictReader, convertCSVDictReaderToListDict
```

`csvDict.fieldnames` is only populated **after** you iterate the reader, so call
`convertCSVDictReaderToListDict` first and read `.fieldnames` after.

Resolve the path through `alt_config` so alternatives can point at different
files, with a default if the key is absent:

```python
def _resolveConfigPath(network, key, default):
    configCSV = default
    try:
        altSetupSV = network.getStateVariable("Alternative_Setup")
        configFromAlt = altSetupSV.varGet(key)
        if configFromAlt:
            configCSV = configFromAlt
    except:
        pass
    return network.makeAbsolutePathFromWatershed(configCSV)
```

Register the new key in `alt_config/_default.txt` with a comment saying which
script reads it.

**Generate config CSVs, do not type them.** Put a desktop-Python generator in
`externalRules/_offline_tests/build_*.py` that reads the raw source and writes
the config, and have it check its own output. Then a data update is a rerun, not
an editing session.

---

## Errors, and how to find them

ResSim reports a syntax error like this:

```
Python Compilation Error of Scripted Rule <name> failed
Failed to initialize Element <name>
```

No line number, no message. When that happens:

1. Parse the file under the Python 2 grammar. This catches most of it:
   ```bash
   python3 -c "from lib2to3.pgen2 import driver; from lib2to3 import pygram, pytree; \
   driver.Driver(pygram.python_grammar, convert=pytree.convert).parse_string(open('F.py').read())"
   ```
2. Check for tabs, CRLF and non-ASCII bytes.
3. Diff your file against a rule that is known to work, construct by construct.
4. Delete anything the corpus does not already use. Four constructs once broke a
   rule this way: tuple returns, `%+` format specifiers, `or 0.0` defaulting, and
   tuple `except` clauses.

If you cannot find it, say so plainly. Do not guess at a fix and call it fixed.

**Use a bare `except:`.** Java throwables do not all derive from Python's
`Exception`, so `except Exception:` can miss them. The corpus uses bare `except:`
54 times. `except Exception, e:` (Python 2 spelling) also appears.

Pylance and pyright cannot help here. They are Python 3 checkers, they cannot see
inside `.jar` files, and they cannot parse Python 2 `print` statements. Their
reports on this folder are noise.

---

## Testing before you paste

You can test the parts that are yours without ResSim. Stub the Java imports and
run on desktop Python:

```python
def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

for pkg in ("hec", "hec.rss", "hec.heclib", "hec.script"):
    _mod(pkg)
_mod("hec.rss.model", OpValue=OpValue, OpRule=OpRule)
_mod("hec.heclib.util", HecTime=HecTime)
```

Working examples: `externalRules/_offline_tests/test_MinFlowPlusWithdrawal.py`
and `test_DiversionFromCSV.py`.

This tests CSV parsing, arithmetic and lookup. It tests nothing about rule stack
behavior or whether a Java method exists. Say which is which when reporting
results.

---

## ResSim 4.1 versus 3.5

Six classes moved packages. Write every affected import to work in both:

```python
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5
```

| 3.5 | 4.1 |
|---|---|
| `hec.model.LocalTSRecordImpl` | `hec.rss.model.LocalTSRecordImpl` |
| `hec.client.ClientApp` | `hec.clientapp.client.ClientApp` |
| `hec.client.ManagerChooser` | `hec.clientapp.client.ManagerChooser` |
| `hec.script.ClientAppWrapper` | `hec.rss.script.ClientAppWrapper` |
| `hec.script.ResSim` | `hec.rss.script.ResSim` |
| `hec.model.TSDataSet` | gone; nothing used it |

Full write-up in `MIGRATION_3.5_to_4.1.md`. Audit tooling in `_migration/`:

```powershell
python data\scripts\_migration\catalog_imports.py
python data\scripts\_migration\check_against_install.py "C:\path\to\HEC-ResSim-4.1.0"
.\data\scripts\_migration\run_with_jython.ps1 -Install "C:\path\to\HEC-ResSim-4.1.0"
```

Only the imports were checked. A renamed **method** on a class that still imports
would not be caught. Running the model is the real test.

---

## Things that have gone wrong here before

1. **Invented API names.** `network.getDiversionNames()`, `findDiversion()`.
   Neither exists. Grep the corpus or `ressim_api.txt` first.
2. **Unattested syntax.** Four constructs broke a rule with no line number.
3. **`$py.class` files.** Jython writes one next to every module it imports.
   They are gitignored. Never commit them.
4. **Leap-year day-of-year.** Silently shifts everything after 28 February.
5. **Scripts-pane code missed.** An audit that only looked for
   `initRuleScript` / `initStateVariable` skipped 7 menu tools. Check the
   `# displayinmenu=` headers too.
6. **Stale caches.** A fix that "did nothing" was usually a missing `reload()`
   or a config read once and cached.
7. **Feedback loops.** A rule that chases a storage error can oscillate. Reading
   a rule curve's **slope** is feedforward and structurally cannot. Prefer it.

---

## House style

Match the surrounding files, then:

- A module docstring saying what the rule does and what its config looks like.
- `################` banner comments between sections, as the other files do.
- `USER INPUT` constants at the top, in caps, each with a comment.
- Leading underscore for helpers that are not entry points.
- A `DEBUG` flag guarding chatty `printMessage` calls.
- One `printMessage` per load saying what was read, so the compute log always
  shows which numbers were in play.
- Errors should say what to do, not just what happened. Name the file, the
  element, and what a fix looks like.
