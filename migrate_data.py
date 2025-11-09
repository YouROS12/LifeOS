"""
LifeOS Data Migration Script
Migrates data from old JSON files to new unified SQLite database

Run once: python migrate_data.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import os
import models
from datetime import datetime

def migrate_life_os_data():
    """Migrate data from life_os_data.json"""
    filename = "life_os_data.json"

    if not os.path.exists(filename):
        print(f"ℹ️  {filename} not found, skipping...")
        return 0

    print(f"\n📂 Migrating {filename}...")

    with open(filename, 'r') as f:
        data = json.load(f)

    migrated = 0

    # Migrate tasks
    for task in data.get("tasks", []):
        try:
            # Check if this is a V2G synced task
            is_v2g = task.get("v2g_request_id") is not None

            task_id = models.create_task(
                title=task.get("title", "Untitled"),
                context=task.get("context", "personal"),
                task_type='v2g_request' if is_v2g else 'general',
                priority=task.get("priority", "Medium"),
                status=task.get("status", "To Do"),
                due_date=task.get("due_date") or None,
                energy_needed=task.get("energy_needed", "Medium"),
                estimated_time=task.get("estimated_time", "1hour"),
                project=task.get("project") or None,
                notes=task.get("notes") or None,
                v2g_needs_gabriel=task.get("needs_gabriel", "NO") if is_v2g else None
            )

            # Set created and completed dates
            if task.get("created_date"):
                models.update_task(task_id, created_date=task["created_date"])
            if task.get("completed_date"):
                models.update_task(task_id, completed_date=task["completed_date"])

            migrated += 1
        except Exception as e:
            print(f"  ⚠️  Error migrating task '{task.get('title', 'Unknown')}': {e}")

    # Migrate time logs
    time_logs_migrated = 0
    for log in data.get("time_logs", []):
        try:
            # Parse the timestamp to extract date and time
            timestamp = log.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Manually insert into database to preserve timestamp
            with models.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO time_logs (timestamp, context, duration_minutes, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    timestamp,
                    log.get("context", "wasting"),
                    log.get("duration_minutes", 15),
                    log.get("notes")
                ))

            time_logs_migrated += 1
        except Exception as e:
            print(f"  ⚠️  Error migrating time log: {e}")

    print(f"  ✅ Migrated {migrated} tasks")
    print(f"  ✅ Migrated {time_logs_migrated} time logs")

    return migrated + time_logs_migrated

def migrate_v2g_data():
    """Migrate data from v2g_data.json"""
    filename = "v2g_data.json"

    if not os.path.exists(filename):
        print(f"ℹ️  {filename} not found, skipping...")
        return 0

    print(f"\n📂 Migrating {filename}...")

    with open(filename, 'r') as f:
        data = json.load(f)

    migrated = 0

    # Migrate V2G requests
    for req in data.get("requests", []):
        try:
            # Map V2G status to task status
            status_map = {
                "To Do": "To Do",
                "In Progress": "In Progress",
                "Needs Gabriel": "Waiting",
                "Waiting": "Waiting",
                "Done": "Done"
            }

            task_id = models.create_task(
                title=f"V2G: {req.get('requester', 'Unknown')} - {req.get('request_summary', 'Request')[:50]}",
                context='avl',  # V2G requests are always AVL
                task_type='v2g_request',
                priority=req.get("priority", "Medium"),
                status=status_map.get(req.get("status", "To Do"), "To Do"),
                due_date=req.get("target_date") or None,
                notes=req.get("notes") or None,
                v2g_requester=req.get("requester", ""),
                v2g_source=req.get("source", "Email"),
                v2g_needs_gabriel=req.get("needs_gabriel", "NO"),
                v2g_gabriel_question=req.get("gabriel_question") or None
            )

            # Set dates
            if req.get("date_received"):
                models.update_task(task_id, created_date=req["date_received"])
            if req.get("last_update"):
                models.update_task(task_id, last_update=req["last_update"])

            migrated += 1
        except Exception as e:
            print(f"  ⚠️  Error migrating V2G request '{req.get('requester', 'Unknown')}': {e}")

    print(f"  ✅ Migrated {migrated} V2G requests")

    return migrated

def backup_json_files():
    """Backup old JSON files"""
    files = ["life_os_data.json", "v2g_data.json"]
    backup_dir = "json_backup"

    backed_up = []

    for filename in files:
        if os.path.exists(filename):
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            backup_path = os.path.join(backup_dir, f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.rename(filename, backup_path)
            backed_up.append(filename)

    if backed_up:
        print(f"\n💾 Backed up old files to: {backup_dir}/")
        for f in backed_up:
            print(f"  • {f}")

def main():
    print("="*70)
    print("🔄 LifeOS Data Migration")
    print("="*70)
    print("\nThis script will migrate your data from JSON files to SQLite")
    print("\n⚠️  WARNING: This will:")
    print("  • Initialize a new SQLite database (lifeos.db)")
    print("  • Import all tasks and time logs")
    print("  • Backup and remove old JSON files")
    print("\n")

    # Auto-confirm migration
    print("\n🚀 Starting migration...\n")

    # Initialize database
    print("📊 Initializing SQLite database...")
    models.init_database()

    # Migrate data
    total_migrated = 0
    total_migrated += migrate_life_os_data()
    total_migrated += migrate_v2g_data()

    # Backup old files
    backup_json_files()

    print("\n" + "="*70)
    print(f"✅ Migration Complete!")
    print("="*70)
    print(f"\n📊 Total items migrated: {total_migrated}")
    print(f"💾 New database: lifeos.db")
    print("\n🚀 You can now run the unified LifeOS:")
    print("   python app.py")
    print("\n💡 Your old JSON files have been backed up to: json_backup/")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
