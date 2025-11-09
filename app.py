"""
LifeOS - Unified Command Center
Integrated task management, V2G tracking, and time analytics

Run: python app.py
Access: http://localhost:5001
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import models

app = Flask(__name__)

# Context definitions
CONTEXTS = {
    "phd": {"name": "🎓 PhD Research", "color": "#3b82f6", "icon": "🎓"},
    "avl": {"name": "💼 AVL Work", "color": "#8b5cf6", "icon": "💼"},
    "vitasana": {"name": "🏢 VitaSana", "color": "#10b981", "icon": "🏢"},
    "personal": {"name": "🏠 Personal", "color": "#f59e0b", "icon": "🏠"}
}

# ============================================================================
# Web Routes
# ============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', contexts=CONTEXTS)

# ============================================================================
# API Routes - Tasks
# ============================================================================

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks with statistics and next action"""
    tasks = models.get_all_tasks(include_done=False)
    stats = models.get_task_stats()
    next_action = models.get_next_action()
    time_analytics = models.get_time_analytics()

    return jsonify({
        "tasks": tasks,
        "stats": stats,
        "next_action": next_action,
        "time_analytics": time_analytics
    })

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.json

    task_id = models.create_task(
        title=data.get('title', ''),
        context=data.get('context', 'personal'),
        task_type='general',
        priority=data.get('priority', 'Medium'),
        status=data.get('status', 'To Do'),
        due_date=data.get('due_date') or None,
        energy_needed=data.get('energy_needed', 'Medium'),
        estimated_time=data.get('estimated_time', '1hour'),
        project=data.get('project') or None,
        notes=data.get('notes') or None
    )

    return jsonify({"success": True, "id": task_id})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    data = request.json
    success = models.update_task(task_id, **data)
    return jsonify({"success": success})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    success = models.delete_task(task_id)
    return jsonify({"success": success})

# ============================================================================
# API Routes - V2G Requests
# ============================================================================

@app.route('/api/v2g/requests', methods=['GET'])
def get_v2g_requests():
    """Get all V2G requests with statistics"""
    requests = models.get_v2g_requests(include_done=False)

    # Calculate V2G-specific stats
    today = datetime.now().date()
    stats = {
        "total": 0,
        "overdue": 0,
        "today": 0,
        "week": 0,
        "gabriel": 0,
        "stale": 0
    }

    for req in requests:
        stats["total"] += 1

        if req.get("v2g_needs_gabriel") == "YES":
            stats["gabriel"] += 1

        if req.get("due_date"):
            try:
                target = datetime.strptime(req["due_date"], "%Y-%m-%d").date()
                days = (target - today).days
                if days < 0:
                    stats["overdue"] += 1
                elif days == 0:
                    stats["today"] += 1
                elif days <= 7:
                    stats["week"] += 1
            except:
                pass

        if req.get("last_update"):
            try:
                last = datetime.strptime(req["last_update"], "%Y-%m-%d").date()
                if (today - last).days >= 3:
                    stats["stale"] += 1
            except:
                pass

    return jsonify({"requests": requests, "stats": stats})

@app.route('/api/v2g/requests', methods=['POST'])
def create_v2g_request():
    """Create a new V2G request"""
    data = request.json

    task_id = models.create_task(
        title=f"V2G: {data.get('requester', 'Unknown')} - {data.get('request_summary', 'Request')[:50]}",
        context='avl',  # V2G requests are always AVL context
        task_type='v2g_request',
        priority=data.get('priority', 'Medium'),
        status=data.get('status', 'To Do'),
        due_date=data.get('target_date') or None,
        notes=data.get('notes') or None,
        v2g_requester=data.get('requester', ''),
        v2g_source=data.get('source', 'Email'),
        v2g_needs_gabriel=data.get('needs_gabriel', 'NO'),
        v2g_gabriel_question=data.get('gabriel_question') or None
    )

    return jsonify({"success": True, "id": task_id})

@app.route('/api/v2g/requests/<int:req_id>', methods=['PUT'])
def update_v2g_request(req_id):
    """Update a V2G request"""
    data = request.json

    # Map V2G fields to task fields
    update_data = {}

    if 'status' in data:
        update_data['status'] = data['status']
    if 'priority' in data:
        update_data['priority'] = data['priority']
    if 'target_date' in data:
        update_data['due_date'] = data['target_date']
    if 'notes' in data:
        update_data['notes'] = data['notes']
    if 'requester' in data:
        update_data['v2g_requester'] = data['requester']
    if 'source' in data:
        update_data['v2g_source'] = data['source']
    if 'needs_gabriel' in data:
        update_data['v2g_needs_gabriel'] = data['needs_gabriel']
    if 'gabriel_question' in data:
        update_data['v2g_gabriel_question'] = data['gabriel_question']
    if 'request_summary' in data:
        # Update title with new summary
        task = models.get_task_by_id(req_id)
        if task:
            requester = data.get('requester', task.get('v2g_requester', 'Unknown'))
            update_data['title'] = f"V2G: {requester} - {data['request_summary'][:50]}"

    success = models.update_task(req_id, **update_data)
    return jsonify({"success": success})

@app.route('/api/v2g/requests/<int:req_id>', methods=['DELETE'])
def delete_v2g_request(req_id):
    """Delete a V2G request"""
    success = models.delete_task(req_id)
    return jsonify({"success": success})

# ============================================================================
# API Routes - Time Tracking
# ============================================================================

@app.route('/api/time-log', methods=['POST'])
def log_time():
    """Log time spent on a context"""
    data = request.json

    log_id = models.log_time(
        context=data.get('context', 'wasting'),
        duration_minutes=data.get('duration_minutes', 15),
        task_id=data.get('task_id'),
        notes=data.get('notes')
    )

    return jsonify({"success": True, "id": log_id})

@app.route('/api/time-analytics', methods=['GET'])
def get_time_analytics():
    """Get time tracking analytics"""
    analytics = models.get_time_analytics()
    return jsonify(analytics)

# ============================================================================
# API Routes - Statistics
# ============================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get comprehensive statistics"""
    task_stats = models.get_task_stats()
    time_analytics = models.get_time_analytics()

    return jsonify({
        "tasks": task_stats,
        "time": time_analytics
    })

# ============================================================================
# Initialize & Run
# ============================================================================

def init_app():
    """Initialize the application"""
    models.init_database()
    print("\n" + "="*70)
    print("🧠 LifeOS - Unified Command Center")
    print("="*70)
    print("\n🚀 Starting your integrated productivity system...")
    print("\n📊 Open: http://localhost:5001")
    print("\n💡 Features:")
    print("   • Task Management (PhD/AVL/VitaSana/Personal)")
    print("   • V2G Request Tracking")
    print("   • Smart Priority Engine")
    print("   • Time Tracking & Analytics")
    print("   • Energy-Aware Recommendations")
    print("\n💾 Database: lifeos.db (SQLite)")
    print("\n⏹️  Press Ctrl+C to stop")
    print("="*70 + "\n")

if __name__ == '__main__':
    init_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
