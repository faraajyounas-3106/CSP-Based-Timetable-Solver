

from copy import deepcopy


class Variable:

    def __init__(self, name, metadata=None):
        self.name = name
        self.metadata = metadata or {}  

    def __repr__(self):
        return f"Variable({self.name})"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name


class Domain:

    def __init__(self, values):
        self._values = list(values)
        self._pruned = []          

    @property
    def values(self):
        return list(self._values)

    def __len__(self):
        return len(self._values)

    def is_empty(self):
        return len(self._values) == 0

    def push_pruning_level(self, reason=None):
        """Record a restoration checkpoint."""
        self._pruned.append((reason, []))

    def prune(self, value):
        """Remove a value and record it in the current checkpoint."""
        if value in self._values:
            self._values.remove(value)
            if self._pruned:
                self._pruned[-1][1].append(value)
            return True
        return False

    def restore(self):
        if self._pruned:
            _, values = self._pruned.pop()
            self._values.extend(values)

    def contains(self, value):
        return value in self._values

    def copy(self):
        d = Domain(self._values)
        d._pruned = deepcopy(self._pruned)
        return d

    def __repr__(self):
        return f"Domain({self._values})"


class Constraint:
   

    def __init__(self, var_i, var_j, check_fn, name=""):
        self.var_i = var_i
        self.var_j = var_j
        self.check_fn = check_fn
        self.name = name

    def satisfied(self, val_i, val_j):
        """Return True if this constraint is satisfied for the given values."""
        return self.check_fn(val_i, val_j)

    def __repr__(self):
        return f"Constraint({self.name}: {self.var_i.name} ↔ {self.var_j.name})"


class CSP:
  

    def __init__(self, variables, domains, constraints):
       
        self.variables = variables
        self.domains = domains                   

        self.constraints = {v: [] for v in variables}
        for c in constraints:
            self.constraints[c.var_i].append(c)

            reversed_c = Constraint(
                c.var_j, c.var_i,
                lambda vi, vj, _c=c: _c.check_fn(vj, vi),
                name=c.name + "_rev"
            )
            self.constraints[c.var_j].append(reversed_c)

        self._constraint_list = constraints      


    def is_complete(self, assignment):
        """True when every variable has been assigned a value."""
        return len(assignment) == len(self.variables)

    def get_unassigned(self, assignment):
        """Return variables not yet in the assignment."""
        return [v for v in self.variables if v not in assignment]

    def is_consistent(self, var, value, assignment, metrics=None):
        """
        Check all constraints between var=value and already-assigned neighbours.
        Increments constraint_checks in metrics if provided.
        """
        for c in self.constraints[var]:
            if c.var_j in assignment:
                if metrics:
                    metrics.constraint_checks += 1
                if not c.satisfied(value, assignment[c.var_j]):
                    return False
        return True

    def get_neighbours(self, var):
        """Return all variables that share a constraint with var."""
        return [c.var_j for c in self.constraints[var]]

    def constraints_between(self, var_i, var_j):
        """Return all Constraint objects involving both var_i and var_j."""
        return [c for c in self.constraints[var_i] if c.var_j == var_j]


    def save_domains(self):
        """Snapshot current domains (deep copy). Used by MAC."""
        return {v: d.copy() for v, d in self.domains.items()}

    def restore_domains(self, snapshot):
        """Restore domains from a snapshot."""
        self.domains = snapshot

    def count_conflicts(self, var, value, assignment):
        """Count how many constraints are violated if var=value given assignment."""
        count = 0
        for c in self.constraints[var]:
            if c.var_j in assignment and c.var_j != var:
                if not c.satisfied(value, assignment[c.var_j]):
                    count += 1
        return count

    def conflicted_variables(self, assignment):
        """Return list of variables currently involved in at least one conflict."""
        conflicted = []
        for v in self.variables:
            val = assignment.get(v)
            if val is None:
                continue
            for c in self.constraints[v]:
                if c.var_j in assignment:
                    if not c.satisfied(val, assignment[c.var_j]):
                        conflicted.append(v)
                        break
        return conflicted

    def verify_solution(self, assignment):
        """
        Verify a complete assignment.
        Returns (bool, list_of_violations).
        """
        violations = []
        seen = set()
        for c in self._constraint_list:
            key = (c.var_i, c.var_j, c.name.replace("_rev", ""))
            if key in seen:
                continue
            seen.add(key)
            vi = assignment.get(c.var_i)
            vj = assignment.get(c.var_j)
            if vi is not None and vj is not None:
                if not c.satisfied(vi, vj):
                    violations.append(
                        f"VIOLATION: {c.name} between {c.var_i.name} and {c.var_j.name}"
                    )
        return len(violations) == 0, violations
