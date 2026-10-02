"""
The ResSim network exported by export/ExportNetwork.py (network.json), loaded
into plain Python objects.

Element ids are '<type>:<name>' with type junction, reach, reservoir, pool
(a reservoir's pool, '<pool:reservoir name>') or diversion, exactly as in the
JSON. Time series mappings are looked up the way ResSim does it: by the
location's time series proxy name plus the variable id.
"""
import json
import os
import re
from dataclasses import dataclass, field

SUPPORTED_ROUTING = ("SSARR", "Muskingum", "Modified Puls", "Null")


@dataclass
class TSRecord:
    name: str
    variable_id: int
    param: str
    dss_file: str
    pathname: str

    @property
    def is_blank(self):
        return self.dss_file.strip() == "" or self.pathname.strip("/ ") == "" or \
            len(self.pathname) == self.pathname.count("/")


@dataclass
class Alternative:
    name: str
    time_step: str
    observed: dict = field(default_factory=dict)   # (name, variable id) -> TSRecord
    input: dict = field(default_factory=dict)

    def observed_record(self, proxy_name, variable_id):
        return self.observed.get((proxy_name, variable_id))

    def input_record(self, proxy_name, variable_id):
        return self.input.get((proxy_name, variable_id))


class Network:
    def __init__(self, data, source=None):
        self.source = source
        self.export_version = data["exportVersion"]
        self.exported = data.get("exported")
        self.simulation_window = data["simulationWindow"]
        self.vid = data["variableIds"]
        net = data["network"]
        self.elements = net["elements"]
        self.order = net["orderFromUpstream"]
        self.headwater_junctions = net["headwaterJunctions"]
        self.confluence_junctions = net["confluenceJunctions"]
        self.confluence_reservoirs = net["confluenceReservoirs"]
        self.alternatives = {}
        for alt_name, alt in data["alternatives"].items():
            a = Alternative(alt_name, alt["timeStep"])
            for rec in alt["observed"]:
                r = _record(rec)
                a.observed[(r.name, r.variable_id)] = r
            for rec in alt["input"]:
                r = _record(rec)
                a.input[(r.name, r.variable_id)] = r
            self.alternatives[alt_name] = a

    @classmethod
    def load(cls, json_file):
        with open(json_file) as f:
            return cls(json.load(f), source=os.path.abspath(json_file))

    # ------------------------------------------------------------------ lookups
    def of_type(self, element_type):
        return {k: v for k, v in self.elements.items() if v["type"] == element_type}

    @property
    def junctions(self):
        return self.of_type("junction")

    @property
    def reaches(self):
        return self.of_type("reach")

    @property
    def reservoirs(self):
        return self.of_type("reservoir")

    def element(self, elem_id):
        return self.elements[elem_id]

    def reservoir_of_pool(self, pool_id):
        return "reservoir:" + pool_id.split(":", 1)[1]

    def unsupported_reaches(self):
        return sorted((r["name"], r["routing"]["method"]) for r in self.reaches.values()
                      if not r["routing"].get("supported") or r["routing"]["method"] not in SUPPORTED_ROUTING
                      or r["routing"].get("hasChannelLosses"))

    def specified_release(self, alternative, reservoir_name):
        """
        The Specified Release record for a reservoir in an alternative's
        Time-Series tab: '<reservoir> (ABC) Specified Release'. None if absent.
        """
        alt = self.alternatives[alternative]
        pattern = re.compile(r"^%s\s*\([^)]*\)\s*Specified Release$" % re.escape(reservoir_name), re.I)
        for (name, vid), rec in alt.input.items():
            if vid == self.vid["OPRULETS_TSINPUT"] and pattern.match(name):
                return rec
        return None


def _record(rec):
    return TSRecord(rec["name"], int(rec["variableId"]), rec.get("param", ""), rec["dssFile"], rec["pathname"])
