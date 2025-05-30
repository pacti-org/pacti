from pacti.contracts import PropositionalIoContract
from pacti.iocontract import Var
from ipdb import set_trace as st
import networkx as nx
import os


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


def print_graph(G, filename):
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
    G_agr.draw("imgs/"+filename+".pdf", prog='dot')


def guarantee_generator(clist):
    """
    Generate a guarantee generator from a list of guarantees.
    """
    guarantees = []
    
    # guarantee generator for one changing car
    for c in clist:
        status = f'(~{c} & {c}_prev)'
        for cx in clist:
            if cx != c:
                status += f' & ({cx} <=> {cx}_prev)'
        for q in [2,3,4]:
            guarantees.append(f'G({status} & q_{q}_prev => q_{q-1} )')

    # guarantee generator for two changing cars
    for c in clist:
        status = f'({c} <=> {c}_prev)'
        for cx in clist:
            if cx != c:
                status += f' & (~{cx} & {cx}_prev)'
        for q in [3,4]:
            guarantees.append(f'G({status} & q_{q}_prev => q_{q-2} )')

    # guarantee generator for three changing cars
    status = ''
    for c in clist:
        status += f'(~{c} & {c}_prev) &'
    status = status[:-2]  # remove last '&'
    guarantees.append(f'G({status} & q_4_prev => q_1 )')

    guarantees.append('G((q_1 & ~q_2 & ~q_3 & ~q_4) | (~q_1 & q_2 & ~q_3 & ~q_4) | (~q_1 & ~q_2 & q_3 & ~q_4) | (~q_1 & ~q_2 & ~q_3 & q_4))')

    # print(guarantees)
    # st()
    return guarantees

world = PropositionalIoContract.from_strings(
    input_vars=[''],
    output_vars=['car_l_T', 'q_1_T'],
    assumptions=[],
    guarantees=['G(1)'])

perception = PropositionalIoContract.from_strings(
    input_vars=['car_l_T', 'car_r_T', 'car_s_T', 'poor_visibility'],
    output_vars=['car_l_P', 'car_r_P', 'car_s_P'],
    assumptions=['G(~ poor_visibility)'],
    guarantees=['G(car_l_T <=> car_l_P)'])

planner = PropositionalIoContract.from_strings(
    input_vars=['car_l_P', 'car_r_P', 'car_s_P', 'car_l_P_prev', 'car_r_P_prev', 'car_s_P_prev', 'q_1_prev', 'q_2_prev', 'q_3_prev', 'q_4_prev'],
    output_vars=['q_1', 'q_2', 'q_3', 'q_4'],
    assumptions=['G((q_1_prev & ~q_2_prev & ~q_3_prev & ~q_4_prev) | (~q_1_prev & q_2_prev & ~q_3_prev & ~q_4_prev) | (~q_1_prev & ~q_2_prev & q_3_prev & ~q_4_prev) | (~q_1_prev & ~q_2_prev & ~q_3_prev & q_4_prev))'],
    guarantees=guarantee_generator(['car_l_P', 'car_r_P', 'car_s_P']))


# Notes:
# interface
# goals (l,r,s)
# plan (where we are, where we're going / next waypoint)
# honk if mistake (input -> unexpected then stop and honk)
# emergency stop if something too close


tracker = PropositionalIoContract.from_strings(
    input_vars=['q_1'],#, 'q_2', 'q_3', 'q_4'],
    output_vars=['v'],
    assumptions=[],#'G((q_1 & ~q_2 & ~q_3 & ~q_4) | (~q_1 & q_2 & ~q_3 & ~q_4) | (~q_1 & ~q_2 & q_3 & ~q_4) | (~q_1 & ~q_2 & ~q_3 & q_4))'],
    guarantees=['G(q_1 <=> v)'])

# where you are (current waypoint)

# safety = PropositionalIoContract.from_strings(
#     input_vars=['q_1_T', 'v', 'poor_visibility'],
#     output_vars=['safe'],
#     assumptions=['G(~poor_visibility)'], # we cannot use q1T because it is related to v but pacti doesnt know it!!!
#     guarantees=['G(v & ~q_1_T => ~safe)'])


# get system trace
trace = {}
trace['car_l_T'] = [1]
trace['car_r_T'] = [1] 
trace['car_s_T'] = [1]
trace['poor_visibility'] = [0]
trace['car_l_P'] = [1]
trace['car_r_P'] = [1]
trace['car_s_P'] = [1]
trace['car_l_P_prev'] = [1]
trace['car_r_P_prev'] = [1]
trace['car_s_P_prev'] = [1]
trace['q_1_prev'] = [0]
trace['q_2_prev'] = [0]
trace['q_3_prev'] = [0]
trace['q_4_prev'] = [1]

i = 0
behavior = {Var(key) : trace[key][i] for key in trace.keys()}
# perception.a.contains_behavior(behavior)
# perception.g.contains_behavior(behavior)
# st()

# add planner
print('composing perception and planner')
perception_and_planner, G1 = perception.compose_diagnostics(planner)
print(perception_and_planner)
for i in G1.nodes():
    if i not in perception_and_planner.g.terms and i not in perception_and_planner.a.terms:
        G1.nodes[i]['output'] = False
print_graph(G1, 'perception_and_planner')
st()


# add tracker
print('composing perception/planner and tracker')
# st()
sys, G2 = perception_and_planner.compose_diagnostics(tracker, vars_to_keep = ['v','q_1', 'q_2', 'q_3', 'q_4', 'car_l_P', 'car_r_P', 'car_s_P'])
print(sys)
for i in G2.nodes(): # filter out every guarantee that is dropped
    if i not in sys.g.terms and i not in sys.a.terms:
        G2.nodes[i]['output'] = False
print_graph(G2, 'sys')
st()

# add safety
# print('composing perception/planner/tracker and safety')
# # st()
# safe_sys, G3 = sys.compose_diagnostics(safety)
# print(safe_sys)
# for i in G3.nodes(): # filter out every guarantee that is dropped
#     if i not in safe_sys.g.terms and i not in safe_sys.a.terms:
#         G3.nodes[i]['output'] = False
# print_graph(G3, 'safe_sys')
# st()
