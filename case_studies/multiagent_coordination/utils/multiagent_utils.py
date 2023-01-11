import random
from itertools import combinations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from ipdb import set_trace as st
from IPython.display import HTML
from matplotlib.patches import Circle, Rectangle

from pacti.terms.polyhedra.loaders import readContract

# from copy import deepcopy


# coordinate class
class Coord:
    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.xy = pos


# robot class with position and goal
class Robot:
    def __init__(self, name, pos, goal):
        self.name = name
        self.pos = Coord(pos)
        self.goal = Coord(goal)

    def move(self, new_pos):
        self.pos = Coord(new_pos)


# # snapshot of the simulation for a timestep
# class Snapshot():
#     def __init__(self, timestep, robots, goals):
#         self.t = timestep
#         self.robots = [Coord(robot) for robot in robots]
#         self.goals = [Coord(goal) for goal in goals]


def distance(candidate, goal):
    """
    Distance measure from current robot positions to desired position.
    """
    distance = 0
    for i, move in enumerate(candidate):
        distance = distance + np.abs(move[0] - goal[i].x) + np.abs(move[1] - goal[i].y)

    # distance_a = np.abs(candidate[0][0]-goal[0].x)+np.abs(candidate[0][1]-goal[0].y)
    # distance_b = np.abs(candidate[1][0]-goal[1].x)+np.abs(candidate[1][1]-goal[1].y)
    return distance


def strategy(move_candidates, goal):
    """
    Function to return a chosen move for both robots.
    """
    min_dist = {}
    for candidate in move_candidates:
        candidate_list = []
        dist = distance(candidate, goal)

        if dist in min_dist.keys():
            for entry in min_dist[dist]:
                candidate_list.append(entry)

        candidate_list.append(candidate)
        min_dist.update({dist: candidate_list})
    # find the best options and pick randomly
    # print(min_dist)
    # print(sorted(min_dist.keys()))
    # print(min(sorted(min_dist.keys())))
    # options_key = min(min_dist, key=min_dist.get)
    # print(options_key)

    move = random.choice(min_dist[min(sorted(min_dist.keys()))])
    return move


def strategy_multiple(move_candidates, goal):
    """
    Function to return a chosen move for both robots.
    """
    min_dist = {}
    for candidate in move_candidates:
        candidate_list = []
        dist = distance(candidate, goal)

        if dist in min_dist.keys():
            for entry in min_dist[dist]:
                candidate_list.append(entry)

        candidate_list.append(candidate)
        min_dist.update({dist: candidate_list})
    move = random.choice(min_dist[min(sorted(min_dist.keys()))])
    return move


#
# def save_trace(trace, robots , goal):
#     if trace:
#         t = trace[-1].t + 1
#     else:
#         t = 0
#     snap = Snapshot(t, robots, goal)
#     trace.append(snap)
#     return trace
#
# def plot_grid_world(n,m,robots):
#     gridsize = 10
#     r1 = robots[0]
#     r2 = robots[1]
#     if len(robots) > 5:
#         print('Need more colors!')
#
#     colors = ['blue', 'red', 'orange','yellow', 'green']
#     color_map = {}
#     for i,robot in enumerate(robots):
#         color_map.update({robot: colors[i]})
#
#     xs = np.linspace(0, n*gridsize, n+1)
#     ys = np.linspace(0, m*gridsize, m+1)
#     ax = plt.gca()
#
#     w, h = xs[1] - xs[0], ys[1] - ys[0]
#     for i, x in enumerate(xs[:-1]):
#         for j, y in enumerate(ys[:-1]):
#             if i % 2 == j % 2:
#                 ax.add_patch(Rectangle((x, y), w, h, fill=True, color='lemonchiffon'))
#     for x in xs:
#         plt.plot([x, x], [ys[0], ys[-1]], color='black', alpha=.3)
#     for y in ys:
#         plt.plot([xs[0], xs[-1]], [y, y], color='black', alpha=.3)
#
#     for x in range(n):
#         for y in range(m):
#             for robot in robots:
#                 if (x,y) == robot.pos.xy:
#                     ax.add_patch(Circle(((x+0.5)*gridsize, (y+0.5)*gridsize), 0.2*gridsize, color=color_map[robot], alpha=0.6))
#                 if (x,y) == robot.goal.xy:
#                     ax.add_patch(Circle(((x+0.5)*gridsize, (y+0.5)*gridsize), 0.2*gridsize, color=color_map[robot], alpha=0.3))
#
#     ax.set_aspect('equal', 'box')
#     ax.xaxis.set_visible(False)
#     ax.yaxis.set_visible(False)
#     plt.gca().invert_yaxis()
#     plt.title('Grid World')
#     plt.show()
#
#
# def animate(trace, n, m):
#     colors = ['blue', 'red', 'orange','yellow', 'green']
#     frames = len(trace)
#     print("Rendering %d frames..." % frames)
#     gridsize = 10
#
#     # prepare the gridworld
#     xs = np.linspace(0, n*gridsize, n+1)
#     ys = np.linspace(0, m*gridsize, m+1)
#     w, h = xs[1] - xs[0], ys[1] - ys[0]
#     fig, ax = plt.subplots()
#
#     ax.set_xlim(xs[0], n*gridsize)
#     ax.set_ylim(ys[0], m*gridsize)
#     ax.xaxis.set_visible(False)
#     ax.yaxis.set_visible(False)
#
#     def render_frame(i):
#         robots = trace[i].robots
#         goals = trace[i].goals
#
#         for i, x in enumerate(xs[:-1]):
#             for j, y in enumerate(ys[:-1]):
#                 if i % 2 == j % 2:
#                     ax.add_patch(Rectangle((x, y), w, h, fill=True, color='lemonchiffon'))
#                 else:
#                     ax.add_patch(Rectangle((x, y), w, h, fill=True, color='white'))
#         for x in xs:
#             ax.plot([x, x], [ys[0], ys[-1]], color='black', alpha=.3)
#         for y in ys:
#             ax.plot([xs[0], xs[-1]], [y, y], color='black', alpha=.3)
#
#         for x in range(n):
#             for y in range(m):
#                 for i,robot in enumerate(robots):
#                     if (x,y) == robot.xy:
#                         ax.add_patch(Circle(((x+0.5)*gridsize, (y+0.5)*gridsize), 0.2*gridsize, color=colors[i], alpha=0.6))
#                 for i,goal in enumerate(goals):
#                     if (x,y) == goal.xy:
#                         ax.add_patch(Circle(((x+0.5)*gridsize, (y+0.5)*gridsize), 0.2*gridsize, color=colors[i], alpha=0.3))
#
#         ax.set_aspect('equal', 'box')
#
#     anim = matplotlib.animation.FuncAnimation(
#         fig, render_frame, frames=frames, interval=1000, blit=False)
#
#     anim.save("test.mp4", fps=1)
#
#     plt.close()
#     display(HTML(anim.to_html5_video()))


def check_collision_quadrants(merged_dyn_contract, c_q1, c_q2, c_q3, c_q4):
    merged_contracts = []
    # st()

    try:
        merged_contract_q1 = merged_dyn_contract.merge(c_q1)
        merged_contracts.append(merged_contract_q1)
    except:
        pass

    try:
        merged_contract_q2 = merged_dyn_contract.merge(c_q2)
        merged_contracts.append(merged_contract_q2)
    except:
        pass

    try:
        merged_contract_q3 = merged_dyn_contract.merge(c_q3)
        merged_contracts.append(merged_contract_q3)
    except:
        pass

    try:
        merged_contract_q4 = merged_dyn_contract.merge(c_q4)
        merged_contracts.append(merged_contract_q4)
    except:
        pass
    return merged_contracts


def find_move_candidates_multiple(n, m, robots, t_0, contract, c_dyn_collision):
    x_A_0 = robots[0].pos.x
    y_A_0 = robots[0].pos.y
    x_B_0 = robots[1].pos.x
    y_B_0 = robots[1].pos.y
    x_C_0 = robots[2].pos.x
    y_C_0 = robots[2].pos.y
    current_distance_1 = np.abs(x_A_0 - x_B_0) + np.abs(x_A_0 - x_B_0)
    current_distance_2 = np.abs(x_B_0 - x_C_0) + np.abs(x_B_0 - x_C_0)
    current_distance_3 = np.abs(x_A_0 - x_C_0) + np.abs(x_A_0 - x_C_0)
    current_distance = min(current_distance_1, current_distance_2, current_distance_3)
    t_1 = t_0 + 1
    # find possible [(x,y),(x,y)] options for robots
    possible_sol = []
    for x_a in range(n):
        for y_a in range(m):
            for x_b in range(n):
                for y_b in range(m):
                    for x_c in range(n):
                        for y_c in range(m):
                            x_A_1 = x_a
                            y_A_1 = y_a
                            x_B_1 = x_b
                            y_B_1 = y_b
                            x_C_1 = x_c
                            y_C_1 = y_c
                            delta_x_A_B = (x_A_1 - x_B_1) * (x_A_0 - x_B_0)
                            delta_y_A_B = (y_A_1 - y_B_1) * (y_A_0 - y_B_0)
                            delta_x_A_C = (x_A_1 - x_C_1) * (x_A_0 - x_C_0)
                            delta_y_A_C = (y_A_1 - y_C_1) * (y_A_0 - y_C_0)
                            delta_x_B_C = (x_B_1 - x_C_1) * (x_B_0 - x_C_0)
                            delta_y_B_C = (y_B_1 - y_C_1) * (y_B_0 - y_C_0)

                            sol = True
                            for g in contract.g.terms:
                                holds = eval(str(g))
                                dynamic_collision_holds = eval(str(c_dyn_collision.g))
                                if not holds or not dynamic_collision_holds:
                                    sol = False
                            if sol:
                                possible_sol.append([(x_a, y_a), (x_b, y_b), (x_c, y_c)])
    return possible_sol, t_1


def robots_move(robots, move):
    for i in range(len(robots)):
        robots[i].move(move[i])


def get_possible_moves_multiple_robots(n, m, robots, merged_dyn_contract, collision_contracts, c_dyn_collision):
    # go though each robot pair
    # go through each of the 4 collision contracts
    # merge the contract with the dynamics and
    # print(collision_contracts)
    # merged_contracts = check_collision_quadrants(merged_dyn_contract, c_q1, c_q2, c_q3, c_q4)
    t_0 = 0
    move_options = []
    for contract_list in collision_contracts:
        # st()
        # print(contract_list)
        # print(contract_list[0])
        merged_contracts = check_collision_quadrants(
            merged_dyn_contract, contract_list[0], contract_list[1], contract_list[2], contract_list[3]
        )
        # print(len(merged_contracts))
        # print(merged_contracts)
        sols = []
        for i in range(len(merged_contracts)):
            # possible_sol, t_1 = find_move_candidates(r1, r2, t_0, merged_contracts[i])
            possible_sol, t_1 = find_move_candidates_multiple(n, m, robots, t_0, merged_contracts[i], c_dyn_collision)
            sols = sols + possible_sol
        move_options.append(sols)

    n = len(move_options)
    moves = []
    for move in move_options[0]:
        move_ok = True
        for k in range(1, n):
            if not move in move_options[k]:
                move_ok = False
        if move_ok:
            moves.append(move)

    # print(moves)
    return moves


def get_dynamic_collision_contract(robots):
    robotnames = []
    for robot in robots:
        robotnames.append(robot.name)

    combis = combinations(robotnames, 2)

    inputvars = ["current_distance"]
    delta_pairs = []
    for combi in combis:
        del_x_str = "delta_x_" + str(combi[0]) + "_" + str(str(combi[1]))
        del_y_str = "delta_y_" + str(combi[0]) + "_" + str(str(combi[1]))
        inputvars = inputvars + [del_x_str, del_y_str]
        delta_pairs.append((del_x_str, del_y_str))
    outputvars = []

    contract = {
        "InputVars": inputvars,
        "OutputVars": outputvars,
        "assumptions": [{"constant": -1, "coefficients": {"current_distance": -1}}],
        "guarantees": [{"constant": -1, "coefficients": {delta[0]: -1, delta[1]: -1}} for delta in delta_pairs],
    }

    c_dyn_coll = readContract(contract)

    return c_dyn_coll


def get_collision_contracts_robot_pair(robot_1, robot_2, other):
    """
    For each pair of robots, we will get four contracts describing the four collision quadrants.
    """
    inputvars = [
        "x_" + str(robot_1) + "_0",
        "y_" + str(robot_1) + "_0",
        "x_" + str(robot_2) + "_0",
        "y_" + str(robot_2) + "_0",
        "x_" + str(other) + "_0",
        "y_" + str(other) + "_0",
        "t_0",
        "current_distance",
    ]
    outputvars = [
        "x_" + str(robot_1) + "_1",
        "y_" + str(robot_1) + "_1",
        "x_" + str(robot_2) + "_1",
        "y_" + str(robot_2) + "_1",
        "x_" + str(other) + "_1",
        "y_" + str(other) + "_1",
        "t_1",
    ]

    contract_1 = {
        "InputVars": inputvars,
        "OutputVars": outputvars,
        "assumptions": [{"constant": -1, "coefficients": {"current_distance": -1}}],
        "guarantees": [
            {
                "constant": -1,
                "coefficients": {
                    "x_" + str(robot_1) + "_1": 1,
                    "x_" + str(robot_2) + "_1": -1,
                    "y_" + str(robot_1) + "_1": 1,
                    "y_" + str(robot_2) + "_1": -1,
                },
            }
        ],
    }

    contract_2 = {
        "InputVars": inputvars,
        "OutputVars": outputvars,
        "assumptions": [
            # Assume no collision
            {"constant": -1, "coefficients": {"current_distance": -1}}
        ],
        "guarantees": [
            {
                "constant": -1,
                "coefficients": {
                    "x_" + str(robot_1) + "_1": -1,
                    "x_" + str(robot_2) + "_1": 1,
                    "y_" + str(robot_1) + "_1": -1,
                    "y_" + str(robot_2) + "_1": 1,
                },
            }
        ],
    }

    contract_3 = {
        "InputVars": inputvars,
        "OutputVars": outputvars,
        "assumptions": [
            # Assume no collision
            {"constant": -1, "coefficients": {"current_distance": -1}}
        ],
        "guarantees": [
            # collision constraints (for each set of robots)
            {
                "constant": -1,
                "coefficients": {
                    "x_" + str(robot_1) + "_1": 1,
                    "x_" + str(robot_2) + "_1": -1,
                    "y_" + str(robot_1) + "_1": -1,
                    "y_" + str(robot_2) + "_1": 1,
                },
            }
        ],
    }

    contract_4 = {
        "InputVars": inputvars,
        "OutputVars": outputvars,
        "assumptions": [
            # Assume no collision
            {"constant": -1, "coefficients": {"current_distance": -1}}
        ],
        "guarantees": [
            # collision constraints (for each set of robots)
            {
                "constant": -1,
                "coefficients": {
                    "x_" + str(robot_1) + "_1": -1,
                    "x_" + str(robot_2) + "_1": 1,
                    "y_" + str(robot_1) + "_1": 1,
                    "y_" + str(robot_2) + "_1": -1,
                },
            }
        ],
    }

    contract_c1 = readContract(contract_1)
    contract_c2 = readContract(contract_2)
    contract_c3 = readContract(contract_3)
    contract_c4 = readContract(contract_4)

    return [contract_c1, contract_c2, contract_c3, contract_c4]
