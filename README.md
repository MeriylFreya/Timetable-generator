# 🎓 College Timetable Generator

A complete web-based timetable generation system with **automatic scheduling**, **teacher clash prevention**, and **drag-and-drop editing**.

## 🌟 Features

### Core Features
- **Automatic Timetable Generation**: Uses backtracking algorithm to generate clash-free timetables
- **Teacher Clash Prevention**: Ensures no teacher is assigned to multiple classes at the same time
- **Multi-Class Support**: Generate timetables for all classes simultaneously
- **Drag-and-Drop Editor**: Manually adjust timetables with real-time validation
- **Beautiful UI**: Modern, responsive design with Bootstrap 5

### Management Features
- ✅ Manage Teachers
- ✅ Manage Subjects
- ✅ Manage Classes
- ✅ Configure Subject Requirements (periods per week)
- ✅ View and Edit Timetables
- ✅ Real-time Clash Detection

## 🏗️ Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite (with SQLAlchemy ORM)
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Drag & Drop**: HTML5 Drag and Drop API
- **JavaScript**: Vanilla JS (no frameworks needed)

## 📋 Database Models

### Teacher
- `id`: Primary Key
- `name`: Teacher's name

### Subject
- `id`: Primary Key
- `name`: Subject name
- `teacher_id`: Foreign Key to Teacher

### ClassRoom
- `id`: Primary Key
- `name`: Class name (e.g., CSE-A)

### SubjectRequirement
- `id`: Primary Key
- `classroom_id`: Foreign Key to ClassRoom
- `subject_id`: Foreign Key to Subject
- `periods_per_week`: How many periods needed per week

### TimeSlot
- `id`: Primary Key
- `day`: Monday-Friday
- `period_number`: 1-6

### ScheduleEntry
- `id`: Primary Key
- `classroom_id`: Foreign Key to ClassRoom
- `subject_id`: Foreign Key to Subject
- `teacher_id`: Foreign Key to Teacher
- `timeslot_id`: Foreign Key to TimeSlot

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Flask and Flask-SQLAlchemy

### Installation Steps

1. **Install Dependencies**
   ```bash
   pip install flask flask-sqlalchemy --break-system-packages
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access the Application**
   - Open your browser and navigate to: `http://localhost:5000`

## 📖 Usage Guide

### Step 1: Add Teachers
1. Navigate to **Teachers** page
2. Add teacher names (e.g., "Dr. Smith", "Prof. Johnson")

### Step 2: Add Subjects
1. Navigate to **Subjects** page
2. Add subjects and assign them to teachers
3. Example: "Mathematics" → Dr. Smith

### Step 3: Create Classes
1. Navigate to **Classes** page
2. Add class names (e.g., "CSE-A", "ECE-B")

### Step 4: Configure Subject Requirements
1. Navigate to **Requirements** page
2. For each class, specify:
   - Which subjects are needed
   - How many periods per week for each subject
3. Example: CSE-A needs Mathematics 5 periods/week

### Step 5: Generate Timetables
1. Go to **Dashboard**
2. Click **"Generate Timetables Now"**
3. The system will automatically create clash-free schedules

### Step 6: View & Edit Timetables
1. Navigate to **View Timetable** page
2. Select a class from the dropdown
3. **Drag and drop** subject blocks to adjust the schedule
4. The system will automatically validate moves and prevent clashes

## 🧠 Timetable Generation Algorithm

The system uses a **backtracking algorithm** with the following logic:

1. **Initialize**: Create all time slots (5 days × 6 periods = 30 slots)
2. **Iterate**: For each class:
   - Get all subject requirements
   - Create a list of subjects (with repetitions based on periods needed)
3. **Assign**: Try to place each subject in a time slot
4. **Validate**: Before assignment, check:
   - Class is free at that time
   - Teacher is not teaching another class at that time
5. **Backtrack**: If no valid slot found, backtrack and try different combinations
6. **Fallback**: If backtracking fails, use greedy algorithm to fill what's possible

## 🎨 UI Features

### Dashboard
- Quick access to all management features
- One-click timetable generation
- Feature highlights

### Management Pages
- Clean, card-based layouts
- Add/Delete functionality for all entities
- Real-time validation

### Timetable View
- **Grid Layout**: Days vs Periods
- **Color-Coded Blocks**: Each subject in a colored block
- **Drag-and-Drop**: Move subjects between slots
- **Real-Time Validation**: Instant clash detection
- **Responsive Design**: Works on all screen sizes

## 🔧 API Endpoints

### Teacher Management
- `GET /teachers` - View all teachers
- `POST /teachers/add` - Add a new teacher
- `POST /teachers/delete/<id>` - Delete a teacher

### Subject Management
- `GET /subjects` - View all subjects
- `POST /subjects/add` - Add a new subject
- `POST /subjects/delete/<id>` - Delete a subject

### Class Management
- `GET /classes` - View all classes
- `POST /classes/add` - Add a new class
- `POST /classes/delete/<id>` - Delete a class

### Requirements
- `GET /requirements` - View all requirements
- `POST /requirements/add` - Add/update requirement
- `POST /requirements/delete/<id>` - Delete requirement

### Timetable
- `GET /timetable` - View timetable for a class
- `POST /generate` - Generate timetables for all classes
- `POST /move-entry` - Move a schedule entry (drag-and-drop)

## 🎯 Timetable Rules

The system enforces these constraints:

1. ✅ **No Teacher Clash**: A teacher cannot teach two classes at the same time
2. ✅ **No Class Overlap**: A class cannot have two subjects simultaneously
3. ✅ **Exact Period Count**: Each subject gets exactly the required number of periods per week
4. ✅ **Valid Time Slots**: All entries fit within Mon-Fri, 6 periods per day

## 📊 Sample Data

The application comes with sample data for quick testing:

**Teachers**: Dr. Smith, Prof. Johnson, Dr. Williams, Prof. Brown, Dr. Davis

**Subjects**: Mathematics, Physics, Chemistry, Computer Science, English, Data Structures, Electronics, Database Systems

**Classes**: CSE-A, CSE-B, ECE-A

## 🐛 Troubleshooting

### Issue: Timetable generation fails
**Solution**: Make sure you have:
- Added teachers
- Created subjects with teacher assignments
- Created classes
- Configured subject requirements for all classes
- Ensured total periods don't exceed 30 per week per class

### Issue: Drag-and-drop not working
**Solution**: 
- Make sure JavaScript is enabled in your browser
- Check browser console for errors
- Try refreshing the page

### Issue: Teacher clash still occurs
**Solution**: The system validates moves before saving. If you see a clash error, the move was prevented - this is expected behavior.

## 🔮 Future Enhancements

Potential features for future versions:
- Export timetables to PDF/Excel
- Multiple timetable templates
- Break/lunch period management
- Room allocation
- Teacher preference settings
- Weekly timetable variations
- Email notifications
- Mobile app

## 📝 License

This project is open source and available for educational purposes.

## 👨‍💻 Developer Notes

### Code Structure
```
timetable_generator/
├── app.py                 # Main Flask application
├── templates/
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Dashboard
│   ├── teachers.html     # Teacher management
│   ├── subjects.html     # Subject management
│   ├── classes.html      # Class management
│   ├── requirements.html # Requirements configuration
│   └── timetable.html    # Timetable view with drag-drop
└── timetable.db          # SQLite database (auto-created)
```

### Key Functions
- `generate_timetables()`: Main generation algorithm
- `schedule_class()`: Backtracking scheduler
- `is_valid_assignment()`: Validation logic
- `move_entry()`: Drag-and-drop handler

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📞 Support

For issues or questions, please create an issue in the repository.

---

**Built with ❤️ for educational institutions**