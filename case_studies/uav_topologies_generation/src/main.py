import random
from datetime import datetime

from case_studies.uav_topologies_generation.src.contracts_utils.union import ContractsUnions
from case_studies.uav_topologies_generation.src.grammar.grammar import Grammar
from case_studies.uav_topologies_generation.src.grammar.grid import GridBuilder
from case_studies.uav_topologies_generation.src.shared import DirectionsAssignment, SymbolType
from case_studies.uav_topologies_generation.src.shared.paths import rules_path
from case_studies.uav_topologies_generation.src.tools.refinement_checking import rule_matching
from case_studies.uav_topologies_generation.src.tools.simple_rule_search import set_rules_search

grid_half_size = 2
max_num_wings = 2
max_num_rotors = 2

if __name__ == "__main__":

    grammar = Grammar.from_json(rules_json_path=rules_path)

    directions_assignment = DirectionsAssignment()

    directions_assignment.set_direction_assignment(grammar.get_directions_assignment())

    print(directions_assignment.data)

    rule_contracts: dict[SymbolType, list[ContractsUnions]] = grammar.to_contracts()

    grid = GridBuilder.generate(half_size=grid_half_size)

    step = 0

    while len(grid.points_to_visit) > 0:
        print(f"STEP {step}")

        print(f"{len(grid.points_to_visit)} POINTS LEFT:\t{grid.points_to_visit}")
        # print(grid.points_to_visit)
        grid.update_current_point()

        current_state = grid.local_state()

        if step > 0 and not current_state.has_non_empty_symbols():
            continue

        current_state.plot.show()
        current_state.plot.savefig(f"step_{step}_point_{current_state.ego}")

        forbidden_symbols = set()

        if grid.n_wings == max_num_wings and grid.n_rotors == max_num_rotors:
            break

        if grid.n_wings >= max_num_wings:
            forbidden_symbols.add(SymbolType.WING)

        if grid.n_rotors >= max_num_rotors:
            forbidden_symbols.add(SymbolType.ROTOR)

        rules_allowed_contracts = list({k: v for k, v in rule_contracts.items() if k not in forbidden_symbols}.values())
        rules_allowed_contracts = [item for sublist in rules_allowed_contracts for item in sublist]

        if step > 0:
            rules_allowed_contracts = list(filter(lambda x: x.name != "r0", rules_allowed_contracts))

        rule_names_allowed = [r.name for r in rules_allowed_contracts]

        # """Simple rule search"""
        # start = datetime.now()
        rules_compatible = set_rules_search(current_state, grammar, rule_names_allowed)
        # end = datetime.now()
        # time_search = (end - start).total_seconds() * 10 ** 6

        """Contract-Based Refinement Search"""
        start = datetime.now()
        if step == 0:
            rules_compatible_contracts = [grammar.rules["r0"]]
        else:
            rules_compatible_contracts = rule_matching(current_state.contract, rules_allowed_contracts)
        end = datetime.now()
        time_contracts = (end - start).total_seconds() * 10 ** 6
        #
        # print(time_search)
        # print(time_contracts)
        #
        r_id_from_search = [r.name for r in rules_compatible]
        r_id_from_contracts = [rc.name for rc in rules_compatible_contracts]

        r_id_from_search_str = "-".join(sorted(r_id_from_search))
        r_id_from_contracts_str = "-".join(sorted(r_id_from_contracts))

        print(f"R_S: {r_id_from_search_str}")
        print(f"R_C: {r_id_from_contracts_str}")

        print(len(rules_compatible))
        print(len(rules_compatible_contracts))
        if len(rules_compatible) != len(rules_compatible_contracts):
            print(step)
            raise Exception

        if len(rules_compatible) == 0:
            current_state.plot.show()
            continue

        for rule in rules_compatible:
            print(grammar.rules[rule.name].production.symbol_type)
        if len(rules_compatible) > 1:
            remove_rule = None
            for rule in rules_compatible:
                if grammar.rules[rule.name].production.symbol_type == SymbolType.EMPTY:
                    remove_rule = rule
                    break
            if remove_rule is not None:
                rules_compatible.remove(remove_rule)
        chosen_rule = random.choice(list(rules_compatible))

        grid.apply_rule(grammar.rules[chosen_rule.name])

        grid.plot_with_edges.show()
        step += 1

    grid.plot_with_edges.savefig("before.pdf")
    grid.cleanup()
    grid.plot_with_edges.savefig("after.pdf")
    pass
