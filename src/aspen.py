from dataclasses import dataclass, field
from typing import Callable, Any

import win32com.client as win32

Aspen = win32.CDispatch


def init_aspen(filename: str):
    aspen = win32.gencache.EnsureDispatch("Apwn.Document")
    aspen.InitFromArchive2(filename)
    aspen.Visible = False
    aspen.SuppressDialogs = True

    return aspen


def run_aspen(aspen: Aspen):
    aspen.Engine.Run2()


def get_all_children(node, parent=""):
    for i in range(node.Elements.Count):
        child = node.Elements.Item(i)

        yield child, rf"{parent}\{child.Name}"


@dataclass
class Res:
    name: str
    data: float
    unit: str


FetchingStrategy = Callable[[Any, str], Res]


@dataclass
class SearchBlock:
    fetchers: list[FetchingStrategy]
    children: list[str] = field(default_factory=list)


def fetch_from_data(path: str, output_name: str) -> FetchingStrategy:
    def fetch(block, block_path):
        b = block.FindNode(path)
        assert b is not None, f"couldn't find {path} for {block.Name}"
        return Res(output_name, b.Value, b.UnitString)

    return fetch

def fetch_from_connection(port: str, path: str, output_name: str) -> FetchingStrategy:
    def fetch(block, block_path):
        p, *other = [b for b, _ in get_all_children(block.FindNode(rf"Ports\{port}"))]
        assert len(other) == 0, f"Multiple blocks connected to {port}. Expected 1 but got {1 + len(other)}"

        # need to read the stream relative to the block_path since we need to use the one from the closest hierarchy
        b = block.Application.Tree.FindNode(rf"{block_path}\..\..\Streams\{p.Value}\{path}")

        return Res(output_name, b.Value, b.UnitString)

    return fetch


search = {
    "Hierarchy": SearchBlock([], [r"Data\Blocks"]),
    "Mixer": SearchBlock(
        [fetch_from_connection("P(OUT)", r"Output\VOLFLMX2", "Outlet Flow")]
    ),
    "Flash2": SearchBlock([fetch_from_data(r"Output\B_PRES", "Outlet Pressure")]),
    "Flash3": SearchBlock([fetch_from_data(r"Output\B_PRES", "Outlet Pressure")]),
    "Decanter": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "Sep": SearchBlock([]),  # TODO: figure out how to get pressure
    "Sep2": SearchBlock([]), # TODO: figure out how to get pressure
    # for the heater, not sure if the heating duty is `QNET` or `QCALC`
    "Heater": SearchBlock([fetch_from_data(r"Output\QCALC", "Heating Duty")]),
    "HeatX": SearchBlock([fetch_from_data(r"Output\HX_AREAP", "Heat Transfer Area")]),
    # "MHeatX": SearchBlock([]),
    # All types of Columns
    "DSTWU": SearchBlock([]),
    "Distl": SearchBlock([]),
    "SCFrac": SearchBlock([]),
    "RadFrac": SearchBlock([]),
    "MultiFrac": SearchBlock([]),
    "PetroFrac": SearchBlock([]),
    "RateFrac": SearchBlock([]),
    #All types of Reactor
    "RYield": SearchBlock([]),
    "REquil": SearchBlock([]),
    "RGibbs": SearchBlock([]),
    "RCSTR": SearchBlock([
        fetch_from_data(r"Output\B_PRES", "Pressure"),
        fetch_from_data(r"Output\TOT_VOL", "Volume")
    ]),
    "RPlug": SearchBlock([]),
    "RBatch": SearchBlock([]),
    "RStoic": SearchBlock(
        [fetch_from_data(r"Output\B_PRES", "Pressure")]
    ),  # TODO: Find the length and width/ volume
    # TODO: Pump VFLOW is in cum/sec in Aspen, needs to be in L/sec
    "Pump": SearchBlock([fetch_from_data(r"Output\VFLOW", "Volumetric Flow")]),
    "Compr": SearchBlock([fetch_from_data(r"Output\WNET", "Net Power")]),
    "MCompr": SearchBlock([fetch_from_data(r"Output\WNET", "Net Power")]),
    "Crytallizer": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "Crusher": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "Dryer": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "Fluidbed": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "Cyclone": SearchBlock([
        fetch_from_connection("G(OUT)", r"Output\VOLFLMX2", "Outlet Volumetric Gas Rate"),
    ]),
    "Cfuge": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "Filter": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    "CfFilter": SearchBlock([]),  # TODO: Not in cstr-ch4.apw
    # Valve not in TEA?
}

HAP_RECORDTYPE = 6
# Port in or out
HAP_INOUT = 14

def read_data(aspen: Aspen):
    data = {}

    blocks = list(
        get_all_children(
            aspen.Application.Tree.FindNode(r"\Data\Blocks"), r"\Data\Blocks"
        )
    )

    for block, path in blocks:
        record_type = block.AttributeValue(HAP_RECORDTYPE)

        print(block.Name, record_type, path)

        curr_data = {
            "path": path,
            "record_type": record_type,
            "data": {},
        }

        if s := search.get(record_type):
            for fetch in s.fetchers:
                res = fetch(block, path)
                curr_data["data"][res.name] = (res.data, res.unit)
                data[path] = curr_data

            for child_path in s.children:
                b = block.FindNode(child_path)
                blocks.extend(get_all_children(b, rf"{path}\{child_path}"))


    return data

def read_all_data(aspen: Aspen):
    data = {}

    blocks = list(
        get_all_children(
            aspen.Application.Tree.FindNode(r"\Data\Blocks"), r"\Data\Blocks"
        )
    )

    # Loop through all blocks
    for block, path in blocks:
        record_type = block.AttributeValue(HAP_RECORDTYPE)
        print(block.Name, block.Value, block.ValueType, record_type)

        curr_data = {
            "path": path,
            "record_type": record_type,
            "data": {},
            "input": {},
            "connections": {},
        }

        if s := search.get(record_type):
            for b, _ in get_all_children(block.FindNode("Input")):
                curr_data["input"][b.Name] = (b.Value, b.UnitString)

            for b, _ in get_all_children(block.FindNode("Output")):
                curr_data["data"][b.Name] = (b.Value, b.UnitString)

            for b, _ in get_all_children(block.FindNode("Connections")):
                curr_data["connections"][b.Name] = (
                    b.Value,
                    b.AttributeValue(HAP_INOUT),
                )

            for child_path in s.children:
                b = block.FindNode(child_path)
                blocks.extend(get_all_children(b, path))

        data[block.Name] = curr_data

    return data
