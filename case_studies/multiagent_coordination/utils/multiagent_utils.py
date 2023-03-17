import random
from itertools import combinations

import numpy as np
from pacti.terms.polyhedra import PolyhedralContractCompound
from pacti.iocontract import Var
from pacti.terms.polyhedra import PolyhedralContract


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
    distance = np.abs(move[0] - goal.x) + np.abs(move[1] - goal.y)
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
    """
    Function to return a chosen move for all robots.
    """
    min_dist = {}
    for candidate in move_candidates:
        candidate_list = []
        dist = distance(candidate, goal)

        if dist in min_dist.keys():
            for entry in min_dist[dist]:
                candidate_list.append(entry)
        if candidate not in candidate_list:
            candidate_list.append(candidate)
        min_dist.update({dist: candidate_list})

    best_move = random.choice(min_dist[min(sorted(min_dist.keys()))])

    best_dist = distance(best_move, goal)
    cur_dist = distance(cur_pos, goal)

    if best_dist < cur_dist:
        move_options = []
        for distances in min_dist:
            if distances < cur_dist:
                move_options = move_options + min_dist[distances]
        # prune options where robots leave their goal
        moves = []
        for move in move_options:
            move_ok = True
            for i in range(len(cur_pos)):  # keep robots at goal at goal
                if indiv_distance(cur_pos[i], goal[i]) < indiv_distance(
                    move[i], goal[i]
                ):  # indiv_distance(cur_pos[i],goal[i]) < indiv_distance(move[i],goal[i]):
                    move_ok = False
            if move_ok and move not in moves:
                moves = moves + [move]

        if random.random() < 0.1:  # take the best move 10% of the time
            move = random.choice(min_dist[min(sorted(min_dist.keys()))])
        else:  # take a random good move
            move = random.choice(moves)
    # check that other moves are possible
    elif best_dist == cur_dist:
        moves = []
        for move in move_candidates:
            move_ok = True
            if move == cur_pos:  # remove staying in the same position
                move_ok = False
            if move == last_pos:  # remove going back to previous position
                move_ok = False
            for i in range(len(cur_pos)):  # keep robots at goal at goal
                if (
                    indiv_distance(cur_pos[i], goal[i]) == 0 and indiv_distance(move[i], goal[i]) != 0
                ):  # indiv_distance(cur_pos[i],goal[i]) < indiv_distance(move[i],goal[i]):
                    move_ok = False
            if move_ok and move not in moves:  # add move to possible moves
                moves = moves + [move]

        move = random.choice(moves)  # take a random move

    return move


def find_move_candidates_three(n, m, robots, T_0, contract):
    """
    Evaluate the contracts for possible next positions
    of the robots to find allowed moves.
    """
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

    # find possible [(x,y),(x,y),(x,y)] options for robots
    possible_sol = []
    for x_a in list(set([max(X_A_0-1,0), X_A_0, min(X_A_0+1,n)])):
        for y_a in list(set([max(Y_A_0-1,0), Y_A_0, min(Y_A_0+1,m)])):
            for x_b in list(set([max(X_B_0-1,0), X_B_0, min(X_B_0+1,n)])):
                for y_b in list(set([max(Y_B_0-1,0), Y_B_0, min(Y_B_0+1,m)])):
                    for x_c in list(set([max(X_C_0-1,0), X_C_0, min(X_C_0+1,n)])):
                        for y_c in list(set([max(Y_C_0-1,0), Y_C_0, min(Y_C_0+1,m)])):

                            del_x_A_B = (x_a - x_b) * (X_A_0 - X_B_0)
                            del_y_A_B = (y_a - y_b) * (Y_A_0 - Y_B_0)
                            del_x_A_C = (x_a - x_c) * (X_A_0 - X_C_0)
                            del_y_A_C = (y_a - y_c) * (Y_A_0 - Y_C_0)
                            del_x_B_C = (x_b - x_c) * (X_B_0 - X_C_0)
                            del_y_B_C = (y_b - y_c) * (Y_B_0 - Y_C_0)

                            var_dict = {
                                x_A_0: X_A_0,
                                y_A_0: Y_A_0,
                                x_B_0: X_B_0,
                                y_B_0: Y_B_0,
                                x_C_0: X_C_0,
                                y_C_0: Y_C_0,
                                current_distance: cur_dist,
                                t_0: T_0,
                                t_1: T_1,
                                x_A_1: x_a,
                                y_A_1: y_a,
                                x_B_1: x_b,
                                y_B_1: y_b,
                                x_C_1: x_c,
                                y_C_1: y_c,
                                delta_x_A_B: del_x_A_B,
                                delta_y_A_B: del_y_A_B,
                                delta_x_A_C: del_x_A_C,
                                delta_y_A_C: del_y_A_C,
                                delta_x_B_C: del_x_B_C,
                                delta_y_B_C: del_y_B_C,
                            }

                            if contract.a.contains_behavior(var_dict) and \
                                contract.g.contains_behavior(var_dict):
                                possible_sol.append([(x_a,y_a),(x_b,y_b),(x_c,y_c)])

    return possible_sol, t_1


def robots_move(robots, move):
    """
    Apply next move and update positions.
    """
    for i in range(len(robots)):
        robots[i].move(move[i])


def get_swapping_contract(robots):
    '''
    Contract ensuring no swapping conflicts for all robots.
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

    contract = PolyhedralContractCompound.from_string(
    InputVars = inputvars,
    OutputVars= outputvars,
    assumptions=[["-current_distance <= -1"
                 ]],
    guarantees=[[f"-{delta[0]}-{delta[1]} <= -1" for delta in delta_pairs]])

    return contract

def get_collision_contract(robots):
    robotnames = []
    for robot in robots:
        robotnames.append(robot.name)

    combis = combinations(robotnames, 2)
    # c_collison = collision_contract_named(combis[0][0], combis[0][1])
    contracts = []
    for combi in combis:
        contract = collision_contract_named(combi[0], combi[1])
        contracts.append(contract)

    c_collison = contracts[0]
    for contract in contracts[1:]:
        c_collison = c_collison.merge(contract)

    return c_collison


def collision_contract_named(robot_1, robot_2):
    inputvars = [
        "x_" + str(robot_1) + "_0",
        "y_" + str(robot_1) + "_0",
        "x_" + str(robot_2) + "_0",
        "y_" + str(robot_2) + "_0",
        "t_0",
        "current_distance",
    ]
    outputvars = [
            "x_" + str(robot_1) + "_1",
            "y_" + str(robot_1) + "_1",
            "x_" + str(robot_2) + "_1",
            "y_" + str(robot_2) + "_1",
            "t_1",
        ]

    contract = PolyhedralContractCompound.from_string(
    InputVars = inputvars,
    OutputVars= outputvars,
    assumptions=[["-current_distance <= -1"
                 ]],
    guarantees=[["x_" + str(robot_1) + "_1 - x_" + str(robot_2) + "_1 + y_" + str(robot_1) + "_1 - y_" + str(robot_2) + "_1 <= -1"], \
                ["- x_" + str(robot_1) + "_1 + x_" + str(robot_2) + "_1 - y_" + str(robot_1) + "_1 + y_" + str(robot_2) + "_1 <= -1"],\
               ["x_" + str(robot_1) + "_1 - x_" + str(robot_2) + "_1 - y_" + str(robot_1) + "_1 + y_" + str(robot_2) + "_1 <= -1"],\
               ["- x_" + str(robot_1) + "_1 + x_" + str(robot_2) + "_1 + y_" + str(robot_1) + "_1 - y_" + str(robot_2) + "_1 <= -1"]])
    return contract
