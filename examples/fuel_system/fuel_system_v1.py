import numpy as np
from pacti.contracts import PolyhedralIoContract
from utils import show_contract


'''Some basic atmospheric model'''
base_alt = [0, 11, 20, 32, 47, 51, 71]
lapse_rate = [-6.5, 0, 1, 2.8,0,-2.8,-2]
base_temp = [288.15,0,0,0,0,0,0]    
base_pressure = [101325,0,0,0,0,0,0]

def init_atm_model():
    for i in range(6):
        base_temp[i+1] = base_temp[i] + (base_alt[i+1] - base_alt[i])*lapse_rate[i]
        base_pressure[i+1] = pow((1 + (base_alt[i+1] - base_alt[i])*lapse_rate[i] / base_temp[i]), 9.8/(lapse_rate[i]*6356.766))

def air_density(T:float,p:float):
    return p/ (287 * T)

'''Fuel flow model'''
def engine_fuel_flow(thrust:float):
    return (0.7*thrust / 3600)


'''Values to be revised'''
params = {
    'C_f' : 0.2, # kJ/(kg*K) 
    'm_dot_in': 8.0, # (kg/s)   
    'm_dot_e': 4.0, # (kg/s) for roughly 20 tons of thrust 
    'm_dot_out': 4.0, # (kg/s) must be equal to m_dot_in - m_dot_e
    'q_leak_min' : 1000, # (W) 
    'q_leak_max' : 2000, # (W)
    'epsilon_tank' : 5, # (W)
    'T_e_min' : 300.0, # (K)
    'T_e_max' : 330.0, # (K)
    'eta_ep' : 0.8, # pump efficiency
    'Delta_P_ep' : 6900000 , # pascal
    'rho_f' : 800.0, # (kg/m^3) 
    'epsilon_ep_t' : 10.0, # (K)
    'epsilon_ep_w' : 100.0, # (W)
    'epsilon_hl' : 10.0, # (K)
    'k_e' : 5000.0, 
    'epsilon_e':1000, # (W)
    'epsilon_s':5.0, # (K)
    'eta_x' : 0.6, 
    'm_dot_s':4.0, # (kg/s) must be equal to m_dot_in - m_dot_e
    'm_dot_a' : 2.0,
    'C_a' : 1.0, # kJ/(kg*K)
    'eta_g':0.9, 
    'w_g' : 200000,
    'epsilon_g' : 20.0,
    'w_nom' : 80000, # (W)
    'eta_l':0.9, 
    'epsilon_l_w' : 1000, # (W)
    'epsilon_l_h' : 20,
    'f_e_min' : 5100.0, # ~3600/0.7
    'f_e_max' : 5200.0,
    'T_a_min' : 220, # (K)
    'T_a_max' : 240 # (K)
}

'''
    We are going to model a fuel tank 
    as a component that accepts fuel requests
    and accepts fule returns. Essentially, the 
    fuel tank is a passive object. 
    In addition, the fuel tank may leak some 
    heat through its walls. epsilon_tank 
    takes care of unmodelled effects.
'''
def fuel_tank(epsilon_tank:float,m_dot_in:float,m_dot_out:float,c_f:float,):
    ft = PolyhedralIoContract.from_strings(
        input_vars=["T_out","q_w"],
        output_vars=["T_in"],
        assumptions=[],
        guarantees=[f"-{epsilon_tank} <= {m_dot_out*c_f} * T_out - {m_dot_in*c_f}*T_in - q_w <= {epsilon_tank}"]
    )
    return ft

def fuel_tank_requirement():
    ft = PolyhedralIoContract.from_strings(
        input_vars=["T_in"],
        output_vars=[],
        assumptions=[" 270 <= T_in <= 300"],
        guarantees=[]
    )
    return ft

def engine(T_e_min:float,T_e_max:float,m_dot_e:float,k_e:float,epsilon_e:float,f_e_min:float,f_e_max:float):
    e = PolyhedralIoContract.from_strings(
        input_vars=["T_e"],
        output_vars=["hh_e","f_e"],
        assumptions=[
            f"{T_e_min} <= T_e <= {T_e_max}"
        ],
        guarantees=[
            f"{k_e*m_dot_e - epsilon_e} <= hh_e <= {k_e*m_dot_e + epsilon_e}", 
            f"{f_e_min * m_dot_e} <= f_e <= {f_e_max * m_dot_e}"]
    )
    return e

def ghost_engine(T_e_min:float,T_e_max:float,m_dot_e:float,k_e:float,epsilon_e:float,f_e_min:float,f_e_max:float):
    e = PolyhedralIoContract.from_strings(
        input_vars=["T_e"],
        output_vars=["h_e"],
        assumptions=[
            # f"{T_e_min} <= T_e <= {T_e_max}"
        ],
        guarantees=[
            f"{k_e*m_dot_e - epsilon_e} <= h_e <= {k_e*m_dot_e + epsilon_e}", 
        ]
    )
    return e

def electric_pump(m_dot_in:float,eta_ep:float,Delta_P_ep:float,rho_f:float,C_f:float,epsilon_ep_w:float,epsilon_ep_t:float):
    w_ep_min = m_dot_in * Delta_P_ep / (rho_f*eta_ep) - epsilon_ep_w
    w_ep_max = w_ep_min + 2*epsilon_ep_w
    dt_min = (1-eta_ep)*Delta_P_ep/(C_f*rho_f*eta_ep) - epsilon_ep_t
    dt_max = dt_min + 2*epsilon_ep_t
    ep = PolyhedralIoContract.from_strings(
        input_vars=["T_in"],
        output_vars=["T_ep","w_ep"],
        assumptions=[],
        guarantees=[f"{w_ep_min} <= w_ep <= {w_ep_max}",f"T_in + {dt_min} <= T_ep <= T_in + {dt_max}"]
    )
    return ep

def heat_load(m_dot_in:float,C_f:float,epsilon_hl:float):
    c = 1.0 / (C_f * m_dot_in)
    hl = PolyhedralIoContract.from_strings(
        input_vars=["T_ep","h_g","h_l","h_e"],
        output_vars=["T_hl"],
        assumptions=[],
        guarantees=[f"T_ep + {c}*(h_g + h_l + h_e) - {epsilon_hl} <= T_hl <= T_ep + {c}*(h_g + h_l + h_e) + {epsilon_hl}"]
    )
    return hl

def fuel_splitter(epsilon_s:float):
    fs = PolyhedralIoContract.from_strings(
        input_vars=["T_hl"],
        output_vars=["T_e","T_s"],
        assumptions=[],
        guarantees=[f"T_hl - {epsilon_s} <= T_s <= T_hl + {epsilon_s}",f"T_hl - {epsilon_s} <= T_e <= T_hl + {epsilon_s}"]
    )
    return fs

def fuel_air_heat_exchanger(eta_x:float,m_dot_s:float,C_f:float,m_dot_a:float,C_a:float,epsilon_x:float,T_a_min:float,T_a_max:float):
    c = eta_x*m_dot_a*C_a / (m_dot_s*C_f)
    x = PolyhedralIoContract.from_strings(
        input_vars=["T_s","T_a"],
        output_vars=["T_out"],
        assumptions=[
            f"{T_a_min} <= T_a <= {T_a_max}"
        ],
        guarantees=[f"T_s + {c}*(T_a - T_s) - {epsilon_x} <= T_out <= T_s +{c}*(T_a-T_s) + {epsilon_x}"]
    )
    return x

def generator(eta_g:float,w_g:float,epsilon_g:float):
    c = 1 - eta_g 
    g = PolyhedralIoContract.from_strings(
        input_vars=["w_ep","w_l"],
        output_vars=["h_g"],
        assumptions=[f"0 <= w_ep + w_l <= {w_g}"],
        guarantees=[f"{c}*(w_ep + w_l) - {epsilon_g} <= h_g <= {c}*(w_ep + w_l) + {epsilon_g}"]
    )
    return g
    
def load(eta_l:float,epsilon_l_w:float,epsilon_l_h:float):
    c = 1 - eta_l
    l = PolyhedralIoContract.from_strings(
        input_vars=["w_nom"],
        output_vars=["h_l","w_l"],
        assumptions=[],
        guarantees=[f"w_nom - {epsilon_l_w} <= w_l <= w_nom + {epsilon_l_w}", f"{c}*w_l - {epsilon_l_h} <= h_l <= {c}*w_l + {epsilon_l_h}"]
        
    )
    return l

def fixed_fuel_flow_rate(params:dict) :
    ft = fuel_tank(params['epsilon_tank'],params['m_dot_in'],params['m_dot_out'],params['C_f'])
    ge = ghost_engine(params['T_e_min'],params['T_e_max'],params['m_dot_e'],params['k_e'],params['epsilon_e'],params['f_e_min'],params['f_e_max'])
    e = engine(params['T_e_min'],params['T_e_max'],params['m_dot_e'],params['k_e'],params['epsilon_e'],params['f_e_min'],params['f_e_max'])
    ep = electric_pump(params['m_dot_in'],params['eta_ep'],params['Delta_P_ep'],params['rho_f'],params['C_f'],params['epsilon_ep_w'],params['epsilon_ep_t'])
    el = heat_load(params['m_dot_in'],params['C_f'],params['epsilon_hl'])
    fs = fuel_splitter(params['epsilon_s'])
    x = fuel_air_heat_exchanger(params['eta_x'],params['m_dot_s'],params['C_f'],params['m_dot_a'],params['C_a'],params['epsilon_s'],params['T_a_min'],params['T_a_max'])
    g = generator(params['eta_g'],params['w_g'],params['epsilon_g'])
    l = load(params['eta_l'],params['epsilon_l_w'],params['epsilon_l_h'])
    
    # loop: HeatLoad, FuelSplitter, Engine
    # loop: Electric Pump, Electric Generator, Heat Load, (Electric Load?)
    # loop: Fuel-Air Heat Exchanger, Fuel Tank, Electric Pump, Heat Load, Fuel Splitter
    
    s1 = ft.compose(ep)
    s2 = s1.compose(g)
    s3 = s2.compose(l)
    s4 = s3.compose(el)
    s5 = s4.compose(fs)
    s6 = s5.compose(x)
    print(f"s6={show_contract(s6)}")
    s7 = s6.compose(ge)
    s = s7.compose(e)
    return s

def compute_envelope():
    # thrust levels to fuel flow
    m_dot_e_v = map(engine_fuel_flow, [5000, 10000, 15000, 20000])
    tair_v = [220, 230, 240, 250, 270, 280]
    # need to sweep over m_dot_in and m_dot_a
    m_dot_in_v = np.linspace(2,10,num=20)
    m_dot_a_v = np.linspace(2,10,num=20)
    for m_dot_e in m_dot_e_v:
        for m_dot_in in m_dot_in_v:
            for m_dot_a in m_dot_a_v:
                if (m_dot_in > m_dot_e):
                    compute_one_envelope(m_dot_e, m_dot_in, m_dot_a)

def compute_one_envelope(m_dot_e: float, m_dot_in: float, m_dot_a: float):
    params['m_dot_e'] = m_dot_e
    params['m_dot_in'] = m_dot_in
    params['m_dot_out'] = m_dot_in - m_dot_e
    params['m_dot_s'] = m_dot_in - m_dot_e
    params['m_dot_a'] = m_dot_a
    fs = fixed_fuel_flow_rate(params)
    print(f"fs={show_contract(fs)}")
    
if __name__ == "__main__":
    compute_envelope()
                        
                        
                        
    
    
    