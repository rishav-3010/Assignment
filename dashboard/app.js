/* ─── Clara Answers Dashboard - App Logic ─── */

// ─── State ──────────────────────────────────────────
let accounts = {};
let selectedAccount = null;
let activeTab = 'memo';

// ─── Sample Data (built-in for demo purposes) ──────
const SAMPLE_DATA = {
    "bens_electric_solutions": {
        v1: {
            "account_memo.json": {
                account_id: "bens_electric_solutions",
                company_name: "Ben's Electric Solutions",
                business_hours: { days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], start: "7:00 AM", end: "5:00 PM", timezone: "America/Denver" },
                office_address: { street: "", city: "Calgary", state: "Alberta", zip_code: "", country: "CA" },
                services_supported: ["Electrical Installation", "Electrical Repair", "Panel Upgrades", "Inspections"],
                emergency_definition: ["Power Outage", "Electrical Fire", "Exposed Wiring", "Sparking Outlets"],
                emergency_routing_rules: [{ contact_name: "Ben Parker", phone_number: "", role: "Owner", priority: 1, notes: "Primary after-hours contact" }],
                non_emergency_routing_rules: [{ contact_name: "Shelley Manley", phone_number: "403-870-8494", role: "Dispatcher", priority: 1, notes: "Handles all scheduling" }],
                call_transfer_rules: { timeout_seconds: 60, max_retries: 2, fallback_message: "I apologize, I'm unable to connect you right now. Let me take your information and have someone call you back as soon as possible.", transfer_numbers: ["403-870-8494"], notes: "" },
                integration_constraints: [],
                after_hours_flow_summary: "Take a message with name and number, call back in the morning",
                office_hours_flow_summary: "Route through dispatcher Shelley Manley",
                questions_or_unknowns: ["Exact office address not provided", "Ben's direct phone number not shared during demo", "No integration constraints discussed"],
                notes: "Also partners with G&M Pressure Washing. Contact: gm_pressurewash@yahoo.ca",
                version: "v1",
                source: "demo"
            },
            "agent_spec.json": {
                agent_name: "Clara - Ben's Electric Solutions",
                version: "v1",
                version_description: "Preliminary agent from demo call",
                voice_id: "retell-Cimo",
                voice_model: "eleven_turbo_v2",
                voice_style: "professional, warm, empathetic",
                language: "en-US",
                system_prompt: "[Generated system prompt - see Prompt tab]",
                key_variables: {
                    timezone: "America/Denver",
                    business_hours: "7:00 AM - 5:00 PM",
                    business_days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    services: ["Electrical Installation", "Electrical Repair", "Panel Upgrades", "Inspections"]
                },
                call_transfer_protocol: { transfer_numbers: ["403-870-8494"], timeout_seconds: 60, max_retries: 2 },
                fallback_protocol: { message: "I apologize, I'm unable to connect you right now.", action: "collect_info_and_notify" },
                boosted_keywords: ["electrical", "panel", "wiring", "inspection", "Ben's Electric Solutions"]
            }
        },
        v2: {
            "account_memo.json": {
                account_id: "bens_electric_solutions",
                company_name: "Ben's Electric Solutions",
                business_hours: { days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], start: "7:00 AM", end: "5:00 PM", timezone: "America/Edmonton" },
                office_address: { street: "445 35th Street NE", city: "Calgary", state: "Alberta", zip_code: "T2A 6K3", country: "CA" },
                services_supported: ["Electrical Installation", "Electrical Repair", "Panel Upgrades", "Inspections"],
                emergency_definition: ["Power Outage", "Electrical Fire", "Exposed Wiring", "Sparking Outlets", "Burning Smell"],
                emergency_routing_rules: [
                    { contact_name: "On-Call Technician", phone_number: "403-555-0199", role: "On-call (rotating)", priority: 1, notes: "45-second timeout" },
                    { contact_name: "Ben Parker", phone_number: "403-870-1122", role: "Owner", priority: 2, notes: "If on-call doesn't answer" }
                ],
                non_emergency_routing_rules: [{ contact_name: "Shelley Manley", phone_number: "403-870-8494", role: "Dispatcher", priority: 1, notes: "Handles all scheduling and triage" }],
                call_transfer_rules: { timeout_seconds: 45, max_retries: 2, fallback_message: "I apologize, I'm unable to connect you right now. Let me take your information and I'll text both our on-call team and the owner. Someone will call you back as soon as possible.", transfer_numbers: ["403-555-0199", "403-870-1122", "403-870-8494"], notes: "Text both numbers if no answer" },
                integration_constraints: ["Never create electrical inspection jobs directly in ServiceTrade - must go through Shelley", "G&M Pressure Washing calls must be flagged separately from electrical jobs"],
                after_hours_flow_summary: "Emergency: try on-call (403-555-0199), then Ben (403-870-1122), then text both. Non-emergency: take message for next business day.",
                office_hours_flow_summary: "All calls go through Shelley Manley (403-870-8494) for triage and dispatch. Ask if caller is new or existing customer.",
                questions_or_unknowns: ["Saturday hours are 8 AM to 2 PM (different from weekday hours)"],
                notes: "Partners with G&M Pressure Washing. Sparking outlet or burning smell = always emergency. Ask if new/existing customer.",
                version: "v2",
                source: "onboarding"
            },
            "agent_spec.json": {
                agent_name: "Clara - Ben's Electric Solutions",
                version: "v2",
                version_description: "Updated agent after onboarding",
                voice_id: "retell-Cimo",
                voice_model: "eleven_turbo_v2",
                voice_style: "professional, warm, empathetic",
                language: "en-US",
                system_prompt: "[Updated system prompt with confirmed hours, emergency routing, and integration constraints]",
                key_variables: {
                    timezone: "America/Edmonton",
                    business_hours: "7:00 AM - 5:00 PM (Sat: 8:00 AM - 2:00 PM)",
                    business_days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    services: ["Electrical Installation", "Electrical Repair", "Panel Upgrades", "Inspections"]
                },
                call_transfer_protocol: { transfer_numbers: ["403-555-0199", "403-870-1122", "403-870-8494"], timeout_seconds: 45, max_retries: 2 },
                fallback_protocol: { message: "I apologize, I'm unable to connect you right now. I'll text both our on-call technician and the owner immediately.", action: "collect_info_and_notify_via_text" },
                boosted_keywords: ["electrical", "panel", "wiring", "inspection", "Ben's Electric Solutions", "sparking", "burning"]
            },
            "changelog.json": {
                account_id: "bens_electric_solutions",
                company_name: "Ben's Electric Solutions",
                from_version: "v1",
                to_version: "v2",
                changes: [
                    { field: "business_hours.days", old_value: "Mon-Fri", new_value: "Mon-Sat (Sat: 8AM-2PM)", reason: "Saturday hours confirmed during onboarding" },
                    { field: "business_hours.timezone", old_value: "America/Denver", new_value: "America/Edmonton", reason: "Corrected timezone for Calgary" },
                    { field: "office_address", old_value: "(empty)", new_value: "445 35th Street NE, Calgary, AB T2A 6K3", reason: "Address provided during onboarding" },
                    { field: "emergency_definition", old_value: "4 triggers", new_value: "5 triggers (added 'Burning Smell')", reason: "Client specified burning smell as always emergency" },
                    { field: "emergency_routing_rules", old_value: "Ben Parker only", new_value: "On-call tech (priority 1) + Ben (priority 2)", reason: "Structured escalation chain confirmed" },
                    { field: "call_transfer_rules.timeout_seconds", old_value: "60", new_value: "45", reason: "Client requested 45-second timeout for on-call" },
                    { field: "integration_constraints", old_value: "(none)", new_value: "2 constraints added", reason: "ServiceTrade and G&M Pressure constraints specified" }
                ],
                summary: "Updated 7 fields from onboarding. Major changes: added Saturday hours, established emergency escalation chain, added integration constraints."
            }
        }
    },
    "apex_fire_protection": {
        v1: {
            "account_memo.json": {
                account_id: "apex_fire_protection",
                company_name: "Apex Fire Protection",
                business_hours: { days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], start: "8:00 AM", end: "5:00 PM", timezone: "America/Chicago" },
                office_address: { street: "", city: "Dallas", state: "Texas", zip_code: "", country: "US" },
                services_supported: ["Fire Sprinkler Installation", "Fire Sprinkler Maintenance", "Fire Alarm Systems", "Fire Extinguisher Inspections", "Backflow Prevention Testing"],
                emergency_definition: ["Sprinkler System Leaks/Breaks", "Fire Alarm Malfunctions", "Fire Suppression System Failure"],
                emergency_routing_rules: [{ contact_name: "Mike Torres", phone_number: "214-555-0147", role: "Dispatch Manager", priority: 1, notes: "" }],
                non_emergency_routing_rules: [],
                call_transfer_rules: { timeout_seconds: 60, max_retries: 2, fallback_message: "I apologize, I'm unable to connect you right now.", transfer_numbers: ["214-555-0147"], notes: "Field supervisor as backup - number not provided" },
                integration_constraints: [],
                after_hours_flow_summary: "24/7 emergency availability",
                office_hours_flow_summary: "Route to dispatch",
                questions_or_unknowns: ["Field supervisor name and number not provided", "Office address incomplete", "Non-emergency routing not specified"],
                notes: "30 technicians, DFW area. Emergencies are 24/7.",
                version: "v1",
                source: "demo"
            }
        },
        v2: {
            "account_memo.json": {
                account_id: "apex_fire_protection",
                company_name: "Apex Fire Protection",
                business_hours: { days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], start: "8:00 AM", end: "5:00 PM", timezone: "America/Chicago" },
                office_address: { street: "2847 Commerce Street, Suite 200", city: "Dallas", state: "Texas", zip_code: "75226", country: "US" },
                services_supported: ["Fire Sprinkler Installation", "Fire Sprinkler Maintenance", "Fire Alarm Systems", "Fire Extinguisher Inspections", "Backflow Prevention Testing"],
                emergency_definition: ["Sprinkler System Leaks/Breaks", "Fire Alarm Malfunctions", "Fire Suppression System Failure", "Active Sprinkler Head Discharge"],
                emergency_routing_rules: [
                    { contact_name: "Mike Torres", phone_number: "214-555-0147", role: "Dispatch Manager", priority: 1, notes: "30-second timeout" },
                    { contact_name: "Jake Williams", phone_number: "214-555-0283", role: "Field Supervisor", priority: 2, notes: "Backup if Mike unavailable" }
                ],
                non_emergency_routing_rules: [{ contact_name: "Mike Torres", phone_number: "214-555-0147", role: "Dispatch Manager", priority: 1, notes: "During business hours" }],
                call_transfer_rules: { timeout_seconds: 30, max_retries: 2, fallback_message: "I apologize, I'm unable to reach our team right now. I've sent an emergency notification and someone will call you back within 15 minutes.", transfer_numbers: ["214-555-0147", "214-555-0283"], notes: "15-minute callback promise for emergencies" },
                integration_constraints: ["Never create sprinkler inspection jobs automatically in ServiceTrade", "Backflow testing jobs require separate category"],
                after_hours_flow_summary: "Emergency: Mike → Jake → emergency text to both with 15-min callback promise. Non-emergency: take message.",
                office_hours_flow_summary: "Route through Mike Torres for dispatch. Saturday 9AM-1PM for emergency follow-ups only.",
                questions_or_unknowns: [],
                notes: "Active sprinkler head discharge = highest priority. Get address immediately, transfer to Mike right away.",
                version: "v2",
                source: "onboarding"
            },
            "changelog.json": {
                account_id: "apex_fire_protection",
                company_name: "Apex Fire Protection",
                from_version: "v1",
                to_version: "v2",
                changes: [
                    { field: "office_address", old_value: "(incomplete)", new_value: "2847 Commerce St, Suite 200, Dallas, TX 75226", reason: "Full address provided during onboarding" },
                    { field: "emergency_routing_rules", old_value: "Mike Torres only", new_value: "Mike Torres (1st) + Jake Williams (2nd)", reason: "Escalation chain confirmed" },
                    { field: "call_transfer_rules.timeout_seconds", old_value: "60", new_value: "30", reason: "Client wants faster 30-second timeout" },
                    { field: "integration_constraints", old_value: "(none)", new_value: "2 ServiceTrade constraints", reason: "Confirmed during onboarding" },
                    { field: "emergency_definition", old_value: "3 triggers", new_value: "4 triggers (added active sprinkler discharge)", reason: "Highest priority emergency specified" }
                ],
                summary: "Updated 5 fields. Key: full address, escalation chain with Jake Williams, 30s timeout, ServiceTrade constraints."
            }
        }
    }
};

// ─── Initialization ─────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadSampleData();
});

// ─── Theme Toggle ───────────────────────────────────
function toggleTheme() {
    document.body.classList.toggle('light');
    const btn = document.getElementById('themeToggle');
    btn.querySelector('.btn-icon').textContent = document.body.classList.contains('light') ? '☀️' : '🌙';
}

// ─── Data Loading ───────────────────────────────────
function loadSampleData() {
    // Prefer real pipeline data if available (generated by export_dashboard_data.py)
    if (typeof PIPELINE_DATA !== 'undefined' && Object.keys(PIPELINE_DATA).length > 0) {
        accounts = PIPELINE_DATA;
    } else {
        accounts = {};
    }
    renderAccountList();
    updateStats();
}

function loadSampleDataAndClose() {
    loadSampleData();
    closeModal();
}

function loadFromPaste() {
    const input = document.getElementById('jsonInput').value.trim();
    if (!input) return;
    try {
        const data = JSON.parse(input);
        if (data.account_id) {
            const aid = data.account_id;
            if (!accounts[aid]) accounts[aid] = {};
            const version = data.version || 'v1';
            if (!accounts[aid][version]) accounts[aid][version] = {};
            accounts[aid][version]['account_memo.json'] = data;
        }
        renderAccountList();
        updateStats();
        closeModal();
    } catch (e) {
        alert('Invalid JSON: ' + e.message);
    }
}

function loadFromFiles() {
    const input = document.getElementById('fileInput');
    if (!input.files.length) return;
    const reader = new FileReader();
    Array.from(input.files).forEach(file => {
        const r = new FileReader();
        r.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (data.account_id) {
                    const aid = data.account_id;
                    if (!accounts[aid]) accounts[aid] = {};
                    const version = data.version || 'v1';
                    if (!accounts[aid][version]) accounts[aid][version] = {};
                    accounts[aid][version][file.name] = data;
                    renderAccountList();
                    updateStats();
                }
            } catch (err) { console.error('Error parsing', file.name, err); }
        };
        r.readAsText(file);
    });
    closeModal();
}

// ─── Modal ──────────────────────────────────────────
function openModal() {
    document.getElementById('jsonModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('jsonModal').style.display = 'none';
}

function switchTab(name) {
    document.querySelectorAll('.modal-tabs .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => { t.style.display = 'none'; t.classList.remove('active'); });
    event.target.classList.add('active');
    const panel = document.getElementById('tab-' + name);
    if (panel) { panel.style.display = 'block'; panel.classList.add('active'); }
}

document.getElementById('loadDataBtn').addEventListener('click', openModal);

// ─── Stats ──────────────────────────────────────────
function updateStats() {
    const aids = Object.keys(accounts);
    document.getElementById('totalAccounts').textContent = aids.length;
    document.getElementById('accountCount').textContent = aids.length;

    let v1 = 0, v2 = 0, changes = 0;
    aids.forEach(aid => {
        if (accounts[aid].v1) v1++;
        if (accounts[aid].v2) v2++;
        if (accounts[aid].v2 && accounts[aid].v2['changelog.json']) {
            changes += accounts[aid].v2['changelog.json'].changes?.length || 0;
        }
    });
    document.getElementById('v1Count').textContent = v1;
    document.getElementById('v2Count').textContent = v2;
    document.getElementById('totalChanges').textContent = changes;
}

// ─── Account List ───────────────────────────────────
function renderAccountList() {
    const list = document.getElementById('accountList');
    const aids = Object.keys(accounts);

    if (!aids.length) {
        list.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>No accounts loaded</p></div>`;
        return;
    }

    list.innerHTML = aids.map(aid => {
        const data = accounts[aid];
        const name = (data.v2?.['account_memo.json']?.company_name || data.v1?.['account_memo.json']?.company_name || aid);
        const hasV1 = !!data.v1;
        const hasV2 = !!data.v2;
        const isActive = selectedAccount === aid ? 'active' : '';
        return `
            <div class="account-item ${isActive}" onclick="selectAccount('${aid}')">
                <div class="account-item-name">${escapeHtml(name)}</div>
                <div class="account-item-meta">
                    ${hasV1 ? '<span class="version-badge v1">v1</span>' : ''}
                    ${hasV2 ? '<span class="version-badge v2">v2</span>' : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ─── Account Selection ──────────────────────────────
function selectAccount(aid) {
    selectedAccount = aid;
    renderAccountList();
    renderDetailView(aid);
}

function renderDetailView(aid) {
    const data = accounts[aid];
    const detail = document.getElementById('detailView');
    const memo = data.v2?.['account_memo.json'] || data.v1?.['account_memo.json'];
    const hasV2 = !!data.v2;

    detail.innerHTML = `
        <div class="detail-header">
            <div>
                <div class="detail-title">${escapeHtml(memo?.company_name || aid)}</div>
                <div class="detail-subtitle">Account ID: ${aid} • ${hasV2 ? 'v1 + v2' : 'v1 only'}</div>
            </div>
            <div style="display:flex;gap:0.4rem">
                ${hasV2 ? '<span class="version-badge v2" style="font-size:0.8rem;padding:0.3rem 0.6rem">Updated</span>' : '<span class="version-badge v1" style="font-size:0.8rem;padding:0.3rem 0.6rem">Preliminary</span>'}
            </div>
        </div>

        <div class="detail-tabs">
            <button class="detail-tab ${activeTab === 'memo' ? 'active' : ''}" onclick="switchDetailTab('memo')">📋 Account Memo</button>
            <button class="detail-tab ${activeTab === 'spec' ? 'active' : ''}" onclick="switchDetailTab('spec')">🤖 Agent Spec</button>
            ${hasV2 ? `<button class="detail-tab ${activeTab === 'diff' ? 'active' : ''}" onclick="switchDetailTab('diff')">🔄 Diff Viewer</button>` : ''}
            ${hasV2 ? `<button class="detail-tab ${activeTab === 'changelog' ? 'active' : ''}" onclick="switchDetailTab('changelog')">📊 Changelog</button>` : ''}
            <button class="detail-tab ${activeTab === 'raw' ? 'active' : ''}" onclick="switchDetailTab('raw')">{ } Raw JSON</button>
        </div>

        <div id="tab-panel-memo" class="tab-panel ${activeTab === 'memo' ? 'active' : ''}">${renderMemoPanel(data)}</div>
        <div id="tab-panel-spec" class="tab-panel ${activeTab === 'spec' ? 'active' : ''}">${renderSpecPanel(data)}</div>
        ${hasV2 ? `<div id="tab-panel-diff" class="tab-panel ${activeTab === 'diff' ? 'active' : ''}">${renderDiffPanel(data)}</div>` : ''}
        ${hasV2 ? `<div id="tab-panel-changelog" class="tab-panel ${activeTab === 'changelog' ? 'active' : ''}">${renderChangelogPanel(data)}</div>` : ''}
        <div id="tab-panel-raw" class="tab-panel ${activeTab === 'raw' ? 'active' : ''}">${renderRawPanel(data)}</div>
    `;
}

function switchDetailTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    const panel = document.getElementById('tab-panel-' + tab);
    if (panel) panel.classList.add('active');
}

// ─── Memo Panel ─────────────────────────────────────
function renderMemoPanel(data) {
    const memo = data.v2?.['account_memo.json'] || data.v1?.['account_memo.json'];
    if (!memo) return '<div class="empty-state"><p>No memo data</p></div>';

    const bh = memo.business_hours || {};
    const addr = memo.office_address || {};
    const transfer = memo.call_transfer_rules || {};

    return `
        <div class="info-grid">
            <div class="info-card">
                <div class="info-card-label">Business Hours</div>
                <div class="info-card-value">${(bh.days || []).join(', ') || 'Not specified'}</div>
                <div style="color:var(--text-secondary);font-size:0.82rem">${bh.start || '?'} - ${bh.end || '?'} (${bh.timezone || '?'})</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Office Address</div>
                <div class="info-card-value">${[addr.street, addr.city, addr.state, addr.zip_code].filter(Boolean).join(', ') || 'Not specified'}</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Transfer Timeout</div>
                <div class="info-card-value">${transfer.timeout_seconds || 60}s timeout, ${transfer.max_retries || 2} retries</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Version</div>
                <div class="info-card-value">${memo.version} (${memo.source})</div>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-card">
                <div class="info-card-label">Services Supported</div>
                <ul class="info-card-list">
                    ${(memo.services_supported || []).map(s => `<li>${escapeHtml(s)}</li>`).join('') || '<li>Not specified</li>'}
                </ul>
            </div>
            <div class="info-card">
                <div class="info-card-label">Emergency Definitions</div>
                <ul class="info-card-list">
                    ${(memo.emergency_definition || []).map(e => `<li>${escapeHtml(e)}</li>`).join('') || '<li>Not specified</li>'}
                </ul>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-card">
                <div class="info-card-label">Emergency Routing</div>
                <ul class="info-card-list">
                    ${(memo.emergency_routing_rules || []).map(r => `<li>P${r.priority}: ${escapeHtml(r.contact_name)} (${escapeHtml(r.role)}) - ${escapeHtml(r.phone_number || 'no number')}</li>`).join('') || '<li>Not specified</li>'}
                </ul>
            </div>
            <div class="info-card">
                <div class="info-card-label">Non-Emergency Routing</div>
                <ul class="info-card-list">
                    ${(memo.non_emergency_routing_rules || []).map(r => `<li>${escapeHtml(r.contact_name)} (${escapeHtml(r.role)}) - ${escapeHtml(r.phone_number || 'no number')}</li>`).join('') || '<li>Not specified</li>'}
                </ul>
            </div>
        </div>

        ${(memo.integration_constraints || []).length ? `
            <div class="info-card" style="margin-bottom:0.8rem">
                <div class="info-card-label">Integration Constraints</div>
                <ul class="info-card-list">
                    ${memo.integration_constraints.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                </ul>
            </div>` : ''}

        ${(memo.questions_or_unknowns || []).length ? `
            <div class="info-card" style="border-color:var(--warning);margin-bottom:0.8rem">
                <div class="info-card-label" style="color:var(--warning)">⚠ Questions / Unknowns</div>
                <ul class="info-card-list">
                    ${memo.questions_or_unknowns.map(q => `<li>${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}

        ${memo.notes ? `
            <div class="info-card">
                <div class="info-card-label">Notes</div>
                <div class="info-card-value" style="font-size:0.85rem;font-weight:400">${escapeHtml(memo.notes)}</div>
            </div>` : ''}
    `;
}

// ─── Spec Panel ─────────────────────────────────────
function renderSpecPanel(data) {
    const spec = data.v2?.['agent_spec.json'] || data.v1?.['agent_spec.json'];
    if (!spec) return '<div class="empty-state"><p>No agent spec</p></div>';

    return `
        <div class="info-grid">
            <div class="info-card">
                <div class="info-card-label">Agent Name</div>
                <div class="info-card-value">${escapeHtml(spec.agent_name)}</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Voice</div>
                <div class="info-card-value">${spec.voice_id} (${spec.voice_model})</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Language</div>
                <div class="info-card-value">${spec.language}</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Version</div>
                <div class="info-card-value">${spec.version} - ${escapeHtml(spec.version_description)}</div>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-card">
                <div class="info-card-label">Transfer Protocol</div>
                <div class="info-card-value">${(spec.call_transfer_protocol?.transfer_numbers || []).join(', ') || 'None'}</div>
                <div style="color:var(--text-secondary);font-size:0.82rem">Timeout: ${spec.call_transfer_protocol?.timeout_seconds || 60}s, Retries: ${spec.call_transfer_protocol?.max_retries || 2}</div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Fallback</div>
                <div class="info-card-value" style="font-weight:400;font-size:0.85rem">${escapeHtml(spec.fallback_protocol?.message || 'N/A')}</div>
            </div>
        </div>

        <div class="info-card" style="margin-top:0.8rem">
            <div class="info-card-label">Key Variables</div>
            <div class="json-viewer" style="max-height:300px">${syntaxHighlight(JSON.stringify(spec.key_variables, null, 2))}</div>
        </div>

        <div class="info-card" style="margin-top:0.8rem">
            <div class="info-card-label">Boosted Keywords</div>
            <div class="info-card-value" style="font-weight:400;font-size:0.85rem">${(spec.boosted_keywords || []).join(', ')}</div>
        </div>
    `;
}

// ─── Diff Panel ─────────────────────────────────────
function renderDiffPanel(data) {
    const v1 = data.v1?.['account_memo.json'];
    const v2 = data.v2?.['account_memo.json'];
    if (!v1 || !v2) return '<div class="empty-state"><p>Need both v1 and v2 for diff</p></div>';

    const diffs = computeDiffs(v1, v2);
    const additions = diffs.filter(d => d.type === 'added' || d.type === 'modified').length;
    const removals = diffs.filter(d => d.type === 'removed').length;

    return `
        <div class="diff-container">
            <div class="diff-header">
                <div class="diff-title">Account Memo Diff: v1 → v2</div>
                <div class="diff-stats">
                    <span class="diff-stat-add">+${additions} modified/added</span>
                    <span class="diff-stat-remove">-${removals} removed</span>
                </div>
            </div>
            <div class="diff-body">
                ${diffs.map(d => `
                    <div class="diff-row">
                        <div class="diff-row-header">${escapeHtml(d.field)}</div>
                    </div>
                    <div class="diff-row">
                        <div class="diff-cell removed">
                            <div class="diff-cell-label">v1 (Demo)</div>
                            ${escapeHtml(formatValue(d.oldValue))}
                        </div>
                        <div class="diff-cell added">
                            <div class="diff-cell-label">v2 (Onboarding)</div>
                            ${escapeHtml(formatValue(d.newValue))}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function computeDiffs(v1, v2) {
    const diffs = [];
    const skipFields = new Set(['version', 'source', 'account_id']);
    const allKeys = new Set([...Object.keys(v1), ...Object.keys(v2)]);

    allKeys.forEach(key => {
        if (skipFields.has(key)) return;
        const old = v1[key];
        const nw = v2[key];
        if (JSON.stringify(old) !== JSON.stringify(nw)) {
            diffs.push({
                field: key,
                oldValue: old,
                newValue: nw,
                type: old === undefined ? 'added' : nw === undefined ? 'removed' : 'modified'
            });
        }
    });

    return diffs;
}

function formatValue(val) {
    if (val === undefined || val === null) return '(empty)';
    if (typeof val === 'object') return JSON.stringify(val, null, 2);
    return String(val);
}

// ─── Changelog Panel ────────────────────────────────
function renderChangelogPanel(data) {
    const cl = data.v2?.['changelog.json'];
    if (!cl) return '<div class="empty-state"><p>No changelog available</p></div>';

    return `
        <div style="margin-bottom:1rem">
            <h3 style="font-size:1rem;margin-bottom:0.3rem">${cl.from_version} → ${cl.to_version}</h3>
            <p style="color:var(--text-secondary);font-size:0.85rem">${escapeHtml(cl.summary)}</p>
        </div>
        <div class="changelog-list">
            ${(cl.changes || []).map(c => `
                <div class="changelog-item">
                    <div class="changelog-field">${escapeHtml(c.field)}</div>
                    <div class="changelog-reason">${escapeHtml(c.reason)}</div>
                    <div class="changelog-values">
                        <div class="changelog-val old">${escapeHtml(String(c.old_value))}</div>
                        <div class="changelog-val new">${escapeHtml(String(c.new_value))}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// ─── Raw JSON Panel ─────────────────────────────────
function renderRawPanel(data) {
    const versions = Object.keys(data).sort();
    return versions.map(ver => {
        const files = data[ver];
        return Object.keys(files).map(fname => `
            <div style="margin-bottom:1rem">
                <div style="font-size:0.82rem;font-weight:600;margin-bottom:0.3rem;color:var(--text-secondary)">${ver}/${fname}</div>
                <div class="json-viewer">${syntaxHighlight(JSON.stringify(files[fname], null, 2))}</div>
            </div>
        `).join('');
    }).join('');
}

// ─── Utilities ──────────────────────────────────────
function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function syntaxHighlight(json) {
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return `<span class="${cls}">${match}</span>`;
    });
}
