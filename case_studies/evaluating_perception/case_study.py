# Import libraries
from pacti.iocontract.utils import getVarlist
from PIL import Image
from pacti.terms.polyhedra.loaders import read_contract, write_contract
import pdb
from utils import *
import random
import pickle as pkl
import collections

# Construct random confusion matrix
def construct_CM(tp_ped, tp_obj, tp_emp):
    C = dict()
    C["ped", "ped"] = tp_ped
    coeff = random.random()
    C["obj", "ped"] = coeff*(1-tp_ped)
    C["empty", "ped"] = (1-coeff)*(1 - tp_ped)

    C["ped", "obj"] = 0.1*(1-tp_obj)
    C["obj", "obj"] = tp_obj
    C["empty", "obj"] = 0.9*(1-tp_obj)

    C["ped", "empty"] = 0.5*(1-tp_emp)
    C["obj", "empty"] = 0.5*(1-tp_emp)
    C["empty", "empty"] = tp_emp
    return C

def call_MC(K, K_backup, C, true_env, true_env_type, state_info, M):
    importlib.reload(Kped)
    importlib.reload(Kobj)
    importlib.reload(Kempty)

    K_strat = dict()
    K_strat["ped"] = Kped
    K_strat["obj"] = Kobj
    K_strat["empty"] = Kempty

    obs_keys = dict()
    obs_keys["ped"] = ["xcar", "vcar"]
    obs_keys["obj"] = ["xobj"]
    obs_keys["empty"] = ["xempty"]

    M.set_confusion_matrix(C)
    M.set_true_env_state(true_env, true_env_type)
    M.set_controller(K, K_strat, K_backup)

    M.construct_internal_state_maps()

    # Construct Markov chain:
    M.construct_markov_chain()
    start_state = state_info["start"]
    bad_states = state_info["bad"]
    good_state = state_info["good"]
    MC = M.to_MC(start_state) # For setting initial conditions and assigning bad/good labels
    print(M.M)
    return M

def initialize_ped(vmax, MAX_V, true_env_type):
    Ncar = int(MAX_V*(MAX_V+1)/2 + 2)
    Vlow =  0
    Vhigh = vmax
    x_vmax_stop = vmax*(vmax+1)/2 + 1
    xcross_start = 2
    Nped = Ncar - xcross_start + 1
    if x_vmax_stop >= xcross_start:
        min_xped = int(x_vmax_stop + 1 - (xcross_start - 1))
    else:
        min_xped = 3
    assert(min_xped > 0)
    assert(min_xped<= Nped)
    if min_xped < Nped:
        xped = np.random.randint(min_xped, Nped)
    else:
        xped = int(min_xped)
    xped = int(min_xped)
    xcar_stop = xped + xcross_start - 2
    assert(xcar_stop > 0)
    state_f = lambda x,v: (Vhigh-Vlow+1)*(x-1)+v
    bad_states = set()
    good_state = set()

    def get_formula_states(xcar_stop):
        bst = set()
        for vi in range(1,Vhigh+1):
            state = state_f(xcar_stop, vi)
            bst |= {"S"+str(state)}
        gst = {"S" + str(state_f(xcar_stop,0))}
        bad = "" # Expression for bad states
        good = "" # Expression for good states
        for st in list(gst):
            if good == "":
                good = good + "\"" + st+"\""
            else:
                good = good + "|\""+st+"\""
        for st in list(bst):
            if bad == "":
                bad = bad + "\"" + st+"\""
            else:
                bad = bad + "|\""+st+"\""
        return good, bad, gst, bst
    good, bad, gst, bst = get_formula_states(xcar_stop)
    good_state |= gst
    bad_states |= bst
    pdb.set_trace()
    phi1 = "!("+good+")" # This is for empty and obj states --> to keep driving
    phi2 = "("+good+") | !("+bad # This is to stop if there is a ped
    for xcar_ii in range(xcar_stop+1, Ncar+1):
        good, bad, gst, bst = get_formula_states(xcar_ii) # We only want the bad states; ignore the good states output here
        bad_states |= bst
        phi2 = phi2 + "|" + bad
    phi2 = phi2 + ")"
    if true_env_type == "ped":
        formula = "P=?[G("+str(phi2)+")]" # Don't reach bad states and eventually reach good states
    else:
        formula = "P=?[G("+str(phi1)+")]" # Don't reach the stop state at crosswalk
    print(formula)
    return Ncar, Vlow, Vhigh, xped, bad_states, good_state, formula

# Checking initialization
def new_initialize_ped(vmax, Ncar, true_env_type):
    assert vmax*(vmax+1)/2 <= Ncar
    Vlow =  0
    Vhigh = vmax
    x_vmax_stop = vmax*(vmax+1)/2 + 1
    xped = Ncar - 1
    xcar_stop = xped - 1
    assert(xcar_stop > 0)
    state_f = lambda x,v: (Vhigh-Vlow+1)*(x-1)+v
    bad_states = set()
    good_state = set()

    def get_formula_states(xcar_stop):
        bst_cw = set() # Bad states at crosswalk
        bst_prior = set() # Bad states prior to crosswalk
        # Having non-zero speed at crosswalk is a bad state:
        for vi in range(1,Vhigh+1):
            state = state_f(xcar_stop, vi)
            bst_cw |= {"S"+str(state)}
        # Having zero speed at any cell before crosswalk is a bad state:
        for xi in range(1,xcar_stop):
            state = state_f(xi, 0)
            bst_prior |= {"S"+str(state)}
        gst = {"S" + str(state_f(xcar_stop,0))}
        bad_cw = "" # Expression for bad states for crosswalk
        bad_prior = "" # Expression for bad states before crosswalk
        good = "" # Expression for good states
        for st in list(gst):
            if good == "":
                good = good + "\"" + st+"\""
            else:
                good = good + "|\""+st+"\""
        for st in list(bst_cw):
            if bad_cw == "":
                bad_cw = bad_cw + "\"" + st+"\""
            else:
                bad_cw = bad_cw + "|\""+st+"\""
        for st in list(bst_prior):
            if bad_prior == "":
                bad_prior = bad_prior + "\"" + st+"\""
            else:
                bad_prior = bad_prior + "|\""+st+"\""
        return good, bad_cw, bad_prior, gst, bst_cw, bst_prior
    good, bad_cw, bad_prior, gst, bst_cw, bst_prior = get_formula_states(xcar_stop)

    good_state |= gst
    bad_states |= bst_cw
    bad_states |= bst_prior
    phi = "G("+good+" | !("+bad_cw+"|" + bad_prior+"))" # eventually good
    if true_env_type == "ped":
        formula = "P=?[" + phi +"]" # Don't reach bad states and eventually reach good states
    else:
        formula = "P=?[G !(" + good +")]"
    print(formula)
    return xped, bad_states, good_state, formula
# Construct backup controller:
def construct_backup_controller(Ncar, Vlow, Vhigh):
    K_backup = dict()
    for xcar in range(1,Ncar+1):
        for vcar in range(Vlow, Vhigh+1):
            st = (xcar, vcar)
            end_st = []
            if xcar == Ncar:
                end_st.append((xcar, vcar))
            elif vcar == 0:
                xcar_p = min(Ncar, xcar+1)
                end_st.append((xcar, vcar))
                end_st.append((xcar_p, vcar+1))
                end_st.append((xcar, vcar+1))
            else:
                xcar_p = min(Ncar, xcar+vcar)
                end_st.append((xcar_p, vcar))
                end_st.append((xcar_p, vcar-1))
                if vcar < Vhigh:
                    end_st.append((xcar_p, vcar+1))
            K_backup[st] = end_st
    return K_backup

# Creating the states of the markov chain for the system:
# Returns product states S and (pos,vel) to state dictionary
def system_states(Ncar, Vlow, Vhigh):
    nS = Ncar*(Vhigh-Vlow+1)
    state = lambda x,v: (Vhigh-Vlow+1)*(x-1) + v
    state_to_S = dict()
    S = set()
    for xcar in range(1,Ncar+1):
        for vcar in range(Vlow, Vhigh+1):
            st = "S"+str(state(xcar, vcar))
            state_to_S[xcar,vcar] = st
            S|={st}
    K_backup = construct_backup_controller(Ncar, Vlow, Vhigh)
    return S, state_to_S, K_backup

def get_states_and_controllers(C, M, start_state, good_state, bad_states, K, K_backup, true_env_type="ped"):
    true_env = str(1) #Sidewalk 3
    true_env_type = true_env_type
    state_info = dict()
    state_info["start"] = start_state
    state_info["bad"] = bad_states
    state_info["good"] = good_state
    if true_env_type == "ped":
        for st in list(good_state):
            formula2 = 'P=?[F(\"'+st+'\")]'
    else:
        for st in list(good_state):
            formula2 = 'P=?[G !(\"'+st+'\")]'
    MC = call_MC(K, K_backup, C, true_env, true_env_type, state_info, M)
    result2 = MC.prob_TL(formula2)
    # MC = call_MC(K, K_backup, C, true_env, true_env_type, state_info, M)
    return MC, result2[start_state]

# Construct state (x,v) back from state:
def state_f(x,v):
    S_value = (Vhigh-Vlow+1)*(x-1) + v
    return S_value


# Generate probability points from Confusion Matrix:
def gen_points(Ncar, Vlow, Vhigh, xped, bad_states, good_state, formula, vmax):
    points_ped = [] # Satisfaction probabilities for true env as ped

    vcar = 1 # Initial speed at starting point
    start_state = "S"+str(state_f(1,vcar))
    S, state_to_S, K_backup = system_states(Ncar, Vlow, Vhigh)
    O = {"ped", "obj", "empty"}
    tp_range = np.linspace(0.6, 0.999, num=100)
    Nrand = 15 # Fifteen random instantiations of confusion matrix for each true positive rate
    tp_range_vals = []
    for tp_ped in tp_range:
        for i in range(Nrand):
            tp_obj = 0.9
            tp_emp = 0.9
            K = K_des.construct_controllers(Ncar, Vlow, Vhigh, xped, vcar)
            Mped = MarkovChain(S, O, state_to_S)
            Cped = construct_CM(tp_ped, tp_obj, tp_emp)
            MC, prob = get_states_and_controllers(Cped, Mped, start_state, good_state, bad_states, K, K_backup, true_env_type="ped")
            # prob = MC.prob_TL(formula)
            points_ped.append(prob)
            tp_range_vals.append(tp_ped)
    print("Found probabilities for pedestrian env!")
    return points_ped, tp_range_vals

# Generate probability points from Confusion Matrix:
def gen_points_obj(Ncar, Vlow, Vhigh, xped, bad_states, good_state, formula, vmax):
    points_obj = [] # Satisfaction probabilities for true env as ped
    vcar = 1 # Initial speed at starting point
    start_state = "S"+str(state_f(1,vcar))
    S, state_to_S, K_backup = system_states(Ncar, Vlow, Vhigh)
    O = {"ped", "obj", "empty"}
    tp_range = np.linspace(0.3, 0.999, num=100)
    Nrand = 15 # Fifteen random instantiations of confusion matrix for each true positive rate
    tp_range_vals = []
    for tp_obj in tp_range:
        for i in range(Nrand):
            tp_ped = 0.9
            tp_emp = 0.9
            K = K_des.construct_controllers(Ncar, Vlow, Vhigh, xped, vcar)
            Mobj = MarkovChain(S, O, state_to_S)
            Cobj = construct_CM(tp_ped, tp_obj, tp_emp)
            MC, prob = get_states_and_controllers(Cobj, Mobj, start_state, good_state, bad_states, K, K_backup, true_env_type="obj")
            # prob = MC.prob_TL(formula)
            points_obj.append(prob)
            tp_range_vals.append(tp_obj)
    print("Found probabilities for object env!")
    return points_obj, tp_range_vals

# Generate probability points from Confusion Matrix:
def gen_points_emp(Ncar, Vlow, Vhigh, xped, bad_states, good_state, formula, vmax):
    points_emp = [] # Satisfaction probabilities for true env as ped
    vcar = 1 # Initial speed at starting point
    start_state = "S"+str(state_f(1,vcar))
    S, state_to_S, K_backup = system_states(Ncar, Vlow, Vhigh)
    O = {"ped", "obj", "empty"}
    tp_range = np.linspace(0.6, 0.999, num=100)
    Nrand = 15 # Fifteen random instantiations of confusion matrix for each true positive rate
    tp_range_vals = []
    for tp_emp in tp_range:
        for i in range(Nrand):
            tp_obj = 0.9
            tp_ped = 0.9
            K = K_des.construct_controllers(Ncar, Vlow, Vhigh, xped, vcar)
            Memp = MarkovChain(S, O, state_to_S)
            Cemp = construct_CM(tp_ped, tp_obj, tp_emp)
            MC, prob = get_states_and_controllers(Cemp, Memp, start_state, good_state, bad_states, K, K_backup, true_env_type="empty")
            # prob = MC.prob_TL(formula)
            points_emp.append(prob)
            tp_range_vals.append(tp_emp)
    print("Found probabilities for empty env!")
    return points_emp, tp_range_vals

# Plot probability points:
def plot_probabilities(points, tpped_vals, true_env, vmax, rand =True):
    fig, ax = plt.subplots()
    ax.set_title(true_env)
    plt.rcParams['text.usetex'] = True
    ax.set_ylabel(r'$\mathbb{P}$')
    plt.plot(tpped_vals, points, 'b*')
    lb = min(tpped_vals)
    ub = max(tpped_vals)
    if rand:
        plt.savefig("saved_plots/points_"+true_env+"_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"_N"+str(Ncar)+"rand.png")
    else:
        plt.savefig("saved_plots/points_"+true_env+"_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"_N"+str(Ncar)+".png")

# Plot probability points:
def plot_probabilities_bounds(points, tpped_vals, true_env, vmax, Ncar, ubounds, lbounds, rand =True):
    fig, ax = plt.subplots()
    ax.set_title(true_env)
    plt.rcParams['text.usetex'] = True
    ax.set_ylabel(r'$\mathbb{P}$')
    plt.plot(tpped_vals, points, 'b*')
    ub_m, ub_c = ubounds
    lb_m, lb_c = lbounds
    y_ub = ub_m*np.array(tpped_vals) + ub_c
    y_lb = lb_m*np.array(tpped_vals) + lb_c
    plt.plot(tpped_vals, y_ub, 'r')
    plt.plot(tpped_vals, y_lb, 'k')

    lb = min(tpped_vals)
    ub = max(tpped_vals)
    if rand:
        plt.savefig("saved_plots/bounded_points_"+true_env+"_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"_N"+str(Ncar)+"rand.png")
    else:
        plt.savefig("saved_plots/bounded_points_"+true_env+"_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"_N"+str(Ncar)+".png")

def save_result(points_ped, tpped_vals, true_env, vmax, Ncar, rand=True):
    lb = min(tpped_vals)
    ub = max(tpped_vals)
    if rand:
        fn = "results/points_"+true_env+"_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"_N"+str(Ncar)+"rand.pkl"
    else:
        fn = "results/points_"+true_env+"_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"_N"+str(Ncar)+".pkl"
    with open(fn, "wb") as f:
        pkl.dump([points_ped, tpped_vals], f)
    f.close()
    return fn

def load_result(fn):
    with open(fn, "rb") as f:
        points_ped, tpped_vals = pkl.load(f)
    f.close()
    return points_ped, tpped_vals

def find_min_max_probs(result_tuple):
    max_probs = dict()
    min_probs = dict()
    for r in result_tuple:
        tpped, prob = r
        if tpped in max_probs.keys():
            if max_probs[tpped] < prob:
                max_probs[tpped] = prob
        else:
            max_probs[tpped] = prob
        if tpped in min_probs.keys():
            if min_probs[tpped] > prob:
                min_probs[tpped] = prob
        else:
            min_probs[tpped] = prob
    return max_probs, min_probs

def bound_probs_obj(max_probs, min_probs):
    # Picking the two largest max_probs:
    sorted_max = sorted(max_probs.items(), key=lambda kv: kv[1])
    sorted_max = list(reversed(sorted_max))
    sorted_max = collections.OrderedDict(sorted_max)

    sorted_min = sorted(min_probs.items(), key=lambda kv: kv[1])
    sorted_min = collections.OrderedDict(sorted_min)

    # Getting the eyeballed lines
    tp_max1, pmax1 = list(sorted_max.items())[-1]
    tp_max2, pmax2 = list(sorted_max.items())[0]

    first_min_set = False
    for tp, prob in min_probs.items():
        if tp > 0.8 and not first_min_set:
            tp_min1 = tp
            pmin1 = prob
            first_min_set = True
            continue
        if first_min_set:
            tp_min2 = tp
            pmin2 = prob
            break

    # Finding line:
    ub_m = (pmax1 - pmax2)/(tp_max1 - tp_max2)
    ub_c = pmax2 - ub_m*tp_max2
    lb_m = (pmin1 - pmin2)/(tp_min1 - tp_min2)
    lb_c = pmin2 - lb_m*tp_min2
    # Picking the two smallest min_probs:
    try:
        assert ub_m + ub_c <= 1 + 1e-4
    except:
        pdb.set_trace()
    ub = [ub_m, ub_c]
    lb = [lb_m, lb_c]
    return ub, lb

def bound_probs_emp(max_probs, min_probs):
    # Picking the two largest max_probs:
    sorted_max = sorted(max_probs.items(), key=lambda kv: kv[1])
    sorted_max = list(reversed(sorted_max))
    sorted_max = collections.OrderedDict(sorted_max)

    sorted_min = sorted(min_probs.items(), key=lambda kv: kv[1])
    sorted_min = collections.OrderedDict(sorted_min)

    # Getting the eyeballed lines
    for tp, prob in max_probs.items():
        if tp >= 0.9:
            tp_max1 = tp
            pmax1 = prob
            break
    tp_max2 = 1
    pmax2 = 1
    tp_min1, pmin1 = list(sorted_min.items())[0]
    tp_min2, pmin2 = list(sorted_min.items())[-1]
    # Finding line:
    ub_m = (pmax1 - pmax2)/(tp_max1 - tp_max2)
    ub_c = pmax2 - ub_m*tp_max2
    lb_m = (pmin1 - pmin2)/(tp_min1 - tp_min2)
    lb_c = pmin2 - lb_m*tp_min2
    # Picking the two smallest min_probs:

    try:
        assert ub_m + ub_c <= 1 + 1e-4
    except:
        pdb.set_trace()
    ub = [ub_m, ub_c]
    lb = [lb_m, lb_c]
    return ub, lb

def bound_probs_ped(max_probs, min_probs):
    # Picking the two largest max_probs:
    sorted_max = sorted(max_probs.items(), key=lambda kv: kv[1])
    sorted_max = list(reversed(sorted_max))
    sorted_max = collections.OrderedDict(sorted_max)

    sorted_min = sorted(min_probs.items(), key=lambda kv: kv[1])
    sorted_min = collections.OrderedDict(sorted_min)

    # Getting the eyeballed lines
    for tp, prob in max_probs.items():
        if tp > 0.8:
            tp_max1 = tp
            pmax1 = prob
            break
    tp_max2, pmax2 = list(sorted_max.items())[0]

    for tp, prob in min_probs.items():
        if tp > 0.8:
            tp_min1 = tp
            pmin1 = prob
            break
    tp_min2, pmin2 = list(sorted_min.items())[-1]

    # Finding line:
    ub_m = (pmax1 - pmax2)/(tp_max1 - tp_max2)
    ub_c = pmax2 - ub_m*tp_max2
    lb_m = (pmin1 - pmin2)/(tp_min1 - tp_min2)
    lb_c = pmin2 - lb_m*tp_min2
    # Picking the two smallest min_probs:
    try:
        assert ub_m + ub_c <= 1 + 1e-4
        assert lb_c + ub_c <= -1e-4
    except:
        pdb.set_trace()
    ub = [ub_m, ub_c]
    lb = [lb_m, lb_c]
    return ub, lb

def derive_prob_bounds(fn, true_env):
    points_ped, tpped_vals = load_result(fn)
    lb_ped = min(tpped_vals)
    ub_ped = max(tpped_vals)
    result_tuple = [[tpped_vals[i],points_ped[i]] for i in range(len(tpped_vals))]
    # Finding the max and min probabilities for each true positive value:
    max_probs, min_probs = find_min_max_probs(result_tuple)
    if true_env == "ped":
        ub, lb = bound_probs_ped(max_probs, min_probs)
    elif true_env == "obj":
        ub, lb = bound_probs_obj(max_probs, min_probs)
    else:
        ub, lb = bound_probs_emp(max_probs, min_probs)
    return ub, lb, points_ped, tpped_vals


if __name__=='__main__':
    vmax = 2
    Ncar = 6
    Vlow = 0
    Vhigh = vmax
    recompute = False
    true_env = "ped"

    if recompute:
        xped, bad_states_ped, good_state_ped, formula_ped = new_initialize_ped(vmax, Ncar, true_env)
        if true_env == "ped":
            points, tp_vals = gen_points(Ncar, Vlow, Vhigh, xped, bad_states_ped, good_state_ped, formula_ped, vmax)
        elif true_env == "obj":
            points, tp_vals = gen_points_obj(Ncar, Vlow, Vhigh, xped, bad_states_ped, good_state_ped, formula_ped, vmax)
        elif true_env == "empty":
            points, tp_vals = gen_points_emp(Ncar, Vlow, Vhigh, xped, bad_states_ped, good_state_ped, formula_ped, vmax)
        # Save results and plot:
        plot_probabilities(points, tp_vals, true_env, vmax)
        fn = save_result(points, tp_vals, true_env, vmax, Ncar)
    # Derive bounds and plot probability bounds:
    else:
        fn = "results/points_"+true_env+"_lb0.6_ub0.999_vmax2_N6rand.pkl"

    ubounds, lbounds, points, tp_vals = derive_prob_bounds(fn, true_env)
    plot_probabilities_bounds(points, tp_vals, true_env, vmax, Ncar, ubounds, lbounds, rand =True)
