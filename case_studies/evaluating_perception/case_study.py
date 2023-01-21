# Import libraries
from pacti.iocontract.utils import getVarlist
from PIL import Image
from pacti.terms.polyhedra.loaders import readContract, writeContract
import pdb
from utils import *
import random
import pickle as pkl
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

    formula = "P=?[" + phi +"]" # Don't reach bad states and eventually reach good states
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
def system_states_example_ped(Ncar, Vlow, Vhigh):
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
    for st in list(good_state):
        formula2 = 'P=?[F(\"'+st+'\")]'
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
    points_obj = [] # Satisfaction probabilities for true env as ped
    points_emp = [] # Satisfaction probabilities for true env as ped

    vcar = 1 # Initial speed at starting point
    start_state = "S"+str(state_f(1,vcar))
    S, state_to_S, K_backup = system_states_example_ped(Ncar, Vlow, Vhigh)
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

def gen_points_other_env():
    for tp_obj in tp_range:
        tp_ped = 0.8
        tp_emp = 0.8
        C = construct_CM(tp_ped, tp_obj, tp_emp)
        prob = get_states_and_controllers(C, M, start_state, good_state, bad_states, K, K_backup, true_env_type="obj")
        points_obj.append(prob)
    print("Found probabilities for obj env!")

    for tp_emp in tp_range:
        tp_obj = 0.8
        tp_ped = 0.8
        C = construct_CM(tp_ped, tp_obj, tp_emp)
        prob = get_states_and_controllers(C, M, start_state, good_state, bad_states, K, K_backup, true_env_type="empty")
        points_emp.append(prob)
    return points_obj, points_emp

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
        plt.savefig("saved_plots/points_ped_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"rand.png")
    else:
        plt.savefig("saved_plots/points_ped_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+".png")

def save_result(points_ped, tpped_vals, true_env, vmax, rand=True):
    lb = min(tpped_vals)
    ub = max(tpped_vals)
    if rand:
        fn = "results/points_ped_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+"rand.pkl"
    else:
        fn = "results/points_ped_lb"+str(lb)+"_ub"+str(ub)+"_vmax"+str(vmax)+".pkl"
    with open(fn, "wb") as f:
        pkl.dump([points_ped, tpped_vals], f)
    f.close()

def load_result(fn):
    with open(fn, "rb") as f:
        points_ped, tpped_vals = pkl.load(f)
    f.close()
    return points_ped, tpped_vals
    
def find_min_max_probs(result_dict):
    max_probs = dict()
    min_probs = dict()
    for tpped, prob in result_dict.items():
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

def derive_prob_bounds(fn):
    points_ped, tpped_vals = load_result(fn)
    lb_ped = min(tpped_vals)
    ub_ped = max(tpped_vals)
    result_dict = {tpped_vals[i]:points_ped[i] for i in range(len(tpped_vals))}
    # Finding the max and min probabilities for each true positive value:
    max_probs, min_probs = find_min_max_probs(result_dict)


if __name__=='__main__':
    MAX_V = 1
    vmax = 5
    Ncar = 15
    Vlow = 0
    Vhigh = vmax
    xped, bad_states_ped, good_state_ped, formula_ped = new_initialize_ped(vmax, Ncar, "ped")
    points_ped, tpped_vals = gen_points(Ncar, Vlow, Vhigh, xped, bad_states_ped, good_state_ped, formula_ped, vmax)

    # Save results and plot:
    plot_probabilities(points_ped, tpped_vals, "ped", vmax)
    save_result(points_ped, tpped_vals, "ped", vmax)
