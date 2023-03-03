import random
from itertools import combinations
import numpy as np
from pacti.terms.polyhedra import PolyhedralContract
from pacti.iocontract import Var

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


def distance(candidate, goal):
    """
    Distance measure from current robot positions to desired position.
    """
    distance = 0
    for i, move in enumerate(candidate):
        distance = distance + np.abs(move[0] - goal[i].x) + np.abs(move[1] - goal[i].y)

    return distance

def indiv_distance(move, goal):
    distance = np.abs(move[0]-goal.x)+np.abs(move[1]-goal.y)
    return distance


def strategy(move_candidates, goal):
    """
    Function to return a chosen move for both robots
    by choosing the best next move.
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

def strategy_multiple_simple(move_candidates, goal):
    """
    Function to return a chosen move for both robots,
    a random move is taken in 10% of the cases and
    otherwise the best next move is taken.
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

    if random.random() < 0.2:
        move = random.choice(move_candidates)
    else:
        move = random.choice(min_dist[min(sorted(min_dist.keys()))])

    return move


def strategy_multiple(move_candidates, goal, cur_pos, last_pos):
    '''
    Function to return a chosen move for all robots.
    '''
    min_dist = {}
    for candidate in move_candidates:
        candidate_list = []
        dist = distance(candidate,goal)

        if dist in min_dist.keys():
            for entry in min_dist[dist]:
                candidate_list.append(entry)
        if candidate not in candidate_list:
            candidate_list.append(candidate)
        min_dist.update({dist: candidate_list})

    best_move = random.choice(min_dist[min(sorted(min_dist.keys()))])

    best_dist = distance(best_move,goal)
    cur_dist = distance(cur_pos,goal)

    if best_dist < cur_dist:
        move_options = []
        for distances in min_dist:
            if distances < cur_dist:
                move_options = move_options + min_dist[distances]
        # prune options where robots leave their goal
        moves = []
        for move in move_options:
            move_ok = True
            for i in range(len(cur_pos)): # keep robots at goal at goal
                if indiv_distance(cur_pos[i],goal[i]) < indiv_distance(move[i],goal[i]):#indiv_distance(cur_pos[i],goal[i]) < indiv_distance(move[i],goal[i]):
                    move_ok = False
            if move_ok and move not in moves:
                moves = moves + [move]

        if random.random() < 0.1: # take the best move 10% of the time
            move = random.choice(min_dist[min(sorted(min_dist.keys()))])
        else: # take a random good move
            move = random.choice(moves)
    # check that other moves are possible
    elif best_dist == cur_dist:
        moves = []
        for move in move_candidates:
            move_ok = True
            if move == cur_pos: # remove staying in the same position
                move_ok = False
            if move == last_pos: # remove going back to previous position
                move_ok = False
            for i in range(len(cur_pos)): # keep robots at goal at goal
                if indiv_distance(cur_pos[i],goal[i]) == 0 and indiv_distance(move[i],goal[i]) != 0:#indiv_distance(cur_pos[i],goal[i]) < indiv_distance(move[i],goal[i]):
                    move_ok = False
            if move_ok and move not in moves: # add move to possible moves
                moves = moves + [move]

        move = random.choice(moves) # take a random move

    return move


def check_collision_quadrants(merged_dyn_contract, c_q1, c_q2, c_q3, c_q4):
    '''
    Merge each of the collision contracts with
    the dynamics contract.
    '''
    merged_contracts = []
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


def find_move_candidates_multiple(n, m, robots, T_0, contract, c_dyn_collision):
    '''
    Evaluate the contracts for possible next positions
    of the robots to find allowed moves.
    '''
    x_A_0 = Var("x_A_0")
    y_A_0 = Var("y_A_0")
    x_B_0 = Var("x_B_0")
    y_B_0 = Var("y_B_0")
    x_C_0 = Var("x_C_0")
    y_C_0 = Var("y_C_0")
    current_distance = Var("current_distance")
    t_0 = Var("t_0")
    t_1 = Var("t_1")
    x_A_1 = Var("x_A_1")
    y_A_1 = Var("y_A_1")
    x_B_1 = Var("x_B_1")
    y_B_1 = Var("y_B_1")
    x_C_1 = Var("x_C_1")
    y_C_1 = Var("y_C_1")
    delta_x_A_B = Var("delta_x_A_B")
    delta_y_A_B = Var("delta_y_A_B")
    delta_x_A_C = Var("delta_x_A_C")
    delta_y_A_C = Var("delta_y_A_C")
    delta_x_B_C = Var("delta_x_B_C")
    delta_y_B_C = Var("delta_y_B_C")

    X_A_0 = robots[0].pos.x
    Y_A_0 = robots[0].pos.y
    X_B_0 = robots[1].pos.x
    Y_B_0 = robots[1].pos.y
    X_C_0 = robots[2].pos.x
    Y_C_0 = robots[2].pos.y
    current_distance_1 = np.abs(X_A_0 - X_B_0) + np.abs(Y_A_0 - Y_B_0)
    current_distance_2 = np.abs(X_B_0 - X_C_0) + np.abs(Y_B_0 - Y_C_0)
    current_distance_3 = np.abs(X_A_0 - X_C_0) + np.abs(Y_A_0 - Y_C_0)
    cur_dist = min(current_distance_1, current_distance_2, current_distance_3)
    T_1 = T_0 + 1

    # find possible [(x,y),(x,y)] options for robots
    possible_sol = []
    for x_a in [max(X_A_0-1,0), X_A_0, min(X_A_0+1,n)]:
        for y_a in [max(Y_A_0-1,0), Y_A_0, min(Y_A_0+1,m)]:
            for x_b in [max(X_B_0-1,0), X_B_0, min(X_B_0+1,n)]:
                for y_b in [max(Y_B_0-1,0), Y_B_0, min(Y_B_0+1,m)]:
                    for x_c in [max(X_C_0-1,0), X_C_0, min(X_C_0+1,n)]:
                        for y_c in [max(Y_C_0-1,0), Y_C_0, min(Y_C_0+1,m)]:

                            del_x_A_B = (x_a - x_b) * (X_A_0 - X_B_0)
                            del_y_A_B = (y_a - y_b) * (Y_A_0 - Y_B_0)
                            del_x_A_C = (x_a - x_c) * (X_A_0 - X_C_0)
                            del_y_A_C = (y_a - y_c) * (Y_A_0 - Y_C_0)
                            del_x_B_C = (x_b - x_c) * (X_B_0 - X_C_0)
                            del_y_B_C = (y_b - y_c) * (Y_B_0 - Y_C_0)

                            var_dict = {x_A_0: X_A_0, y_A_0: Y_A_0, x_B_0: X_B_0, \
                               y_B_0: Y_B_0, x_C_0: X_C_0, y_C_0: Y_C_0, \
                               current_distance: cur_dist, \
                               t_0: T_0, t_1: T_1, x_A_1: x_a, y_A_1: y_a, \
                               x_B_1: x_b, y_B_1: y_b, x_C_1: x_c, y_C_1: y_c,\
                               delta_x_A_B: del_x_A_B, delta_y_A_B: del_y_A_B, \
                               delta_x_A_C: del_x_A_C, delta_y_A_C: del_y_A_C, \
                               delta_x_B_C: del_x_B_C, delta_y_B_C: del_y_B_C}

                            # from ipdb import set_trace as st
                            # st()
                            if c_dyn_collision.a.contains_behavior(var_dict) and \
                                c_dyn_collision.g.contains_behavior(var_dict) and \
                                contract.a.contains_behavior(var_dict) and \
                                contract.g.contains_behavior(var_dict):

                                possible_sol.append([(x_a,y_a),(x_b,y_b),(x_c,y_c)])

                            # sol = True
                            # for g in c_dyn_collision.g.terms:
                            #     dynamic_collision_holds = eval(str(g)+'<='+str(g.constant))
                            #     if not dynamic_collision_holds:
                            #         sol = False
                            # if sol:
                            #     for g in contract.g.terms:
                            #         holds = eval(str(g)+'<='+str(g.constant))
                            #         if not holds or not dynamic_collision_holds:
                            #             sol = False
                            # if sol:
    #                         #     possible_sol.append([(x_a, y_a), (x_b, y_b), (x_c, y_c)])
    # if possible_sol == []:
    #     from ipdb import set_trace as st
    #     st()

    return possible_sol, t_1


def robots_move(robots, move):
    '''
    Apply next move and update positions.
    '''
    for i in range(len(robots)):
        robots[i].move(move[i])


def get_possible_moves_multiple_robots(n, m, robots, merged_dyn_contract, collision_contracts, c_dyn_collision):
    '''
    Iterate though the robot pairs, merge each collision
    contract with the dynamics contract and find the
    possible moves for that robot pair.
    Returns moves that are allowed for all robot pairs.
    '''
    t_0 = 0
    move_options = []
    for contract_list in collision_contracts:
        merged_contracts = check_collision_quadrants(
            merged_dyn_contract, contract_list[0], contract_list[1], contract_list[2], contract_list[3]
        )
        sols = []
        for i in range(len(merged_contracts)):
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

    return moves


def get_dynamic_collision_contract(robots):
    '''
    Contract ensureing no swapping conflicts for all robots.
    '''
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
        "input_vars": inputvars,
        "output_vars": outputvars,
        "assumptions": [{"constant": -1, "coefficients": {"current_distance": -1}}],
        "guarantees": [{"constant": -1, "coefficients": {delta[0]: -1, delta[1]: -1}} for delta in delta_pairs],
    }

    c_dyn_coll = PolyhedralContract.from_dict(contract)

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
        "input_vars": inputvars,
        "output_vars": outputvars,
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
        "input_vars": inputvars,
        "output_vars": outputvars,
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
        "input_vars": inputvars,
        "output_vars": outputvars,
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
        "input_vars": inputvars,
        "output_vars": outputvars,
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

    contract_c1 = PolyhedralContract.from_dict(contract_1)
    contract_c2 = PolyhedralContract.from_dict(contract_2)
    contract_c3 = PolyhedralContract.from_dict(contract_3)
    contract_c4 = PolyhedralContract.from_dict(contract_4)

    return [contract_c1, contract_c2, contract_c3, contract_c4]
