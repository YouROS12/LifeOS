// LifeOS - Client-Side JavaScript
// Handles all UI interactions, API calls, and data rendering

// Global state
let allTasks = [];
let allV2GRequests = [];
let currentTaskFilter = 'all';
let currentTaskContext = 'all';
let currentV2GFilter = 'all';
let currentTab = 'dashboard';
let timeCheckInterval = null;
let lastTimeCheck = null;

const TIME_CHECK_INTERVAL = 15; // minutes

const CONTEXTS = {
    phd: { color: '#3b82f6', icon: '🎓' },
    avl: { color: '#8b5cf6', icon: '💼' },
    vitasana: { color: '#10b981', icon: '🏢' },
    personal: { color: '#f59e0b', icon: '🏠' },
    wasting: { color: '#64748b', icon: '📱' }
};

// ============================================================================
// Initialization
// ============================================================================

window.onload = function() {
    loadDashboard();
    startTimeCheckNotifications();
    setupEventListeners();

    // Refresh data every minute
    setInterval(() => {
        if (currentTab === 'dashboard' || currentTab === 'tasks') {
            loadTasks();
        }
        if (currentTab === 'v2g') {
            loadV2GRequests();
        }
    }, 60000);
};

function setupEventListeners() {
    // Context filter buttons
    document.querySelectorAll('.context-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.context-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentTaskContext = this.dataset.context;
            renderTaskTable();
        });
    });

    // Close modals when clicking outside
    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    };
}

// ============================================================================
// Tab Navigation
// ============================================================================

function switchTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');

    // Load data for the tab
    if (tabName === 'dashboard') {
        loadDashboard();
    } else if (tabName === 'tasks') {
        loadTasks();
    } else if (tabName === 'v2g') {
        loadV2GRequests();
    } else if (tabName === 'analytics') {
        loadAnalytics();
    }
}

// ============================================================================
// Dashboard
// ============================================================================

async function loadDashboard() {
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();

        allTasks = data.tasks;
        updateDashboardStats(data.stats);
        updateNextAction(data.next_action);
        updateTimeAnalytics(data.time_analytics);
        renderDashboardTasks();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateDashboardStats(stats) {
    document.getElementById('header-active').textContent = stats.total_active;
    document.getElementById('header-overdue').textContent = stats.overdue;
    document.getElementById('header-today').textContent = stats.due_today;
    document.getElementById('header-done-today').textContent = stats.completed_today;

    document.getElementById('stat-overdue').textContent = stats.overdue;
    document.getElementById('stat-today').textContent = stats.due_today;
    document.getElementById('stat-week').textContent = stats.due_week;
    document.getElementById('stat-completed').textContent = stats.completed_week;
}

function updateNextAction(nextAction) {
    const banner = document.getElementById('nextActionBanner');

    if (!nextAction) {
        banner.innerHTML = '';
        return;
    }

    const ctx = CONTEXTS[nextAction.context] || {};

    banner.innerHTML = `
        <div class="next-action-banner">
            <h2>🎯 Your Next Best Action</h2>
            <div class="next-action-content">
                <div>
                    <div class="next-task-title">${ctx.icon} ${nextAction.title}</div>
                    <div class="next-task-meta">
                        <span>⏱️ ${nextAction.estimated_time || '1 hour'}</span>
                        <span>${getEnergyIcon(nextAction.energy_needed)} ${nextAction.energy_needed || 'Medium'} Energy</span>
                        <span>Priority Score: ${nextAction._priority_score}</span>
                    </div>
                </div>
                <button class="btn" style="background: white; color: #ef4444;" onclick="startTask(${nextAction.id})">Start Now →</button>
            </div>
        </div>
    `;
}

function renderDashboardTasks() {
    const container = document.getElementById('dashboardTasks');

    const recentTasks = allTasks
        .filter(t => t.status !== 'Done')
        .slice(0, 10);

    if (recentTasks.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#64748b; padding:40px;">No active tasks</p>';
        return;
    }

    let html = '<table><thead><tr><th>Task</th><th>Context</th><th>Priority</th><th>Due Date</th><th>Status</th></tr></thead><tbody>';

    recentTasks.forEach(task => {
        const ctx = CONTEXTS[task.context] || {};
        const rowClass = getRowClass(task);
        const priorityClass = 'priority-' + task.priority.toLowerCase();

        html += `
            <tr class="${rowClass}">
                <td><strong>${task.title}</strong></td>
                <td><span class="context-tag" style="background: ${ctx.color};">${ctx.icon} ${task.context.toUpperCase()}</span></td>
                <td><span class="priority-badge ${priorityClass}">${task.priority}</span></td>
                <td>${task.due_date || '-'}</td>
                <td><span class="status-badge status-${task.status.toLowerCase().replace(' ', '')}">${task.status}</span></td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// ============================================================================
// Tasks
// ============================================================================

async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();

        allTasks = data.tasks;
        updateDashboardStats(data.stats);
        renderTaskTable();
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

function renderTaskTable() {
    const container = document.getElementById('taskTableContainer');

    let tasks = allTasks.filter(t => t.type === 'general' || !t.type);

    // Filter by context
    if (currentTaskContext !== 'all') {
        tasks = tasks.filter(t => t.context === currentTaskContext);
    }

    // Filter by view
    if (currentTaskFilter === 'urgent') {
        tasks = tasks.filter(t =>
            t.status !== 'Done' &&
            (t.priority === 'High' || t.priority === 'Critical' || isOverdue(t) || isDueToday(t))
        );
    } else if (currentTaskFilter === 'all') {
        tasks = tasks.filter(t => t.status !== 'Done');
    }

    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">🎉</div><h3>All clear!</h3><p>No tasks match your filters.</p></div>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>Task</th>
                    <th>Context</th>
                    <th>Priority</th>
                    <th>Energy</th>
                    <th>Due Date</th>
                    <th>Time</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    tasks.forEach(task => {
        const ctx = CONTEXTS[task.context] || {};
        const rowClass = getRowClass(task);
        const priorityClass = 'priority-' + task.priority.toLowerCase();

        html += `
            <tr class="${rowClass}">
                <td>
                    <strong>${task.title}</strong>
                    ${task.project ? `<br><small style="color: #94a3b8;">${task.project}</small>` : ''}
                </td>
                <td><span class="context-tag" style="background: ${ctx.color};">${ctx.icon} ${task.context.toUpperCase()}</span></td>
                <td><span class="priority-badge ${priorityClass}">${task.priority}</span></td>
                <td style="font-size: 18px;">${getEnergyIcon(task.energy_needed)}</td>
                <td>${task.due_date || '-'}</td>
                <td>${task.estimated_time || '-'}</td>
                <td><span class="status-badge status-${task.status.toLowerCase().replace(' ', '')}">${task.status}</span></td>
                <td>
                    <button class="btn btn-small" onclick="editTask(${task.id})">✏️</button>
                    <button class="btn btn-small btn-success" onclick="markTaskDone(${task.id})">✓</button>
                    <button class="btn btn-small btn-danger" onclick="deleteTask(${task.id})">🗑️</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function filterTaskView(view) {
    currentTaskFilter = view;
    renderTaskTable();
}

// ============================================================================
// V2G Requests
// ============================================================================

async function loadV2GRequests() {
    try {
        const response = await fetch('/api/v2g/requests');
        const data = await response.json();

        allV2GRequests = data.requests;
        updateV2GStats(data.stats);
        renderV2GTable();
    } catch (error) {
        console.error('Error loading V2G requests:', error);
    }
}

function updateV2GStats(stats) {
    document.getElementById('v2g-stat-total').textContent = stats.total;
    document.getElementById('v2g-stat-overdue').textContent = stats.overdue;
    document.getElementById('v2g-stat-today').textContent = stats.today;
    document.getElementById('v2g-stat-gabriel').textContent = stats.gabriel;
}

function renderV2GTable() {
    const container = document.getElementById('v2gTableContainer');

    let requests = allV2GRequests;

    // Filter by view
    if (currentV2GFilter === 'urgent') {
        requests = requests.filter(r =>
            r.status !== 'Done' &&
            (r.priority === 'High' || r.priority === 'Urgent' || isOverdue(r) || isDueToday(r))
        );
    } else {
        requests = requests.filter(r => r.status !== 'Done');
    }

    if (requests.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><h3>No V2G requests!</h3><p>All clear.</p></div>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Requester</th>
                    <th>Request</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Target Date</th>
                    <th>Gabriel?</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    requests.forEach(req => {
        const rowClass = getRowClass(req);
        const priorityClass = 'priority-' + req.priority.toLowerCase();

        html += `
            <tr class="${rowClass}">
                <td><strong>#${req.id}</strong></td>
                <td>${req.v2g_requester || 'Unknown'}</td>
                <td>${req.title.replace('V2G: ', '').replace(req.v2g_requester + ' - ', '')}</td>
                <td><span class="status-badge status-${req.status.toLowerCase().replace(' ', '')}">${req.status}</span></td>
                <td><span class="priority-badge ${priorityClass}">${req.priority}</span></td>
                <td>${req.due_date || '-'}</td>
                <td style="text-align:center; font-weight:bold; color:${req.v2g_needs_gabriel === 'YES' ? '#8b5cf6' : '#64748b'};">${req.v2g_needs_gabriel || 'NO'}</td>
                <td>
                    <button class="btn btn-small" onclick="editV2GRequest(${req.id})">✏️</button>
                    <button class="btn btn-small btn-success" onclick="markV2GDone(${req.id})">✓</button>
                    <button class="btn btn-small btn-danger" onclick="deleteV2GRequest(${req.id})">🗑️</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function filterV2GView(view) {
    currentV2GFilter = view;
    renderV2GTable();
}

// ============================================================================
// Analytics
// ============================================================================

async function loadAnalytics() {
    try {
        const response = await fetch('/api/time-analytics');
        const analytics = await response.json();

        renderWeekTimeAnalytics(analytics);
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function renderWeekTimeAnalytics(analytics) {
    const container = document.getElementById('weekTimeAnalytics');
    const week = analytics.week;

    if (week.total === 0) {
        container.innerHTML = '<p style="color:#64748b;">No time logged this week</p>';
        return;
    }

    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">';

    const contexts = [
        { key: 'phd', name: '🎓 PhD Research', color: '#3b82f6' },
        { key: 'avl', name: '💼 AVL Work', color: '#8b5cf6' },
        { key: 'vitasana', name: '🏢 VitaSana', color: '#10b981' },
        { key: 'personal', name: '🏠 Personal', color: '#f59e0b' },
        { key: 'wasting', name: '📱 Wasting Time', color: '#ef4444' }
    ];

    contexts.forEach(ctx => {
        if (week[ctx.key] > 0) {
            const percentage = ((week[ctx.key] / week.total) * 100).toFixed(1);
            html += `
                <div class="stat-card" style="border-left-color: ${ctx.color};">
                    <div class="stat-number" style="color: ${ctx.color};">${week[ctx.key]}h</div>
                    <div class="stat-label">${ctx.name}</div>
                    <div style="margin-top: 8px; font-size: 12px; color: #94a3b8;">${percentage}% of total</div>
                </div>
            `;
        }
    });

    html += `
        <div class="stat-card" style="border-left-color: #667eea;">
            <div class="stat-number" style="color: #667eea;">${week.total}h</div>
            <div class="stat-label">Total Logged</div>
        </div>
    `;

    html += '</div>';
    container.innerHTML = html;
}

function updateTimeAnalytics(analytics) {
    if (!analytics || !analytics.today) {
        return;
    }

    const container = document.getElementById('timeAnalyticsToday');
    const today = analytics.today;

    if (today.total === 0) {
        container.innerHTML = '<div style="color: #64748b;">No time logged yet</div>';
        return;
    }

    let html = '<div style="display: flex; flex-direction: column; gap: 8px;">';

    const contexts = [
        { key: 'phd', icon: '🎓', name: 'PhD' },
        { key: 'avl', icon: '💼', name: 'AVL' },
        { key: 'vitasana', icon: '🏢', name: 'VitaSana' },
        { key: 'personal', icon: '🏠', name: 'Personal' },
        { key: 'wasting', icon: '📱', name: 'Wasting' }
    ];

    contexts.forEach(ctx => {
        if (today[ctx.key] > 0) {
            html += `
                <div style="display: flex; justify-content: space-between;">
                    <span>${ctx.icon} ${ctx.name}</span>
                    <span style="font-weight: 700;">${today[ctx.key]}h</span>
                </div>
            `;
        }
    });

    html += `
        <div style="display: flex; justify-content: space-between; padding-top: 8px; margin-top: 8px; border-top: 1px solid #334155; font-weight: 700;">
            <span>Total</span>
            <span>${today.total}h</span>
        </div>
    `;

    html += '</div>';
    container.innerHTML = html;
}

// ============================================================================
// Time Tracking
// ============================================================================

function startTimeCheckNotifications() {
    // Show first time check after 15 minutes
    setTimeout(() => {
        showTimeCheck();
    }, TIME_CHECK_INTERVAL * 60000);

    // Subsequent checks every 15 minutes
    setInterval(() => {
        showTimeCheck();
    }, TIME_CHECK_INTERVAL * 60000);
}

function showTimeCheck() {
    document.getElementById('timeCheckBackdrop').style.display = 'block';
    document.getElementById('timeCheckModal').style.display = 'block';

    // Browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('⏰ Time Check!', {
            body: 'What are you working on right now?',
            requireInteraction: true
        });
    } else if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function closeTimeCheck() {
    document.getElementById('timeCheckBackdrop').style.display = 'none';
    document.getElementById('timeCheckModal').style.display = 'none';
    lastTimeCheck = new Date();
}

async function logTime(context) {
    const now = new Date();
    const minutesSinceLast = lastTimeCheck ? (now - lastTimeCheck) / 60000 : TIME_CHECK_INTERVAL;

    await fetch('/api/time-log', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            context: context,
            duration_minutes: Math.round(minutesSinceLast)
        })
    });

    closeTimeCheck();
    loadDashboard(); // Refresh to update time analytics
}

// ============================================================================
// Task Modals & Actions
// ============================================================================

function quickAdd() {
    if (currentTab === 'v2g') {
        showAddV2GModal();
    } else {
        showAddTaskModal();
    }
}

function showAddTaskModal() {
    document.getElementById('taskModalTitle').textContent = 'Add New Task';
    document.getElementById('taskForm').reset();
    document.getElementById('taskEditId').value = '';
    document.getElementById('taskModal').style.display = 'block';
}

function editTask(id) {
    const task = allTasks.find(t => t.id === id);
    if (!task) return;

    document.getElementById('taskModalTitle').textContent = 'Edit Task';
    document.getElementById('taskEditId').value = task.id;
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskContext').value = task.context;
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.due_date || '';
    document.getElementById('taskEnergy').value = task.energy_needed;
    document.getElementById('taskTime').value = task.estimated_time;
    document.getElementById('taskStatus').value = task.status;
    document.getElementById('taskProject').value = task.project || '';
    document.getElementById('taskNotes').value = task.notes || '';

    document.getElementById('taskModal').style.display = 'block';
}

function closeTaskModal() {
    document.getElementById('taskModal').style.display = 'none';
}

async function saveTask(event) {
    event.preventDefault();

    const editId = document.getElementById('taskEditId').value;
    const data = {
        title: document.getElementById('taskTitle').value,
        context: document.getElementById('taskContext').value,
        priority: document.getElementById('taskPriority').value,
        due_date: document.getElementById('taskDueDate').value,
        energy_needed: document.getElementById('taskEnergy').value,
        estimated_time: document.getElementById('taskTime').value,
        status: document.getElementById('taskStatus').value,
        project: document.getElementById('taskProject').value,
        notes: document.getElementById('taskNotes').value
    };

    if (editId) {
        await fetch(`/api/tasks/${editId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    } else {
        await fetch('/api/tasks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    }

    closeTaskModal();
    loadTasks();
    loadDashboard();
}

async function markTaskDone(id) {
    await fetch(`/api/tasks/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: 'Done'})
    });
    loadTasks();
    loadDashboard();
}

async function startTask(id) {
    await fetch(`/api/tasks/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: 'In Progress'})
    });
    loadDashboard();
}

async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;

    await fetch(`/api/tasks/${id}`, {
        method: 'DELETE'
    });
    loadTasks();
    loadDashboard();
}

// ============================================================================
// V2G Modals & Actions
// ============================================================================

function showAddV2GModal() {
    document.getElementById('v2gModalTitle').textContent = 'Add V2G Request';
    document.getElementById('v2gForm').reset();
    document.getElementById('v2gEditId').value = '';
    document.getElementById('v2gModal').style.display = 'block';
}

function editV2GRequest(id) {
    const req = allV2GRequests.find(r => r.id === id);
    if (!req) return;

    document.getElementById('v2gModalTitle').textContent = 'Edit V2G Request';
    document.getElementById('v2gEditId').value = req.id;
    document.getElementById('v2gRequester').value = req.v2g_requester || '';
    document.getElementById('v2gSource').value = req.v2g_source || 'Email';
    document.getElementById('v2gSummary').value = req.title.replace('V2G: ', '').replace(req.v2g_requester + ' - ', '');
    document.getElementById('v2gStatus').value = req.status;
    document.getElementById('v2gPriority').value = req.priority;
    document.getElementById('v2gNeedsGabriel').value = req.v2g_needs_gabriel || 'NO';
    document.getElementById('v2gTargetDate').value = req.due_date || '';
    document.getElementById('v2gGabrielQuestion').value = req.v2g_gabriel_question || '';
    document.getElementById('v2gNotes').value = req.notes || '';

    document.getElementById('v2gModal').style.display = 'block';
}

function closeV2GModal() {
    document.getElementById('v2gModal').style.display = 'none';
}

async function saveV2GRequest(event) {
    event.preventDefault();

    const editId = document.getElementById('v2gEditId').value;
    const data = {
        requester: document.getElementById('v2gRequester').value,
        source: document.getElementById('v2gSource').value,
        request_summary: document.getElementById('v2gSummary').value,
        status: document.getElementById('v2gStatus').value,
        priority: document.getElementById('v2gPriority').value,
        needs_gabriel: document.getElementById('v2gNeedsGabriel').value,
        target_date: document.getElementById('v2gTargetDate').value,
        gabriel_question: document.getElementById('v2gGabrielQuestion').value,
        notes: document.getElementById('v2gNotes').value
    };

    if (editId) {
        await fetch(`/api/v2g/requests/${editId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    } else {
        await fetch('/api/v2g/requests', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    }

    closeV2GModal();
    loadV2GRequests();
}

async function markV2GDone(id) {
    await fetch(`/api/v2g/requests/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: 'Done'})
    });
    loadV2GRequests();
}

async function deleteV2GRequest(id) {
    if (!confirm('Delete this V2G request?')) return;

    await fetch(`/api/v2g/requests/${id}`, {
        method: 'DELETE'
    });
    loadV2GRequests();
}

// ============================================================================
// Helper Functions
// ============================================================================

function getRowClass(task) {
    if (task.status === 'Done') return 'row-done';
    if (task.status === 'Blocked') return 'row-blocked';
    if (isOverdue(task)) return 'row-overdue';
    if (isDueToday(task)) return 'row-today';
    return '';
}

function isOverdue(task) {
    if (!task.due_date) return false;
    const due = new Date(task.due_date);
    const today = new Date();
    today.setHours(0,0,0,0);
    return due < today;
}

function isDueToday(task) {
    if (!task.due_date) return false;
    const due = new Date(task.due_date);
    const today = new Date();
    return due.toDateString() === today.toDateString();
}

function getEnergyIcon(energy) {
    const icons = { 'Low': '☕', 'Medium': '⚡', 'High': '🔥' };
    return icons[energy] || '⚡';
}
