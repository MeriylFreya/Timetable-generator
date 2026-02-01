from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

db = SQLAlchemy(app)

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
    subject = db.relationship('Subject')
    
    def __repr__(self):
        return f'<SubjectRequirement {self.classroom.name} - {self.subject.name}>'

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)  # Mon, Tue, Wed, Thu, Fri
    period_number = db.Column(db.Integer, nullable=False)  # 1-6
    
    def __repr__(self):
        return f'<TimeSlot {self.day} P{self.period_number}>'

class ScheduleEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('class_room.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    
    classroom = db.relationship('ClassRoom')
    subject = db.relationship('Subject')
    teacher = db.relationship('Teacher')
    timeslot = db.relationship('TimeSlot')
    
    def __repr__(self):
        return f'<ScheduleEntry {self.classroom.name} - {self.subject.name}>'

# ==================== TIMETABLE GENERATION LOGIC ====================

def generate_timetables():
    """Generate timetables for all classes using backtracking algorithm"""
    
    # Clear existing schedule entries
    ScheduleEntry.query.delete()
    db.session.commit()
    
    # Get all timeslots
    timeslots = TimeSlot.query.all()
    if not timeslots:
        create_timeslots()
        timeslots = TimeSlot.query.all()
    
    # Get all classes
    classrooms = ClassRoom.query.all()
    
    # For each class, create a schedule
    for classroom in classrooms:
        requirements = SubjectRequirement.query.filter_by(classroom_id=classroom.id).all()
        
        # Create list of subjects to schedule (with repetitions based on periods_per_week)
        subjects_to_schedule = []
        for req in requirements:
            for _ in range(req.periods_per_week):
                subjects_to_schedule.append(req.subject)
        
        # Shuffle for randomness
        random.shuffle(subjects_to_schedule)
        
        # Try to schedule using backtracking
        if not schedule_class(classroom, subjects_to_schedule, timeslots, 0):
            # If backtracking fails, use greedy approach
            schedule_class_greedy(classroom, subjects_to_schedule, timeslots)
    
    db.session.commit()
    return True

def schedule_class(classroom, subjects, timeslots, subject_index):
    """Backtracking algorithm to schedule subjects"""
    if subject_index >= len(subjects):
        return True  # All subjects scheduled
    
    subject = subjects[subject_index]
    
    # Try each timeslot
    for timeslot in timeslots:
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
        for timeslot in timeslots:
            if is_valid_assignment(classroom, subject, timeslot):
                entry = ScheduleEntry(
                    classroom_id=classroom.id,
                    subject_id=subject.id,
                    teacher_id=subject.teacher_id,
                    timeslot_id=timeslot.id
                )
                db.session.add(entry)
                break

def is_valid_assignment(classroom, subject, timeslot):
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
    
    return True

def create_timeslots():
    """Create timeslots for Mon-Fri, 6 periods each"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in days:
        for period in range(1, 7):
            timeslot = TimeSlot(day=day, period_number=period)
            db.session.add(timeslot)
    db.session.commit()

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

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
    
    if classroom_id and subject_id and periods:
        # Check if requirement already exists
        existing = SubjectRequirement.query.filter_by(
            classroom_id=classroom_id,
            subject_id=subject_id
        ).first()
        
        if existing:
            existing.periods_per_week = periods
        else:
            requirement = SubjectRequirement(
                classroom_id=classroom_id,
                subject_id=subject_id,
                periods_per_week=periods
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
        generate_timetables()
        return jsonify({'success': True, 'message': 'Timetables generated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/timetable')
def timetable():
    classroom_id = request.args.get('classroom_id', type=int)
    classrooms = ClassRoom.query.all()
    
    if not classroom_id and classrooms:
        classroom_id = classrooms[0].id
    
    if classroom_id:
        classroom = ClassRoom.query.get(classroom_id)
        entries = ScheduleEntry.query.filter_by(classroom_id=classroom_id).all()
        timeslots = TimeSlot.query.all()
        
        # Organize entries by day and period
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        timetable_grid = {}
        for day in days:
            timetable_grid[day] = {}
            for period in range(1, 7):
                timetable_grid[day][period] = None
        
        for entry in entries:
            day = entry.timeslot.day
            period = entry.timeslot.period_number
            timetable_grid[day][period] = entry
        
        return render_template('timetable.html', 
                             classrooms=classrooms,
                             current_classroom=classroom,
                             timetable_grid=timetable_grid,
                             days=days,
                             timeslots=timeslots)
    
    return render_template('timetable.html', classrooms=classrooms)

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
    
    # Check if classroom is free at new timeslot
    existing_class = ScheduleEntry.query.filter_by(
        classroom_id=entry.classroom_id,
        timeslot_id=new_timeslot_id
    ).first()
    
    if existing_class and existing_class.id != entry_id:
        return jsonify({'success': False, 'message': 'This slot is already occupied!'})
    
    # Check if teacher is free at new timeslot
    existing_teacher = ScheduleEntry.query.filter_by(
        teacher_id=entry.teacher_id,
        timeslot_id=new_timeslot_id
    ).first()
    
    if existing_teacher and existing_teacher.id != entry_id:
        return jsonify({
            'success': False, 
            'message': f'Teacher clash! {entry.teacher.name} is already teaching {existing_teacher.subject.name} to {existing_teacher.classroom.name} at this time.'
        })
    
    # Update the entry
    entry.timeslot_id = new_timeslot_id
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
    
    # Swap timeslots
    temp_timeslot = entry1.timeslot_id
    entry1.timeslot_id = entry2.timeslot_id
    entry2.timeslot_id = temp_timeslot
    
    # Validate both entries
    # Check teacher clashes
    teacher1_clash = ScheduleEntry.query.filter_by(
        teacher_id=entry1.teacher_id,
        timeslot_id=entry1.timeslot_id
    ).filter(ScheduleEntry.id != entry1.id).first()
    
    teacher2_clash = ScheduleEntry.query.filter_by(
        teacher_id=entry2.teacher_id,
        timeslot_id=entry2.timeslot_id
    ).filter(ScheduleEntry.id != entry2.id).first()
    
    if teacher1_clash or teacher2_clash:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Teacher clash detected during swap!'})
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Entries swapped successfully!'})

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