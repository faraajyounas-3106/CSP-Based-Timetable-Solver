

import random
from collections import deque
from metrics import Metrics

def backtrack(csp, var_heuristic=None, val_heuristic=None, metrics=None):
   

    if metrics is None:
        metrics = Metrics()

    if var_heuristic is None:
        from heuristics import select_unassigned_variable_no_heuristic
        var_heuristic = select_unassigned_variable_no_heuristic

    if val_heuristic is None:
        from heuristics import order_domain_values_default
        val_heuristic = order_domain_values_default

    metrics.start()

    result = _backtrack_recursive(
        csp,
        {},  # start with empty assignment
        var_heuristic,
        val_heuristic,
        metrics
    )

    metrics.stop()

    return result, metrics

    
def _backtrack_recursive(csp, assignment, var_heuristic, val_heuristic, metrics):
    if csp.is_complete(assignment):
        return assignment

    var = var_heuristic(csp, assignment)
    if var is None:
        return None

    for value in val_heuristic(csp, var, assignment, metrics):
        metrics.constraint_checks += len([
            c for c in csp.constraints[var] if c.var_j in assignment
        ])
        if csp.is_consistent(var, value, assignment, metrics):
            assignment[var] = value
            metrics.record_assign(var.name, value)

            result = _backtrack_recursive(csp, assignment, var_heuristic, val_heuristic, metrics)
            if result is not None:
                return result

            del assignment[var]
            metrics.record_backtrack(var.name)

    return None

def forward_checking(csp, var_heuristic=None, val_heuristic=None, metrics=None):
   

    if metrics is None:
        metrics = Metrics()

    if var_heuristic is None:
        from heuristics import select_unassigned_variable_no_heuristic
        var_heuristic = select_unassigned_variable_no_heuristic

    if val_heuristic is None:
        from heuristics import order_domain_values_default
        val_heuristic = order_domain_values_default

    metrics.start()

    result = _fc_recursive(
        csp,
        {},  
        var_heuristic,
        val_heuristic,
        metrics
    )

    metrics.stop()
    return result, metrics


def _fc_recursive(csp, assignment, var_heuristic, val_heuristic, metrics):
    if csp.is_complete(assignment):
        return assignment

    var = var_heuristic(csp, assignment)
    if var is None:
        return None

    for value in val_heuristic(csp, var, assignment, metrics):
        metrics.constraint_checks += len([
            c for c in csp.constraints[var] if c.var_j in assignment
        ])
        if csp.is_consistent(var, value, assignment, metrics):
            assignment[var] = value
            metrics.record_assign(var.name, value)

            for neighbour in csp.get_neighbours(var):
                if neighbour not in assignment:
                    csp.domains[neighbour].push_pruning_level(reason=var.name)

            failure = False
            for c in csp.constraints[var]:
                neighbour = c.var_j
                if neighbour in assignment:
                    continue
                for nval in list(csp.domains[neighbour].values):
                    metrics.constraint_checks += 1
                    if not c.satisfied(value, nval):
                        csp.domains[neighbour].prune(nval)
                        metrics.record_prune(neighbour.name, nval)
                if csp.domains[neighbour].is_empty():
                    failure = True
                    break

            if not failure:
                result = _fc_recursive(csp, assignment, var_heuristic, val_heuristic, metrics)
                if result is not None:
                    return result

            del assignment[var]
            metrics.record_backtrack(var.name)
            for neighbour in csp.get_neighbours(var):
                if neighbour not in assignment:
                    csp.domains[neighbour].restore()

    return None

def mac(csp, var_heuristic=None, val_heuristic=None, metrics=None):

    if metrics is None:
        metrics = Metrics()

    if var_heuristic is None:
        from heuristics import select_unassigned_variable_no_heuristic
        var_heuristic = select_unassigned_variable_no_heuristic

    if val_heuristic is None:
        from heuristics import order_domain_values_default
        val_heuristic = order_domain_values_default

    metrics.start()

    result = _mac_recursive(
        csp,
        {},
        var_heuristic,
        val_heuristic,
        metrics
    )

    metrics.stop()
    return result, metrics

def _mac_recursive(csp, assignment, var_heuristic, val_heuristic, metrics):
    if csp.is_complete(assignment):
        return assignment

    var = var_heuristic(csp, assignment)
    if var is None:
        return None

    for value in val_heuristic(csp, var, assignment, metrics):
        metrics.constraint_checks += len([
            c for c in csp.constraints[var] if c.var_j in assignment
        ])
        if csp.is_consistent(var, value, assignment, metrics):
            assignment[var] = value
            metrics.record_assign(var.name, value)

            saved_domains = csp.save_domains()

            csp.domains[var] = _singleton_domain(value)

            ok, pruned = _ac3(csp, assignment, var, metrics)

            if ok:
                result = _mac_recursive(csp, assignment, var_heuristic, val_heuristic, metrics)
                if result is not None:
                    return result

            csp.restore_domains(saved_domains)
            del assignment[var]
            metrics.record_backtrack(var.name)

    return None


def _singleton_domain(value):
    from csp import Domain
    return Domain([value])


def _ac3(csp, assignment, assigned_var, metrics):
    
    queue = deque()
    unassigned_set = set(csp.get_unassigned(assignment))

    for c in csp.constraints[assigned_var]:
        neighbour = c.var_j
        if neighbour in unassigned_set:

            for rc in csp.constraints[neighbour]:
                if rc.var_j == assigned_var:
                    queue.append((neighbour, assigned_var, rc))
                    break

    pruned = []
    queued = set((xi, xj) for xi, xj, _ in queue)

    while queue:
        xi, xj, constraint = queue.popleft()
        queued.discard((xi, xj))

        revised, removed = _revise(csp, xi, xj, constraint, metrics)
        if revised:
            if csp.domains[xi].is_empty():
                return False, pruned
            pruned.extend([(xi, v) for v in removed])

            for rc in csp.constraints[xi]:
                xk = rc.var_j
                if xk != xj and xk in unassigned_set and (xk, xi) not in queued:

                    for rrc in csp.constraints[xk]:
                        if rrc.var_j == xi:
                            queue.append((xk, xi, rrc))
                            queued.add((xk, xi))
                            break

    return True, pruned

def _revise(csp, xi, xj, constraint, metrics):  
    revised = False
    removed = []
    for val_i in list(csp.domains[xi].values):

        support_found = False
        for val_j in csp.domains[xj].values:
            metrics.constraint_checks += 1
            if constraint.satisfied(val_i, val_j):
                support_found = True
                break
        if not support_found:
            csp.domains[xi].prune(val_i)
            removed.append(val_i)
            revised = True
    return revised, removed


def min_conflicts(csp, max_steps=10000, metrics=None):

    if metrics is None:
        metrics = Metrics()

    metrics.start()

    assignment = {}
    for var in csp.variables:
        values = csp.domains[var].values
        if values:
            assignment[var] = random.choice(values)
        else:
            metrics.stop()
            return None, metrics

    metrics.assignments = len(assignment)

    for step in range(max_steps):
        conflicted = csp.conflicted_variables(assignment)
        if not conflicted:
            metrics.stop()
            return assignment, metrics

        var = random.choice(conflicted)

        best_value = None
        best_count = float('inf')
        for value in csp.domains[var].values:

            old_val = assignment[var]
            assignment[var] = value
            metrics.constraint_checks += len(csp.constraints[var])
            count = csp.count_conflicts(var, value, assignment)
            assignment[var] = old_val
            if count < best_count:
                best_count = count
                best_value = value

        if best_value is not None:
            assignment[var] = best_value
            metrics.record_assign(var.name, best_value)

    metrics.stop()
    return None, metrics

ALGORITHM_MAP = {
    "backtrack":       backtrack,
    "forward_checking": forward_checking,
    "mac":             mac,
    "min_conflicts":   min_conflicts,
}

ALGORITHM_LABELS = {
    "backtrack":        "Backtracking Search",
    "forward_checking": "Backtracking with Forward Checking",
    "mac":              "Backtracking with MAC (AC-3)",
    "min_conflicts":    "Min-Conflicts Local Search",
}


def get_algorithm(name):
    if name not in ALGORITHM_MAP:
        raise ValueError(f"Unknown algorithm '{name}'. Choose from: {list(ALGORITHM_MAP)}")
    return ALGORITHM_MAP[name]
