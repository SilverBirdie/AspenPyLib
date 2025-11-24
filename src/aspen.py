from dataclasses import dataclass, field
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


def get_all_children(node, parent):
    for i in range(node.Elements.Count):
        child = node.Elements.Item(i)

        yield child, rf'{parent}\{child.Name}'


@dataclass
class SearchBlock:
    data: list[tuple[str, str]]
    children: list[str] = field(default_factory=list)

search = {
    "Hierarchy": SearchBlock([], [r"Data\Blocks"]),
    "Mixer": SearchBlock([]),  # TODO: Grab one of the streams from the connection and read the flow rate from there
    "Flash2": SearchBlock([(r"Data\B_PRES", "Outlet Pressure")]),
    "Flash3": SearchBlock([(r"Data\B_PRES", "Outlet Pressure")]),
    "Decanter": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "Sep": SearchBlock([]), # TODO: Read the output pressure from the connections
    "Sep2": SearchBlock([]),
    # for the heater, not sure if the heating duty is `QNET` or `QCALC`
    "Heater": SearchBlock([(r"Data\QCALC", "Heating Duty")]),
    "HeatX": SearchBlock([(r'Data\HX_AREAP', "Heat Transfer Area")]),
    # "MHeatX": SearchBlock([]),
    # All types of Columns
    # TODO: Figure out the ids of columns
    # All types of Reactors
    "RStoic": SearchBlock([(r'Data\B_PRES', "Pressure")]), # TODO: Find the length and width/ volume
    "RCSTR": SearchBlock([(r'Data\B_PRES', "Pressure"), (r'Data\TOT_VOL', "Volume")]),

    "Pump": SearchBlock([(r'Data\VFLOW', "Volumetric Flow")]), # TODO: This is in cum/sec in Aspen, needs to be in L/sec
    "Compr": SearchBlock([(r"Data\WNET", "Net Power")]),
    "MCompr": SearchBlock([(r"Data\WNET", "Net Power")]),
    "Crytallizer": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "Crusher": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "Dryer": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "Fluidbed": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "Cyclone": SearchBlock([]), # TODO: Grab one of the streams from the connection and read the flow rate from there
    "Cfuge": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "Filter": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    "CfFilter": SearchBlock([]), # TODO: Not in cstr-ch4.apw
    # Valve not in TEA?
}
HAP_RECORDTYPE = 6
# Port in or out
HAP_INOUT = 14


def read_data(aspen: Aspen):
    data = {}

    blocks = list(get_all_children(aspen.Application.Tree.FindNode(r"\Data\Blocks"), r"\Data\Blocks"))

    # Loop through all blocks
    for block, path in blocks:
        record_type = block.AttributeValue(HAP_RECORDTYPE)
        print(block.Name, block.Value, block.ValueType, record_type)

        curr_data = { "path": path, "record_type": record_type, "data": {}, "input": {}, "connections": {} }

        if s := search.get(record_type):
            for b, _ in get_all_children(block.FindNode("Input"), rf"{path}\Input"):
                curr_data["input"][b.Name] = (b.Value, b.UnitString)

            for b, _ in get_all_children(block.FindNode("Output"), rf"{path}\Output"):
                curr_data["data"][b.Name] = (b.Value, b.UnitString)

            for b, _ in get_all_children(block.FindNode("Connections"), rf"{path}\Connections"):
                curr_data["connections"][b.Name] = (b.Value, b.AttributeValue(HAP_INOUT))

            for child_path in s.children:
                b = block.FindNode(child_path)
                blocks.extend(get_all_children(b, path))

        data[block.Name] = curr_data

    return data
