from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from io import BytesIO
import json
import random
import time
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'dev-only-secret-key'
)
db = SQLAlchemy(app)
SCHEDULE_DEADLINE = 0

# ==================== MODELS ====================

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subjects = db.relationship('Subject', backref='teacher', lazy=True)
    
    def __repr__(self):
        return f'<Teacher {self.name}>'

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    
    def __repr__(self):
        return f'<Subject {self.name}>'

class ClassRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    requirements = db.relationship('SubjectRequirement', backref='classroom', lazy=True)
    
    def __repr__(self):
        return f'<ClassRoom {self.name}>'

class SubjectRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('class_room.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    periods_per_week = db.Column(db.Integer, nullable=False)
    is_lab = db.Column(db.Boolean, nullable=False, default=False)
    lab_sessions = db.Column(db.Integer, nullable=False, default=0)
    lab_periods = db.Column(db.Integer, nullable=False, default=1)
    lab_room = db.Column(db.String(100), nullable=False, default='')
    subject = db.relationship('Subject')
    
    def __repr__(self):
        return f'<SubjectRequirement {self.classroom.name} - {self.subject.name}>'

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(50), nullable=False)
    period_number = db.Column(db.Integer, nullable=False)  # 1-6
    start_time = db.Column(db.String(5), nullable=False, default='09:00')
    end_time = db.Column(db.String(5), nullable=False, default='10:00')
    is_break = db.Column(db.Boolean, nullable=False, default=False)
    label = db.Column(db.String(50), nullable=False, default='')
    slot_order = db.Column(db.Integer, nullable=False, default=0)
    
    def __repr__(self):
        return f'<TimeSlot {self.day} P{self.period_number}>'

class TimetableConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    selected_days = db.Column(db.Text, nullable=False, default='["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]')
    start_time = db.Column(db.String(5), nullable=False, default='09:00')
    end_time = db.Column(db.String(5), nullable=False, default='16:00')
    period_duration = db.Column(db.Integer, nullable=False, default=60)
    break_duration = db.Column(db.Integer, nullable=False, default=15)
    break_after = db.Column(db.Integer, nullable=False, default=4)
    lunch_duration = db.Column(db.Integer, nullable=False, default=60)
    lunch_after = db.Column(db.Integer, nullable=False, default=4)
    second_break_duration = db.Column(db.Integer, nullable=False, default=0)
    second_break_after = db.Column(db.Integer, nullable=False, default=0)
    break_start = db.Column(db.String(5), nullable=False, default='10:40')
    second_break_start = db.Column(db.String(5), nullable=False, default='15:00')
    lunch_start = db.Column(db.String(5), nullable=False, default='12:30')
    title = db.Column(db.String(150), nullable=False, default='Weekly timetable')
    institution = db.Column(db.String(150), nullable=False, default='')
    academic_period = db.Column(db.String(100), nullable=False, default='')
    subtitle = db.Column(db.String(200), nullable=False, default='')
    daily_structure = db.Column(db.Text, nullable=False, default='[]')
    day_overrides = db.Column(db.Text, nullable=False, default='{}')

    @property
    def days(self):
        return json.loads(self.selected_days or '[]')

    @property
    def structure(self):
        return json.loads(self.daily_structure or '[]')

    @property
    def overrides(self):
        return json.loads(self.day_overrides or '{}')

class ScheduleEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('class_room.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    session_id = db.Column(db.String(50), nullable=False, default='')
    required_room = db.Column(db.String(100), nullable=False, default='')
    
    classroom = db.relationship('ClassRoom')
    subject = db.relationship('Subject')
    teacher = db.relationship('Teacher')
    timeslot = db.relationship('TimeSlot')
    
    def __repr__(self):
        return f'<ScheduleEntry {self.classroom.name} - {self.subject.name}>'

class CombinedGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    classroom_ids = db.Column(db.Text, nullable=False, default='[]')

    @property
    def ids(self):
        return json.loads(self.classroom_ids or '[]')

    subject = db.relationship('Subject')

class TimetableSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entries = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def ensure_schema():
    """Create new tables and add slot metadata to databases created by older versions."""
    db.create_all()
    columns = {row[1] for row in db.session.execute(db.text('PRAGMA table_info(time_slot)'))}
    additions = {
        'start_time': "VARCHAR(5) NOT NULL DEFAULT '09:00'",
        'end_time': "VARCHAR(5) NOT NULL DEFAULT '10:00'",
        'is_break': "BOOLEAN NOT NULL DEFAULT 0",
        'label': "VARCHAR(50) NOT NULL DEFAULT ''",
        'slot_order': 'INTEGER NOT NULL DEFAULT 0'
    }
    for name, definition in additions.items():
        if name not in columns:
            db.session.execute(db.text(f'ALTER TABLE time_slot ADD COLUMN {name} {definition}'))
    for table, definitions in {
        'subject_requirement': {
            'is_lab': 'BOOLEAN NOT NULL DEFAULT 0', 'lab_sessions': 'INTEGER NOT NULL DEFAULT 0',
            'lab_periods': 'INTEGER NOT NULL DEFAULT 1', 'lab_room': "VARCHAR(100) NOT NULL DEFAULT ''"
        },
        'timetable_config': {
            'second_break_duration': 'INTEGER NOT NULL DEFAULT 0', 'second_break_after': 'INTEGER NOT NULL DEFAULT 0',
            'break_start': "VARCHAR(5) NOT NULL DEFAULT '10:40'", 'second_break_start': "VARCHAR(5) NOT NULL DEFAULT '15:00'",
            'lunch_start': "VARCHAR(5) NOT NULL DEFAULT '12:30'", 'daily_structure': "TEXT NOT NULL DEFAULT '[]'",
            'day_overrides': "TEXT NOT NULL DEFAULT '{}'"
        },
        'schedule_entry': {
            'session_id': "VARCHAR(50) NOT NULL DEFAULT ''", 'required_room': "VARCHAR(100) NOT NULL DEFAULT ''"
        },
        'combined_group': {'subject_id': 'INTEGER NOT NULL DEFAULT 0'}
    }.items():
        existing = {row[1] for row in db.session.execute(db.text(f'PRAGMA table_info({table})'))}
        for name, definition in definitions.items():
            if name not in existing:
                db.session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
    db.session.commit()

with app.app_context():
    ensure_schema()

def get_config():
    config = TimetableConfig.query.first()
    if not config:
        config = TimetableConfig()
        db.session.add(config)
        db.session.commit()
    if not config.structure:
        existing = TimeSlot.query.order_by(TimeSlot.slot_order, TimeSlot.id).all()
        if existing:
            first_day = existing[0].day
            config.daily_structure = json.dumps([{
                'type': 'break' if slot.is_break else 'class', 'label': slot.label or ('Break' if slot.is_break else f'Period {slot.period_number}'),
                'start': slot.start_time, 'end': slot.end_time
            } for slot in existing if slot.day == first_day])
        else:
            config.daily_structure = json.dumps([
                {'type': 'class', 'label': f'Period {number}', 'start': f'{8 + number - 1:02d}:00', 'end': f'{8 + number:02d}:00'}
                for number in range(1, 7)
            ])
        db.session.commit()
    return config

def time_value(value):
    return datetime.strptime(value, '%H:%M')

def slot_definitions(config):
    """Clone the saved daily structure for each selected day without changing its clock times."""
    result = []
    structure = config.structure
    for day in config.days:
        day_structure = config.overrides.get(day, structure)
        period_number = 1
        for slot_order, item in enumerate(day_structure):
            is_break = item.get('type') in ('break', 'lunch')
            result.append({'day': day, 'period_number': period_number, 'start_time': item['start'], 'end_time': item['end'],
                           'is_break': is_break, 'label': item.get('label') or ('Lunch' if item.get('type') == 'lunch' else 'Break' if is_break else f'Period {period_number}'),
                           'slot_order': slot_order})
            if not is_break:
                period_number += 1
    return result

# ==================== TIMETABLE GENERATION LOGIC ====================

def generate_timetables():
    """Generate timetables for all classes using backtracking algorithm"""
    
    # Clear existing schedule entries
    ScheduleEntry.query.delete()
    TimetableSnapshot.query.delete()
    db.session.commit()
    
    config = get_config()
    global SCHEDULE_DEADLINE
    SCHEDULE_DEADLINE = time.monotonic() + 8
    create_timeslots(config)
    timeslots = TimeSlot.query.filter_by(is_break=False).all()
    
    # Get all classes
    classrooms = ClassRoom.query.all()
    combined_requirements = set()
    for group in CombinedGroup.query.all():
        members = [classroom for classroom in classrooms if classroom.id in group.ids]
        subject = group.subject
        if not members or not subject:
            continue
        requirement = SubjectRequirement.query.filter_by(classroom_id=members[0].id, subject_id=subject.id).first()
        if not requirement:
            continue
        for slot in timeslots:
            if all(is_valid_assignment(member, subject, slot) for member in members):
                session_id = f'combined-{group.id}'
                for member in members:
                    db.session.add(ScheduleEntry(classroom_id=member.id, subject_id=subject.id,
                                                 teacher_id=subject.teacher_id, timeslot_id=slot.id, session_id=session_id))
                combined_requirements.update((member.id, subject.id) for member in members)
                break
    
    # For each class, create a schedule
    for classroom in classrooms:
        requirements = SubjectRequirement.query.filter_by(classroom_id=classroom.id).all()
        
        # Create list of subjects to schedule (with repetitions based on periods_per_week)
        subjects_to_schedule = []
        for req in requirements:
            if (classroom.id, req.subject_id) in combined_requirements:
                continue
            if req.is_lab and req.lab_sessions:
                for session_number in range(req.lab_sessions):
                    if not schedule_lab_block(classroom, req, timeslots, session_number):
                        continue
                continue
            for _ in range(req.periods_per_week):
                subjects_to_schedule.append(req.subject)
        
        # Shuffle for randomness
        random.shuffle(subjects_to_schedule)
        
        # Try to schedule using backtracking
        if not schedule_class(classroom, subjects_to_schedule, timeslots, 0):
            # If backtracking fails, use greedy approach
            schedule_class_greedy(classroom, subjects_to_schedule, timeslots)
    
    db.session.commit()
    incomplete = []
    for requirement in SubjectRequirement.query.all():
        expected = requirement.lab_sessions * requirement.lab_periods if requirement.is_lab and requirement.lab_sessions else requirement.periods_per_week
        scheduled = ScheduleEntry.query.filter_by(classroom_id=requirement.classroom_id, subject_id=requirement.subject_id).count()
        if scheduled < expected:
            incomplete.append({'class': requirement.classroom.name, 'subject': requirement.subject.name,
                               'scheduled': scheduled, 'required': expected})
    return incomplete

def schedule_class(classroom, subjects, timeslots, subject_index):
    """Backtracking algorithm to schedule subjects"""
    if subject_index >= len(subjects):
        return True  # All subjects scheduled
    if time.monotonic() >= SCHEDULE_DEADLINE:
        return False
    
    subject = subjects[subject_index]
    
    # Try less crowded days first, then avoid repeating a subject in adjacent periods.
    existing = ScheduleEntry.query.filter_by(classroom_id=classroom.id).all()
    day_counts = {day: sum(entry.timeslot.day == day for entry in existing) for day in {slot.day for slot in timeslots}}
    def preference(timeslot):
        adjacent = any(entry.timeslot.day == timeslot.day and abs(entry.timeslot.period_number - timeslot.period_number) == 1 and entry.subject_id == subject.id for entry in existing)
        return (day_counts.get(timeslot.day, 0), adjacent, (timeslot.period_number + subject_index) % 2)

    candidates = sorted(timeslots, key=preference)
    for timeslot in candidates:
        if is_valid_assignment(classroom, subject, timeslot):
            # Make assignment
            entry = ScheduleEntry(
                classroom_id=classroom.id,
                subject_id=subject.id,
                teacher_id=subject.teacher_id,
                timeslot_id=timeslot.id
            )
            db.session.add(entry)
            db.session.flush()
            
            # Recurse
            if schedule_class(classroom, subjects, timeslots, subject_index + 1):
                return True
            
            # Backtrack
            db.session.delete(entry)
            db.session.flush()
    
    return False

def schedule_class_greedy(classroom, subjects, timeslots):
    """Greedy approach - schedule what we can"""
    for subject in subjects:
        existing = ScheduleEntry.query.filter_by(classroom_id=classroom.id).all()
        day_counts = {day: sum(entry.timeslot.day == day for entry in existing) for day in {slot.day for slot in timeslots}}
        for timeslot in sorted(timeslots, key=lambda slot: day_counts.get(slot.day, 0)):
            if is_valid_assignment(classroom, subject, timeslot):
                entry = ScheduleEntry(
                    classroom_id=classroom.id,
                    subject_id=subject.id,
                    teacher_id=subject.teacher_id,
                    timeslot_id=timeslot.id
                )
                db.session.add(entry)
                day_counts[timeslot.day] = day_counts.get(timeslot.day, 0) + 1
                break

def is_valid_assignment(classroom, subject, timeslot, required_room=''):
    """Check if a subject can be assigned to a timeslot for a classroom"""
    
    # Check if classroom is already occupied at this timeslot
    existing_class = ScheduleEntry.query.filter_by(
        classroom_id=classroom.id,
        timeslot_id=timeslot.id
    ).first()
    if existing_class:
        return False
    
    # Check if teacher is already teaching at this timeslot
    existing_teacher = ScheduleEntry.query.filter_by(
        teacher_id=subject.teacher_id,
        timeslot_id=timeslot.id
    ).first()
    if existing_teacher:
        return False

    if required_room:
        existing_room = ScheduleEntry.query.filter_by(required_room=required_room, timeslot_id=timeslot.id).first()
        if existing_room:
            return False
    
    return True

def schedule_lab_block(classroom, requirement, timeslots, session_number):
    subject = requirement.subject
    if time.monotonic() >= SCHEDULE_DEADLINE:
        return False
    ordered = sorted([slot for slot in timeslots if slot.day in get_config().days], key=lambda slot: (get_config().days.index(slot.day), slot.period_number))
    for start_index in range(len(ordered) - requirement.lab_periods + 1):
        if time.monotonic() >= SCHEDULE_DEADLINE:
            return False
        block = ordered[start_index:start_index + requirement.lab_periods]
        if len({slot.day for slot in block}) != 1 or any(block[index].period_number + 1 != block[index + 1].period_number for index in range(len(block) - 1)):
            continue
        if all(is_valid_assignment(classroom, subject, slot, requirement.lab_room) for slot in block):
            session_id = f'lab-{requirement.id}-{session_number}'
            for slot in block:
                db.session.add(ScheduleEntry(classroom_id=classroom.id, subject_id=subject.id,
                                             teacher_id=subject.teacher_id, timeslot_id=slot.id,
                                             session_id=session_id, required_room=requirement.lab_room))
            db.session.flush()
            return True
    return False

def save_snapshot():
    TimetableSnapshot.query.delete()
    snapshot = TimetableSnapshot(entries=json.dumps([
        {'id': entry.id, 'timeslot_id': entry.timeslot_id}
        for entry in ScheduleEntry.query.all()
    ]))
    db.session.add(snapshot)

def schedule_conflict(entry, timeslot_id, ignore_ids=()):
    target = db.session.get(TimeSlot, timeslot_id)
    if not target:
        return 'The selected time slot no longer exists.'
    if target.is_break:
        return 'Breaks cannot contain subjects.'
    ignored = set(ignore_ids)
    class_conflict = next((item for item in ScheduleEntry.query.filter_by(classroom_id=entry.classroom_id, timeslot_id=timeslot_id).all() if item.id not in ignored), None)
    if class_conflict:
        return f'{entry.classroom.name} already has {class_conflict.subject.name} in this period.'
    teacher_conflict = next((item for item in ScheduleEntry.query.filter_by(teacher_id=entry.teacher_id, timeslot_id=timeslot_id).all()
                             if item.id not in ignored and not (entry.session_id and item.session_id == entry.session_id)), None)
    if teacher_conflict:
        return f'{entry.teacher.name} is already teaching {teacher_conflict.subject.name} in this period.'
    if entry.required_room:
        room_conflict = next((item for item in ScheduleEntry.query.filter_by(required_room=entry.required_room, timeslot_id=timeslot_id).all() if item.id not in ignored), None)
        if room_conflict:
            return f'{entry.required_room} is already occupied by {room_conflict.classroom.name}.'
    return None

def schedule_validation_errors():
    """Validate hard constraints and required session counts independently of generation."""
    errors = []
    entries = ScheduleEntry.query.all()
    selected_days = set(get_config().days)
    for entry in entries:
        slot = entry.timeslot
        if slot.day not in selected_days or slot.is_break:
            errors.append(f'{entry.subject.name} is assigned outside an available class slot.')
    for slot_id in {entry.timeslot_id for entry in entries}:
        at_slot = [entry for entry in entries if entry.timeslot_id == slot_id]
        for resource, label in [('teacher_id', 'Teacher'), ('classroom_id', 'Class'), ('required_room', 'Room')]:
            used = {}
            for entry in at_slot:
                value = getattr(entry, resource)
                if not value or (resource == 'teacher_id' and entry.session_id):
                    continue
                if value in used:
                    errors.append(f'{label} conflict for {entry.subject.name} at {entry.timeslot.day} {entry.timeslot.label}.')
                used[value] = entry.id
    for requirement in SubjectRequirement.query.all():
        expected = requirement.lab_sessions * requirement.lab_periods if requirement.is_lab and requirement.lab_sessions else requirement.periods_per_week
        actual = ScheduleEntry.query.filter_by(classroom_id=requirement.classroom_id, subject_id=requirement.subject_id).count()
        if actual != expected:
            errors.append(f'{requirement.classroom.name} / {requirement.subject.name}: {actual} of {expected} required periods scheduled.')
        if requirement.is_lab and requirement.lab_sessions:
            sessions = {}
            for entry in ScheduleEntry.query.filter_by(classroom_id=requirement.classroom_id, subject_id=requirement.subject_id).all():
                sessions.setdefault(entry.session_id, []).append(entry)
            for session_entries in sessions.values():
                if len(session_entries) != requirement.lab_periods:
                    errors.append(f'{requirement.subject.name} has an incomplete lab block.')
    return list(dict.fromkeys(errors))

def entry_snapshot():
    return {entry.id: entry.timeslot_id for entry in ScheduleEntry.query.all()}

def restore_snapshot(snapshot):
    for entry_id, timeslot_id in snapshot.items():
        entry = db.session.get(ScheduleEntry, entry_id)
        if entry:
            entry.timeslot_id = timeslot_id

def conflicts_for(entry, timeslot_id, ignored):
    conflict_ids = []
    for other in ScheduleEntry.query.all():
        if other.id in ignored or other.id == entry.id or other.timeslot_id != timeslot_id:
            continue
        if other.classroom_id == entry.classroom_id or other.teacher_id == entry.teacher_id or (entry.required_room and other.required_room == entry.required_room):
            if entry.session_id and other.session_id == entry.session_id:
                continue
            conflict_ids.append(other.id)
    return conflict_ids

def place_with_cascade(entry, target_id, locked=None, visited=None):
    """Recursively clear dependencies before placing an entry in a candidate slot."""
    locked = set(locked or ())
    visited = set(visited or ())
    if entry.id in visited or entry.id in locked:
        return False
    target = db.session.get(TimeSlot, target_id)
    if not target or target.is_break:
        return False
    conflicts = conflicts_for(entry, target_id, locked)
    if conflicts:
        for conflict_id in conflicts:
            conflict = db.session.get(ScheduleEntry, conflict_id)
            moved = False
            candidates = sorted(TimeSlot.query.filter_by(is_break=False).all(), key=lambda slot: (slot.day != entry.timeslot.day, slot.slot_order))
            for candidate in candidates:
                if candidate.id == conflict.timeslot_id or candidate.id == target_id:
                    continue
                if place_with_cascade(conflict, candidate.id, locked | {entry.id}, visited | {entry.id}):
                    moved = True
                    break
            if not moved:
                return False
    entry.timeslot_id = target_id
    return not schedule_conflict(entry, target_id, locked | {entry.id})

def create_timeslots(config=None):
    """Replace generated slots with the current ordered day and break configuration."""
    config = config or get_config()
    ScheduleEntry.query.delete()
    TimetableSnapshot.query.delete()
    TimeSlot.query.delete()
    for slot in slot_definitions(config):
        db.session.add(TimeSlot(**slot))
    db.session.commit()

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html', config=get_config(), classrooms=ClassRoom.query.all(), subjects=Subject.query.all(), combined_groups=CombinedGroup.query.all())

@app.route('/combined', methods=['POST'])
def combined():
    name = request.form.get('name', '').strip()
    subject_id = request.form.get('subject_id', type=int)
    classroom_ids = request.form.getlist('classroom_ids')
    if name and subject_id and len(classroom_ids) > 1:
        db.session.add(CombinedGroup(name=name, subject_id=subject_id, classroom_ids=json.dumps([int(value) for value in classroom_ids])))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/combined/delete/<int:id>', methods=['POST'])
def delete_combined(id):
    group = CombinedGroup.query.get_or_404(id)
    db.session.delete(group)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/settings', methods=['POST'])
def settings():
    config = get_config()
    days = request.form.getlist('days')
    custom_days = [day.strip() for day in request.form.get('custom_days', '').split(',') if day.strip()]
    selected_days = days + [day for day in custom_days if day not in days]
    config.selected_days = json.dumps(selected_days or ['Monday'])
    try:
        structure = json.loads(request.form.get('daily_structure', '[]'))
    except json.JSONDecodeError:
        structure = []
    valid_structure = []
    for item in structure if isinstance(structure, list) else []:
        try:
            if item.get('type') in ('class', 'break', 'lunch') and time_value(item.get('start', '')) < time_value(item.get('end', '')):
                valid_structure.append({'type': item['type'], 'label': item.get('label', '').strip(), 'start': item['start'], 'end': item['end']})
        except (TypeError, ValueError):
            continue
    structure = valid_structure
    if not structure:
        structure = config.structure
    config.daily_structure = json.dumps(structure)
    overrides = request.form.get('day_overrides', '').strip()
    try:
        raw_overrides = json.loads(overrides) if overrides else {}
        clean_overrides = {}
        for day, rows in raw_overrides.items() if isinstance(raw_overrides, dict) else []:
            clean_rows = []
            for item in rows if isinstance(rows, list) else []:
                try:
                    if item.get('type') in ('class', 'break', 'lunch') and time_value(item.get('start', '')) < time_value(item.get('end', '')):
                        clean_rows.append({'type': item['type'], 'label': item.get('label', '').strip(), 'start': item['start'], 'end': item['end']})
                except (TypeError, ValueError):
                    continue
            if clean_rows:
                clean_overrides[day] = clean_rows
        config.day_overrides = json.dumps(clean_overrides)
    except json.JSONDecodeError:
        config.day_overrides = '{}'
    config.title = request.form.get('title', '').strip() or 'Weekly timetable'
    config.institution = request.form.get('institution', '').strip()
    config.academic_period = request.form.get('academic_period', '').strip()
    config.subtitle = request.form.get('subtitle', '').strip()
    db.session.commit()
    create_timeslots(config)
    return redirect(url_for('index'))

@app.route('/settings/reset', methods=['POST'])
def reset_settings():
    config = get_config()
    config.daily_structure = json.dumps([
        {'type': 'class', 'label': f'Period {number}', 'start': f'{8 + number - 1:02d}:00', 'end': f'{8 + number:02d}:00'}
        for number in range(1, 7)
    ])
    config.day_overrides = '{}'
    db.session.commit()
    create_timeslots(config)
    return redirect(url_for('index'))

@app.route('/teachers')
def teachers():
    teachers = Teacher.query.all()
    return render_template('teachers.html', teachers=teachers)

@app.route('/teachers/add', methods=['POST'])
def add_teacher():
    name = request.form.get('name')
    if name:
        teacher = Teacher(name=name)
        db.session.add(teacher)
        db.session.commit()
    return redirect(url_for('teachers'))

@app.route('/teachers/delete/<int:id>', methods=['POST'])
def delete_teacher(id):
    teacher = Teacher.query.get_or_404(id)
    db.session.delete(teacher)
    db.session.commit()
    return redirect(url_for('teachers'))

@app.route('/subjects')
def subjects():
    subjects = Subject.query.all()
    teachers = Teacher.query.all()
    return render_template('subjects.html', subjects=subjects, teachers=teachers)

@app.route('/subjects/add', methods=['POST'])
def add_subject():
    name = request.form.get('name')
    teacher_id = request.form.get('teacher_id')
    if name and teacher_id:
        subject = Subject(name=name, teacher_id=teacher_id)
        db.session.add(subject)
        db.session.commit()
    return redirect(url_for('subjects'))

@app.route('/subjects/delete/<int:id>', methods=['POST'])
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    return redirect(url_for('subjects'))

@app.route('/classes')
def classes():
    classrooms = ClassRoom.query.all()
    return render_template('classes.html', classrooms=classrooms)

@app.route('/classes/add', methods=['POST'])
def add_class():
    name = request.form.get('name')
    if name:
        classroom = ClassRoom(name=name)
        db.session.add(classroom)
        db.session.commit()
    return redirect(url_for('classes'))

@app.route('/classes/delete/<int:id>', methods=['POST'])
def delete_class(id):
    classroom = ClassRoom.query.get_or_404(id)
    db.session.delete(classroom)
    db.session.commit()
    return redirect(url_for('classes'))

@app.route('/requirements')
def requirements():
    classrooms = ClassRoom.query.all()
    subjects = Subject.query.all()
    requirements = SubjectRequirement.query.all()
    return render_template('requirements.html', 
                         classrooms=classrooms, 
                         subjects=subjects,
                         requirements=requirements)

@app.route('/requirements/add', methods=['POST'])
def add_requirement():
    classroom_id = request.form.get('classroom_id')
    subject_id = request.form.get('subject_id')
    periods = request.form.get('periods_per_week')
    is_lab = request.form.get('is_lab') == 'on'
    lab_sessions = request.form.get('lab_sessions', 0, type=int) or 0
    lab_periods = request.form.get('lab_periods', 1, type=int) or 1
    lab_room = request.form.get('lab_room', '').strip()
    
    if classroom_id and subject_id and periods:
        # Check if requirement already exists
        existing = SubjectRequirement.query.filter_by(
            classroom_id=classroom_id,
            subject_id=subject_id
        ).first()
        
        if existing:
            existing.periods_per_week = periods
            existing.is_lab = is_lab
            existing.lab_sessions = lab_sessions
            existing.lab_periods = lab_periods
            existing.lab_room = lab_room
        else:
            requirement = SubjectRequirement(
                classroom_id=classroom_id,
                subject_id=subject_id,
                periods_per_week=periods
                , is_lab=is_lab, lab_sessions=lab_sessions, lab_periods=lab_periods, lab_room=lab_room
            )
            db.session.add(requirement)
        db.session.commit()
    return redirect(url_for('requirements'))

@app.route('/requirements/delete/<int:id>', methods=['POST'])
def delete_requirement(id):
    requirement = SubjectRequirement.query.get_or_404(id)
    db.session.delete(requirement)
    db.session.commit()
    return redirect(url_for('requirements'))

@app.route('/generate', methods=['POST'])
def generate():
    try:
        incomplete = generate_timetables()
        if incomplete:
            details = ', '.join(f"{item['class']} / {item['subject']} ({item['scheduled']}/{item['required']})" for item in incomplete)
            return jsonify({'success': True, 'message': f'Timetable generated with unscheduled requirements: {details}', 'incomplete': incomplete})
        return jsonify({'success': True, 'message': 'Timetables generated successfully!', 'incomplete': []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/validate')
def validate():
    errors = schedule_validation_errors()
    return jsonify({'valid': not errors, 'errors': errors})

@app.route('/timetable')
def timetable():
    classroom_id = request.args.get('classroom_id', type=int)
    classrooms = ClassRoom.query.all()
    
    if not classroom_id and classrooms:
        classroom_id = classrooms[0].id
    
    if classroom_id:
        classroom = ClassRoom.query.get(classroom_id)
        entries = ScheduleEntry.query.filter_by(classroom_id=classroom_id).all()
        config = get_config()
        timeslots = TimeSlot.query.order_by(TimeSlot.id).all()
        days = config.days
        columns = []
        for slot in timeslots:
            key = slot.slot_order
            if key not in [column['slot_order'] for column in columns]:
                columns.append({'period_number': slot.period_number, 'is_break': slot.is_break,
                                'label': slot.label, 'start_time': slot.start_time, 'end_time': slot.end_time, 'slot_order': slot.slot_order})
        timetable_grid = {}
        for day in days:
            timetable_grid[day] = {}
            for column in columns:
                timetable_grid[day][(column['period_number'], column['is_break'])] = None
        
        for entry in entries:
            day = entry.timeslot.day
            period = entry.timeslot.period_number
            timetable_grid[day][(period, False)] = entry
        
        return render_template('timetable.html', 
                             classrooms=classrooms,
                             current_classroom=classroom,
                             timetable_grid=timetable_grid,
                             days=days,
                             timeslots=timeslots,
                             columns=columns,
                             config=config)
    
    return render_template('timetable.html', classrooms=classrooms)

def export_options():
    config = get_config()
    return {
        'title': request.args.get('title', config.title) or 'Weekly timetable',
        'institution': request.args.get('institution', config.institution),
        'academic_period': request.args.get('academic_period', config.academic_period),
        'subtitle': request.args.get('subtitle', config.subtitle)
    }

def timetable_rows(classroom_id):
    config = get_config()
    slots = TimeSlot.query.order_by(TimeSlot.id).all()
    days = config.days
    columns = []
    for slot in slots:
        if not any(column['slot_order'] == slot.slot_order for column in columns):
            columns.append({'period_number': slot.period_number, 'is_break': slot.is_break, 'label': slot.label,
                            'start_time': slot.start_time, 'end_time': slot.end_time, 'slot_order': slot.slot_order})
    entries = {(entry.timeslot.day, entry.timeslot.period_number): entry
               for entry in ScheduleEntry.query.filter_by(classroom_id=classroom_id).all()}
    rows = []
    for day in days:
        cells = []
        for column in columns:
            cells.append({'slot': column, 'entry': None if column['is_break'] else entries.get((day, column['period_number']))})
        rows.append((day, cells))
    return config, columns, rows

@app.route('/export/image')
def export_image():
    from PIL import Image, ImageDraw, ImageFont
    classroom = ClassRoom.query.get_or_404(request.args.get('classroom_id', type=int))
    config, columns, rows = timetable_rows(classroom.id)
    options = export_options()
    try:
        font = ImageFont.truetype('arial.ttf', 22)
        small_font = ImageFont.truetype('arial.ttf', 16)
    except OSError:
        font = ImageFont.load_default()
        small_font = font
    cell_width, cell_height, label_width = max(220, 240 - len(columns) * 2), 110, 150
    image = Image.new('RGB', (label_width + cell_width * len(columns), 180 + cell_height * len(rows)), '#f4f8f8')
    draw = ImageDraw.Draw(image)
    draw.text((30, 25), options['title'], fill='#18323d', font=font)
    draw.text((30, 62), ' | '.join(value for value in [options['institution'], classroom.name, options['academic_period'], options['subtitle']] if value), fill='#60757b', font=small_font)
    top = 125
    draw.rectangle((0, top, label_width, top + 45), fill='#dcebed', outline='#c4d8da')
    draw.text((20, top + 14), 'Day', fill='#245b68', font=small_font)
    for index, column in enumerate(columns):
        left = label_width + index * cell_width
        draw.rectangle((left, top, left + cell_width, top + 45), fill='#dcebed', outline='#c4d8da')
        draw.text((left + 8, top + 5), column['label'], fill='#245b68', font=small_font)
        draw.text((left + 8, top + 25), f"{column['start_time']}-{column['end_time']}", fill='#245b68', font=small_font)
    for row_index, (day, cells) in enumerate(rows):
        y = top + 45 + row_index * cell_height
        draw.rectangle((0, y, label_width, y + cell_height), fill='#e8f1f2', outline='#dce7e9')
        draw.text((20, y + 40), day, fill='#18323d', font=small_font)
        for index, cell in enumerate(cells):
            left = label_width + index * cell_width
            fill = '#eef1ef' if cell['slot']['is_break'] else '#ffffff'
            draw.rectangle((left, y, left + cell_width, y + cell_height), fill=fill, outline='#dce7e9')
            text = cell['slot']['label'] if cell['slot']['is_break'] else (cell['entry'].subject.name if cell['entry'] else 'Free')
            draw.text((left + 12, y + 40), text, fill='#60757b' if not cell['entry'] else '#18323d', font=small_font)
    output = BytesIO()
    image.save(output, format='PNG', optimize=True)
    output.seek(0)
    return send_file(output, mimetype='image/png', as_attachment=True, download_name=f'{classroom.name}-timetable.png')

@app.route('/export/pdf')
def export_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    classroom = ClassRoom.query.get_or_404(request.args.get('classroom_id', type=int))
    config, columns, rows = timetable_rows(classroom.id)
    options = export_options()
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    story = [Paragraph(options['title'], styles['Title'])]
    meta = ' | '.join(value for value in [options['institution'], classroom.name, options['academic_period'], options['subtitle']] if value)
    if meta:
        story.append(Paragraph(meta, styles['Normal']))
    story.append(Spacer(1, 6*mm))
    page_columns = 4
    for group_start in range(0, len(columns), page_columns):
        group = columns[group_start:group_start + page_columns]
        data = [['Day'] + [f"{column['label']}\n{column['start_time']}-{column['end_time']}" for column in group]]
        for day, cells in rows:
            visible = cells[group_start:group_start + page_columns]
            data.append([day] + [cell['slot']['label'] if cell['slot']['is_break'] else (cell['entry'].subject.name if cell['entry'] else 'Free') for cell in visible])
        table = Table(data, colWidths=[30*mm] + [55*mm] * len(group), repeatRows=1, rowHeights=[18*mm] + [25*mm] * len(rows))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dcebed')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#245b68')),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#e8f1f2')), ('GRID', (0, 0), (-1, -1), .5, colors.HexColor('#cbdcde')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafa')])
        ]))
        story.append(table)
        if group_start + page_columns < len(columns):
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
    document.build(story)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=f'{classroom.name}-timetable.pdf')

@app.route('/move-entry', methods=['POST'])
def move_entry():
    data = request.get_json()
    entry_id = data.get('entry_id')
    new_timeslot_id = data.get('new_timeslot_id')
    
    if not entry_id or not new_timeslot_id:
        return jsonify({'success': False, 'message': 'Missing parameters'})
    
    entry = ScheduleEntry.query.get(entry_id)
    new_timeslot = TimeSlot.query.get(new_timeslot_id)
    
    if not entry or not new_timeslot:
        return jsonify({'success': False, 'message': 'Invalid entry or timeslot'})

    before = entry_snapshot()
    if not place_with_cascade(entry, new_timeslot_id):
        restore_snapshot(before)
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Cannot move {entry.subject.name}: no valid cascading arrangement was found after checking the available class periods.'})
    errors = schedule_validation_errors()
    if errors:
        restore_snapshot(before)
        db.session.rollback()
        return jsonify({'success': False, 'message': errors[0]})
    save_snapshot()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Schedule updated successfully!'})

@app.route('/swap-entry', methods=['POST'])
def swap_entry():
    """Swap two schedule entries"""
    data = request.get_json()
    entry1_id = data.get('entry1_id')
    entry2_id = data.get('entry2_id')
    
    entry1 = ScheduleEntry.query.get(entry1_id)
    entry2 = ScheduleEntry.query.get(entry2_id)
    
    if not entry1 or not entry2:
        return jsonify({'success': False, 'message': 'Invalid entries'})

    if entry1.id == entry2.id or entry1.timeslot.is_break or entry2.timeslot.is_break:
        return jsonify({'success': False, 'message': 'Only two subject periods can be swapped.'})

    if entry1.session_id or entry2.session_id:
        return jsonify({'success': False, 'message': 'Lab blocks must be moved as a complete consecutive session.'})
    
    before = entry_snapshot()
    temp_timeslot = entry1.timeslot_id
    entry1.timeslot_id = entry2.timeslot_id
    entry2.timeslot_id = temp_timeslot
    
    locked = {entry1.id, entry2.id}
    valid = True
    for entry in (entry1, entry2):
        for conflict_id in conflicts_for(entry, entry.timeslot_id, locked):
            conflict = db.session.get(ScheduleEntry, conflict_id)
            candidates = [slot for slot in TimeSlot.query.filter_by(is_break=False).all() if slot.id not in (entry1.timeslot_id, entry2.timeslot_id)]
            if not any(place_with_cascade(conflict, slot.id, locked, {entry1.id, entry2.id}) for slot in candidates):
                valid = False
                break
        if not valid:
            break
    errors = schedule_validation_errors()
    if not valid or errors:
        restore_snapshot(before)
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Cannot complete this swap: {errors[0] if errors else "no valid cascading arrangement was found after checking the available class periods."}'})
    
    save_snapshot()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Entries swapped successfully!'})

@app.route('/undo', methods=['POST'])
def undo():
    snapshot = TimetableSnapshot.query.order_by(TimetableSnapshot.id.desc()).first()
    if not snapshot:
        return jsonify({'success': False, 'message': 'There is no timetable change to undo.'})
    for item in json.loads(snapshot.entries):
        entry = ScheduleEntry.query.get(item['id'])
        if entry:
            entry.timeslot_id = item['timeslot_id']
    db.session.delete(snapshot)
    db.session.commit()
    return jsonify({'success': True, 'message': 'The latest timetable change was undone.'})

# ==================== INITIALIZE DATABASE ====================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create timeslots if they don't exist
        if TimeSlot.query.count() == 0:
            create_timeslots()
        
        # Add sample data if database is empty
        if Teacher.query.count() == 0:
            print("Adding sample data...")
            
            # Teachers
            teachers_data = ['Dr. Smith', 'Prof. Johnson', 'Dr. Williams', 'Prof. Brown', 'Dr. Davis']
            teachers = []
            for name in teachers_data:
                t = Teacher(name=name)
                db.session.add(t)
                teachers.append(t)
            db.session.commit()
            
            # Subjects
            subjects_data = [
                ('Mathematics', 0), ('Physics', 1), ('Chemistry', 2),
                ('Computer Science', 3), ('English', 4), ('Data Structures', 3),
                ('Electronics', 1), ('Database Systems', 3)
            ]
            subjects = []
            for name, teacher_idx in subjects_data:
                s = Subject(name=name, teacher_id=teachers[teacher_idx].id)
                db.session.add(s)
                subjects.append(s)
            db.session.commit()
            
            # Classes
            classes_data = ['CSE-A', 'CSE-B', 'ECE-A']
            classrooms = []
            for name in classes_data:
                c = ClassRoom(name=name)
                db.session.add(c)
                classrooms.append(c)
            db.session.commit()
            
            # Requirements
            requirements_data = [
                (0, 0, 5), (0, 1, 4), (0, 2, 3), (0, 3, 6), (0, 4, 2),  # CSE-A
                (1, 0, 4), (1, 1, 5), (1, 3, 6), (1, 5, 4), (1, 4, 3),  # CSE-B
                (2, 1, 6), (2, 2, 5), (2, 6, 6), (2, 0, 3), (2, 4, 2)   # ECE-A
            ]
            for class_idx, subject_idx, periods in requirements_data:
                req = SubjectRequirement(
                    classroom_id=classrooms[class_idx].id,
                    subject_id=subjects[subject_idx].id,
                    periods_per_week=periods
                )
                db.session.add(req)
            db.session.commit()
            
            print("Sample data added successfully!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)