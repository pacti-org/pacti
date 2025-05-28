
from pacti.contracts import PropositionalIoContract
import networkx as nx
import os
from ipdb import set_trace as st

def postprocess(G):
    outputs = [i for i in G.nodes() if G.get_node(i).attr["output"] == "True"]
    inputs = [i for i in G.nodes() if G.get_node(i).attr["input"] == "True"]
    # find intersection
    intersection = set(inputs).intersection(set(outputs))
    internal_nodes = [i for i in G.nodes() if G.get_node(i).attr["input"] == "False" and G.get_node(i).attr["output"] == "False"]

    G_mod = nx.DiGraph()
    mapping = {}
    new_inputnodes = {}
    new_outputnodes = {}
    new_internal_nodes = {}
    for i,node in enumerate(G.nodes()):
        if node in intersection:
            # if node is both input and output, create two nodes
            G_mod.add_node('s'+str(i)+'i', term=node, type = G.get_node(node).attr["type"], input="True", output="False", contract = G.get_node(node).attr["component"])
            new_inputnodes.update({node: 's'+str(i)+'i'})
            G_mod.add_node('s'+str(i)+'o', term=node, type = G.get_node(node).attr["type"], input="False", output="True", contract = "composition")
            new_outputnodes.update({node:'s'+str(i)+'o'})

            mapping.update({node: 's'+str(i)})
            G_mod.add_edge('s'+str(i)+'i', 's'+str(i)+'o')  # connect the same terms
        elif node in inputs:
            G_mod.add_node('s'+str(i)+'i', term=node, type = G.get_node(node).attr["type"], input="True", output="False", contract = G.get_node(node).attr["component"])
            new_inputnodes.update({node: 's'+str(i)+'i'})
            mapping.update({node: 's'+str(i)+ 'i'})
        elif node in outputs:
            G_mod.add_node('s'+str(i)+'o', term=node, type = G.get_node(node).attr["type"], input="False", output="True", contract = "composition")
            mapping.update({node: 's'+str(i)+ 'o'})
            new_outputnodes.update({node: 's'+str(i)+'o'})
        elif node in internal_nodes:
            G_mod.add_node('s'+str(i), term=node, type = G.get_node(node).attr["type"], input="False", output="False", contract = "internal")
            mapping.update({node: 's'+str(i)})
            new_internal_nodes.update({node: 's'+str(i)})
        
    for u, v in G.edges():
        if u in inputs and v in outputs:
            # connect input to output
            out_node = new_inputnodes[u]
            in_node = new_outputnodes[v]
            G_mod.add_edge(out_node, in_node)#, type=G.get_edge_data(u, v).get("type", "default"))
        elif u in inputs and v in internal_nodes:
            # connect input to internal
            out_node = new_inputnodes[u]
            in_node = new_internal_nodes[v]
            G_mod.add_edge(out_node, in_node)#,, type=G.get_edge_data(u, v).get("type", "default"))
        elif u in internal_nodes and v in outputs:
            # connect internal to output
            out_node = new_internal_nodes[u]
            in_node = new_outputnodes[v]
            G_mod.add_edge(out_node, in_node)#,, type=G.get_edge_data(u, v).get("type", "default"))
        elif u in internal_nodes and v in internal_nodes:
            # connect internal to internal
            out_node = new_internal_nodes[u]
            in_node = new_internal_nodes[v]
            G_mod.add_edge(out_node, in_node)#,, type=G.get_edge_data(u, v).get("type", "default"))
    G2 = nx.nx_agraph.to_agraph(G_mod)
    print(mapping)
    return G2, mapping


def print_graph(G):
    G2 = nx.nx_agraph.to_agraph(G)
    G_agr, mapping = postprocess(G2)
    # Set left-to-right layout
    G_agr.graph_attr["rankdir"] = "LR"
    G_agr.node_attr['style'] = 'filled'
    G_agr.node_attr['gradientangle'] = 90

    for i in G_agr.nodes():
        n = G_agr.get_node(i)
        # st()
        n.attr['shape'] = 'box'
        n.attr['fillcolor'] = '#ffffff'  # default color white
        n.attr['alpha'] = 0.6
        # n.attr['label'] = ''
        if n.attr['type'] == 'assumption':
            n.attr['fillcolor'] = '#ffb000'
        elif n.attr['type'] == 'guarantee':
            n.attr['fillcolor'] = '#648fff'
        # if n.attr['output'] == 'True':
        #     n.attr['shape']='circle'

    #Align inputs and outputs using subgraphs
    inputs = [i for i in G_agr.nodes() if G_agr.get_node(i).attr["input"] == "True"]
    outputs = [i for i in G_agr.nodes() if G_agr.get_node(i).attr["output"] == "True"]

    if inputs:
        sg_in = G_agr.add_subgraph(inputs, name="cluster_inputs")
        sg_in.graph_attr["rank"] = "same"

    if outputs:
        sg_out = G_agr.add_subgraph(outputs, name="cluster_outputs")
        sg_out.graph_attr["rank"] = "same"

    if not os.path.exists("imgs"):
        os.makedirs("imgs")
    G_agr.draw("imgs/diagnosticsG.pdf", prog='dot')



c1 = PropositionalIoContract.from_strings(
    input_vars=['a', 'x', 'y'], 
    output_vars=['b'], 
    assumptions=['G(a)', 'G(x & ~y)'], 
    guarantees=['G(F(b))', "G(a => ~b)"])

c2 = PropositionalIoContract.from_strings(
    input_vars=['b'], 
    output_vars=['c'], 
    assumptions=['G(F(b))'], 
    guarantees=['G(c & ~ b)', 'G(c)'])


c3, G = c1.compose_diagnostics(c2)
print_graph(G)
print(c3)
