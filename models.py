"""
LifeOS Database Models
SQLite-based data layer for unified task & time tracking
"""

import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Optional
import os

DATABASE_PATH = "lifeos.db"

# ============================================================================
# Database Connection & Setup
# ============================================================================

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_database():
    """Initialize database schema"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Tasks table (unified: general tasks + V2G requests)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL DEFAULT 'general',  -- 'general' or 'v2g_request'
                created_date TEXT NOT NULL,
                title TEXT NOT NULL,
                context TEXT NOT NULL,  -- 'phd', 'avl', 'vitasana', 'personal'
                priority TEXT NOT NULL DEFAULT 'Medium',  -- 'Low', 'Medium', 'High', 'Critical', 'Urgent'
                status TEXT NOT NULL DEFAULT 'To Do',  -- 'To Do', 'In Progress', 'Blocked', 'Waiting', 'Done'
                due_date TEXT,
                energy_needed TEXT DEFAULT 'Medium',  -- 'Low', 'Medium', 'High'
                estimated_time TEXT DEFAULT '1hour',
                project TEXT,
                notes TEXT,
                completed_date TEXT,
                last_update TEXT,

                -- V2G specific fields (NULL for general tasks)
                v2g_requester TEXT,
                v2g_source TEXT,
                v2g_needs_gabriel TEXT,  -- 'YES' or 'NO'
                v2g_gabriel_question TEXT,

                UNIQUE(id)
            )
        """)

        # Time logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                context TEXT NOT NULL,  -- 'phd', 'avl', 'vitasana', 'personal', 'wasting'
                duration_minutes INTEGER NOT NULL DEFAULT 15,
                task_id INTEGER,
                notes TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """)

        # Settings table (key-value store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_context ON tasks(context)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_logs_timestamp ON time_logs(timestamp)")

        print("✅ Database initialized successfully")

# ============================================================================
# Task Operations
# ============================================================================

def create_task(
    title: str,
    context: str,
    task_type: str = 'general',
    priority: str = 'Medium',
    status: str = 'To Do',
    due_date: str = None,
    energy_needed: str = 'Medium',
    estimated_time: str = '1hour',
    project: str = None,
    notes: str = None,
    # V2G specific
    v2g_requester: str = None,
    v2g_source: str = None,
    v2g_needs_gabriel: str = 'NO',
    v2g_gabriel_question: str = None
) -> int:
    """Create a new task (general or V2G request)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (
                type, created_date, title, context, priority, status,
                due_date, energy_needed, estimated_time, project, notes,
                last_update, v2g_requester, v2g_source, v2g_needs_gabriel,
                v2g_gabriel_question
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_type, datetime.now().strftime("%Y-%m-%d"), title, context,
            priority, status, due_date, energy_needed, estimated_time,
            project, notes, datetime.now().strftime("%Y-%m-%d"),
            v2g_requester, v2g_source, v2g_needs_gabriel, v2g_gabriel_question
        ))
        return cursor.lastrowid

def get_all_tasks(include_done: bool = False) -> List[Dict]:
    """Get all tasks"""
    with get_db() as conn:
        cursor = conn.cursor()
        if include_done:
            cursor.execute("SELECT * FROM tasks ORDER BY created_date DESC")
        else:
            cursor.execute("SELECT * FROM tasks WHERE status != 'Done' ORDER BY created_date DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_task_by_id(task_id: int) -> Optional[Dict]:
    """Get a specific task"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_task(task_id: int, **kwargs) -> bool:
    """Update task fields"""
    if not kwargs:
        return False

    # Auto-update last_update timestamp
    kwargs['last_update'] = datetime.now().strftime("%Y-%m-%d")

    # Auto-set completed_date if status changed to Done
    if kwargs.get('status') == 'Done' and 'completed_date' not in kwargs:
        kwargs['completed_date'] = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        cursor = conn.cursor()

        # Build UPDATE query dynamically
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [task_id]

        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount > 0

def delete_task(task_id: int) -> bool:
    """Delete a task"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0

def get_tasks_by_context(context: str, include_done: bool = False) -> List[Dict]:
    """Get tasks filtered by context"""
    with get_db() as conn:
        cursor = conn.cursor()
        if include_done:
            cursor.execute("SELECT * FROM tasks WHERE context = ? ORDER BY created_date DESC", (context,))
        else:
            cursor.execute("SELECT * FROM tasks WHERE context = ? AND status != 'Done' ORDER BY created_date DESC", (context,))
        return [dict(row) for row in cursor.fetchall()]

def get_v2g_requests(include_done: bool = False) -> List[Dict]:
    """Get all V2G requests"""
    with get_db() as conn:
        cursor = conn.cursor()
        if include_done:
            cursor.execute("SELECT * FROM tasks WHERE type = 'v2g_request' ORDER BY created_date DESC")
        else:
            cursor.execute("SELECT * FROM tasks WHERE type = 'v2g_request' AND status != 'Done' ORDER BY created_date DESC")
        return [dict(row) for row in cursor.fetchall()]

# ============================================================================
# Time Tracking Operations
# ============================================================================

def log_time(context: str, duration_minutes: int = 15, task_id: int = None, notes: str = None) -> int:
    """Log time spent on a context"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO time_logs (timestamp, context, duration_minutes, task_id, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), context, duration_minutes, task_id, notes))
        return cursor.lastrowid

def get_time_logs(days: int = 7) -> List[Dict]:
    """Get time logs for the last N days"""
    with get_db() as conn:
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor.execute("SELECT * FROM time_logs WHERE timestamp >= ? ORDER BY timestamp DESC", (cutoff,))
        return [dict(row) for row in cursor.fetchall()]

def get_time_analytics():
    """Calculate time spent per context (today and this week)"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    analytics = {
        "today": {"phd": 0, "avl": 0, "vitasana": 0, "personal": 0, "wasting": 0, "total": 0},
        "week": {"phd": 0, "avl": 0, "vitasana": 0, "personal": 0, "wasting": 0, "total": 0},
        "today_logs": 0,
        "week_logs": 0
    }

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, context, duration_minutes FROM time_logs")

        for row in cursor.fetchall():
            log_date = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S").date()
            context = row['context']
            duration = row['duration_minutes']

            if log_date == today:
                analytics["today"][context] += duration
                analytics["today"]["total"] += duration
                analytics["today_logs"] += 1

            if log_date >= week_ago:
                analytics["week"][context] += duration
                analytics["week"]["total"] += duration
                analytics["week_logs"] += 1

    # Convert minutes to hours (rounded to 1 decimal)
    for period in ["today", "week"]:
        for ctx in analytics[period]:
            analytics[period][ctx] = round(analytics[period][ctx] / 60, 1)

    return analytics

# ============================================================================
# Statistics & Analytics
# ============================================================================

def get_task_stats() -> Dict:
    """Calculate task statistics"""
    today = datetime.now().date()

    stats = {
        "total_active": 0,
        "overdue": 0,
        "due_today": 0,
        "due_week": 0,
        "blocked": 0,
        "by_context": {"phd": 0, "avl": 0, "vitasana": 0, "personal": 0},
        "completed_today": 0,
        "completed_week": 0,
        "v2g_needs_gabriel": 0,
        "v2g_overdue": 0
    }

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks")

        for row in cursor.fetchall():
            task = dict(row)
            status = task['status']

            # Completed tasks
            if status == 'Done':
                completed_date = task.get('completed_date')
                if completed_date:
                    try:
                        comp_date = datetime.strptime(completed_date, "%Y-%m-%d").date()
                        if comp_date == today:
                            stats["completed_today"] += 1
                        if comp_date >= today - timedelta(days=7):
                            stats["completed_week"] += 1
                    except:
                        pass
                continue

            # Active tasks
            stats["total_active"] += 1

            # Count by context
            ctx = task.get('context', 'personal')
            if ctx in stats["by_context"]:
                stats["by_context"][ctx] += 1

            # Blocked tasks
            if status == 'Blocked':
                stats["blocked"] += 1

            # V2G specific
            if task['type'] == 'v2g_request' and task.get('v2g_needs_gabriel') == 'YES':
                stats["v2g_needs_gabriel"] += 1

            # Due date analysis
            if task.get('due_date'):
                try:
                    due = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                    days = (due - today).days

                    if days < 0:
                        stats["overdue"] += 1
                        if task['type'] == 'v2g_request':
                            stats["v2g_overdue"] += 1
                    elif days == 0:
                        stats["due_today"] += 1
                    elif days <= 7:
                        stats["due_week"] += 1
                except:
                    pass

    return stats

def calculate_priority_score(task: Dict) -> int:
    """
    Smart priority algorithm considering:
    - Urgency (deadline proximity)
    - Importance (user-set priority)
    - Context (PhD > Work > Business for long-term value)
    - Energy match (does current time match energy need?)
    """
    score = 0
    today = datetime.now().date()

    # Base priority (0-300 points)
    priority_map = {"Low": 50, "Medium": 100, "High": 200, "Critical": 300, "Urgent": 300}
    score += priority_map.get(task.get("priority", "Medium"), 100)

    # Deadline urgency (0-200 points)
    if task.get("due_date"):
        try:
            due = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
            days_until = (due - today).days

            if days_until < 0:
                score += 200  # Overdue!
            elif days_until == 0:
                score += 180  # Due today
            elif days_until == 1:
                score += 150  # Due tomorrow
            elif days_until <= 3:
                score += 120  # Due this week
            elif days_until <= 7:
                score += 80
            elif days_until <= 14:
                score += 40
        except:
            pass

    # Context weight (PhD gets boost for long-term impact)
    context_weight = {
        "phd": 1.2,      # PhD is your future
        "avl": 1.0,      # Current job
        "vitasana": 1.1, # Your business
        "personal": 0.8  # Important but lower priority
    }
    score *= context_weight.get(task.get("context", "personal"), 1.0)

    # Blocked tasks get reduced priority
    if task.get("status") == "Blocked":
        score *= 0.5

    # Quick wins get a small boost
    if task.get("estimated_time") == "15min":
        score += 20

    return int(score)

def get_next_action() -> Optional[Dict]:
    """Recommend THE NEXT THING to work on right now"""
    tasks = get_all_tasks(include_done=False)

    # Filter to actionable tasks
    actionable = [t for t in tasks if t.get("status") not in ["Done", "Archived"]]

    if not actionable:
        return None

    # Calculate scores
    for task in actionable:
        task["_priority_score"] = calculate_priority_score(task)

    # Sort by score
    actionable.sort(key=lambda x: x["_priority_score"], reverse=True)

    # Get current hour to match energy
    current_hour = datetime.now().hour

    # Morning (7-12): High energy tasks
    # Afternoon (12-17): Medium energy tasks
    # Evening (17-22): Low energy tasks

    if 7 <= current_hour < 12:
        energy_pref = ["High", "Medium", "Low"]
    elif 12 <= current_hour < 17:
        energy_pref = ["Medium", "High", "Low"]
    else:
        energy_pref = ["Low", "Medium", "High"]

    # Try to match energy level
    for energy in energy_pref:
        for task in actionable[:10]:  # Check top 10
            if task.get("energy_needed") == energy:
                return task

    # If no energy match, just return highest priority
    return actionable[0]

# ============================================================================
# Settings Operations
# ============================================================================

def get_setting(key: str, default: str = None) -> str:
    """Get a setting value"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

def set_setting(key: str, value: str):
    """Set a setting value"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))

# ============================================================================
# Initialize on import
# ============================================================================

if __name__ == '__main__':
    print("Initializing LifeOS database...")
    init_database()
    print("Done!")
