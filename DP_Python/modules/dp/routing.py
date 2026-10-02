"""
Reach routing, ported line for line from NWDJyLib/cRouting.py (the routing the
ResSim Damages Prevented mini-simulations use): Null, Modified Puls, Muskingum
and SSARR. Each reach object routes a whole hourly series with route(values,
dt_hours), starting from steady state at the first value, as cRouting does.

build_reach(routing) takes the routing dict from network.json.
"""
import math
import numpy as np


class PairedTable:
    """HEC PairedValuesExt.interpolate: linear, extended linearly past the ends."""

    def __init__(self, x, y):
        order = np.argsort(np.asarray(x, dtype=float), kind="stable")
        self.x = np.asarray(x, dtype=float)[order]
        self.y = np.asarray(y, dtype=float)[order]

    def interpolate(self, v):
        x, y = self.x, self.y
        if len(x) == 1:
            return float(y[0])
        if v <= x[0]:
            i = 0
        elif v >= x[-1]:
            i = len(x) - 2
        else:
            return float(np.interp(v, x, y))
        if x[i + 1] == x[i]:
            return float(y[i])
        return float(y[i] + (v - x[i]) * (y[i + 1] - y[i]) / (x[i + 1] - x[i]))


class NullReach:
    def route(self, values, dt_hours=1.0):
        return np.array(values, dtype=float)


class ModPulsReach:
    """Modified Puls, no losses. Storage in acre-feet, outflow in cfs."""

    def __init__(self, storage, outflow, subreaches):
        self.n = int(subreaches)
        self.storage = list(storage)
        self.outflow = list(outflow)
        self._dt = None

    def _init_tables(self, dt_seconds):
        si = [0.5 * q + s * 43560.0 / dt_seconds / self.n for s, q in zip(self.storage, self.outflow)]
        self.si_from_q = PairedTable(self.outflow, si)
        self.q_from_si = PairedTable(si, self.outflow)
        self._dt = dt_seconds

    def route(self, values, dt_hours=1.0):
        values = np.asarray(values, dtype=float)
        if self._dt != dt_hours * 3600.0:
            self._init_tables(dt_hours * 3600.0)
        q_init = values[0]
        self.final = [q_init] * self.n
        self.working = [q_init] * self.n
        out = np.empty(len(values))
        for j in range(len(values)):
            q1 = values[j]
            q0 = values[j] if j == 0 else values[j - 1]
            out[j] = self._step(q0, q1)
        return out

    def _step(self, qin0, qin1):
        d1 = qin1
        for i in range(self.n):
            qin_avg = 0.5 * (qin0 + qin1)
            d0 = self.working[i]
            si0 = self.si_from_q.interpolate(d0)
            si1 = max(0.0, si0 - d0 + qin_avg)
            d1 = max(0.0, self.q_from_si.interpolate(si1))
            self.working[i] = d1
            qin0 = self.final[i]
            qin1 = d1
            self.final[i] = d1
        return d1


class MuskingumReach:
    def __init__(self, k, x, subreaches):
        assert 0 <= x <= 0.5, "Muskingum X must be between 0 and 0.5"
        self.k = float(k)
        self.x = float(x)
        self.n = int(subreaches)

    def route(self, values, dt_hours=1.0):
        values = np.asarray(values, dtype=float)
        q_init = values[0]
        self.initial = [q_init] * self.n
        self.final = [q_init] * self.n
        out = np.empty(len(values))
        for j in range(len(values)):
            q1 = values[j]
            q0 = values[j] if j == 0 else values[j - 1]
            out[j] = self._step(dt_hours, q0, q1)
        return out

    def _step(self, dt, q0, q1):
        sub_k = self.k / float(self.n)
        x = self.x
        den = sub_k - sub_k * x + 0.5 * dt
        c0 = (-sub_k * x + 0.5 * dt) / den
        c1 = (sub_k * x + 0.5 * dt) / den
        c2 = (sub_k - sub_k * x - 0.5 * dt) / den
        qin0, qin1 = q0, q1
        qout1 = q1
        for i in range(self.n):
            qout0 = self.initial[i]
            qout1 = c0 * qin1 + c1 * qin0 + c2 * qout0
            qin1 = qout1
            self.final[i] = qout1
            qin0 = qout0
        self.initial = list(self.final)
        return qout1


class SsarrReach:
    """SSARR, by KTS/n coefficients or an outflow vs time-of-storage table."""

    def __init__(self, subreaches, kts=None, n=None, table=None):
        self.nps = int(subreaches)
        self.kts = kts
        self.ncoeff = n
        self.table = PairedTable(table["outflow"], table["timeOfStorage"]) if table else None

    def route(self, values, dt_hours=1.0, allow_negatives=False):
        values = np.asarray(values, dtype=float)
        self.xhr = dt_hours
        out = np.empty(len(values))
        for x in range(len(values)):
            if x == 0:
                self.qph = [values[0]] * self.nps
            elif allow_negatives:
                self._step(values[x - 1], values[x])
            else:
                self._step(max(1.0, values[x - 1]), max(1.0, values[x]))
            out[x] = self.qph[-1]
        return out

    def _step(self, q1, q2):
        ph = self.qph
        phave = sum(ph) / self.nps
        if phave <= 0.001:
            phave = 1.0
        if self.table is not None:
            ts = self.table.interpolate(phave)
        else:
            ts = self.kts / math.pow(phave, self.ncoeff)
        if ts < 0.05:
            q_ph = [q2] * self.nps
        else:
            q_ph = list(ph)
            if ts < self.xhr / 2:
                n = int(self.xhr / 2 / ts) + 1
                xh2r = self.xhr / 2.0 / n
            else:
                n = 1
                xh2r = self.xhr / 2.0
            tsr = xh2r / (ts + xh2r)
            xint = (q2 - q1) / n
            pqi = q1 - xint / 2
            for _ in range(n):
                pqi = pqi + xint
                qi = pqi
                for x in range(self.nps):
                    dq = (qi - q_ph[x]) * tsr
                    qi = q_ph[x] + dq
                    q_ph[x] = qi + dq
        self.qph = q_ph
        return q_ph[-1]


def build_reach(routing):
    """Reach object for a network.json routing dict, or None if unsupported"""
    method = routing.get("method")
    if method == "Null":
        return NullReach()
    if method == "Modified Puls":
        return ModPulsReach(routing["storage"], routing["outflow"], routing["subreaches"])
    if method == "Muskingum":
        return MuskingumReach(routing["k"][0], routing["x"][0], routing["subreaches"])
    if method == "SSARR":
        if routing.get("kts"):
            return SsarrReach(routing["subreaches"], kts=routing["kts"], n=routing["n"])
        return SsarrReach(routing["subreaches"], table=routing["table"])
    return None
