from dataclasses import dataclass
import win32com.client as win32
import sys
import scipy as sc
import time

@dataclass
class SearchBlock:
    data: list[tuple[str, str]]
    children: list[str]

search = {
    "Hierarchy": SearchBlock([], ["Blocks"]),
    "Compr": SearchBlock([("WNET", "Net Power")], []),
    "MCompr": SearchBlock([("WNET", "Net Power")], []),
    "Cyclone": SearchBlock([], []),
    "Sep": SearchBlock([], []),
    "HeatX": SearchBlock([], []),
    "Dupl": SearchBlock([], []),
    "Flash2": SearchBlock([], []),
    "Heater": SearchBlock([], []),
    "Mixer": SearchBlock([], []),
    "Sep2": SearchBlock([], []),
    "RPlug": SearchBlock([], []),
    "Valve": SearchBlock([], []),
    "RStoic": SearchBlock([], []),
}

if len(sys.argv) < 2:
    print("Should be called with the name of the aspen file")
    exit(1)
    
def get_all_children(node):
    return (node.Elements.Item(i) for i in range(node.Elements.Count))
    
def getTEAResult(blocksArray, record_type, searchDict, dataVar):
    """ Placeholder function for TEA review functionality """
    aspenOutput = readAspen(blocksArray, record_type, searchDict, dataVar)
    blocksOutput = list(aspenOutput.keys())
    totalpower = 0
    #print(aspenOutput)
    
    for blockName in blocksOutput:
        totalpower += float(aspenOutput[blockName]['Net Power'][0])

    return totalpower
    
def aspenBlackBox(valuesArray, isBlock, paramArray, blockNameArray, getTeaResultFunc, blocksArray, dataVar, aspen):
    global RECORD_TYPE, search
    if (len(paramArray) != len(blockNameArray) and len(paramArray) != len(valuesArray)):
        print("ERROR: enter correct number of parameters and blocks")
        sys.exit()
        
    if isBlock == True:
        typename = "Blocks"
    else:
        typename = "Streams"
    
    for paramCount in range(len(paramArray)):
        paramPath = str(blockNameArray[paramCount]) + "\\Input\\" + str(paramArray[paramCount])
        #print(rf"\Data\{typename}\{paramPath}")
        paramNode = aspen.Application.Tree.FindNode(rf"\Data\{typename}\{paramPath}")
        
        if paramNode is None:
            print("BAD PATH:", rf"\Data\{typename}\{paramPath}")
            raise Exception("Node not found")
        #print(valuesArray[paramCount])
        paramNode.Value = float(valuesArray[paramCount])
        
    aspen.Engine.Run2()
    cost = getTeaResultFunc(blocksArray, RECORD_TYPE, search, dataVar)
    return cost
    
def optimizeInputs(initialValues, bounds, blackBoxFunc, isBlock, paramArray, blockNameArray, getTeaResultsFunc, blocksArray, dataVar, aspenItem):
    argumentsArr = (isBlock, paramArray, blockNameArray, getTeaResultsFunc, blocksArray, dataVar, aspenItem)
    upperBound = bounds[1]
    lowerBound = bounds[0]
    limits = sc.optimize.Bounds(lowerBound, upperBound)
    result = sc.optimize.minimize(blackBoxFunc, initialValues, bounds=limits, method='trust-constr', args=argumentsArr)
    return result
    
        
def readAspen(blocksVar, RECORD_TYPE, searchDict, dataVar):
    # Loop through all blocks
    for block in blocksVar:
        recordType = block.AttributeValue(RECORD_TYPE)
        #print(block.Name, block.Value, block.ValueType, recordType)

        curr_data = {}

        if s := searchDict.get(recordType):
            for path, name in s.data:
                b = block.FindNode(rf"Output\{path}")
                curr_data[name] = (b.Value, b.UnitString)
                dataVar[block.Name] = curr_data

            for path in s.children:
                b = block.FindNode(rf"Data\{path}")
                blocks.extend(get_all_children(b))
    
    return dataVar
    
#CONNECT TO ASPEN FILE#
#print(f"Open file {sys.argv[1]}")
aspen = win32.gencache.EnsureDispatch("Apwn.Document")
aspen.InitFromArchive2(sys.argv[1])
aspen.Visible = False
aspen.SuppressDialogs = True  # Suppress windows dialogs
aspen.Engine.Run2()

data = {}

RECORD_TYPE = 6

blocks = list(get_all_children(aspen.Application.Tree.FindNode(r"\Data\Blocks")))

initialData = readAspen(blocks, RECORD_TYPE, search, data)
blocksList = list(initialData.keys())
trueFeedStreams = []
inputStreams = []
outputStreams = []

for block in blocksList:
    connections = aspen.Application.Tree.FindNode(rf"\Data\Blocks\{block}\Connections")
    
    if (connections is not None):
        elements = connections.Elements.Count
        for i in range(0, elements):
            stream = connections.Elements.Item(i)

            inputOrOutputNode = aspen.Application.Tree.FindNode(rf"\Data\Blocks\{block}\Connections\{stream.Name}")
            inOrOut = str(inputOrOutputNode.Value)
            if inOrOut == "F(IN)":
                inputStreams.append(stream.Name)
            else:
                outputStreams.append(stream.Name)
            
trueFeedStreams = set(inputStreams) - set(outputStreams)
trueOutputStreams = set(outputStreams) - set(inputStreams)

print(f"Possible Blocks: {blocksList}")
print(f"Possible True Feed Streams: {trueFeedStreams}")

"""
node = aspen.Application.Tree.FindNode(r"\Data\Streams\S1\Input\TOTFLOW")
print("FOUND:", node is not None)
if node:
    print(node.Value)
"""

result = optimizeInputs([7],
            [5, 10],
            aspenBlackBox,
            True,
            ["PRES"],
            ["COMP-1"],
            getTEAResult,
            blocks,
            data, 
            aspen)
            
print(result)


#minVal = aspenBlackBox([10.00], True, ["PRES"], ["COMP-1"], getTEAResult, blocks, data, aspen)
#print(minVal)

            
#######################






