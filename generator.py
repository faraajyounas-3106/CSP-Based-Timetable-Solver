

import os
import random
import math
import csv

FIRST_NAMES_MALE = [
    "Ali", "Ahmed", "Hassan", "Usman", "Bilal", "Tariq", "Asad", "Imran",
    "Zain", "Omar", "Faisal", "Saad", "Adnan", "Kamran", "Waqar", "Rizwan",
    "Fahad", "Shahid", "Babar", "Danish", "Naveed", "Junaid", "Irfan", "Talha",
]
FIRST_NAMES_FEMALE = [
    "Fatima", "Ayesha", "Maryam", "Zainab", "Sana", "Hira", "Nadia", "Amna",
    "Sara", "Rabia", "Sadia", "Iqra", "Layla", "Noor", "Mehwish", "Bushra",
    "Farah", "Saba", "Kiran", "Afshan", "Sidra", "Naila", "Asma", "Rukhsana",
]
LAST_NAMES = [
    "Khan", "Ali", "Ahmed", "Malik", "Hussain", "Shah", "Iqbal", "Chaudhry",
    "Siddiqui", "Butt", "Qureshi", "Mirza", "Sheikh", "Ansari", "Raza", "Abbasi",
    "Hashmi", "Cheema", "Nawaz", "Baig", "Aslam", "Javed", "Niazi", "Bhatti",
]

REQUIRED_INSTRUCTORS = [
    "Mr Aamir Gulzar",
    "Mr Arshad Islam",
    "Maam Marium Hida",
    "Mr Anas Bin Rashid",
    "Mr Hasnain Akhtar",
    "Mr Hasan Mujtaba",
    "Maam Bushra Kanwal",
]

EXTRA_INSTRUCTOR_FIRST_MALE   = ["Zahid", "Pervaiz", "Muneer", "Shabbir", "Tanveer", "Mazhar"]
EXTRA_INSTRUCTOR_FIRST_FEMALE = ["Samina", "Rubina", "Tahira", "Shahida", "Nasreen", "Humera"]
EXTRA_INSTRUCTOR_LAST = ["Rana", "Gillani", "Qadri", "Warsi", "Durrani", "Lodhi"]

COURSE_TEMPLATES = [
    ("Introduction to Programming", "Lab"),
    ("Data Structures", "Projector"),
    ("Algorithms", "Projector"),
    ("Database Systems", "Lab"),
    ("Software Engineering", "Projector"),
    ("Artificial Intelligence", "Projector"),
    ("Machine Learning", "Lab"),
    ("Computer Networks", "Projector"),
    ("Operating Systems", "Lab"),
    ("Calculus I", "Whiteboard"),
    ("Calculus II", "Whiteboard"),
    ("Linear Algebra", "Whiteboard"),
    ("Discrete Mathematics", "Whiteboard"),
    ("Physics I", "Lab"),
    ("Physics II", "Lab"),
    ("English Composition", "Projector"),
    ("Technical Writing", "Projector"),
    ("Probability & Statistics", "Whiteboard"),
    ("Computer Architecture", "Lab"),
    ("Theory of Computation", "Whiteboard"),
    ("Compiler Design", "Projector"),
    ("Digital Logic Design", "Lab"),
    ("Embedded Systems", "Lab"),
    ("Web Engineering", "Lab"),
    ("Human-Computer Interaction", "Projector"),
    ("Cloud Computing", "Projector"),
    ("Cybersecurity", "Lab"),
    ("Data Mining", "Projector"),
    ("Computer Vision", "Lab"),
    ("Natural Language Processing", "Projector"),
    ("Parallel Computing", "Lab"),
    ("Numerical Methods", "Whiteboard"),
    ("Signals & Systems", "Lab"),
    ("Engineering Economics", "Whiteboard"),
    ("Project Management", "Projector"),
    ("Ethics in Computing", "Projector"),
    ("Robotics", "Lab"),
    ("IoT Systems", "Lab"),
    ("Quantum Computing", "Whiteboard"),
    ("Bioinformatics", "Lab"),
    ("Mobile App Development", "Lab"),
    ("Game Development", "Lab"),
    ("Distributed Systems", "Projector"),
    ("Information Security", "Lab"),
    ("Advanced OOP", "Lab"),
    ("Software Testing", "Lab"),
    ("Research Methods", "Projector"),
    ("Simulation & Modelling", "Lab"),
    ("Formal Methods", "Whiteboard"),
    ("Big Data Analytics", "Lab"),
]

BUILDINGS = ["CS Building", "Lab Building", "Main Building", "Engineering Block", "Science Block"]


def _random_pakistani_student_name():
    if random.random() < 0.5:
        first = random.choice(FIRST_NAMES_MALE)
    else:
        first = random.choice(FIRST_NAMES_FEMALE)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def _generate_instructors(n):
    """Return list of n instructor strings (uses required 7 first, then generates extras)."""
    instructors = list(REQUIRED_INSTRUCTORS)
    i = 0
    while len(instructors) < n:
        if i % 2 == 0:
            first = EXTRA_INSTRUCTOR_FIRST_MALE[i % len(EXTRA_INSTRUCTOR_FIRST_MALE)]
            prefix = "Mr"
        else:
            first = EXTRA_INSTRUCTOR_FIRST_FEMALE[i % len(EXTRA_INSTRUCTOR_FIRST_FEMALE)]
            prefix = "Maam"
        last = EXTRA_INSTRUCTOR_LAST[i % len(EXTRA_INSTRUCTOR_LAST)]
        name = f"{prefix} {first} {last}"
        if name not in instructors:
            instructors.append(name)
        i += 1
    return instructors[:n]


def _generate_timeslots(n_slots):
    """
    Generate up to n_slots time slots mixing MWF (50 min) and TTh (75 min).
    """
    mwf_starts = [
        "07:00", "08:00", "09:00", "10:00", "11:00", "12:00",
        "13:00", "14:00", "15:00", "16:00", "17:00", "18:00",
        "19:00", "20:00",
    ]
    tth_starts = [
        "07:00", "08:00", "09:30", "11:00", "12:30",
        "14:00", "15:30", "17:00", "18:30",
    ]

    mwf_slots = []
    for h in mwf_starts:
        slot_id = f"MWF-{h.replace(':','')}"
        mwf_slots.append((slot_id, "Monday/Wednesday/Friday", h, 50))

    tth_slots = []
    for h in tth_starts:
        slot_id = f"TTh-{h.replace(':','')}"
        tth_slots.append((slot_id, "Tuesday/Thursday", h, 75))

    # Interleave MWF and TTh to ensure both types appear
    all_slots = []
    from itertools import zip_longest
    for mwf, tth in zip_longest(mwf_slots, tth_slots):
        if mwf:
            all_slots.append(mwf)
        if tth:
            all_slots.append(tth)

    return all_slots[:n_slots]


class InstanceGenerator:
    """
    Generates a random university timetabling CSP instance.

    Parameters
    ----------
    n_courses  : int   — number of course sections
    n_rooms    : int   — number of rooms (typically 60-80% of courses)
    n_slots    : int   — number of time slots (20-40)
    density    : float — proportion of student-overlap edges (0.3-0.7)
    tightness  : float — room capacity tightness (0.3=loose, 0.7=tight)
    seed       : int   — random seed for reproducibility
    """

    def __init__(self, n_courses=10, n_rooms=8, n_slots=20,
                 density=0.3, tightness=0.3, seed=None):
        self.n_courses  = n_courses
        self.n_rooms    = n_rooms
        self.n_slots    = n_slots
        self.density    = density
        self.tightness  = tightness
        if seed is not None:
            random.seed(seed)

    def generate(self, output_dir):
        """Generate all CSV files to output_dir."""
        os.makedirs(output_dir, exist_ok=True)

        courses, instructors = self._generate_courses()
        rooms               = self._generate_rooms(courses)
        slots               = _generate_timeslots(self.n_slots)
        students, student_enrollments = self._generate_students(courses)

        self._write_courses(output_dir, courses)
        self._write_rooms(output_dir, rooms)
        self._write_timeslots(output_dir, slots)
        self._write_students(output_dir, students, student_enrollments)
        self._write_availability(output_dir, instructors, slots)

        print(f"[Generator] Instance written to: {output_dir}")
        print(f"  Courses: {self.n_courses} | Rooms: {self.n_rooms} | "
              f"Slots: {len(slots)} | Density: {self.density} | Tightness: {self.tightness}")


    def _generate_courses(self):
        n_instructors = max(7, math.ceil(self.n_courses / 3))
        instructors = _generate_instructors(n_instructors)
        courses = []
        templates_used = {}

        for i in range(self.n_courses):
            tmpl_idx = i % len(COURSE_TEMPLATES)
            name, feature = COURSE_TEMPLATES[tmpl_idx]
            count = templates_used.get(tmpl_idx, 0)
            templates_used[tmpl_idx] = count + 1
            section = f"{count+1:02d}"

            parts = name.split()
            abbrev = "".join(w[0] for w in parts if w[0].isupper())[:4]
            num = 100 + (tmpl_idx // 10) * 100 + (tmpl_idx % 10) * 10
            course_id = f"{abbrev}{num}-{section}"

            duration = 50 if feature in {"Projector", "Whiteboard"} else 75

            if feature == "Lab" and random.random() < 0.4:
                duration = 50

            max_enroll = int(15 + (100 - 15) * (1 - self.tightness * 0.5))
            enrollment = random.randint(15, max(15, max_enroll))

            instructor = instructors[i % len(instructors)]
            courses.append({
                'CourseID':     course_id,
                'CourseName':   name,
                'Instructor':   instructor,
                'Enrollment':   enrollment,
                'Duration':     duration,
                'RoomFeatures': feature,
            })

        return courses, list(set(c['Instructor'] for c in courses))

    def _generate_rooms(self, courses):
        features_needed = set(c['RoomFeatures'] for c in courses)
        max_enroll = max(c['Enrollment'] for c in courses)

        rooms = []
        feature_options = {
            "Lab":        ["Lab;Projector", "Lab;Projector;Whiteboard", "Lab"],
            "Projector":  ["Projector;Whiteboard", "Projector"],
            "Whiteboard": ["Whiteboard", "Projector;Whiteboard"],
        }
        all_features = []
        for feat in ["Lab", "Projector", "Whiteboard"]:
            if feat in features_needed:
                all_features.extend(feature_options[feat] * 3)
        if not all_features:
            all_features = ["Lab;Projector;Whiteboard"] * self.n_rooms

        building_cycle = BUILDINGS * (self.n_rooms // len(BUILDINGS) + 1)

        for i in range(self.n_rooms):
            feat = random.choice(all_features)
            # Capacity relative to tightness: tight → capacity near enrollment, loose → big rooms
            base_capacity = int(max_enroll * (0.5 + (1 - self.tightness) * 0.8))
            variance = random.randint(-10, 20)
            capacity = max(15, base_capacity + variance)
            rooms.append({
                'RoomID':   f"R{100 + i + 1}",
                'Building': building_cycle[i],
                'Capacity': capacity,
                'Features': feat,
            })

        return rooms

    def _generate_students(self, courses):
        n_students = max(20, self.n_courses * 3)
        all_course_ids = [c['CourseID'] for c in courses]

        target_conflicts = int(self.density * self.n_courses * (self.n_courses - 1) / 2)

        students = []
        student_enrollments = {}

        for i in range(n_students):
            sid = f"{i+1:03d}"
            name = _random_pakistani_student_name()

            n_take = random.randint(2, min(5, len(all_course_ids)))
            enrolled = random.sample(all_course_ids, n_take)
            students.append({'StudentID': sid, 'StudentName': name})
            student_enrollments[sid] = enrolled

        return students, student_enrollments



    def _write_courses(self, output_dir, courses):
        path = os.path.join(output_dir, 'courses.csv')
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['CourseID','CourseName','Instructor','Enrollment','Duration','RoomFeatures'])
            w.writeheader()
            w.writerows(courses)

    def _write_rooms(self, output_dir, rooms):
        path = os.path.join(output_dir, 'rooms.csv')
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['RoomID','Building','Capacity','Features'])
            w.writeheader()
            w.writerows(rooms)

    def _write_timeslots(self, output_dir, slots):
        path = os.path.join(output_dir, 'timeslots.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['SlotID','Days','StartTime','Duration'])
            for row in slots:
                w.writerow(row)

    def _write_students(self, output_dir, students, student_enrollments):
        path = os.path.join(output_dir, 'students.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['StudentID','StudentName','EnrolledCourses'])
            for s in students:
                sid = s['StudentID']
                courses_str = ";".join(student_enrollments.get(sid, []))
                w.writerow([sid, s['StudentName'], courses_str])

    def _write_availability(self, output_dir, instructors, slots):
        path = os.path.join(output_dir, 'instructor_availability.csv')
        all_slot_ids = [s[0] for s in slots]

        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Instructor','AvailableSlots','PreferredSlots'])
            for instr in instructors:
                # All slots available (to ensure feasibility of generated instances).
                # Preferred: random 40-70% of available slots.
                avail = all_slot_ids[:]
                n_pref = max(1, int(len(avail) * random.uniform(0.4, 0.7)))
                pref = random.sample(avail, n_pref)
                w.writerow([instr, ";".join(avail), ";".join(pref)])
