
import os
import pandas as pd
from csp import Variable, Domain, Constraint, CSP


def load_courses(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df['CourseID'] = df['CourseID'].str.strip()
    df['Instructor'] = df['Instructor'].str.strip()
    df['RoomFeatures'] = df['RoomFeatures'].str.strip()
    return df


def load_rooms(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df['RoomID'] = df['RoomID'].str.strip()
    df['Features'] = df['Features'].str.strip()
    # Parse Features as a set
    df['FeatureSet'] = df['Features'].apply(lambda x: set(f.strip() for f in x.split(';')))
    return df


def load_timeslots(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df['SlotID'] = df['SlotID'].str.strip()
    return df


def load_students(path):

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df['StudentID'] = df['StudentID'].astype(str).str.strip()
    df['EnrolledCourses'] = df['EnrolledCourses'].str.strip()

    course_students = {}
    for _, row in df.iterrows():
        courses = [c.strip() for c in row['EnrolledCourses'].split(';')]
        for c in courses:
            course_students.setdefault(c, set()).add(row['StudentID'])

    conflict_pairs = set()
    course_list = list(course_students.keys())
    for i in range(len(course_list)):
        for j in range(i + 1, len(course_list)):
            ca, cb = course_list[i], course_list[j]
            if course_students[ca] & course_students[cb]:
                conflict_pairs.add(frozenset({ca, cb}))

    return df, course_students, conflict_pairs


def load_availability(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    result = {}
    for _, row in df.iterrows():
        name = row['Instructor'].strip()
        available = set(s.strip() for s in str(row['AvailableSlots']).split(';'))
        preferred = set(s.strip() for s in str(row['PreferredSlots']).split(';'))
        result[name] = {'available': available, 'preferred': preferred}
    return result



def build_timetabling_csp(input_dir):
    
    courses_df  = load_courses(os.path.join(input_dir, 'courses.csv'))
    rooms_df    = load_rooms(os.path.join(input_dir, 'rooms.csv'))
    slots_df    = load_timeslots(os.path.join(input_dir, 'timeslots.csv'))

    availability = {}
    avail_path = os.path.join(input_dir, 'instructor_availability.csv')
    if os.path.exists(avail_path):
        availability = load_availability(avail_path)

    _, course_students, conflict_pairs = load_students(
        os.path.join(input_dir, 'students.csv')
    )

    variables = []
    var_map = {}   

    for _, row in courses_df.iterrows():
        v = Variable(row['CourseID'], metadata={
            'name':        row['CourseName'],
            'instructor':  row['Instructor'],
            'enrollment':  int(row['Enrollment']),
            'duration':    int(row['Duration']),
            'req_feature': row['RoomFeatures'],
        })
        variables.append(v)
        var_map[row['CourseID']] = v


    domains = {}
    for v in variables:
        meta = v.metadata
        valid_pairs = []
        for _, slot in slots_df.iterrows():
            # Unary 1: Course Time Requirements — duration must match slot duration
            if int(slot['Duration']) != meta['duration']:
                continue
            # Unary 2: Instructor Availability
            if meta['instructor'] in availability:
                if slot['SlotID'] not in availability[meta['instructor']]['available']:
                    continue
            # Unary 3: Room Features + Room Capacity
            for _, room in rooms_df.iterrows():
                req = meta['req_feature']
                if req not in room['FeatureSet']:
                    continue
                # Room Capacity: basic capacity check
                if room['Capacity'] < meta['enrollment']:
                    continue
                valid_pairs.append((slot['SlotID'], room['RoomID']))

        domains[v] = Domain(valid_pairs)

    constraints = []

    def make_room_conflict(vi, vj):
        def check(val_i, val_j):
            return not (val_i[0] == val_j[0] and val_i[1] == val_j[1])
        return Constraint(vi, vj, check, name="RoomOccupancy")

    def make_instructor_conflict(vi, vj):
        def check(val_i, val_j):
            return val_i[0] != val_j[0]
        return Constraint(vi, vj, check, name="InstructorConflict")

    def make_student_conflict(vi, vj):
        def check(val_i, val_j):
            return val_i[0] != val_j[0]
        return Constraint(vi, vj, check, name="StudentConflict")

    def make_room_capacity_conflict(vi, vj):

        enroll_j = vj.metadata['enrollment']
        enroll_i = vi.metadata['enrollment']
        # Build room capacity lookup from rooms_df (closure)
        def check(val_i, val_j):
            # If different rooms — no conflict on this constraint
            if val_i[1] != val_j[1]:
                return True

            return True
        return Constraint(vi, vj, check, name="RoomCapacity")

    course_ids = [v.name for v in variables]
    for i in range(len(variables)):
        for j in range(i + 1, len(variables)):
            vi, vj = variables[i], variables[j]
            ci, cj = vi.name, vj.name

            constraints.append(make_room_conflict(vi, vj))

            if vi.metadata['instructor'] == vj.metadata['instructor']:
                constraints.append(make_instructor_conflict(vi, vj))

            if frozenset({ci, cj}) in conflict_pairs:
                constraints.append(make_student_conflict(vi, vj))

    csp = CSP(variables, domains, constraints)

    meta = {
        'courses_df':      courses_df,
        'rooms_df':        rooms_df,
        'slots_df':        slots_df,
        'availability':    availability,
        'course_students': course_students,
        'conflict_pairs':  conflict_pairs,
        'var_map':         var_map,
    }
    return csp, meta



def format_time_range(slot_row):
    """Return human-readable time range like '09:00-09:50'."""
    start = slot_row['StartTime']
    duration = int(slot_row['Duration'])
    h, m = map(int, start.split(':'))
    total_min = h * 60 + m + duration
    end_h, end_m = divmod(total_min, 60)
    return f"{start}-{end_h:02d}:{end_m:02d}"


def print_solution(assignment, csp, meta, algo_label, metrics, algo_name=""):
    """
    Print the full formatted solution output.
    """
    courses_df  = meta['courses_df']
    rooms_df    = meta['rooms_df']
    slots_df    = meta['slots_df']
    n_courses   = len(csp.variables)
    n_scheduled = len(assignment) if assignment else 0

    status = "SOLUTION FOUND" if assignment else "UNSATISFIABLE"

    print()
    print("=" * 58)
    print("UNIVERSITY TIMETABLE SOLUTION")
    print("=" * 58)
    print(f"Algorithm  : {algo_label}")
    print(f"Status     : {status}")
    print("=" * 58)

    if not assignment:
        print("No solution could be found.")
        metrics.print_report(n_courses, n_scheduled)
        return

    print()
    print("COURSE SCHEDULE:")
    print("-" * 40)

    room_map = {r['RoomID']: r for _, r in rooms_df.iterrows()}
    slot_map = {s['SlotID']: s for _, s in slots_df.iterrows()}

    sorted_items = sorted(assignment.items(), key=lambda x: x[0].name)

    for var, (slot_id, room_id) in sorted_items:
        course_row = courses_df[courses_df['CourseID'] == var.name].iloc[0]
        slot_row   = slot_map[slot_id]
        room_row   = room_map[room_id]
        time_range = format_time_range(slot_row)

        print(f"\n{var.name}: {course_row['CourseName']}")
        print(f"  Instructor : {course_row['Instructor']}")
        print(f"  Time Slot  : {slot_id} ({slot_row['Days']} {time_range})")
        print(f"  Room       : {room_id} ({room_row['Building']}, Capacity: {room_row['Capacity']})")
        print(f"  Enrolled   : {course_row['Enrollment']}")


    print()
    print("=" * 58)
    print("SCHEDULE GRID VIEW")
    print("=" * 58)

    all_slot_ids = [s['SlotID'] for _, s in slots_df.iterrows()]
    all_room_ids = [r['RoomID'] for _, r in rooms_df.iterrows()]

    grid = {}
    for var, (slot_id, room_id) in assignment.items():
        grid[(slot_id, room_id)] = var.name

    col_w = 12
    header = f"{'Room':<8} | " + " | ".join(f"{s:<{col_w}}" for s in all_slot_ids)
    print(header)
    print("-" * len(header))
    for room_id in all_room_ids:
        row = f"{room_id:<8} | "
        cells = []
        for slot_id in all_slot_ids:
            val = grid.get((slot_id, room_id), "[EMPTY]")
            cells.append(f"{val:<{col_w}}")
        print(row + " | ".join(cells))


    print()
    print("=" * 58)
    print("CONSTRAINT VERIFICATION")
    print("=" * 58)
    valid, violations = csp.verify_solution(assignment)
    if valid:
        print("All hard constraints satisfied. No violations detected.")
    else:
        print(f"WARNING: {len(violations)} constraint violation(s) found!")
        for v in violations:
            print(f"  {v}")

    preferred_hits = 0
    total_courses = len(assignment)
    avail = meta.get('availability', {})
    for var, (slot_id, room_id) in assignment.items():
        instr = var.metadata['instructor']
        if instr in avail and slot_id in avail[instr].get('preferred', set()):
            preferred_hits += 1
    print()
    print("SOFT CONSTRAINTS:")
    if total_courses > 0:
        pct = 100 * preferred_hits / total_courses
        print(f"  Instructor preferred-slot satisfaction: {preferred_hits}/{total_courses} ({pct:.1f}%)")


    print()
    metrics.print_report(n_courses, n_scheduled)


def print_warnings(assignment, csp, meta):
    """Print any constraint violations found in assignment."""
    if not assignment:
        return
    valid, violations = csp.verify_solution(assignment)
    if not valid:
        print("\n=== WARNINGS ===")
        for v in violations:
            print(f"  {v}")
