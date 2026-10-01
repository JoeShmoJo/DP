# HEC-ResSim 3.5 to 4.1: what changed in the scripts

Every change is an **import path**. No logic, no API calls, no behaviour was
altered. Each one imports the 4.1 path first and falls back to the 3.5 path, so
the same scripts folder runs under both versions and you can move back and forth
while testing.

Verified against HEC-ResSim 4.1.0, which runs **Jython 2.7.3 on Java 21**. Both
versions are Python 2, so no language changes were needed anywhere.

---

## The four files a compute needs

These are in the compute path. Without them the model will not run on 4.1.

| File | Change |
|---|---|
| `externalSVs/baseExternalSV.py` | `LocalTSRecordImpl` moved to `hec.rss.model`; unused `TSDataSet` import dropped |
| `NWDJyLib/CanadianOps/cNatLakeARDB.py` | same two |
| `NWDJyLib/ResSim/cResSim.py` | `ClientApp` moved to `hec.clientapp.client` |
| `NWDJyLib/ResSim/ResSimController.py` | `ClientApp` moved; `ClientAppWrapper` and `ResSim` moved to `hec.rss.script` |

`baseExternalSV.py` is the important one: `tscToTSRecord()` and
`hecMathToTSRecord()` are the base-class methods every external state variable
goes through.

## The eleven that are tools, not compute

These only fail when you use them. Nothing imports them, and no compute touches
them.

| File | Change | Fails when |
|---|---|---|
| `DP_Menu.py` | `ClientApp`, `ClientAppWrapper` | you open the DP menu |
| `Utilities/` &times; 7 | `ManagerChooser` moved to `hec.clientapp.client`; `ClientAppWrapper` moved | you run that Scripts-pane tool |
| `SalemAlbanyAugScript/RunningResSimHeadless/` &times; 3 | `ResSim` moved to `hec.rss.script` | you run a headless batch |

`Save_Scripts.py` is one of the seven. It dumps every scripted rule and state
variable in a watershed to disk, so it is worth having working before you need
it.

---

## The moves themselves

| 3.5 | 4.1 | Kind |
|---|---|---|
| `hec.model.LocalTSRecordImpl` | `hec.rss.model.LocalTSRecordImpl` | moved, gone from old path |
| `hec.client.ClientApp` | `hec.clientapp.client.ClientApp` | moved, gone from old path |
| `hec.client.ManagerChooser` | `hec.clientapp.client.ManagerChooser` | moved, gone from old path |
| `hec.model.TSDataSet` | `hec.clientapp.model.TSDataSet` | moved; **import deleted, never used** |
| `hec.script.ClientAppWrapper` | `hec.rss.script.ClientAppWrapper` | **deprecated, still works** |
| `hec.script.ResSim` | `hec.rss.script.ResSim` | **deprecated, still works** |

The last two are warnings rather than errors. 4.1 accepts the old path and prints
a deprecation notice; following it now avoids a break in some later release.

Everything else resolved unchanged, including `HecTime`, `Constants`, `OpValue`,
`OpRule`, `TSRecord`, `PairedValuesExt`, `RunTimeStep`, all of `hec.hecmath` and
all of `hec.heclib`.

## The shape of every edit

```python
#ClientApp moved from hec.client to hec.clientapp.client in ResSim 4.1. Import it
#both ways so this file runs under 4.1 and 3.5 alike.
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5
```

---

## Verifying it on another machine or another version

`scripts/_migration/` holds the audit tooling. It needs no Python install and
opens no watershed; see the README there. In short:

```powershell
.\data\scripts\_migration\run_with_jython.ps1 -Install "<path to HEC-ResSim>"
```

That imports every Java class and every ResSim-side module under that version's
own Jython and reports what fails. A clean run means the imports are sound.

`_migration` and `_offline_tests` are development tooling. They are harmless in
a watershed but not needed there, and can be left out when copying.

## What this does not prove

Imports only. A **renamed method** on a class that still imports fine would pass
every check here and fail during a compute -- `ClientApp.Workspace()` and the
`LocalTSRecordImpl` constructor are the two most plausible candidates. Those
surface only by running the model, which is the real test.
