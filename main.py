import win32com.client

# Connect to Aspen Plus
aspen = win32com.client.Dispatch("Apwn.Document")
aspen.InitFromFile(r"C:\Programming\delft\Aspen\cstr-ch4.apw")
aspen.Visible = True


#Tree Is the main node in variable explorer
blocks_node = aspen.Application.Tree.FindNode(r"\Data")

#This is all user defined blocks
print(blocks_node.Blocks.Elements.Count)
# Loop through all blocks
EnergyCost = 0
for i in range(blocks_node.Blocks.Elements.Count):
    block = blocks_node.Blocks.Elements.Item(i)
    if hasattr(block.Output, 'WNET'):
        print(f"Block {block.name} consumed {block.Output.WNET.value}kW")
        EnergyCost += block.Output.WNET.value
print(f"Total cost is {EnergyCost}Kw.")

