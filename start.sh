#!/bin/bash

echo "🎓 College Timetable Generator - Starting..."
echo "============================================"
echo ""

# Check if Flask is installed
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Flask not found. Installing dependencies..."
    pip install flask flask-sqlalchemy --break-system-packages
    echo ""
fi

echo "✅ Dependencies OK"
echo "🚀 Starting Flask application..."
echo ""
echo "📍 Application will be available at: http://localhost:5000"
echo "📖 Press Ctrl+C to stop the server"
echo ""
echo "============================================"
echo ""

python app.py