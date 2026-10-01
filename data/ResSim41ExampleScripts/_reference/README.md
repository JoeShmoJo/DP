# _reference

`ressim_api.txt` — method signatures for the Java classes these scripts use,
extracted from `data/javaDocs`. Grep it instead of opening the javadocs.

```bash
grep -A40 "CLASS hec.rss.model.OpValue" ressim_api.txt
grep -B60 "getReservoirElement" ressim_api.txt | grep CLASS | tail -1
```

Inherited methods are listed on the parent class, not the child. If a method is
missing from `ScriptOpRule`, look at `OpRule`.

`build_api_reference.py` regenerates it. Run that after replacing the javadocs
with a different ResSim version.

    python data/scripts/_reference/build_api_reference.py

Neither file is read by ResSim. This folder exists for whoever is writing the
scripts, and can be deleted from a deployed watershed without effect.
