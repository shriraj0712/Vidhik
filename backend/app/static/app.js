/**
 * Vidhik AI - Lawyer Workspace Client Application
 * =================================================
 * Single Page Application logic providing complete client-side routing,
 * real-time API integrations, responsive tabs, modals, and legal search linking.
 */

const App = {
  token: localStorage.getItem('vidhik_token') || null,
  user: null,
  currentView: 'dashboard',
  currentCaseId: null,
  activeCasesList: [],
  activeClientsList: [],
  selectedProvision: null,

  // -------------------------------------------------------------
  // INITIALIZATION
  // -------------------------------------------------------------
  async init() {
    this.bindEvents();
    if (this.token) {
      try {
        await this.fetchCurrentUser();
        this.showApp();
      } catch (e) {
        this.showLogin();
      }
    } else {
      this.showLogin();
    }
  },

  bindEvents() {
    // Navigation clicks
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const view = item.getAttribute('data-view');
        if (view) this.navigate(view);
      });
    });

    // Login Form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await this.handleLogin();
      });
    }

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    // Header Quick Buttons
    document.getElementById('btn-quick-new-client')?.addEventListener('click', () => this.openAddClientModal());
    document.getElementById('btn-quick-new-case')?.addEventListener('click', () => this.openCreateCaseModal());

    // Global Search
    const gSearch = document.getElementById('global-search-input');
    if (gSearch) {
      gSearch.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && gSearch.value.trim()) {
          this.navigate('research');
          document.getElementById('research-query-input').value = gSearch.value.trim();
          this.handleLegalSearch();
        }
      });
    }

    // Case Details Tabs
    document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn[data-tab]').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(tabId)?.classList.add('active');
      });
    });

    // Hearing History Tabs
    document.querySelectorAll('.tab-btn[data-hearing-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn[data-hearing-tab]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.getAttribute('data-hearing-tab');
        this.renderHearingsList(tab);
      });
    });

    // Form Submissions
    document.getElementById('form-add-client')?.addEventListener('submit', (e) => this.submitAddClient(e));
    document.getElementById('form-create-case')?.addEventListener('submit', (e) => this.submitCreateCase(e));
    document.getElementById('form-upload-doc')?.addEventListener('submit', (e) => this.submitUploadDoc(e));
    document.getElementById('form-schedule-hearing')?.addEventListener('submit', (e) => this.submitScheduleHearing(e));
    document.getElementById('form-add-note')?.addEventListener('submit', (e) => this.submitAddNote(e));
    document.getElementById('form-link-provision')?.addEventListener('submit', (e) => this.submitLinkProvision(e));
    document.getElementById('form-edit-profile')?.addEventListener('submit', (e) => this.submitEditProfile(e));
    document.getElementById('research-search-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleLegalSearch();
    });
  },

  // -------------------------------------------------------------
  // API HELPER
  // -------------------------------------------------------------
  async api(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const options = { method, headers };
    if (body) {
      options.body = JSON.stringify(body);
    }

    const res = await fetch(endpoint, options);
    if (!res.ok) {
      let errorMsg = `API Error (${res.status})`;
      try {
        const errJson = await res.json();
        errorMsg = errJson.detail || errorMsg;
      } catch (err) {}
      throw new Error(errorMsg);
    }
    return await res.json();
  },

  // -------------------------------------------------------------
  // AUTHENTICATION
  // -------------------------------------------------------------
  async handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
      const data = await this.api('/api/auth/login', 'POST', { email, password });
      this.token = data.token;
      this.user = data;
      localStorage.setItem('vidhik_token', this.token);
      this.showToast(`Welcome back, ${data.full_name}`, 'success');
      this.showApp();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  },

  async fetchCurrentUser() {
    this.user = await this.api('/api/auth/me');
  },

  handleLogout() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('vidhik_token');
    this.showLogin();
    this.showToast('You have been signed out.', 'success');
  },

  showLogin() {
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('app-shell').style.display = 'none';
  },

  showApp() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-shell').style.display = 'flex';
    this.updateUserUI();
    this.navigate('dashboard');
  },

  updateUserUI() {
    if (!this.user) return;
    const initials = this.user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    document.getElementById('sidebar-lawyer-avatar').innerText = initials;
    document.getElementById('sidebar-lawyer-name').innerText = this.user.full_name;
    document.getElementById('dash-greeting-name').innerText = this.user.full_name;
  },

  // -------------------------------------------------------------
  // ROUTING & NAVIGATION
  // -------------------------------------------------------------
  navigate(viewName) {
    this.currentView = viewName;

    // Update Sidebar Active Class
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      if (item.getAttribute('data-view') === viewName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Hide all view panels
    document.querySelectorAll('.view-panel').forEach(panel => {
      panel.style.display = 'none';
    });

    // Show selected panel
    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) {
      targetPanel.style.display = 'block';
    }

    // Trigger View Data Fetchers
    switch (viewName) {
      case 'dashboard':
        this.loadDashboard();
        break;
      case 'clients':
        this.loadClients();
        break;
      case 'cases':
        this.loadCases();
        break;
      case 'documents':
        this.loadAllDocuments();
        break;
      case 'hearings':
        this.loadHearings();
        break;
      case 'research':
        // Ready for search
        break;
      case 'profile':
        this.loadProfile();
        break;
    }
  },

  // -------------------------------------------------------------
  // 1. DASHBOARD
  // -------------------------------------------------------------
  async loadDashboard() {
    try {
      const data = await this.api('/api/lawyer/dashboard');

      // Update KPIs
      document.getElementById('kpi-clients').innerText = data.total_clients;
      document.getElementById('kpi-cases').innerText = data.active_cases;
      document.getElementById('kpi-hearings').innerText = data.upcoming_hearings;
      document.getElementById('kpi-documents').innerText = data.recent_documents_count;

      document.getElementById('sidebar-client-count').innerText = data.total_clients;
      document.getElementById('sidebar-case-count').innerText = data.active_cases;
      document.getElementById('sidebar-hearing-count').innerText = data.upcoming_hearings;

      // Render Hearings
      const hList = document.getElementById('dash-hearings-list');
      if (data.upcoming_hearings_list.length === 0) {
        hList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No upcoming court hearings scheduled.</div></div>`;
      } else {
        hList.innerHTML = data.upcoming_hearings_list.map(h => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; color: var(--text-primary); font-size: 14px;">${this.escape(h.title)}</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 3px;">
                ⚖️ ${this.escape(h.case_title)} (${this.escape(h.case_number || 'Brief')})
              </div>
              <div style="font-size: 12px; color: var(--accent-cyan); margin-top: 2px;">
                🏛️ ${this.escape(h.court_name || 'Designated Court')}
              </div>
            </div>
            <div style="text-align: right;">
              <span class="badge badge-active">${h.reminder_date}</span>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${h.reminder_time || '10:30 AM'}</div>
            </div>
          </div>
        `).join('');
      }

      // Render Recent Cases
      const cList = document.getElementById('dash-cases-list');
      if (data.recent_cases.length === 0) {
        cList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No active case briefs found.</div></div>`;
      } else {
        cList.innerHTML = data.recent_cases.map(c => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="App.openCaseDetail(${c.case_id})">
            <div>
              <div style="font-weight: 600; color: var(--text-primary); font-size: 14px;">${this.escape(c.case_title)}</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 3px;">
                👤 ${this.escape(c.client_name || 'Client')} • <code>${this.escape(c.case_number || 'Brief')}</code>
              </div>
            </div>
            <div style="text-align: right;">
              <span class="badge badge-${c.status}">${c.status}</span>
              <div style="font-size: 11px; color: #818CF8; margin-top: 4px;">Open Brief →</div>
            </div>
          </div>
        `).join('');
      }

      // Render Recent Activity
      const aList = document.getElementById('dash-activity-list');
      if (data.recent_activity.length === 0) {
        aList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No procedural updates logged yet.</div></div>`;
      } else {
        aList.innerHTML = data.recent_activity.map(a => `
          <div style="display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--border-subtle);">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(99, 102, 241, 0.15); color: #818CF8; display: flex; align-items: center; justify-content: center; font-size: 14px;">
              ⚡
            </div>
            <div style="flex: 1;">
              <div style="font-size: 13.5px; font-weight: 600; color: var(--text-primary);">${this.escape(a.update_title)}</div>
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">${this.escape(a.update_description)}</div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
                Case: ${this.escape(a.case_title)} • ${new Date(a.update_date).toLocaleDateString()}
              </div>
            </div>
          </div>
        `).join('');
      }

      // Render Recent Documents
      const dList = document.getElementById('dash-documents-list');
      if (data.recent_documents.length === 0) {
        dList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No documents uploaded.</div></div>`;
      } else {
        dList.innerHTML = data.recent_documents.map(d => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-subtle);">
            <div>
              <div style="font-size: 13px; font-weight: 500; color: var(--text-primary);">📄 ${this.escape(d.document_name)}</div>
              <div style="font-size: 11.5px; color: var(--text-muted);">${this.escape(d.case_title)} • <span class="badge badge-completed">${d.document_type}</span></div>
            </div>
            <span style="font-size: 11px; color: var(--text-muted);">${(d.file_size_bytes / 1024 / 1024).toFixed(1)} MB</span>
          </div>
        `).join('');
      }

    } catch (e) {
      this.showToast('Failed to load dashboard data: ' + e.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 2. CLIENT MANAGEMENT
  // -------------------------------------------------------------
  async loadClients() {
    const search = document.getElementById('client-search-input')?.value || '';
    const tbody = document.getElementById('clients-table-body');
    tbody.innerHTML = `<tr><td colspan="6"><div class="spinner"></div></td></tr>`;

    try {
      const data = await this.api(`/api/lawyer/clients?search=${encodeURIComponent(search)}`);
      this.activeClientsList = data.clients;

      if (data.clients.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-state-title">No clients found</div><div class="empty-state-desc">Add your first client to associate them with case matters.</div></div></td></tr>`;
        return;
      }

      tbody.innerHTML = data.clients.map(c => `
        <tr>
          <td>
            <strong>${this.escape(c.full_name)}</strong>
            <div style="font-size: 11.5px; color: var(--text-muted);">ID: #${c.user_id}</div>
          </td>
          <td>${this.escape(c.email)}</td>
          <td>${this.escape(c.phone || 'N/A')}</td>
          <td><span class="badge badge-active">${c.active_cases_count} Matters</span></td>
          <td>${new Date(c.created_at).toLocaleDateString()}</td>
          <td style="text-align: right;">
            <button class="btn btn-secondary btn-sm" onclick="App.openClientCasesModal(${c.user_id})">View Matters</button>
          </td>
        </tr>
      `).join('');
    } catch (e) {
      this.showToast('Error loading clients: ' + e.message, 'error');
    }
  },

  openAddClientModal() {
    document.getElementById('form-add-client').reset();
    document.getElementById('modal-add-client').classList.add('active');
  },

  async submitAddClient(e) {
    e.preventDefault();
    const payload = {
      full_name: document.getElementById('m-client-name').value,
      email: document.getElementById('m-client-email').value,
      phone: document.getElementById('m-client-phone').value || null
    };

    try {
      await this.api('/api/lawyer/clients', 'POST', payload);
      this.showToast('Client added successfully!', 'success');
      this.closeModals();
      this.loadClients();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async openClientCasesModal(clientId) {
    try {
      const client = await this.api(`/api/lawyer/clients/${clientId}`);
      let msg = `Client: ${client.full_name}\nActive Matters: ${client.active_cases_count}\n`;
      if (client.cases && client.cases.length > 0) {
        msg += client.cases.map(c => `• ${c.case_number || 'Matter'}: ${c.case_title} (${c.court_name})`).join('\n');
      } else {
        msg += 'No cases currently associated with this client.';
      }
      alert(msg);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 3. CASE MANAGEMENT
  // -------------------------------------------------------------
  async loadCases() {
    const search = document.getElementById('cases-search-input')?.value || '';
    const status = document.getElementById('cases-status-filter')?.value || '';
    const caseType = document.getElementById('cases-type-filter')?.value || '';

    const tbody = document.getElementById('cases-table-body');
    tbody.innerHTML = `<tr><td colspan="7"><div class="spinner"></div></td></tr>`;

    try {
      const query = new URLSearchParams({ search, status, case_type: caseType }).toString();
      const data = await this.api(`/api/lawyer/cases?${query}`);
      this.activeCasesList = data.cases;

      if (data.cases.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-state-title">No cases found</div><div class="empty-state-desc">Create a new case matter or adjust your search filter.</div></div></td></tr>`;
        return;
      }

      tbody.innerHTML = data.cases.map(c => `
        <tr>
          <td>
            <strong>${this.escape(c.case_title)}</strong>
            <div style="font-size: 11.5px; color: var(--accent-cyan); font-family: 'JetBrains Mono';">${this.escape(c.case_number || 'Brief')} • ${this.escape(c.case_type || 'General')}</div>
          </td>
          <td>
            <div>${this.escape(c.client_name || 'Client')}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${this.escape(c.client_phone || '')}</div>
          </td>
          <td>${this.escape(c.court_name || 'Court')}</td>
          <td>${this.escape(c.opposite_party || 'N/A')}</td>
          <td>${c.filing_date || 'N/A'}</td>
          <td><span class="badge badge-${c.status}">${c.status}</span></td>
          <td style="text-align: right;">
            <button class="btn btn-primary btn-sm" onclick="App.openCaseDetail(${c.case_id})">Open Workspace →</button>
          </td>
        </tr>
      `).join('');
    } catch (e) {
      this.showToast('Error loading cases: ' + e.message, 'error');
    }
  },

  async openCreateCaseModal() {
    const select = document.getElementById('m-case-client');
    select.innerHTML = '<option value="">Loading client list...</option>';

    try {
      const clientsData = await this.api('/api/lawyer/clients');
      select.innerHTML = clientsData.clients.map(cl => `
        <option value="${cl.user_id}">${this.escape(cl.full_name)} (${cl.email})</option>
      `).join('');
      document.getElementById('modal-create-case').classList.add('active');
    } catch (err) {
      this.showToast('Failed to load clients: ' + err.message, 'error');
    }
  },

  async submitCreateCase(e) {
    e.preventDefault();
    const payload = {
      user_id: parseInt(document.getElementById('m-case-client').value),
      case_title: document.getElementById('m-case-title').value,
      case_number: document.getElementById('m-case-number').value || null,
      case_type: document.getElementById('m-case-type').value || null,
      court_name: document.getElementById('m-case-court').value || null,
      opposite_party: document.getElementById('m-case-opposite').value || null,
      filing_date: document.getElementById('m-case-filing-date').value || null,
      case_description: document.getElementById('m-case-description').value || null,
      status: 'active'
    };

    try {
      const newCase = await this.api('/api/lawyer/cases', 'POST', payload);
      this.showToast('Case created successfully!', 'success');
      this.closeModals();
      this.openCaseDetail(newCase.case_id);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 4. CASE DETAILS WORKSPACE
  // -------------------------------------------------------------
  async openCaseDetail(caseId) {
    this.currentCaseId = caseId;
    this.navigate('case-detail');

    try {
      const data = await this.api(`/api/lawyer/cases/${caseId}`);

      // Banner Metadata
      document.getElementById('cd-title').innerText = data.case_title;
      document.getElementById('cd-number').innerText = data.case_number || 'Unnumbered';
      document.getElementById('cd-court').innerText = data.court_name || 'Designated Court';
      document.getElementById('cd-opposite').innerText = data.opposite_party || 'None Specified';
      document.getElementById('cd-type-badge').innerText = data.case_type || 'General Matter';
      
      const badge = document.getElementById('cd-status-badge');
      badge.innerText = data.status;
      badge.className = `badge badge-${data.status}`;

      // Tab Counts
      document.getElementById('cd-doc-count').innerText = data.documents.length;
      document.getElementById('cd-hearing-count').innerText = data.hearings.length;
      document.getElementById('cd-note-count').innerText = data.notes.length;
      document.getElementById('cd-sec-count').innerText = data.legal_sections.length;

      // Overview Tab
      document.getElementById('cd-description').innerText = data.case_description || 'No description provided for this matter.';
      document.getElementById('cd-filing-date').innerText = data.filing_date || 'N/A';
      document.getElementById('cd-incident-date').innerText = data.incident_date || 'N/A';
      document.getElementById('cd-location').innerText = data.location || 'N/A';
      document.getElementById('cd-police-station').innerText = data.police_station || 'N/A';

      // Updates Timeline
      const tList = document.getElementById('cd-timeline-list');
      if (data.updates.length === 0) {
        tList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No updates recorded.</div></div>`;
      } else {
        tList.innerHTML = data.updates.map(u => `
          <div style="padding: 12px 0; border-bottom: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <strong>${this.escape(u.update_title)}</strong>
              <span class="badge badge-completed">${u.update_type || 'Update'}</span>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">${this.escape(u.update_description)}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${new Date(u.update_date).toLocaleDateString()} • Logged by ${u.updated_by}</div>
          </div>
        `).join('');
      }

      // Client Tab
      document.getElementById('cd-client-name').innerText = data.client_name || 'N/A';
      document.getElementById('cd-client-phone').innerText = data.client_phone || 'N/A';
      document.getElementById('cd-client-email').innerText = data.client_email || 'N/A';

      // Documents Tab
      const docBody = document.getElementById('cd-documents-body');
      if (data.documents.length === 0) {
        docBody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-state-desc">No documents attached to this case.</div></div></td></tr>`;
      } else {
        docBody.innerHTML = data.documents.map(d => `
          <tr>
            <td><strong>📄 ${this.escape(d.document_name)}</strong><div style="font-size: 11px; color: var(--text-muted);">${d.description || ''}</div></td>
            <td><span class="badge badge-completed">${d.document_type}</span></td>
            <td>${(d.file_size_bytes / 1024 / 1024).toFixed(1)} MB</td>
            <td>${new Date(d.created_at).toLocaleDateString()}</td>
            <td style="text-align: right;">
              <button class="btn btn-danger btn-sm" onclick="App.deleteDocument(${d.document_id})">Delete</button>
            </td>
          </tr>
        `).join('');
      }

      // Hearings Tab
      const hList = document.getElementById('cd-hearings-list');
      if (data.hearings.length === 0) {
        hList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No hearings scheduled for this case.</div></div>`;
      } else {
        hList.innerHTML = data.hearings.map(h => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-size: 15px; font-weight: 600; color: #F8FAFC;">${this.escape(h.title)}</div>
              <div style="font-size: 13px; color: var(--accent-cyan); margin-top: 3px;">🏛️ ${this.escape(h.court_name || data.court_name)} • Bench: ${this.escape(h.judge_name || 'Designated Bench')}</div>
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 4px;">${this.escape(h.notes || '')}</div>
            </div>
            <div style="text-align: right;">
              <span class="badge badge-${h.status}">${h.status}</span>
              <div style="font-size: 14px; font-weight: 600; color: #818CF8; margin-top: 4px;">${h.reminder_date}</div>
              <div style="font-size: 11px; color: var(--text-muted);">${h.reminder_time || '10:30 AM'}</div>
            </div>
          </div>
        `).join('');
      }

      // Notes Tab
      const nList = document.getElementById('cd-notes-list');
      if (data.notes.length === 0) {
        nList.innerHTML = `<div class="empty-state"><div class="empty-state-desc">No confidential notes added yet.</div></div>`;
      } else {
        nList.innerHTML = data.notes.map(n => `
          <div class="note-card ${n.is_pinned ? 'pinned' : ''}">
            <div class="note-header">
              <span class="note-title">${n.is_pinned ? '📌 ' : ''}${this.escape(n.title || 'Untitled Note')}</span>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span class="note-date">${new Date(n.updated_at).toLocaleDateString()}</span>
                <button class="btn btn-danger btn-sm" style="padding: 2px 6px;" onclick="App.deleteNote(${n.note_id})">✕</button>
              </div>
            </div>
            <div class="note-content">${this.escape(n.content)}</div>
          </div>
        `).join('');
      }

      // Legal Research Sections Tab
      const sList = document.getElementById('cd-sections-list');
      if (data.legal_sections.length === 0) {
        sList.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">⚖️</div>
            <div class="empty-state-title">No statutory sections associated</div>
            <div class="empty-state-desc">Search the Indian legal corpus and link relevant sections directly to this case brief.</div>
            <button class="btn btn-primary btn-sm" style="margin-top: 14px;" onclick="App.openSearchAndLinkModal()">Search Legal Database</button>
          </div>
        `;
      } else {
        sList.innerHTML = data.legal_sections.map(s => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 18px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <div>
                <span class="badge badge-active" style="margin-bottom: 6px;">Section ${s.section_number}</span>
                <h4 style="font-size: 16px; color: #F8FAFC;">${this.escape(s.section_title || 'Section')}</h4>
                <div style="font-size: 13px; color: var(--accent-cyan); font-weight: 500;">📖 ${this.escape(s.law_name)}</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-completed">Relevance: ${s.relevance_score}%</span>
                <button class="btn btn-danger btn-sm" style="margin-top: 6px; display: block; margin-left: auto;" onclick="App.unlinkSectionFromCase(${s.section_id})">Unlink</button>
              </div>
            </div>
            ${s.explanation ? `<div style="font-size: 13px; color: var(--text-secondary); background: var(--bg-primary); padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-top: 8px;"><strong>Rationale:</strong> ${this.escape(s.explanation)}</div>` : ''}
            <div style="margin-top: 10px;">
              <button class="btn btn-secondary btn-sm" onclick="App.viewFullProvisionDetail(${s.section_id})">Read Full Provision Text →</button>
            </div>
          </div>
        `).join('');
      }

    } catch (e) {
      this.showToast('Failed to load case details: ' + e.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 5. DOCUMENT MANAGEMENT
  // -------------------------------------------------------------
  async loadAllDocuments() {
    const tbody = document.getElementById('all-documents-table-body');
    tbody.innerHTML = `<tr><td colspan="7"><div class="spinner"></div></td></tr>`;

    try {
      const data = await this.api('/api/lawyer/documents');
      if (data.documents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-state-title">No documents cataloged</div><div class="empty-state-desc">Upload documents and link them to case briefs.</div></div></td></tr>`;
        return;
      }

      tbody.innerHTML = data.documents.map(d => `
        <tr>
          <td>
            <strong>📄 ${this.escape(d.document_name)}</strong>
            <div style="font-size: 11px; color: var(--text-muted);">${d.description || ''}</div>
          </td>
          <td><a href="javascript:void(0)" onclick="App.openCaseDetail(${d.case_id})" style="color: #818CF8; text-decoration: none;">${this.escape(d.case_title)}</a></td>
          <td>${this.escape(d.client_name || 'Client')}</td>
          <td><span class="badge badge-completed">${d.document_type}</span></td>
          <td>${(d.file_size_bytes / 1024 / 1024).toFixed(1)} MB</td>
          <td>${new Date(d.created_at).toLocaleDateString()}</td>
          <td style="text-align: right;">
            <button class="btn btn-danger btn-sm" onclick="App.deleteDocument(${d.document_id})">Delete</button>
          </td>
        </tr>
      `).join('');
    } catch (e) {
      this.showToast('Error loading documents: ' + e.message, 'error');
    }
  },

  async openUploadDocModal(caseId = null) {
    const select = document.getElementById('m-doc-case-select');
    select.innerHTML = '<option value="">Loading cases...</option>';

    try {
      const casesData = await this.api('/api/lawyer/cases');
      select.innerHTML = casesData.cases.map(c => `
        <option value="${c.case_id}" ${caseId && caseId == c.case_id ? 'selected' : ''}>
          ${this.escape(c.case_title)} (${c.case_number || 'Brief'})
        </option>
      `).join('');
      document.getElementById('modal-upload-doc').classList.add('active');
    } catch (err) {
      this.showToast('Failed to load cases: ' + err.message, 'error');
    }
  },

  async submitUploadDoc(e) {
    e.preventDefault();
    const caseId = parseInt(document.getElementById('m-doc-case-select').value);
    const payload = {
      case_id: caseId,
      document_name: document.getElementById('m-doc-name').value,
      document_type: document.getElementById('m-doc-type').value,
      description: document.getElementById('m-doc-desc').value || null
    };

    try {
      await this.api('/api/lawyer/documents', 'POST', payload);
      this.showToast('Document attached successfully!', 'success');
      this.closeModals();
      if (this.currentView === 'case-detail') {
        this.openCaseDetail(caseId);
      } else {
        this.loadAllDocuments();
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document record?')) return;
    try {
      await this.api(`/api/lawyer/documents/${docId}`, 'DELETE');
      this.showToast('Document deleted.', 'success');
      if (this.currentView === 'case-detail') {
        this.openCaseDetail(this.currentCaseId);
      } else {
        this.loadAllDocuments();
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 6. HEARING MANAGEMENT
  // -------------------------------------------------------------
  async loadHearings() {
    try {
      const data = await this.api('/api/lawyer/hearings');
      this.cachedHearings = data;
      document.getElementById('h-count-upcoming').innerText = data.upcoming.length;
      document.getElementById('h-count-past').innerText = data.past.length;
      this.renderHearingsList('upcoming');
    } catch (e) {
      this.showToast('Failed to load hearings: ' + e.message, 'error');
    }
  },

  renderHearingsList(tab) {
    const container = document.getElementById('hearings-cards-container');
    const list = tab === 'upcoming' ? this.cachedHearings?.upcoming : this.cachedHearings?.past;

    if (!list || list.length === 0) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-title">No ${tab} hearings</div><div class="empty-state-desc">Use the button above to schedule your next court date.</div></div>`;
      return;
    }

    container.innerHTML = list.map(h => `
      <div class="card" style="margin-bottom: 16px; border-left: 4px solid ${h.priority === 'high' ? 'var(--accent-rose)' : 'var(--accent-primary)'};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
              <span class="badge badge-${h.status}">${h.status}</span>
              <span class="badge badge-${h.priority}">${h.priority} Priority</span>
            </div>
            <h3 style="font-size: 17px; color: #F8FAFC;">${this.escape(h.title)}</h3>
            <div style="font-size: 13.5px; color: var(--accent-cyan); margin-top: 4px;">
              ⚖️ Case: <a href="javascript:void(0)" onclick="App.openCaseDetail(${h.case_id})" style="color: #818CF8; text-decoration: none;">${this.escape(h.case_title)}</a> (${this.escape(h.case_number || 'Brief')})
            </div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
              🏛️ ${this.escape(h.court_name || 'Court Room')} • Presiding: ${this.escape(h.judge_name || 'Designated Judge')}
            </div>
            ${h.notes ? `<div style="font-size: 12.5px; color: var(--text-muted); margin-top: 8px; background: var(--bg-primary); padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">📝 Notes: ${this.escape(h.notes)}</div>` : ''}
          </div>
          <div style="text-align: right;">
            <div style="font-size: 18px; font-weight: 700; color: #818CF8; font-family: 'Outfit';">${h.reminder_date}</div>
            <div style="font-size: 13px; color: var(--text-muted);">${h.reminder_time || '10:30 AM'}</div>
          </div>
        </div>
      </div>
    `).join('');
  },

  async openScheduleHearingModal(caseId = null) {
    const select = document.getElementById('m-hearing-case-select');
    select.innerHTML = '<option value="">Loading cases...</option>';

    try {
      const casesData = await this.api('/api/lawyer/cases');
      select.innerHTML = casesData.cases.map(c => `
        <option value="${c.case_id}" ${caseId && caseId == c.case_id ? 'selected' : ''}>
          ${this.escape(c.case_title)} (${c.case_number || 'Brief'})
        </option>
      `).join('');
      document.getElementById('modal-schedule-hearing').classList.add('active');
    } catch (err) {
      this.showToast('Failed to load cases: ' + err.message, 'error');
    }
  },

  async submitScheduleHearing(e) {
    e.preventDefault();
    const caseId = parseInt(document.getElementById('m-hearing-case-select').value);
    const payload = {
      case_id: caseId,
      title: document.getElementById('m-hearing-title').value,
      reminder_date: document.getElementById('m-hearing-date').value,
      reminder_time: document.getElementById('m-hearing-time').value ? document.getElementById('m-hearing-time').value + ':00' : '10:30:00',
      court_name: document.getElementById('m-hearing-court').value || null,
      judge_name: document.getElementById('m-hearing-judge').value || null,
      notes: document.getElementById('m-hearing-notes').value || null,
      status: 'scheduled',
      priority: 'normal'
    };

    try {
      await this.api('/api/lawyer/hearings', 'POST', payload);
      this.showToast('Court hearing scheduled!', 'success');
      this.closeModals();
      if (this.currentView === 'case-detail') {
        this.openCaseDetail(caseId);
      } else {
        this.loadHearings();
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 7. CASE NOTES
  // -------------------------------------------------------------
  openAddCaseNoteModal() {
    document.getElementById('form-add-note').reset();
    document.getElementById('modal-add-note').classList.add('active');
  },

  async submitAddNote(e) {
    e.preventDefault();
    if (!this.currentCaseId) return;

    const payload = {
      case_id: this.currentCaseId,
      title: document.getElementById('m-note-title').value || null,
      content: document.getElementById('m-note-content').value,
      is_pinned: document.getElementById('m-note-pinned').checked
    };

    try {
      await this.api(`/api/lawyer/cases/${this.currentCaseId}/notes`, 'POST', payload);
      this.showToast('Note saved!', 'success');
      this.closeModals();
      this.openCaseDetail(this.currentCaseId);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async deleteNote(noteId) {
    if (!confirm('Are you sure you want to delete this note?')) return;
    try {
      await this.api(`/api/lawyer/notes/${noteId}`, 'DELETE');
      this.showToast('Note deleted.', 'success');
      this.openCaseDetail(this.currentCaseId);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 8. LEGAL RESEARCH (REUSING EXISTING SEARCH ENGINE)
  // -------------------------------------------------------------
  async handleLegalSearch() {
    const q = document.getElementById('research-query-input').value.trim();
    const jurisdiction = document.getElementById('research-jurisdiction-select').value;
    const container = document.getElementById('research-results-container');

    if (!q) {
      this.showToast('Please enter a legal search query.', 'error');
      return;
    }

    container.innerHTML = `<div class="spinner"></div>`;

    try {
      const query = new URLSearchParams({ q, limit: 15 });
      if (jurisdiction) query.append('jurisdiction', jurisdiction);

      // Call existing legal search endpoint
      const data = await this.api(`/api/search?${query.toString()}`);

      if (!data.results || data.results.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-title">No statutory matches found</div>
            <div class="empty-state-desc">No provisions matched "${this.escape(q)}". Try broader search terms.</div>
          </div>
        `;
        return;
      }

      container.innerHTML = `
        <div style="margin-bottom: 16px; font-size: 13.5px; color: var(--text-secondary);">
          Found <strong>${data.total}</strong> provisions in legal corpus. Displaying top relevance matches:
        </div>
        ${data.results.map(r => `
          <div class="card" style="margin-bottom: 16px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <div>
                <span class="badge badge-active" style="margin-bottom: 6px;">Section ${this.escape(r.section_number)}</span>
                <h3 style="font-size: 17px; color: #F8FAFC;">${this.escape(r.section_title || 'Section Provision')}</h3>
                <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 500;">📖 ${this.escape(r.law_name)}</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-completed">${r.jurisdiction || 'Central'}</span>
              </div>
            </div>
            
            <!-- Contextual Snippet generated by LegalSearchService -->
            <div style="font-size: 13.5px; line-height: 1.7; color: var(--text-secondary); background: var(--bg-primary); padding: 12px 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin: 12px 0;">
              ${this.escape(r.snippet)}
            </div>

            <div style="display: flex; gap: 10px; align-items: center; justify-content: flex-end; margin-top: 10px;">
              <button class="btn btn-secondary btn-sm" onclick="App.viewFullProvisionDetail(${r.section_id})">
                📖 View Verbatim Section
              </button>
              <button class="btn btn-primary btn-sm" onclick="App.openLinkToCaseModal(${r.section_id}, '${this.escape(r.section_number)}', '${this.escape(r.law_name)}')">
                🔗 Link to Case Brief
              </button>
            </div>
          </div>
        `).join('')}
      `;
    } catch (e) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-title">Search Error</div><div class="empty-state-desc">${this.escape(e.message)}</div></div>`;
    }
  },

  async viewFullProvisionDetail(sectionId) {
    try {
      const sec = await this.api(`/api/sections/${sectionId}`);
      document.getElementById('m-prov-title').innerText = `Section ${sec.section_number}: ${sec.section_title || ''}`;
      document.getElementById('m-prov-law-name').innerText = `Law ID: ${sec.law_id}`;
      document.getElementById('m-prov-sec-no').innerText = sec.section_number;
      document.getElementById('m-prov-chapter').innerText = sec.chapter_title ? `${sec.chapter_number || ''} - ${sec.chapter_title}` : 'General';
      document.getElementById('m-prov-pages').innerText = sec.source_page_start ? `Pages ${sec.source_page_start} to ${sec.source_page_end}` : 'N/A';
      document.getElementById('m-prov-fulltext').innerText = sec.full_text || sec.section_text || 'No verbatim text available.';

      this.selectedProvision = sec;
      document.getElementById('modal-provision-detail').classList.add('active');
    } catch (err) {
      this.showToast('Failed to load section: ' + err.message, 'error');
    }
  },

  openLinkToCaseModalFromProvision() {
    if (!this.selectedProvision) return;
    this.closeModals();
    this.openLinkToCaseModal(this.selectedProvision.section_id, this.selectedProvision.section_number, `Law ID: ${this.selectedProvision.law_id}`);
  },

  async openLinkToCaseModal(sectionId, sectionNumber, lawName) {
    document.getElementById('m-link-section-id').value = sectionId;
    document.getElementById('m-link-sec-label').innerText = `Section ${sectionNumber} • ${lawName}`;

    const select = document.getElementById('m-link-case-select');
    select.innerHTML = '<option value="">Loading cases...</option>';

    try {
      const casesData = await this.api('/api/lawyer/cases');
      select.innerHTML = casesData.cases.map(c => `
        <option value="${c.case_id}" ${this.currentCaseId && this.currentCaseId == c.case_id ? 'selected' : ''}>
          ${this.escape(c.case_title)} (${c.case_number || 'Brief'})
        </option>
      `).join('');
      document.getElementById('modal-link-provision').classList.add('active');
    } catch (err) {
      this.showToast('Failed to load cases: ' + err.message, 'error');
    }
  },

  openSearchAndLinkModal() {
    this.navigate('research');
  },

  async submitLinkProvision(e) {
    e.preventDefault();
    const caseId = parseInt(document.getElementById('m-link-case-select').value);
    const sectionId = parseInt(document.getElementById('m-link-section-id').value);
    const score = parseFloat(document.getElementById('m-link-score').value) || 85.0;
    const explanation = document.getElementById('m-link-explanation').value || null;

    try {
      await this.api(`/api/lawyer/cases/${caseId}/sections`, 'POST', {
        section_id: sectionId,
        relevance_score: score,
        explanation
      });
      this.showToast('Statutory provision linked to case!', 'success');
      this.closeModals();
      if (this.currentView === 'case-detail' && this.currentCaseId == caseId) {
        this.openCaseDetail(caseId);
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async unlinkSectionFromCase(sectionId) {
    if (!confirm('Unlink this statutory section from the case brief?')) return;
    try {
      await this.api(`/api/lawyer/cases/${this.currentCaseId}/sections/${sectionId}`, 'DELETE');
      this.showToast('Section unlinked from case.', 'success');
      this.openCaseDetail(this.currentCaseId);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 9. LAWYER PROFILE
  // -------------------------------------------------------------
  async loadProfile() {
    try {
      const data = await this.api('/api/lawyer/profile');
      this.cachedProfile = data;

      document.getElementById('prof-name').innerText = data.full_name;
      document.getElementById('prof-bar').innerText = `Bar Council: ${data.bar_council_number || 'Not verified'}`;
      document.getElementById('prof-exp').innerText = `${data.experience_years} Years Active Court Practice`;
      document.getElementById('prof-bio').innerText = data.bio || 'No professional bio provided.';
      document.getElementById('prof-courts').innerText = data.court_practice || 'High Court of Bombay';
      document.getElementById('prof-office').innerText = data.office_address || 'Fort, Mumbai - 400001';

      document.getElementById('prof-email').innerText = data.email;
      document.getElementById('prof-phone').innerText = data.phone || 'N/A';
      document.getElementById('prof-location').innerText = `${data.city || 'Mumbai'}, ${data.state || 'Maharashtra'}`;

      const specsBox = document.getElementById('prof-specs-container');
      specsBox.innerHTML = (data.specializations_list || []).map(s => `
        <span class="badge badge-active">${this.escape(s)}</span>
      `).join('');

      const langsBox = document.getElementById('prof-langs-container');
      langsBox.innerHTML = (data.languages_list || []).map(l => `
        <span class="badge badge-completed">${this.escape(l)}</span>
      `).join('');
    } catch (e) {
      this.showToast('Failed to load profile: ' + e.message, 'error');
    }
  },

  openEditProfileModal() {
    if (!this.cachedProfile) return;
    const p = this.cachedProfile;
    document.getElementById('m-prof-name').value = p.full_name || '';
    document.getElementById('m-prof-phone').value = p.phone || '';
    document.getElementById('m-prof-bar').value = p.bar_council_number || '';
    document.getElementById('m-prof-exp').value = p.experience_years || 0;
    document.getElementById('m-prof-courts').value = p.court_practice || '';
    document.getElementById('m-prof-address').value = p.office_address || '';
    document.getElementById('m-prof-specs').value = (p.specializations_list || []).join(', ');
    document.getElementById('m-prof-langs').value = (p.languages_list || []).join(', ');
    document.getElementById('m-prof-bio').value = p.bio || '';

    document.getElementById('modal-edit-profile').classList.add('active');
  },

  async submitEditProfile(e) {
    e.preventDefault();
    const specs = document.getElementById('m-prof-specs').value.split(',').map(s => s.trim()).filter(Boolean);
    const langs = document.getElementById('m-prof-langs').value.split(',').map(l => l.trim()).filter(Boolean);

    const payload = {
      full_name: document.getElementById('m-prof-name').value,
      phone: document.getElementById('m-prof-phone').value,
      bar_council_number: document.getElementById('m-prof-bar').value,
      experience_years: parseInt(document.getElementById('m-prof-exp').value) || 0,
      court_practice: document.getElementById('m-prof-courts').value,
      office_address: document.getElementById('m-prof-address').value,
      specializations_list: specs,
      languages_list: langs,
      bio: document.getElementById('m-prof-bio').value
    };

    try {
      await this.api('/api/lawyer/profile', 'PUT', payload);
      this.showToast('Profile updated successfully!', 'success');
      this.closeModals();
      this.loadProfile();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // UI UTILITIES & TOASTS
  // -------------------------------------------------------------
  closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => {
      if (m.id !== 'login-screen') {
        m.classList.remove('active');
      }
    });
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : (type === 'error' ? '✕' : 'ℹ');
    toast.innerHTML = `<span style="font-weight: bold;">${icon}</span> <span>${this.escape(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s ease';
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  },

  escape(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};

// Run when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
