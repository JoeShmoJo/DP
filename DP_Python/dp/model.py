"""
The Damages Prevented computation, ported from the ResSim 4.1 scripts
(data/ResSim41ExampleScripts/DamagesPrevented: cTransform, cWaterBalance,
cMiniSims) to plain Python. The ResSim computes of the Observed and
Unregulated alternatives are replaced by simulate():

  Observed run     every reservoir releases its Specified Release record
  Unregulated run  every reservoir passes inflow

Both route with dp.routing (the same routing the mini-simulations always used)
through the network exported from ResSim (network.json). Diversions are
ignored, as in the ResSim process (INCLUDE_DIVERSIONS = False).

Series are pandas Series on one hourly index from the lookback time to the end
of the simulation window. Peaks are taken over that whole index, as in ResSim.

Data types, as ResSim handles them: when ResSim computes an alternative it
converts every INST-VAL input to a period average over the time step, i.e.
(previous value + this value) / 2. The ResSim scripts (water balance, gage
peaks, added-flow gages) use the records as stored. So simulate() averages
INST-VAL inputs and everything else uses them as they are. The water-balance
locals are PER-AVER (cWaterBalance sets the observed flow to PER-AVER); the
transformed locals keep the gage's INST-VAL.
"""
import math
import os

import numpy as np
import pandas as pd

from .network import Network
from .routing import build_reach

DPCALC_NAMES = ("dpcalc.dss", "locals-finalwaterbalance.dss", "locals-transformed.dss")
REREG = {"Detroit": "Big Cliff", "Lookout Point": "Dexter"}


class DPError(Exception):
    """A problem that stops the run, with a message saying what to fix."""


def file_kind(dss_file):
    name = os.path.basename(dss_file.replace("\\", "/")).lower().replace("_", " ")
    if name == "obsdata.dss":
        return "obsData"
    if name == "zero flow record.dss":
        return "zero"
    if name in DPCALC_NAMES:
        return "computed"
    return "other"


def path_key(pathname):
    parts = pathname.strip().upper().split("/")
    if len(parts) >= 7:
        parts[4] = ""
    return "/".join(parts)


def r100(v):
    """Round to the nearest 100 like Jython 2.7's round(v, -2): halves away from zero"""
    return math.copysign(math.floor(abs(v) / 100.0 + 0.5) * 100.0, v)


def force_min(values, min_flow, conserve_volume=True):
    """cMiniSims.forceMinRelease"""
    out = np.array(values, dtype=float)
    running = 0.0
    for i in range(len(out)):
        if conserve_volume:
            new = max(out[i] - running, min_flow)
            running += new - out[i]
        else:
            new = max(out[i], min_flow)
        out[i] = new
    return out


def remove_negative_locals(values):
    """cTsUtils.removeNegativeLocals: zero the negatives, scale the rest to keep the volume"""
    v = np.array(values, dtype=float)
    neg = -v[v < 0].sum()
    pos = v[v >= 0].sum()
    if pos < neg:
        return np.array(values, dtype=float)
    v[v < 0] = 0.0
    return v * ((pos - neg) / pos)


def period_average(s):
    """INST-VAL -> PER-AVER at the same interval: (previous + current) / 2, first value kept"""
    prev = s.shift(1)
    prev.iloc[0] = s.iloc[0]
    out = (s + prev) / 2.0
    out.attrs["type"] = "PER-AVER"
    return out


def typed(s, dtype):
    s.attrs["type"] = dtype
    return s


def read_name_list(path):
    names = []
    for line in open(path):
        line = line.split("#", 1)[0].strip()
        if line:
            names.append(line)
    return names


def read_csv_rows(path):
    rows = []
    for line in open(path):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        rows.append([f.strip() for f in line.rstrip("\n").split(",")])
    return rows


################################################################################
# INPUT DATA

class Inputs:
    """
    Every series the alternatives map, on one hourly index. Records mapped to
    obsData.dss are read from it, the zero-flow record is zeros, and DPcalc.dss
    records come from `computed` (filled by the transform and water-balance steps).
    """

    def __init__(self, obs_dss, index, log=print):
        self.obs = obs_dss
        self.index = index
        self.computed = {}        # key -> Series; Series.attrs["type"] is INST-VAL or PER-AVER
        self._cache = {}
        self.log = log
        self.gaps = {}            # key -> number of hours filled by interpolation
        self.filled = {}          # key -> bool Series, True where an hour was filled
        self.sources = {}         # computed key -> obsData.dss keys it was made from

    def zeros(self):
        return pd.Series(0.0, index=self.index)

    def obsdata(self, pathname):
        key = path_key(pathname)
        if key not in self._cache:
            s = self.obs.read(pathname, self.index[0], self.index[-1])
            if s is None:
                self._cache[key] = None
            else:
                dtype = s.attrs.get("type", "")
                s = s[~s.index.duplicated()].reindex(self.index)
                missing = s.isna()
                if missing.any():
                    #Missing hours would turn every flow downstream into NaN. Fill them by
                    #straight-line interpolation (nearest value at the ends). The first and
                    #last hours of the run window are outside the period step 1 downloads,
                    #so they are held at the nearest value without comment; any other filled
                    #hour is reported and shaded in the plots, and should be cleaned in DSSVue
                    #before a final run.
                    gap = missing.copy()
                    gap.iloc[0] = gap.iloc[-1] = False
                    if gap.any():
                        self.gaps[key] = int(gap.sum())
                        self.filled[key] = gap
                    s = s.interpolate(limit_direction="both")
                s.attrs["type"] = dtype
                self._cache[key] = s
        return self._cache[key]

    def record(self, rec, what, compute=False):
        """
        Series for a TSRecord from network.json, or raise DPError. compute=True:
        as ResSim's compute sees it (INST-VAL converted to a period average).
        """
        s = self._record(rec, what)
        if compute and s is not None and s.attrs.get("type") == "INST-VAL":
            s = period_average(s)
        return s

    def record_keys(self, rec):
        """obsData.dss keys a TSRecord's series comes from (computed records: what they were made from)"""
        if rec is None or rec.is_blank:
            return set()
        kind = file_kind(rec.dss_file)
        if kind == "obsData":
            return {path_key(rec.pathname)}
        if kind == "computed":
            return set(self.sources.get(path_key(rec.pathname), ()))
        return set()

    def filled_mask(self, keys):
        """True at hours where any of these records was filled by interpolation, or None if none was"""
        masks = [self.filled[k] for k in keys if k in self.filled]
        if not masks:
            return None
        out = masks[0].copy()
        for m in masks[1:]:
            out = out | m
        return out if out.any() else None

    def _record(self, rec, what):
        if rec is None or rec.is_blank:
            return None
        kind = file_kind(rec.dss_file)
        if kind == "zero":
            return self.zeros()
        if kind == "computed":
            s = self.computed.get(path_key(rec.pathname))
            if s is None:
                raise DPError(f"{what}: {rec.pathname} is computed by DP but has not been computed yet")
            return s
        if kind == "obsData":
            s = self.obsdata(rec.pathname)
            if s is None:
                raise DPError(f"{what}: {rec.pathname} is not in {self.obs.filename}")
            return s
        raise DPError(f"{what}: mapped to {rec.dss_file}, which DP_Python does not read")


def reservoir_elevation_record(net, alt_name, reservoir_name):
    """TSRecord of a reservoir's observed pool elevation (Observed tab, else its Lookback Elevation), or None"""
    alt = net.alternatives[alt_name]
    proxy = net.elements["reservoir:" + reservoir_name]["inflowProxy"]
    for recs in (alt.observed, alt.input):
        for (name, vid), rec in recs.items():
            if name == proxy and rec.param.lower().startswith("elev") and not rec.is_blank:
                return rec
    return None


def reservoir_elevation(net, alt_name, inputs, reservoir_name):
    """Observed pool elevation of a reservoir, or None"""
    rec = reservoir_elevation_record(net, alt_name, reservoir_name)
    if rec is None:
        return None
    try:
        return inputs.record(rec, f"{reservoir_name} pool elevation")
    except DPError:
        return None


################################################################################
# THE NETWORK WALK

class Walk:
    """Connections derived from network.json (downstream links, upstream lists)."""

    def __init__(self, net: Network):
        self.net = net
        E = net.elements
        self.down = {}
        for eid, e in E.items():
            if e["type"] in ("junction", "reach"):
                self.down[eid] = e["downstream"]
            elif e["type"] == "reservoir":
                self.down[e["pool"]] = e["downstream"]
        order = [x for x in net.order if x]
        for i, eid in enumerate(order):
            if eid.startswith("other:"):
                self.down[eid] = order[i + 1] if i + 1 < len(order) else None
        self.up = {}
        for eid, d in self.down.items():
            if d:
                self.up.setdefault(d, []).append(eid)
        self.order = order
        self.confluence_junctions = set(net.confluence_junctions)
        self.headwaters = set(net.headwater_junctions)

    def connected_reaches(self, junction_id):
        return [c for c in self.net.elements[junction_id]["connected"] if c and c.startswith("reach:")]

    def out_junction(self, reservoir_name):
        return self.net.elements["reservoir:" + reservoir_name]["downstreamElements"][0]


################################################################################
# STEP 1: TRANSFORMED LOCALS (Willamette Falls)

def transform_gage_data(inputs, transform_csv, time_step, log=print):
    """cTransform.transformGageData: area-ratio (and ADD) records into inputs.computed"""
    written = []
    prev = None
    prev_keys = set()
    for row in read_csv_rows(transform_csv):
        row += [""] * (7 - len(row))
        b_part, c_part, station = row[0], row[1], row[2]
        if row[4] or row[5]:
            raise DPError(f"{transform_csv}: MOVE.1 rows ({b_part}) are not supported in DP_Python yet")
        found = inputs.obs.find(station, "FLOW", time_step.upper())
        if not found:
            raise DPError(f"No FLOW record with B part {station} at {time_step} in {inputs.obs.filename} (for {b_part})")
        s = inputs.obsdata(found[0])
        ratio = float(row[3]) if row[3] else None
        new = s * ratio if ratio is not None else s.copy()
        keys = {path_key(found[0])}
        if prev is not None:
            new = new + prev
            keys |= prev_keys
        typed(new, s.attrs.get("type", "INST-VAL"))   # HEC math keeps the gage's type
        if b_part.upper() == "ADD":
            prev, prev_keys = new, keys
            continue
        prev, prev_keys = None, set()
        path = f"//{b_part}/{c_part}//{time_step}/COMPUTED/"
        inputs.computed[path_key(path)] = new
        inputs.sources[path_key(path)] = keys
        written.append(path)
        log(f"Transformed: {path} = {station} x {ratio}")
    return written


################################################################################
# STEP 2: WATER-BALANCE LOCALS

def water_balance_locals(net, walk, alt_name, inputs, negs=True, log=print):
    """
    cWaterBalance.computeWaterBalanceLocals, diversions ignored. At each junction
    with observed flow, the one local mapped to DPcalc.dss = observed - (routed
    flow + every other local there). Results go into inputs.computed.
    """
    alt = net.alternatives[alt_name]
    vid = net.vid
    E = net.elements
    trib = {}
    trib_keys = {}
    reg = None
    reg_keys = set()      # obsData.dss records reg was made from (to mark filled data in the plots)
    n_locals = 0
    for eid in walk.order:
        e = E.get(eid)
        if eid.startswith("pool:"):
            pass  # no confluence reservoirs in this network (checked in run)
        elif e and e["type"] == "junction":
            name = e["name"]
            if eid in walk.confluence_junctions:
                for rch in walk.connected_reaches(eid):
                    if rch in trib:
                        reg = reg + trib[rch] if reg is not None else trib[rch].copy()
                        reg_keys |= trib_keys[rch]
            obs = None
            rec_obs = alt.observed_record(e["flowProxy"], vid["NODE_FLOW"])
            if rec_obs is not None and not rec_obs.is_blank:
                obs = inputs.record(rec_obs, f"Observed flow at {name}")
            obs_keys = inputs.record_keys(rec_obs)
            if eid in walk.headwaters:
                reg = None
                reg_keys = set()
            compute = []
            for loc in e["locals"]:
                rec = alt.input_record(loc["knownFlowProxy"], vid["NODE_KNOWNFLOW"])
                if rec is None or rec.is_blank:
                    continue
                kind = file_kind(rec.dss_file)
                if obs is not None and kind == "computed":
                    compute.append((loc["node"], rec))
                    continue
                if kind == "zero":
                    continue
                if rec_obs is not None and obs is None:
                    continue  # observed expected but blank
                s = inputs.record(rec, f"Local {loc['node']} at {name}") * loc["factor"]
                reg = s.copy() if reg is None else reg + s
                reg_keys |= inputs.record_keys(rec)
            if obs is not None:
                if len(compute) > 1:
                    raise DPError(f"{len(compute)} locals at {name} are mapped to DPcalc.dss: "
                                  f"{', '.join(c[0] for c in compute)}. Only one per gaged junction can take the water balance.")
                if compute:
                    node, rec = compute[0]
                    local = obs.copy() if reg is None else obs - reg
                    if not negs:
                        local = pd.Series(remove_negative_locals(local.values), index=local.index)
                    inputs.computed[path_key(rec.pathname)] = typed(local, "PER-AVER")
                    inputs.sources[path_key(rec.pathname)] = obs_keys | reg_keys
                    n_locals += 1
                    log(f"Local flow at {name} ({node})")
                reg = obs.copy()
                reg_keys = set(obs_keys)
            if reg is None:
                reg = inputs.zeros()
                reg_keys = set()
        elif e and e["type"] == "reach":
            reach = build_reach(e["routing"])
            reg = pd.Series(reach.route(reg.values), index=reg.index)
        ds = walk.down.get(eid)
        if ds and ds in walk.confluence_junctions:
            trib[eid] = reg.copy()
            trib_keys[eid] = set(reg_keys)
            reg = reg * 0.0
            reg_keys = set()
    return n_locals


################################################################################
# THE OBSERVED AND UNREGULATED RUNS

class Run:
    """Flows of one simulated alternative: element outflows, pool inflow/outflow, local flows."""

    def __init__(self, name):
        self.name = name
        self.flow = {}       # element id -> outflow series (junctions, reaches, others)
        self.inflow = {}     # reservoir name -> pool inflow
        self.outflow = {}    # reservoir name -> pool outflow
        self.local = {}      # (junction id, node) -> local flow (multiplier applied)
        # obsData.dss records each flow was made from (to mark filled data in the plots)
        self.keys = {}       # element id -> set of keys
        self.inflow_keys = {}
        self.outflow_keys = {}


def simulate(net, walk, alt_name, inputs, release, log=print):
    """
    One alternative through the network. release='specified': each reservoir
    releases its '<name> (ABC) Specified Release' record; release='inflow':
    each reservoir passes inflow.
    """
    alt = net.alternatives[alt_name]
    vid = net.vid
    E = net.elements
    run = Run(alt_name)
    for eid in walk.order:
        e = E.get(eid)
        inflow = None
        keys = set()
        for u in walk.up.get(eid, []):
            if u.startswith("pool:"):
                s = run.outflow[u.split(":", 1)[1]]
                keys |= run.outflow_keys[u.split(":", 1)[1]]
            else:
                s = run.flow[u]
                keys |= run.keys[u]
            inflow = s.copy() if inflow is None else inflow + s
        if eid.startswith("pool:"):
            rname = eid.split(":", 1)[1]
            run.inflow[rname] = inflow if inflow is not None else inputs.zeros()
            run.inflow_keys[rname] = keys
            if release == "specified":
                rec = net.specified_release(alt_name, rname)
                if rec is None or rec.is_blank:
                    raise DPError(f"No Specified Release record for {rname} in {alt_name}")
                run.outflow[rname] = inputs.record(rec, f"{rname} Specified Release", compute=True)
                run.outflow_keys[rname] = inputs.record_keys(rec)
            else:
                run.outflow[rname] = run.inflow[rname].copy()
                run.outflow_keys[rname] = set(keys)
            continue
        if e and e["type"] == "junction":
            total = inflow if inflow is not None else inputs.zeros()
            for loc in e["locals"]:
                rec = alt.input_record(loc["knownFlowProxy"], vid["NODE_KNOWNFLOW"])
                s = inputs.record(rec, f"Local {loc['node']} at {e['name']}", compute=True)
                s = inputs.zeros() if s is None else s * loc["factor"]
                run.local[(eid, loc["node"])] = s
                keys |= inputs.record_keys(rec)
                total = total + s
            run.flow[eid] = total
        elif e and e["type"] == "reach":
            reach = build_reach(e["routing"])
            run.flow[eid] = pd.Series(reach.route(inflow.values), index=inflow.index)
        else:
            run.flow[eid] = inflow if inflow is not None else inputs.zeros()
        run.keys[eid] = keys
    return run


################################################################################
# STEP 3: MINI-SIMULATIONS

class JuncPeaks:
    def __init__(self, name):
        self.name = name
        self.obs = None            # (peak, time) of the gage, if any
        self.modeled_obs = None
        self.unreg = None
        self.is_gaged = False
        self.note = None
        self.peaks = {}            # reservoir -> {"WITH": (peak, time), "WITHOUT": ..., "reduction": v}
        self.series = {}           # label -> Series (for MiniSimulations output)
        self.filled_gage = None    # bool Series: hours of the gage record filled by interpolation
        self.filled_inputs = None  # bool Series: hours any record the modeled flows use was filled

    def set_peak(self, resv, series, is_with):
        self.peaks.setdefault(resv, {})["WITH" if is_with else "WITHOUT"] = _peak(series)
        self.series[("WITH ONLY " if is_with else "WITHOUT ") + resv] = series

    @property
    def contributing(self):
        return list(self.peaks.keys())


def _peak(s):
    v = s.values
    i = int(np.nanargmax(v))
    return float(v[i]), s.index[i]


def read_added_points(path):
    points = {}
    if not path or not os.path.exists(path):
        return points
    for row in read_csv_rows(path):
        if len(row) < 3 or not row[0] or row[0].upper() == "NAME":
            continue
        factor = float(row[3]) if len(row) > 3 and row[3] else 1.0
        points[row[0]] = {"name": row[0], "base": row[1], "station": row[2], "factor": factor}
    return points


def mini_simulations(net, walk, inputs, obs_alt, run_obs, run_unreg, control_points, reservoirs,
                     added_points, time_step, rereg=REREG, log=print):
    """cMiniSims.runMiniSimulations without the DSS output. Returns (juncPeaks, resvPeaks, cp order, resv order)."""
    E = net.elements
    vid = net.vid
    alt = net.alternatives[obs_alt]
    fails = []
    resvs_to_run = []
    for r in reservoirs:
        if "reservoir:" + r not in E:
            fails.append(f"reservoir: {r}")
        elif r in rereg.values():
            continue
        else:
            resvs_to_run.append(r)
    out_juncs = []
    added_by_junc = {}
    for cp in control_points:
        if cp in added_points:
            p = added_points[cp]
            if "junction:" + p["base"] not in E:
                fails.append(f"base junction of added-flow point {cp}: {p['base']}")
                continue
            found = inputs.obs.find(p["station"], "FLOW", time_step.upper())
            if not found:
                fails.append(f"added-flow point {cp}: no FLOW record with B part {p['station']} in {inputs.obs.filename}")
                continue
            g = inputs.obsdata(found[0]).fillna(0.0) * p["factor"]
            p["add"] = g
            p["keys"] = {path_key(found[0])}
            p["note"] = f"{p['base']} (ResSim) + gage {p['station']}" + (f" x {p['factor']}" if p["factor"] != 1.0 else "") + ", not routed"
            added_by_junc.setdefault("junction:" + p["base"], []).append(p)
            if "junction:" + p["base"] not in out_juncs:
                out_juncs.append("junction:" + p["base"])
            continue
        if "junction:" + cp not in E:
            fails.append(f"junction: {cp}")
        elif "junction:" + cp not in out_juncs:
            out_juncs.append("junction:" + cp)
    if fails:
        raise DPError("These names are not in the network (fix the config files):\n  " + "\n  ".join(fails))

    # Peaks at the control points from the two runs and the gages
    jp = {}
    for jid in out_juncs:
        name = E[jid]["name"]
        p = JuncPeaks(name)
        unreg = run_unreg.flow[jid]
        mobs = run_obs.flow[jid]
        p.unreg, p.modeled_obs = _peak(unreg), _peak(mobs)
        p.series["UNREGULATED"], p.series["MODELED OBSERVED"] = unreg, mobs
        model_keys = run_obs.keys[jid] | run_unreg.keys[jid]
        p.filled_inputs = inputs.filled_mask(model_keys)
        rec = alt.observed_record(E[jid]["flowProxy"], vid["NODE_FLOW"])
        if rec is not None and not rec.is_blank:
            g = inputs.record(rec, f"Observed flow at {name}")
            p.obs = _peak(g)
            p.series["OBSERVED"] = g
            p.is_gaged = True
            p.filled_gage = inputs.filled_mask(inputs.record_keys(rec))
        jp[name] = p
        for ap in added_by_junc.get(jid, []):
            q = JuncPeaks(ap["name"])
            q.note = ap["note"]
            q.filled_inputs = inputs.filled_mask(model_keys | ap["keys"])
            q.series["UNREGULATED"] = unreg + ap["add"]
            q.series["MODELED OBSERVED"] = mobs + ap["add"]
            q.unreg, q.modeled_obs = _peak(q.series["UNREGULATED"]), _peak(q.series["MODELED OBSERVED"])
            jp[ap["name"]] = q

    # Reservoir peak inflow and outflow at that time
    rp = {}
    for r in resvs_to_run:
        inflow = run_obs.inflow[r]
        out_j = walk.out_junction(rereg.get(r, r))
        rec = alt.observed_record(E[out_j]["flowProxy"], vid["NODE_FLOW"])
        out = inputs.record(rec, f"Observed flow at {E[out_j]['name']}") if rec is not None and not rec.is_blank else None
        if out is None:
            out = run_obs.flow[out_j]
        peak, t = _peak(inflow)
        rp[r] = {"inflow": peak, "time": t, "outflow": float(out.loc[t]), "rereg": rereg.get(r)}

    # The WITHOUT and WITH ONLY runs
    out_set = set(out_juncs)
    for is_with in (False, True):
        run = run_unreg if is_with else run_obs
        for r in resvs_to_run:
            label = ("WITH ONLY " if is_with else "WITHOUT ") + r
            rereg_name = rereg.get(r, "")
            ds = ["reservoir:" + r] + list(E["reservoir:" + r]["downstreamElements"])
            ds_set = set(ds)
            flow = run.inflow[r].values.copy()
            for eid in ds:
                e = E[eid]
                if e["type"] == "junction":
                    if eid in walk.confluence_junctions:
                        for rch in walk.connected_reaches(eid):
                            if rch in ds_set:
                                continue
                            flow = flow + run.flow[rch].values
                    for loc in e["locals"]:
                        flow = flow + run.local[(eid, loc["node"])].values
                elif e["type"] == "reach":
                    flow = force_min(flow, 0, conserve_volume=False)
                    flow = build_reach(e["routing"]).route(flow)
                elif e["type"] == "reservoir":
                    rn = e["name"]
                    this = (rn == r or rn == rereg_name)
                    if (is_with and not this) or (not is_with and this):
                        pass
                    else:
                        flow = force_min(flow + run_obs.outflow[rn].values - run_obs.inflow[rn].values, 0, conserve_volume=True)
                if eid in out_set:
                    s = pd.Series(flow.copy(), index=inputs.index)
                    jp[e["name"]].set_peak(r, s, is_with)
                    for ap in added_by_junc.get(eid, []):
                        jp[ap["name"]].set_peak(r, s + ap["add"], is_with)
            log(f"{label}: done")

    # Reductions
    for name in control_points:
        p = jp[name]
        for r in p.contributing:
            unreg = r100(p.unreg[0])
            obs = r100(p.modeled_obs[0])
            with_diff = unreg - r100(p.peaks[r]["WITH"][0])
            without_diff = r100(p.peaks[r]["WITHOUT"][0]) - obs
            p.peaks[r]["reduction"] = (with_diff + without_diff) / 2.0
    return jp, rp, list(control_points), resvs_to_run
