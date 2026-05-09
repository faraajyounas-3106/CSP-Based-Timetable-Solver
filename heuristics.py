
def select_unassigned_variable_no_heuristic(csp, assignment):
    
    for v in csp.variables:
        if v not in assignment:
            return v
    return None


def select_unassigned_variable_mrv(csp, assignment):
    
    unassigned = csp.get_unassigned(assignment)
    if not unassigned:
        return None
    return min(unassigned, key=lambda v: len(csp.domains[v]))


def select_unassigned_variable_mrv_degree(csp, assignment):
    
    unassigned = csp.get_unassigned(assignment)
    if not unassigned:
        return None

    def mrv_degree_key(v):
        mrv_score = len(csp.domains[v])
        degree_score = sum(
            1 for n in csp.get_neighbours(v) if n not in assignment
        )
        return (mrv_score, -degree_score)

    return min(unassigned, key=mrv_degree_key)


def order_domain_values_default(csp, var, assignment, metrics=None):
    
    return csp.domains[var].values


def order_domain_values_lcv(csp, var, assignment, metrics=None):
    values = csp.domains[var].values

    def lcv_score(value):
        score = 0
        for neighbour in csp.get_neighbours(var):
            if neighbour in assignment:
                continue
            for nval in csp.domains[neighbour].values:
                if metrics:
                    metrics.constraint_checks += 1

                consistent = True
                for c in csp.constraints_between(var, neighbour):
                    if not c.satisfied(value, nval):
                        consistent = False
                        break
                if consistent:
                    score += 1
        return score

    return sorted(values, key=lcv_score, reverse=True)


def get_var_heuristic(name):
    mapping = {
        "none":       select_unassigned_variable_no_heuristic,
        "mrv":        select_unassigned_variable_mrv,
        "mrv_degree": select_unassigned_variable_mrv_degree,
    }
    if name not in mapping:
        raise ValueError(f"Unknown var heuristic '{name}'. Choose from: {list(mapping)}")
    return mapping[name]


def get_val_heuristic(name):
    mapping = {
        "none": order_domain_values_default,
        "lcv":  order_domain_values_lcv,
    }
    if name not in mapping:
        raise ValueError(f"Unknown val heuristic '{name}'. Choose from: {list(mapping)}")
    return mapping[name]
