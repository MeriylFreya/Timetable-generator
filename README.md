# College Timetable Generator

A small Flask application for building and maintaining weekly college timetables. It generates schedules for multiple classes, checks teacher and class conflicts, and lets you make manual adjustments from the browser.
https://timetable-generator-jm36.onrender.com/

## What it does

- Manage teachers, subjects, classes, and weekly subject requirements.
- Generate timetables with a backtracking scheduler and a greedy fallback.
- Prevent a teacher from being assigned to two classes at the same time.
- Support laboratory requirements, consecutive lab sessions, and optional room labels.
- Configure the days, class periods, breaks, lunch, titles, and timetable metadata.
- Combine classes for a shared subject session.
- Move or swap timetable entries with validation and cascading changes.
- Undo the latest timetable edit.
- Export a class timetable as PNG or PDF.

The application stores its data in a SQLite database and creates the database tables automatically on startup. A new, empty database is populated with sample data for demonstration.

## Requirements

- Python 3.8 or newer
- A modern web browser

Python dependencies are listed in [requirements.txt](requirements.txt).

## Getting started

### Windows

From the project directory, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000> in a browser. Stop the server with `Ctrl+C`.

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

The included [start.sh](start.sh) script can also be used on systems with Bash:

```bash
./start.sh
```

## Typical workflow

1. Add teachers from **Teachers**.
2. Add subjects and assign each subject to a teacher.
3. Add the classes that need timetables.
4. Add the required number of weekly periods for each class and subject.
5. Mark laboratory subjects and configure their session length where needed.
6. Adjust the timetable structure and metadata in **Settings**.
7. Generate the timetables from the dashboard.
8. Open **Timetable** to review, move, swap, undo, or export a class schedule.

If the requested periods cannot fit the available slots, the generator returns the requirements that could not be scheduled. Review those requirements, the number of available periods, teacher assignments, and any combined groups before generating again.

## Timetable rules

The scheduler and editor validate the following conditions:

- A class has at most one subject in a time slot.
- A teacher cannot teach multiple classes in the same time slot.
- Break and lunch slots cannot contain lessons.
- Laboratory sessions occupy consecutive class periods.
- Combined sessions are placed only when all participating classes and the teacher are available.

The generator has an eight-second scheduling deadline. For difficult or over-constrained inputs it may return a partially completed timetable rather than waiting indefinitely.

## Project layout

```text
.
├── app.py                 # Flask application, models, scheduler, and routes
├── requirements.txt       # Python dependencies
├── start.sh               # Bash startup helper
├── instance/              # Flask instance data, including the SQLite database
└── templates/             # Jinja templates for the web interface
    ├── base.html
    ├── index.html
    ├── teachers.html
    ├── subjects.html
    ├── classes.html
    ├── requirements.html
    └── timetable.html
```

The database file is generated at runtime. Do not commit it if you want a clean, reproducible setup.

## Main routes

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | `GET` | Dashboard |
| `/teachers` | `GET` | Manage teachers |
| `/subjects` | `GET` | Manage subjects |
| `/classes` | `GET` | Manage classes |
| `/requirements` | `GET` | Manage weekly requirements |
| `/settings` | `POST` | Save timetable settings |
| `/generate` | `POST` | Generate all class timetables |
| `/timetable` | `GET` | View a class timetable |
| `/validate` | `GET` | Check the current schedule |
| `/export/image` | `GET` | Download a PNG timetable |
| `/export/pdf` | `GET` | Download a PDF timetable |

The add, delete, move, swap, combined-group, and undo actions are handled by the corresponding form and JSON endpoints in `app.py`.

## Configuration notes

The app currently runs with Flask's development server and uses a placeholder `SECRET_KEY` in `app.py`. Before deploying it outside a local or trusted environment, set a private secret key, use a production WSGI server, and review the application's authentication and database access requirements.

## License

No license has been specified for this project yet. Add a license file before distributing or accepting external contributions.
