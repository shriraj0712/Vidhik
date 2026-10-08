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
  selectedProvision: null,
  currentDocCategory: 'all',
  currentDocSearch: '',
  activeChecklistProcedure: null,
  checklistState: {},
  authMode: 'citizen',
  citizenCases: [],
  citizenDocuments: [],
  citizenBookmarks: [],
  citizenNotifications: [],
  unreadNotifCount: 0,

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

    // Auth Mode Switcher Tabs
    document.querySelectorAll('.auth-tab-btn[data-auth-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.getAttribute('data-auth-tab');
        this.switchAuthMode(mode);
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

    // Register Form
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
      registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await this.handleRegister(e);
      });
    }

    // Mobile Menu & Backdrop
    document.getElementById('btn-mobile-menu-toggle')?.addEventListener('click', () => this.toggleMobileSidebar());
    document.getElementById('mobile-backdrop')?.addEventListener('click', () => this.closeMobileSidebar());

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    // Header Quick Buttons (Lawyer)
    document.getElementById('btn-quick-new-client')?.addEventListener('click', () => this.openAddClientModal());
    document.getElementById('btn-quick-new-case')?.addEventListener('click', () => this.openCreateCaseModal());

    // Header Quick Buttons (Citizen)
    document.getElementById('btn-citizen-quick-new-case')?.addEventListener('click', () => this.openCitizenNewCaseModal());

    // Notification Bell & Popover
    const bellBtn = document.getElementById('btn-notifications-bell');
    if (bellBtn) {
      bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleNotificationsPopover();
      });
    }
    document.getElementById('btn-mark-all-read')?.addEventListener('click', () => this.markAllNotificationsRead());

    // Close notifications popover on click outside
    document.addEventListener('click', (e) => {
      const popover = document.getElementById('notifications-popover');
      const bell = document.getElementById('btn-notifications-bell');
      if (popover && popover.style.display !== 'none' && !popover.contains(e.target) && (!bell || !bell.contains(e.target))) {
        popover.style.display = 'none';
      }
    });

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

    // Documentation Search
    const docSearch = document.getElementById('doc-search-input');
    if (docSearch) {
      docSearch.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.searchDocumentation();
        }
      });
    }

    // Case Details Tabs (Lawyer)
    document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn[data-tab]').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(tabId)?.classList.add('active');
      });
    });

    // Case Details Tabs (Citizen)
    document.querySelectorAll('.tab-btn[data-citizen-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn[data-citizen-tab]').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.citizen-tab-pane').forEach(p => {
          p.classList.remove('active');
          p.style.display = 'none';
        });
        btn.classList.add('active');
        const tabId = btn.getAttribute('data-citizen-tab');
        const pane = document.getElementById(tabId);
        if (pane) {
          pane.classList.add('active');
          pane.style.display = 'block';
        }
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
    document.getElementById('form-citizen-profile')?.addEventListener('submit', (e) => this.submitCitizenProfile(e));
    document.getElementById('research-search-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleLegalSearch();
    });
  },

  // -------------------------------------------------------------
  // MOBILE NAVIGATION & HEADER HELPERS
  // -------------------------------------------------------------
  toggleMobileSidebar() {
    const sb = document.querySelector('.sidebar');
    const bd = document.getElementById('mobile-backdrop');
    if (sb) sb.classList.toggle('open');
    if (bd) bd.classList.toggle('active');
  },

  closeMobileSidebar() {
    const sb = document.querySelector('.sidebar');
    const bd = document.getElementById('mobile-backdrop');
    if (sb) sb.classList.remove('open');
    if (bd) bd.classList.remove('active');
  },

  handleCitizenQuickSearch(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('citizen-quick-search-input');
    if (!input) return;
    const q = input.value.trim();
    if (!q) {
      this.showToast('Please enter a search query.', 'error');
      return;
    }
    this.navigate('research');
    const rInput = document.getElementById('research-query-input');
    if (rInput) rInput.value = q;
    this.handleLegalSearch();
  },

  handleLawyerQuickSearch(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('lawyer-quick-search-input');
    if (!input) return;
    const q = input.value.trim();
    if (!q) {
      this.showToast('Please enter a search query.', 'error');
      return;
    }
    this.navigate('research');
    const rInput = document.getElementById('research-query-input');
    if (rInput) rInput.value = q;
    this.handleLegalSearch();
  },

  navigateToCurrentProfile() {
    if (!this.user) return;
    if (this.user.role === 'lawyer') {
      this.navigate('profile');
    } else {
      this.navigate('citizen-profile');
    }
  },

  navigateToNotifications(e) {
    if (e) e.preventDefault();
    const popover = document.getElementById('notifications-popover');
    if (popover) {
      popover.classList.remove('active');
      popover.style.display = 'none';
    }
    if (this.user && (this.user.role === 'user' || this.user.role === 'citizen')) {
      this.navigate('citizen-notifications');
    } else {
      this.showToast('Notifications are displayed in the Lawyer Dashboard activity feed.', 'info');
    }
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
      if (res.status === 401 && this.token && !endpoint.includes('/api/auth/login')) {
        this.token = null;
        this.user = null;
        localStorage.removeItem('vidhik_token');
        this.showLogin();
        this.showToast('Session expired or unauthorized. Please sign in again.', 'error');
      }
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
  switchAuthMode(mode) {
    this.authMode = mode;
    document.querySelectorAll('.auth-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.auth-tab-btn[data-auth-tab="${mode}"]`)?.classList.add('active');

    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');
    const demoContainer = document.getElementById('login-demo-container');
    const subtitle = document.getElementById('auth-card-subtitle');

    if (mode === 'register') {
      if (loginForm) loginForm.style.display = 'none';
      if (regForm) regForm.style.display = 'block';
      if (demoContainer) demoContainer.style.display = 'none';
      if (subtitle) subtitle.innerText = 'Create your citizen account to track cases and legal documents.';
    } else {
      if (loginForm) loginForm.style.display = 'block';
      if (regForm) regForm.style.display = 'none';
      if (demoContainer) demoContainer.style.display = 'block';

      if (mode === 'citizen') {
        if (subtitle) subtitle.innerText = 'Access your personal case tracker, documents, and legal updates.';
        this.fillDemoLogin('sunita.sharma@example.com', 'password123');
      } else {
        if (subtitle) subtitle.innerText = 'Advocate and legal counsel professional practice suite.';
        this.fillDemoLogin('rajesh.advocate@vidhik.ai', 'password123');
      }
    }
  },

  fillDemoLogin(email, password = 'password123') {
    const emailInput = document.getElementById('login-email');
    const pwdInput = document.getElementById('login-password');
    if (emailInput) emailInput.value = email;
    if (pwdInput) pwdInput.value = password;
  },

  async handleRegister(e) {
    const fullName = document.getElementById('reg-fullname').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirmPwd = document.getElementById('reg-confirm-password').value;

    if (password !== confirmPwd) {
      this.showToast('Passwords do not match.', 'error');
      return;
    }

    try {
      const data = await this.api('/api/auth/register', 'POST', {
        full_name: fullName,
        email: email,
        phone: phone || null,
        password: password
      });

      this.token = data.token;
      this.user = data;
      localStorage.setItem('vidhik_token', this.token);
      this.showToast(`Welcome to Vidhik AI, ${data.full_name}!`, 'success');
      this.showApp();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

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

  async handleLogout() {
    try {
      if (this.token) {
        await this.api('/api/auth/logout', 'POST', {}).catch(() => {});
      }
    } catch (e) {}
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

    const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');
    const citizenNav = document.getElementById('sidebar-citizen-nav');
    const lawyerNav = document.getElementById('sidebar-lawyer-nav');
    const lawyerBtns = document.getElementById('lawyer-quick-actions');
    const citizenBtns = document.getElementById('citizen-quick-actions');
    const brandBadge = document.getElementById('brand-badge-text');

    if (isCitizen) {
      if (citizenNav) citizenNav.style.display = 'block';
      if (lawyerNav) lawyerNav.style.display = 'none';
      if (lawyerBtns) lawyerBtns.style.display = 'none';
      if (citizenBtns) citizenBtns.style.display = 'flex';
      if (brandBadge) brandBadge.innerText = 'Citizen Portal';
      this.navigate('citizen-dashboard');
    } else {
      if (citizenNav) citizenNav.style.display = 'none';
      if (lawyerNav) lawyerNav.style.display = 'block';
      if (lawyerBtns) lawyerBtns.style.display = 'flex';
      if (citizenBtns) citizenBtns.style.display = 'none';
      if (brandBadge) brandBadge.innerText = 'Advocate Suite';
      this.navigate('dashboard');
    }

    this.loadNotifications();
  },

  updateUserUI() {
    if (!this.user) return;
    const initials = this.user.full_name ? this.user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'U';
    const avatar = document.getElementById('sidebar-lawyer-avatar');
    const nameEl = document.getElementById('sidebar-lawyer-name');
    const roleEl = document.getElementById('sidebar-lawyer-role');

    if (avatar) avatar.innerText = initials;
    if (nameEl) nameEl.innerText = this.user.full_name;
    if (roleEl) roleEl.innerText = (this.user.role === 'lawyer') ? 'Verified Advocate' : 'Citizen Account';

    // Top Header User Chip
    const hAvatar = document.getElementById('header-avatar');
    const hName = document.getElementById('header-user-name');
    const hRole = document.getElementById('header-user-role');
    if (hAvatar) hAvatar.innerText = initials;
    if (hName) hName.innerText = this.user.full_name;
    if (hRole) hRole.innerText = (this.user.role === 'lawyer') ? 'Advocate' : 'Citizen';

    const dashGreeting = document.getElementById('dash-greeting-name');
    if (dashGreeting) dashGreeting.innerText = this.user.full_name;
    const citizenGreeting = document.getElementById('dash-citizen-greeting-name');
    if (citizenGreeting) citizenGreeting.innerText = this.user.full_name;
  },

  // -------------------------------------------------------------
  // ROUTING & NAVIGATION
  // -------------------------------------------------------------
  navigate(viewName) {
    this.closeMobileSidebar();
    const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');

    // Strict role redirection for view access
    const lawyerOnlyViews = ['dashboard', 'clients', 'cases', 'documents', 'hearings', 'profile'];
    const citizenOnlyViews = ['citizen-dashboard', 'citizen-cases', 'citizen-case-detail', 'citizen-documents', 'citizen-bookmarks', 'citizen-search-history', 'citizen-notifications', 'citizen-profile'];

    if (isCitizen && lawyerOnlyViews.includes(viewName)) {
      viewName = 'citizen-dashboard';
    } else if (!isCitizen && citizenOnlyViews.includes(viewName)) {
      viewName = 'dashboard';
    }

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
      case 'documentation':
        this.loadDocumentationModule();
        break;
      case 'document-analysis':
        this.loadDocumentAnalysisModule();
        break;
      case 'profile':
        this.loadProfile();
        break;
      case 'citizen-dashboard':
        this.loadCitizenDashboard();
        break;
      case 'citizen-cases':
        this.loadCitizenCases();
        break;
      case 'citizen-case-detail':
        if (this.currentCaseId) this.loadCitizenCaseDetail(this.currentCaseId);
        break;
      case 'citizen-documents':
        this.loadCitizenDocuments();
        break;
      case 'citizen-bookmarks':
        this.loadCitizenBookmarks();
        break;
      case 'citizen-search-history':
        this.loadSearchHistory();
        break;
      case 'citizen-notifications':
        this.loadNotificationsView();
        break;
      case 'citizen-profile':
        this.loadCitizenProfile();
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
    const cnr = document.getElementById('m-case-cnr')?.value.trim() || null;
    const payload = {
      user_id: parseInt(document.getElementById('m-case-client').value),
      case_title: document.getElementById('m-case-title').value,
      case_number: document.getElementById('m-case-number').value || null,
      case_type: document.getElementById('m-case-type').value || null,
      court_name: document.getElementById('m-case-court').value || null,
      opposite_party: document.getElementById('m-case-opposite').value || null,
      filing_date: document.getElementById('m-case-filing-date').value || null,
      case_description: document.getElementById('m-case-description').value || null,
      cnr_number: cnr,
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

      // Official Court Reference (eCourts)
      const cnr = data.cnr_number || (data.court_reference ? data.court_reference.cnr_number : null);
      this.currentCaseCNR = cnr;
      this.currentCaseCourtReference = data.court_reference || {
        cnr_number: data.cnr_number,
        court_source: data.court_source || 'eCourts India',
        official_case_url: data.official_case_url,
        last_verified_at: data.last_verified_at,
        external_status: data.external_status,
        external_next_hearing_date: data.external_next_hearing_date
      };
      
      const cnrElem = document.getElementById('cd-cnr-number');
      if (cnrElem) cnrElem.innerText = cnr || 'Not Linked';
      const cSourceElem = document.getElementById('cd-court-source');
      if (cSourceElem) cSourceElem.innerText = (data.court_reference?.court_source || data.court_source) || 'eCourts India';
      const extStatusElem = document.getElementById('cd-external-status');
      if (extStatusElem) extStatusElem.innerText = (data.court_reference?.external_status || data.external_status) || 'Not verified yet';
      const extHearingElem = document.getElementById('cd-external-hearing-date');
      if (extHearingElem) extHearingElem.innerText = (data.court_reference?.external_next_hearing_date || data.external_next_hearing_date) || 'None recorded';
      const lastVerElem = document.getElementById('cd-last-verified-at');
      if (lastVerElem) {
        const lv = data.court_reference?.last_verified_at || data.last_verified_at;
        lastVerElem.innerText = lv ? new Date(lv).toLocaleString() : 'Never';
      }

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

      // Record citizen search history if logged in as citizen
      if (this.token && this.user && (this.user.role === 'user' || this.user.role === 'citizen')) {
        try {
          await this.api('/api/citizen/search-history', 'POST', {
            query_text: q,
            filters: jurisdiction ? { jurisdiction } : {},
            results_count: data.total || (data.results ? data.results.length : 0)
          });
        } catch (shErr) {
          console.warn('Could not record search history:', shErr);
        }
      }

      if (!data.results || data.results.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-title">No statutory matches found</div>
            <div class="empty-state-desc">No provisions matched "${this.escape(q)}". Try broader search terms.</div>
          </div>
        `;
        return;
      }

      const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');

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

            <div style="display: flex; gap: 10px; align-items: center; justify-content: flex-end; margin-top: 10px; flex-wrap: wrap;">
              <button class="btn btn-secondary btn-sm" onclick="App.viewFullProvisionDetail(${r.section_id})">
                📖 View Verbatim Section
              </button>
              ${isCitizen ? `
                <button class="btn btn-primary btn-sm" onclick="App.quickBookmarkSection(${r.section_id})">
                  🔖 Bookmark Section
                </button>
              ` : `
                <button class="btn btn-primary btn-sm" onclick="App.openLinkToCaseModal(${r.section_id}, '${this.escape(r.section_number)}', '${this.escape(r.law_name)}')">
                  🔗 Link to Case Brief
                </button>
              `}
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

      const linkBtn = document.getElementById('m-prov-btn-link');
      if (linkBtn) {
        const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');
        if (isCitizen) {
          linkBtn.innerText = '🔖 Bookmark Provision';
          linkBtn.onclick = () => {
            App.quickBookmarkSection(sec.section_id);
            App.closeModals();
          };
        } else {
          linkBtn.innerText = '🔗 Save & Link to Case';
          linkBtn.onclick = () => App.openLinkToCaseModalFromProvision();
        }
      }

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
  // 10. DOCUMENTATION SUPPORT & PROCEDURAL CHECKLISTS (PHASE 12)
  // -------------------------------------------------------------
  async loadDocumentationModule() {
    await this.loadDocumentationCategories();
    await this.loadDocumentationProcedures();
  },

  async loadDocumentationCategories() {
    const container = document.getElementById('doc-category-pills');
    if (!container) return;

    try {
      const categories = await this.api('/api/documentation/categories');
      container.innerHTML = `
        <span style="font-size: 13px; color: #94A3B8; margin-right: 4px; font-weight: 500;">Filter Category:</span>
        <button class="filter-pill ${this.currentDocCategory === 'all' ? 'active' : ''}" data-category="all" onclick="App.filterDocumentationCategory('all')">
          All Procedures
        </button>
        ${categories.map(c => `
          <button class="filter-pill ${this.currentDocCategory === c.category ? 'active' : ''}" data-category="${this.escape(c.category)}" onclick="App.filterDocumentationCategory('${this.escape(c.category)}')">
            ${this.escape(c.category)} (${c.procedures_count})
          </button>
        `).join('')}
      `;
    } catch (e) {
      console.error('Failed to load categories:', e);
    }
  },

  async loadDocumentationProcedures() {
    const container = document.getElementById('procedures-grid-container');
    if (!container) return;

    container.innerHTML = '<div class="spinner"></div>';

    try {
      const params = new URLSearchParams();
      if (this.currentDocSearch && this.currentDocSearch.trim()) {
        params.append('search', this.currentDocSearch.trim());
      }
      if (this.currentDocCategory && this.currentDocCategory !== 'all') {
        params.append('category', this.currentDocCategory);
      }

      const queryString = params.toString() ? `?${params.toString()}` : '';
      const data = await this.api(`/api/documentation/procedures${queryString}`);
      this.renderProcedureCards(data.procedures);
    } catch (err) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-state-icon">⚠️</div>
          <div class="empty-state-title">Error Loading Procedures</div>
          <div class="empty-state-desc">${this.escape(err.message)}</div>
        </div>
      `;
    }
  },

  filterDocumentationCategory(category) {
    this.currentDocCategory = category;
    document.querySelectorAll('#doc-category-pills .filter-pill').forEach(pill => {
      if (pill.getAttribute('data-category') === category) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
    this.loadDocumentationProcedures();
  },

  searchDocumentation() {
    const input = document.getElementById('doc-search-input');
    this.currentDocSearch = input ? input.value.trim() : '';
    this.loadDocumentationProcedures();
  },

  resetDocumentationSearch() {
    const input = document.getElementById('doc-search-input');
    if (input) input.value = '';
    this.currentDocSearch = '';
    this.currentDocCategory = 'all';
    this.loadDocumentationCategories();
    this.loadDocumentationProcedures();
  },

  renderProcedureCards(procedures) {
    const container = document.getElementById('procedures-grid-container');
    if (!container) return;

    if (!procedures || procedures.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-title">No Legal Procedures Found</div>
          <div class="empty-state-desc">Try clearing your search term or selecting another category filter.</div>
          <button class="btn btn-secondary btn-sm" style="margin-top: 12px;" onclick="App.resetDocumentationSearch()">Reset Filters</button>
        </div>
      `;
      return;
    }

    container.innerHTML = procedures.map(proc => `
      <div class="procedure-card" onclick="App.openProcedureChecklist(${proc.procedure_id})">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
            <span class="badge badge-info" style="font-size: 11px;">${this.escape(proc.category)}</span>
            ${proc.estimated_processing_days ? `<span style="font-size: 11.5px; color: #94A3B8;">⏱️ ~${proc.estimated_processing_days} Days</span>` : ''}
          </div>
          <h4 class="procedure-card-title">${this.escape(proc.procedure_name)}</h4>
          <p class="procedure-card-desc">${this.escape(proc.description)}</p>
        </div>

        <div class="procedure-card-meta">
          <div style="color: #CBD5E1;">
            🏛️ <strong>Authority:</strong> ${this.escape(proc.authority_type)}
          </div>
          <div style="color: #94A3B8;">
            📍 <strong>Jurisdiction:</strong> ${this.escape(proc.jurisdiction)}
          </div>
          ${proc.governing_law_name ? `
            <div style="color: #818CF8; font-size: 11.5px;">
              ⚖️ ${this.escape(proc.governing_law_name)} ${proc.governing_section_number ? `(Sec ${this.escape(proc.governing_section_number)})` : ''}
            </div>
          ` : ''}
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
            <div style="display: flex; gap: 6px;">
              <span class="badge badge-mandatory" style="font-size: 11px;">
                ${proc.mandatory_documents_count} Mandatory
              </span>
              <span class="badge badge-supporting" style="font-size: 11px;">
                ${proc.supporting_documents_count} Supporting
              </span>
            </div>
            <button class="btn btn-primary btn-sm" style="padding: 5px 12px; font-size: 12px;" onclick="event.stopPropagation(); App.openProcedureChecklist(${proc.procedure_id})">
              View Checklist →
            </button>
          </div>
        </div>
      </div>
    `).join('');
  },

  async openProcedureChecklist(procedureId) {
    try {
      const data = await this.api(`/api/documentation/procedures/${procedureId}`);
      this.activeChecklistProcedure = data;

      // Populate Modal Metadata
      document.getElementById('chk-proc-category').innerText = data.category;
      document.getElementById('chk-proc-title').innerText = data.procedure_name;
      document.getElementById('chk-proc-authority').innerText = `🏛️ Authority: ${data.authority_type} • 📍 Jurisdiction: ${data.jurisdiction}`;
      document.getElementById('chk-proc-desc').innerText = data.description;

      const statuteBox = document.getElementById('chk-proc-statute');
      if (data.governing_law_name) {
        statuteBox.innerHTML = `
          ⚖️ Governing Statute: <strong>${this.escape(data.governing_law_name)}</strong>
          ${data.governing_section_id ? `
            <button type="button" class="legal-ref-badge" style="margin-left: 6px;" onclick="App.viewFullProvisionDetail(${data.governing_section_id})">
              Sec ${this.escape(data.governing_section_number)} ↗
            </button>
          ` : ''}
        `;
      } else {
        statuteBox.innerHTML = '';
      }

      const timelineBox = document.getElementById('chk-proc-timeline');
      timelineBox.innerText = data.estimated_processing_days ? `⏱️ Est. Processing: ~${data.estimated_processing_days} Days` : '';

      const portalBox = document.getElementById('chk-proc-portal');
      if (data.official_portal_url) {
        portalBox.innerHTML = `🌐 <a href="${this.escape(data.official_portal_url)}" target="_blank" rel="noopener noreferrer" style="color: #38BDF8; text-decoration: underline;">Official Filing Portal ↗</a>`;
      } else {
        portalBox.innerHTML = '';
      }

      // Lawyer case attach bar
      const lawyerAttach = document.getElementById('chk-lawyer-case-attach');
      if (this.token && this.user && this.user.role === 'lawyer') {
        lawyerAttach.style.display = 'block';
        try {
          const casesData = await this.api('/api/lawyer/cases');
          const caseSelect = document.getElementById('chk-attach-case-select');
          if (casesData.cases && casesData.cases.length > 0) {
            caseSelect.innerHTML = casesData.cases.map(c => `
              <option value="${c.case_id}">${this.escape(c.case_title)} (${c.case_number || 'Brief'})</option>
            `).join('');
          } else {
            caseSelect.innerHTML = '<option value="">No active cases</option>';
          }
        } catch (e) {
          lawyerAttach.style.display = 'none';
        }
      } else {
        lawyerAttach.style.display = 'none';
      }

      // Load session checklist state
      const savedState = localStorage.getItem(`vidhik_chk_${procedureId}`);
      this.checklistState[procedureId] = savedState ? JSON.parse(savedState) : {};

      // If user is citizen, load and merge persistent tracker state
      if (this.token && this.user && (this.user.role === 'user' || this.user.role === 'citizen')) {
        try {
          const trackers = await this.api('/api/citizen/procedures');
          const tracker = (trackers || []).find(t => t.procedure_id === procedureId);
          if (tracker && tracker.completed_documents && Array.isArray(tracker.completed_documents)) {
            const allDocs = [...(data.mandatory_documents || []), ...(data.supporting_documents || [])];
            allDocs.forEach(d => {
              if (tracker.completed_documents.includes(d.document_name)) {
                this.checklistState[procedureId][d.doc_req_id] = true;
              }
            });
          }
        } catch (trkErr) {
          console.warn('Could not load citizen procedure trackers:', trkErr);
        }
      }

      // Render Mandatory & Supporting lists
      const mandContainer = document.getElementById('chk-mandatory-docs-list');
      if (data.mandatory_documents && data.mandatory_documents.length > 0) {
        mandContainer.innerHTML = data.mandatory_documents.map(d => this.renderChecklistItem(data.procedure_id, d, true)).join('');
      } else {
        mandContainer.innerHTML = '<div style="font-size: 13px; color: #94A3B8; font-style: italic;">No mandatory documents specified.</div>';
      }

      const supContainer = document.getElementById('chk-supporting-docs-list');
      if (data.supporting_documents && data.supporting_documents.length > 0) {
        supContainer.innerHTML = data.supporting_documents.map(d => this.renderChecklistItem(data.procedure_id, d, false)).join('');
      } else {
        supContainer.innerHTML = '<div style="font-size: 13px; color: #94A3B8; font-style: italic;">No optional or supporting documents.</div>';
      }

      this.updateChecklistProgress(procedureId);
      document.getElementById('modal-procedure-checklist').classList.add('active');
    } catch (err) {
      this.showToast('Failed to load procedure checklist: ' + err.message, 'error');
    }
  },

  renderChecklistItem(procId, doc, isMandatory) {
    const isChecked = !!(this.checklistState[procId] && this.checklistState[procId][doc.doc_req_id]);

    return `
      <div class="checklist-item-card ${isChecked ? 'checked' : ''}" id="doc-card-${doc.doc_req_id}">
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <input type="checkbox" class="checklist-checkbox" id="chk-doc-${doc.doc_req_id}" ${isChecked ? 'checked' : ''} onchange="App.toggleChecklistDoc(${procId}, ${doc.doc_req_id}, this.checked)">
          <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
              <label for="chk-doc-${doc.doc_req_id}" style="font-size: 14.5px; font-weight: 600; color: #F8FAFC; cursor: pointer;">
                ${this.escape(doc.document_name)}
              </label>
              <div style="display: flex; gap: 6px; align-items: center;">
                <span class="badge badge-info" style="font-size: 11px;">${this.escape(doc.document_type)}</span>
                <span class="badge ${isMandatory ? 'badge-mandatory' : 'badge-supporting'}" style="font-size: 11px;">
                  ${isMandatory ? 'Mandatory' : 'Supporting'}
                </span>
              </div>
            </div>
            <p style="font-size: 13px; color: #CBD5E1; line-height: 1.5; margin-bottom: 6px;">
              <strong>Purpose:</strong> ${this.escape(doc.purpose)}
            </p>
            ${doc.preparation_guidance ? `
              <div style="font-size: 12.5px; color: #94A3B8; background: rgba(0,0,0,0.25); padding: 8px 10px; border-radius: 6px; margin-bottom: 6px;">
                💡 <strong>Preparation Guidance:</strong> ${this.escape(doc.preparation_guidance)}
              </div>
            ` : ''}
            ${doc.statutory_reference_id ? `
              <div style="margin-top: 6px;">
                <span style="font-size: 11.5px; color: #94A3B8; margin-right: 6px;">Statutory Basis:</span>
                <button type="button" class="legal-ref-badge" onclick="event.stopPropagation(); App.viewFullProvisionDetail(${doc.statutory_reference_id})">
                  ⚖️ Sec ${this.escape(doc.section_number)}: ${this.escape(doc.law_name)} ↗
                </button>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  },

  toggleChecklistDoc(procId, docId, isChecked) {
    if (!this.checklistState[procId]) {
      this.checklistState[procId] = {};
    }
    this.checklistState[procId][docId] = isChecked;
    localStorage.setItem(`vidhik_chk_${procId}`, JSON.stringify(this.checklistState[procId]));

    // If citizen, persist to backend
    if (this.token && this.user && (this.user.role === 'user' || this.user.role === 'citizen') && this.activeChecklistProcedure) {
      const allDocs = [...(this.activeChecklistProcedure.mandatory_documents || []), ...(this.activeChecklistProcedure.supporting_documents || [])];
      const targetDoc = allDocs.find(d => d.doc_req_id === docId);
      if (targetDoc) {
        this.api(`/api/citizen/procedures/${procId}/toggle-doc`, 'POST', {
          document_name: targetDoc.document_name
        }).catch(err => console.warn('Could not persist doc toggle:', err));
      }
    }

    const card = document.getElementById(`doc-card-${docId}`);
    if (card) {
      if (isChecked) {
        card.classList.add('checked');
      } else {
        card.classList.remove('checked');
      }
    }

    this.updateChecklistProgress(procId);
  },

  updateChecklistProgress(procId) {
    if (!this.activeChecklistProcedure) return;

    const allDocs = this.activeChecklistProcedure.all_documents || [];
    const total = allDocs.length;
    if (total === 0) return;

    const state = this.checklistState[procId] || {};
    let completed = 0;
    allDocs.forEach(d => {
      if (state[d.doc_req_id]) completed++;
    });

    const percent = Math.round((completed / total) * 100);
    const progressText = document.getElementById('chk-progress-text');
    const progressBar = document.getElementById('chk-progress-bar');

    if (progressText) {
      progressText.innerText = `${completed} of ${total} Completed (${percent}%)`;
    }
    if (progressBar) {
      progressBar.style.width = `${percent}%`;
    }
  },

  resetCurrentChecklistProgress() {
    if (!this.activeChecklistProcedure) return;
    const procId = this.activeChecklistProcedure.procedure_id;

    this.checklistState[procId] = {};
    localStorage.removeItem(`vidhik_chk_${procId}`);

    document.querySelectorAll('#modal-procedure-checklist .checklist-checkbox').forEach(cb => {
      cb.checked = false;
    });
    document.querySelectorAll('#modal-procedure-checklist .checklist-item-card').forEach(card => {
      card.classList.remove('checked');
    });

    this.updateChecklistProgress(procId);
    this.showToast('Checklist progress reset.', 'info');
  },

  async attachChecklistToCase() {
    if (!this.activeChecklistProcedure) return;
    const caseSelect = document.getElementById('chk-attach-case-select');
    const caseId = parseInt(caseSelect.value);
    if (!caseId) {
      this.showToast('Please select a case to attach this checklist.', 'error');
      return;
    }

    const proc = this.activeChecklistProcedure;
    const state = this.checklistState[proc.procedure_id] || {};

    let noteContent = `PROCEDURAL DOCUMENT CHECKLIST: ${proc.procedure_name}\n`;
    noteContent += `Authority: ${proc.authority_type}\n`;
    noteContent += `Jurisdiction: ${proc.jurisdiction}\n`;
    if (proc.governing_law_name) {
      noteContent += `Governing Law: ${proc.governing_law_name} (Section ${proc.governing_section_number || 'N/A'})\n`;
    }
    noteContent += `\n--- MANDATORY STATUTORY DOCUMENTS ---\n`;
    (proc.mandatory_documents || []).forEach(d => {
      const mark = state[d.doc_req_id] ? '[✓ READY]' : '[ ] PENDING';
      noteContent += `${mark} ${d.document_name} (${d.document_type})\n   Purpose: ${d.purpose}\n`;
      if (d.preparation_guidance) noteContent += `   Guidance: ${d.preparation_guidance}\n`;
    });

    noteContent += `\n--- SUPPORTING & CORROBORATIVE DOCUMENTS ---\n`;
    (proc.supporting_documents || []).forEach(d => {
      const mark = state[d.doc_req_id] ? '[✓ READY]' : '[ ] OPTIONAL';
      noteContent += `${mark} ${d.document_name} (${d.document_type})\n   Purpose: ${d.purpose}\n`;
      if (d.preparation_guidance) noteContent += `   Guidance: ${d.preparation_guidance}\n`;
    });

    try {
      await this.api(`/api/lawyer/cases/${caseId}/notes`, 'POST', {
        case_id: caseId,
        title: `Checklist: ${proc.procedure_name}`,
        content: noteContent,
        is_pinned: true
      });
      this.showToast(`Checklist saved to Case #${caseId} brief as a pinned strategy note!`, 'success');
    } catch (err) {
      this.showToast('Failed to attach checklist: ' + err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // PHASE 11: LEGAL DOCUMENT ANALYSIS MODULE
  // -------------------------------------------------------------
  analysisMode: 'file',
  selectedAnalysisFile: null,
  activeAnalysisResult: null,

  async loadDocumentAnalysisModule() {
    this.populateAnalysisCaseDropdown();
    this.loadAnalysisHistory();
  },

  async populateAnalysisCaseDropdown() {
    const dropdown = document.getElementById('analysis-case-dropdown');
    if (!dropdown) return;
    try {
      const data = await this.api('/api/lawyer/cases');
      dropdown.innerHTML = '<option value="">-- Standalone (No Case) --</option>' + (data.cases || []).map(c => `
        <option value="${c.case_id}">${this.escape(c.case_title)} (${c.case_number || 'Brief'})</option>
      `).join('');
    } catch (e) {
      console.warn('Could not populate analysis cases:', e);
    }
  },

  switchAnalysisMode(mode) {
    this.analysisMode = mode;
    const btnFile = document.getElementById('btn-mode-file');
    const btnText = document.getElementById('btn-mode-text');
    const paneFile = document.getElementById('pane-analysis-file');
    const paneText = document.getElementById('pane-analysis-text');

    if (mode === 'file') {
      btnFile?.classList.add('active');
      btnText?.classList.remove('active');
      if (paneFile) paneFile.style.display = 'block';
      if (paneText) paneText.style.display = 'none';
    } else {
      btnText?.classList.add('active');
      btnFile?.classList.remove('active');
      if (paneText) paneText.style.display = 'block';
      if (paneFile) paneFile.style.display = 'none';
    }
  },

  handleAnalysisFileSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 15 * 1024 * 1024) {
      this.showToast('File exceeds maximum size of 15 MB.', 'error');
      e.target.value = '';
      return;
    }

    this.selectedAnalysisFile = file;
    const chip = document.getElementById('selected-file-chip');
    const nameEl = document.getElementById('selected-file-name');
    const sizeEl = document.getElementById('selected-file-size');

    if (nameEl) nameEl.innerText = file.name;
    if (sizeEl) sizeEl.innerText = (file.size / 1024 / 1024).toFixed(2) + ' MB';
    if (chip) chip.style.display = 'flex';
  },

  handleDragOver(e) {
    e.preventDefault();
    document.getElementById('analysis-dropzone')?.classList.add('dragover');
  },

  handleDragLeave(e) {
    e.preventDefault();
    document.getElementById('analysis-dropzone')?.classList.remove('dragover');
  },

  handleFileDrop(e) {
    e.preventDefault();
    document.getElementById('analysis-dropzone')?.classList.remove('dragover');
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;

    const lower = file.name.toLowerCase();
    if (!lower.endsWith('.pdf') && !lower.endsWith('.docx') && !lower.endsWith('.txt')) {
      this.showToast('Only .pdf, .docx, and .txt files are supported.', 'error');
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      this.showToast('File exceeds maximum size of 15 MB.', 'error');
      return;
    }

    this.selectedAnalysisFile = file;
    const chip = document.getElementById('selected-file-chip');
    const nameEl = document.getElementById('selected-file-name');
    const sizeEl = document.getElementById('selected-file-size');

    if (nameEl) nameEl.innerText = file.name;
    if (sizeEl) sizeEl.innerText = (file.size / 1024 / 1024).toFixed(2) + ' MB';
    if (chip) chip.style.display = 'flex';
  },

  clearAnalysisFile(e) {
    if (e) e.stopPropagation();
    this.selectedAnalysisFile = null;
    const input = document.getElementById('analysis-file-input');
    if (input) input.value = '';
    const chip = document.getElementById('selected-file-chip');
    if (chip) chip.style.display = 'none';
  },

  resetAnalysisInput() {
    this.clearAnalysisFile();
    const txt = document.getElementById('analysis-text-content');
    if (txt) txt.value = '';
    const title = document.getElementById('analysis-text-title');
    if (title) title.value = '';

    document.getElementById('analysis-input-card').style.display = 'block';
    document.getElementById('analysis-loading-card').style.display = 'none';
    document.getElementById('analysis-results-card').style.display = 'none';
  },

  async submitDocumentAnalysis() {
    const caseVal = document.getElementById('analysis-case-dropdown')?.value;
    const caseId = caseVal ? parseInt(caseVal) : null;

    const formData = new FormData();
    if (caseId) formData.append('case_id', caseId);

    if (this.analysisMode === 'file') {
      if (!this.selectedAnalysisFile) {
        this.showToast('Please select or drop a legal document file (.pdf, .docx, .txt).', 'error');
        return;
      }
      formData.append('file', this.selectedAnalysisFile);
    } else {
      const textVal = document.getElementById('analysis-text-content')?.value?.trim();
      if (!textVal || textVal.length < 10) {
        this.showToast('Please paste at least 10 characters of legal document text.', 'error');
        return;
      }
      formData.append('text', textVal);
      const titleVal = document.getElementById('analysis-text-title')?.value?.trim();
      if (titleVal) formData.append('document_title', titleVal);
    }

    // UI Loading state
    document.getElementById('analysis-input-card').style.display = 'none';
    document.getElementById('analysis-loading-card').style.display = 'block';
    document.getElementById('analysis-results-card').style.display = 'none';

    try {
      const headers = {};
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      }

      const res = await fetch('/api/analysis/upload', {
        method: 'POST',
        headers: headers,
        body: formData
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned error ${res.status}`);
      }

      const data = await res.json();
      this.renderAnalysisResults(data);
      this.loadAnalysisHistory();
      this.showToast('Document analyzed successfully!', 'success');
    } catch (err) {
      document.getElementById('analysis-input-card').style.display = 'block';
      document.getElementById('analysis-loading-card').style.display = 'none';
      this.showToast('Analysis failed: ' + err.message, 'error');
    }
  },

  renderAnalysisResults(data) {
    this.activeAnalysisResult = data;

    // Header Meta
    document.getElementById('res-doc-type').innerText = data.document_type || 'Unknown / Unclassified';
    document.getElementById('res-file-type').innerText = (data.file_type || 'TEXT').toUpperCase();
    document.getElementById('res-doc-name').innerText = data.document_name;
    const sizeKB = (data.file_size_bytes / 1024).toFixed(1);
    const hash = data.file_hash_sha256 ? data.file_hash_sha256.substring(0, 16) + '...' : 'N/A';
    document.getElementById('res-doc-meta').innerText = `Size: ${sizeKB} KB • Checksum: sha256:${hash}`;

    const caseBadge = document.getElementById('res-case-badge');
    if (data.case_id) {
      caseBadge.style.display = 'inline-block';
      caseBadge.innerText = `Case #${data.case_id}`;
    } else {
      caseBadge.style.display = 'none';
    }

    // Warning
    const warnAlert = document.getElementById('res-warning-alert');
    const warnText = document.getElementById('res-warning-text');
    if (data.warning_message) {
      warnAlert.style.display = 'flex';
      warnText.innerText = data.warning_message;
    } else {
      warnAlert.style.display = 'none';
    }

    // Executive Summary & Takeaways
    document.getElementById('res-summary-text').innerText = data.summary || 'Summary unavailable.';
    const takeawaysBox = document.getElementById('res-takeaways-container');
    takeawaysBox.innerHTML = (data.executive_takeaways || []).map(t => `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-subtle); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 13px; color: #E2E8F0; display: flex; align-items: center; gap: 8px;">
        <span style="color: #818CF8; font-weight: bold;">•</span> ${this.escape(t)}
      </div>
    `).join('');

    // Tab Counts
    document.getElementById('res-parties-count').innerText = (data.parties || []).length;
    document.getElementById('res-dates-count').innerText = (data.dates || []).length;
    document.getElementById('res-values-count').innerText = (data.monetary_values || []).length;
    document.getElementById('res-clauses-count').innerText = (data.clauses || []).length;
    document.getElementById('res-risks-count').innerText = (data.identified_risks || []).length;
    document.getElementById('res-actions-count').innerText = (data.missing_information || []).length + (data.action_items || []).length;
    document.getElementById('res-statutes-count').innerText = (data.legal_references || []).length;

    // 1. Parties
    const pBody = document.getElementById('res-parties-table-body');
    if (!data.parties || data.parties.length === 0) {
      pBody.innerHTML = '<tr><td colspan="3"><div class="empty-state"><div class="empty-state-desc">No specific contracting parties or litigants were explicitly identified.</div></div></td></tr>';
    } else {
      pBody.innerHTML = data.parties.map(p => `
        <tr>
          <td><strong>${this.escape(p.name)}</strong></td>
          <td><span class="badge badge-active">${this.escape(p.role)}</span></td>
          <td style="font-size: 12px; color: var(--text-muted);">${this.escape(p.raw_text || '-')}</td>
        </tr>
      `).join('');
    }

    // 2. Dates & Values
    const dList = document.getElementById('res-dates-list');
    if (!data.dates || data.dates.length === 0) {
      dList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No dates explicitly identified.</div></div>';
    } else {
      dList.innerHTML = data.dates.map(d => `
        <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: #F8FAFC; font-size: 14px;">${this.escape(d.label)}</strong>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">${this.escape(d.context || '')}</div>
          </div>
          <span class="badge badge-completed" style="font-size: 12px;">${this.escape(d.date_str)}</span>
        </div>
      `).join('');
    }

    const vList = document.getElementById('res-values-list');
    if (!data.monetary_values || data.monetary_values.length === 0) {
      vList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No monetary values detected.</div></div>';
    } else {
      vList.innerHTML = data.monetary_values.map(v => `
        <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: #F8FAFC; font-size: 14px;">${this.escape(v.label)}</strong>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">${this.escape(v.context || '')}</div>
          </div>
          <span style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #34D399; font-size: 14px;">${this.escape(v.amount_text)}</span>
        </div>
      `).join('');
    }

    // 3. Clauses & Obligations
    const cList = document.getElementById('res-clauses-list');
    if (!data.clauses || data.clauses.length === 0) {
      cList.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-state-desc">No standard statutory clause patterns were extracted.</div></div></div>';
    } else {
      cList.innerHTML = data.clauses.map(c => `
        <div class="clause-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="font-size: 15px; color: #F8FAFC;">${this.escape(c.title)}</strong>
            <span class="badge badge-active">${this.escape(c.category)}</span>
          </div>
          <p style="font-size: 13px; color: #94A3B8; margin-bottom: 10px; line-height: 1.5;">${this.escape(c.explanation || '')}</p>
          <div style="background: rgba(15, 23, 42, 0.7); border-left: 3px solid var(--accent-primary); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 12.5px; color: #CBD5E1; font-style: italic; line-height: 1.6;">
            "${this.escape(c.text_excerpt)}"
          </div>
        </div>
      `).join('');
    }

    const oList = document.getElementById('res-obligations-list');
    if (!data.obligations_and_rights || data.obligations_and_rights.length === 0) {
      oList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No specific rights or obligations distinguished.</div></div>';
    } else {
      oList.innerHTML = data.obligations_and_rights.map(o => `
        <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: flex-start; gap: 12px;">
          <span class="badge ${o.type === 'obligation' ? 'badge-mandatory' : 'badge-supporting'}">${o.type.toUpperCase()}</span>
          <div>
            <strong style="font-size: 13px; color: #F8FAFC;">${this.escape(o.party)}:</strong>
            <span style="font-size: 13px; color: var(--text-secondary); margin-left: 4px;">${this.escape(o.description)}</span>
          </div>
        </div>
      `).join('');
    }

    // 4. Risks & Issues
    const rList = document.getElementById('res-risks-list');
    if (!data.identified_risks || data.identified_risks.length === 0) {
      rList.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-state-desc">No rule-based potential legal issues detected in this document.</div></div></div>';
    } else {
      rList.innerHTML = data.identified_risks.map(r => `
        <div class="risk-card severity-${r.severity.toLowerCase()}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="font-size: 15px; color: #F8FAFC;">${this.escape(r.title)}</strong>
            <span class="badge ${r.severity === 'High' ? 'badge-mandatory' : (r.severity === 'Medium' ? 'badge-supporting' : 'badge-completed')}">
              ${r.severity} Priority Issue
            </span>
          </div>
          <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 8px;">
            ${this.escape(r.description)}
          </p>
          ${r.evidence_excerpt ? `
            <div style="font-size: 12px; color: var(--text-muted); background: rgba(15, 23, 42, 0.5); padding: 6px 10px; border-radius: var(--radius-sm); margin-bottom: 8px;">
              🔍 Evidence: ${this.escape(r.evidence_excerpt)}
            </div>
          ` : ''}
          ${r.recommendation ? `
            <div style="font-size: 12.5px; color: #38BDF8; font-weight: 500;">
              💡 Recommendation: ${this.escape(r.recommendation)}
            </div>
          ` : ''}
        </div>
      `).join('');
    }

    // 5. Missing Info & Actions
    const mList = document.getElementById('res-missing-list');
    if (!data.missing_information || data.missing_information.length === 0) {
      mList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No obvious structural omissions detected.</div></div>';
    } else {
      mList.innerHTML = data.missing_information.map(m => `
        <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle);">
          <strong style="font-size: 14px; color: #FDA4AF;">⚠️ ${this.escape(m.item)}</strong>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">${this.escape(m.description)}</div>
          <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">Grounds: ${this.escape(m.why_expected)}</div>
        </div>
      `).join('');
    }

    const aList = document.getElementById('res-actions-list');
    if (!data.action_items || data.action_items.length === 0) {
      aList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No specific action items generated.</div></div>';
    } else {
      aList.innerHTML = data.action_items.map(a => `
        <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 14px; color: #F8FAFC;">${this.escape(a.task)}</strong>
            <span class="badge ${a.priority === 'High' ? 'badge-mandatory' : 'badge-completed'}">${a.priority}</span>
          </div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
            👤 Assigned: ${this.escape(a.responsible_party || 'Advocate')} • Trigger: ${this.escape(a.deadline_or_trigger || 'Prior to filing')}
          </div>
        </div>
      `).join('');
    }

    // 6. Grounded Statutory Provisions
    const sList = document.getElementById('res-statutes-list');
    if (!data.legal_references || data.legal_references.length === 0) {
      sList.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-state-desc">No statutory provisions were mentioned or matched in this document.</div></div></div>';
    } else {
      sList.innerHTML = data.legal_references.map(s => `
        <div class="grounded-ref-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <strong style="font-size: 16px; color: #F8FAFC;">${this.escape(s.citation_text)}</strong>
                ${s.is_verified_in_db ? `
                  <span class="verified-badge">✓ Verified in Vidhik DB</span>
                ` : `
                  <span class="unverified-badge">✕ Unverified / Outside Vidhik DB</span>
                `}
              </div>
              ${s.law_name ? `
                <div style="font-size: 13.5px; color: var(--accent-cyan); margin-top: 3px;">
                  📜 ${this.escape(s.law_name)} ${s.section_number ? `• Section ${this.escape(s.section_number)}` : ''}
                </div>
              ` : ''}
            </div>
            ${s.section_id ? `
              <button class="btn btn-secondary btn-sm" onclick="App.openSectionDetail(${s.section_id})">
                Inspect Section ↗
              </button>
            ` : ''}
          </div>
          ${s.section_title ? `
            <div style="font-size: 13px; font-weight: 500; color: #CBD5E1; margin-bottom: 6px;">
              Title: ${this.escape(s.section_title)}
            </div>
          ` : ''}
          <div style="font-size: 12.5px; color: var(--text-muted); line-height: 1.5;">
            ${this.escape(s.relevance_explanation || '')}
          </div>
        </div>
      `).join('');
    }

    // Reveal results
    document.getElementById('analysis-input-card').style.display = 'none';
    document.getElementById('analysis-loading-card').style.display = 'none';
    document.getElementById('analysis-results-card').style.display = 'block';

    // Switch to first results tab
    this.switchResTab('parties');
  },

  switchResTab(tabName) {
    document.querySelectorAll('.tab-btn[data-res-tab]').forEach(btn => {
      if (btn.getAttribute('data-res-tab') === tabName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    const panes = ['parties', 'dates-values', 'clauses', 'risks', 'actions', 'statutes'];
    panes.forEach(p => {
      const el = document.getElementById(`res-tab-${p}`);
      if (el) {
        el.style.display = (p === tabName) ? 'block' : 'none';
      }
    });
  },

  async openSaveAnalysisModal() {
    if (!this.activeAnalysisResult) return;
    const select = document.getElementById('m-save-analysis-case-select');
    select.innerHTML = '<option value="">Loading active cases...</option>';
    try {
      const data = await this.api('/api/lawyer/cases');
      select.innerHTML = (data.cases || []).map(c => `
        <option value="${c.case_id}" ${this.activeAnalysisResult.case_id === c.case_id ? 'selected' : ''}>
          ${this.escape(c.case_title)} (${c.case_number || 'Brief'})
        </option>
      `).join('');
      document.getElementById('modal-save-analysis-to-case').classList.add('active');
    } catch (e) {
      this.showToast('Failed to load lawyer cases: ' + e.message, 'error');
    }
  },

  async submitSaveAnalysisToCase(e) {
    e.preventDefault();
    if (!this.activeAnalysisResult || !this.activeAnalysisResult.analysis_id) {
      this.showToast('Please analyze a document first before saving to a case.', 'error');
      return;
    }

    const caseId = parseInt(document.getElementById('m-save-analysis-case-select').value);
    if (!caseId) {
      this.showToast('Please select a target case.', 'error');
      return;
    }

    const payload = {
      case_id: caseId,
      save_as_document: document.getElementById('m-save-chk-doc').checked,
      save_summary_note: document.getElementById('m-save-chk-note').checked,
      link_verified_sections: document.getElementById('m-save-chk-sec').checked
    };

    try {
      const res = await this.api(`/api/analysis/${this.activeAnalysisResult.analysis_id}/save-to-case`, 'POST', payload);
      this.showToast(`Analysis saved to Case #${caseId}! (${res.linked_sections_count} sections linked)`, 'success');
      this.closeModals();
      this.loadAnalysisHistory();
    } catch (err) {
      this.showToast('Save to case failed: ' + err.message, 'error');
    }
  },

  exportAnalysisSummary() {
    if (!this.activeAnalysisResult) return;
    const a = this.activeAnalysisResult;
    let md = `# VIDHIK AI LEGAL DOCUMENT ANALYSIS REPORT\n`;
    md += `Document: ${a.document_name}\n`;
    md += `Classification: ${a.document_type}\n`;
    md += `Generated: ${new Date().toLocaleString()}\n`;
    md += `Checksum: ${a.file_hash_sha256 || 'N/A'}\n\n`;
    md += `## EXECUTIVE SUMMARY\n${a.summary}\n\n`;
    md += `## KEY TAKEAWAYS\n` + (a.executive_takeaways || []).map(t => `- ${t}`).join('\n') + `\n\n`;
    md += `## PARTIES IDENTIFIED\n` + (a.parties || []).map(p => `- ${p.name} (${p.role})`).join('\n') + `\n\n`;
    md += `## POTENTIAL ISSUES / RISKS\n` + (a.identified_risks || []).map(r => `[${r.severity}] ${r.title}: ${r.description}`).join('\n') + `\n\n`;
    md += `## STATUTORY GROUNDING\n` + (a.legal_references || []).map(s => `- ${s.citation_text} | Verified: ${s.is_verified_in_db}`).join('\n') + `\n\n`;
    md += `---\nDISCLAIMER: Automated research tool. Does not constitute formal legal counsel.\n`;

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Vidhik_Analysis_${a.document_name.replace(/[^a-zA-Z0-9]/g, '_')}.md`;
    link.click();
    URL.revokeObjectURL(url);
    this.showToast('Analysis report downloaded.', 'success');
  },

  async loadAnalysisHistory() {
    const container = document.getElementById('analysis-history-container');
    if (!container) return;

    try {
      const data = await this.api('/api/analysis/history');
      if (!data.analyses || data.analyses.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No historical analyses yet. Upload or paste a document to begin.</div></div>';
        return;
      }

      container.innerHTML = data.analyses.map(h => `
        <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="color: #F8FAFC; font-size: 15px;">${this.escape(h.document_name)}</strong>
              <span class="badge badge-active">${this.escape(h.document_type)}</span>
              ${h.case_title ? `<span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #A5B4FC;">Case: ${this.escape(h.case_title)}</span>` : ''}
            </div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">
              ${this.escape(h.summary_preview)}
            </div>
            <div style="font-size: 11.5px; color: #64748B; margin-top: 4px;">
              ${new Date(h.created_at).toLocaleDateString()} • Issues: ${h.risks_count} • Verified Provisions: ${h.verified_references_count}
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="App.loadAnalysisById(${h.analysis_id})">Open Report</button>
            <button class="btn btn-danger btn-sm" onclick="App.deleteAnalysis(${h.analysis_id})">Delete</button>
          </div>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-desc">Could not load history: ${this.escape(e.message)}</div></div>`;
    }
  },

  async loadAnalysisById(analysisId) {
    try {
      const data = await this.api(`/api/analysis/${analysisId}`);
      this.renderAnalysisResults(data);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      this.showToast('Could not load analysis: ' + e.message, 'error');
    }
  },

  async deleteAnalysis(analysisId) {
    if (!confirm('Are you sure you want to delete this analysis report?')) return;
    try {
      await this.api(`/api/analysis/${analysisId}`, 'DELETE');
      this.showToast('Analysis deleted.', 'success');
      this.loadAnalysisHistory();
      if (this.activeAnalysisResult && this.activeAnalysisResult.analysis_id === analysisId) {
        this.resetAnalysisInput();
      }
    } catch (e) {
      this.showToast('Delete failed: ' + e.message, 'error');
    }
  },

  // =============================================================
  // PHASE 14: CITIZEN / USER MODULE
  // =============================================================

  // 1. Citizen Dashboard
  async loadCitizenDashboard() {
    try {
      const data = await this.api('/api/citizen/dashboard');

      // Update KPIs
      const kCases = document.getElementById('kpi-citizen-cases');
      const kDocs = document.getElementById('kpi-citizen-docs');
      const kHearings = document.getElementById('kpi-citizen-hearings');
      const kBookmarks = document.getElementById('kpi-citizen-bookmarks');

      if (kCases) kCases.innerText = data.metrics.active_cases;
      if (kDocs) kDocs.innerText = data.metrics.total_documents;
      if (kHearings) kHearings.innerText = data.metrics.upcoming_hearings;
      if (kBookmarks) kBookmarks.innerText = data.metrics.saved_sections;

      // Update sidebar counts
      const sbCases = document.getElementById('sidebar-c-case-count');
      const sbDocs = document.getElementById('sidebar-c-doc-count');
      const sbBm = document.getElementById('sidebar-c-bm-count');
      if (sbCases) sbCases.innerText = data.metrics.active_cases;
      if (sbDocs) sbDocs.innerText = data.metrics.total_documents;
      if (sbBm) sbBm.innerText = data.metrics.saved_sections;

      // Render Active Cases List
      const cList = document.getElementById('citizen-dash-cases-list');
      if (cList) {
        if (!data.recent_cases || data.recent_cases.length === 0) {
          cList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">You do not have any registered legal matters yet. Use "+ File New Matter" to register a case.</div></div>';
        } else {
          cList.innerHTML = data.recent_cases.map(c => `
            <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="App.openCitizenCaseDetail(${c.case_id})">
              <div>
                <div style="font-weight: 600; color: var(--text-primary); font-size: 14px;">${this.escape(c.title)}</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 3px;">
                  🏛️ ${this.escape(c.court || 'Court / Forum')} • <code>${this.escape(c.case_number || 'Matter Brief')}</code>
                </div>
                ${c.lawyer_name ? `<div style="font-size: 11.5px; color: var(--accent-cyan); margin-top: 2px;">Assigned Counsel: ${this.escape(c.lawyer_name)}</div>` : ''}
              </div>
              <div style="text-align: right;">
                <span class="badge badge-${c.status}">${c.status}</span>
                <div style="font-size: 11px; color: #818CF8; margin-top: 4px;">View Matter →</div>
              </div>
            </div>
          `).join('');
        }
      }

      // Render Upcoming Hearings
      const hList = document.getElementById('citizen-dash-hearings-list');
      if (hList) {
        if (!data.upcoming_hearings || data.upcoming_hearings.length === 0) {
          hList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No upcoming court hearings scheduled.</div></div>';
        } else {
          hList.innerHTML = data.upcoming_hearings.map(h => `
            <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="font-weight: 600; color: var(--text-primary); font-size: 14px;">${this.escape(h.title)}</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 3px;">
                  ⚖️ ${this.escape(h.case_title || 'Legal Matter')} (${this.escape(h.court_name || 'Designated Court')})
                </div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-active">${h.reminder_date}</span>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${h.reminder_time || '10:30 AM'}</div>
              </div>
            </div>
          `).join('');
        }
      }

      // Render Recent Document Analyses
      const aList = document.getElementById('citizen-dash-analyses-list');
      if (aList) {
        if (!data.recent_analyses || data.recent_analyses.length === 0) {
          aList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No analyzed legal documents yet. Analyze an agreement or notice to check risk flags.</div></div>';
        } else {
          aList.innerHTML = data.recent_analyses.map(a => `
            <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="App.navigate('document-analysis'); App.loadAnalysisById(${a.analysis_id});">
              <div>
                <div style="font-size: 13.5px; font-weight: 500; color: var(--text-primary);">📄 ${this.escape(a.document_name)}</div>
                <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 2px;">
                  ${this.escape(a.document_type)} • ${new Date(a.created_at).toLocaleDateString()}
                </div>
              </div>
              <div style="font-size: 12px; color: var(--accent-cyan);">View Report →</div>
            </div>
          `).join('');
        }
      }

      // Render Recent Documents
      const dList = document.getElementById('citizen-dash-documents-list');
      if (dList) {
        if (!data.recent_documents || data.recent_documents.length === 0) {
          dList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No case documents uploaded yet. Use "+ Upload Doc" to attach case records.</div></div>';
        } else {
          dList.innerHTML = data.recent_documents.map(d => `
            <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="font-weight: 500; font-size: 13.5px; color: var(--text-primary);">📄 ${this.escape(d.document_name)}</div>
                <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 2px;">
                  ${this.escape(d.document_type || 'Case File')} • ${this.escape(d.case_title || 'Legal Matter')}
                </div>
              </div>
              <span class="badge badge-completed">${d.document_type || 'Attached'}</span>
            </div>
          `).join('');
        }
      }

      // Render Tracked Procedure Progress
      try {
        const procData = await this.api('/api/citizen/procedures');
        const pList = document.getElementById('citizen-dash-procedures-list');
        if (pList) {
          const procs = procData.procedures || [];
          const activeProcs = procs.filter(p => (p.completed_count || 0) > 0 || p.is_tracked);
          const displayProcs = activeProcs.length > 0 ? activeProcs : procs.slice(0, 3);
          if (displayProcs.length === 0) {
            pList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No procedures explored yet. Explore Procedure Checklists to track requirements.</div></div>';
          } else {
            pList.innerHTML = displayProcs.map(p => {
              const comp = p.completed_count || 0;
              const tot = p.required_docs_count || (p.documents ? p.documents.length : 1);
              const pct = tot > 0 ? Math.round((comp / tot) * 100) : 0;
              return `
                <div class="procedure-progress-card" style="cursor: pointer;" onclick="App.openProcedureChecklist(${p.procedure_id})">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="font-size: 13.5px; color: #F8FAFC;">${this.escape(p.procedure_name)}</strong>
                    <span style="font-size: 12px; color: var(--accent-cyan); font-weight: 600;">${pct}% Complete</span>
                  </div>
                  <div class="progress-track">
                    <div class="progress-fill" style="width: ${pct}%;"></div>
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-top: 6px;">
                    <span>${comp} of ${tot} documents ready</span>
                    <span>${this.escape(p.category_name || 'Legal Process')}</span>
                  </div>
                </div>
              `;
            }).join('');
          }
        }
      } catch (procErr) {
        console.warn('Could not load procedures for dashboard:', procErr);
      }

      // Render Saved Provisions
      try {
        const bmData = await this.api('/api/citizen/bookmarks');
        const bList = document.getElementById('citizen-dash-bookmarks-list');
        if (bList) {
          const bms = Array.isArray(bmData) ? bmData : [];
          if (bms.length === 0) {
            bList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No saved provisions yet. Bookmark statutory sections from Legal Research.</div></div>';
          } else {
            bList.innerHTML = bms.slice(0, 4).map(b => `
              <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="App.viewFullProvisionDetail(${b.section_id})">
                <div>
                  <div style="font-weight: 600; font-size: 13.5px; color: #F8FAFC;">Section ${this.escape(b.section_number)}: ${this.escape(b.section_title || '')}</div>
                  <div style="font-size: 11.5px; color: var(--accent-cyan); margin-top: 2px;">📖 ${this.escape(b.law_name || 'Statute')}</div>
                </div>
                <div style="font-size: 11.5px; color: #818CF8;">View →</div>
              </div>
            `).join('');
          }
        }
      } catch (bmErr) {
        console.warn('Could not load bookmarks for dashboard:', bmErr);
      }

      // Render Recent Legal Searches
      try {
        const shData = await this.api('/api/citizen/search-history?limit=4');
        const sList = document.getElementById('citizen-dash-searches-list');
        if (sList) {
          const searches = Array.isArray(shData) ? shData : [];
          if (searches.length === 0) {
            sList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No search history yet. Search statutes in Legal Research.</div></div>';
          } else {
            sList.innerHTML = `
              <div style="display: flex; flex-direction: column; gap: 8px;">
                ${searches.map(s => `
                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(15, 23, 42, 0.4); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                    <div>
                      <span style="font-size: 13px; font-weight: 500; color: #F8FAFC;">🔍 "${this.escape(s.query_text)}"</span>
                      <div style="font-size: 10.5px; color: var(--text-muted); margin-top: 2px;">
                        ${s.results_count || 0} provisions matched • ${new Date(s.searched_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button class="search-again-btn" onclick="App.reSearchFromHistory('${this.escape(s.query_text)}', '${this.escape(s.filters && s.filters.jurisdiction ? s.filters.jurisdiction : '')}')">Search Again</button>
                  </div>
                `).join('')}
              </div>
            `;
          }
        }
      } catch (shErr) {
        console.warn('Could not load search history for dashboard:', shErr);
      }

      // Render Notifications
      const nList = document.getElementById('citizen-dash-notifs-list');
      if (nList) {
        if (!data.recent_notifications || data.recent_notifications.length === 0) {
          nList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No new notifications.</div></div>';
        } else {
          nList.innerHTML = data.recent_notifications.map(n => `
            <div style="padding: 10px 0; border-bottom: 1px solid var(--border-subtle);">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="font-size: 13.5px; color: ${n.is_read ? 'var(--text-secondary)' : '#F8FAFC'};">${this.escape(n.title)}</strong>
                <span style="font-size: 11px; color: var(--text-muted);">${new Date(n.created_at).toLocaleDateString()}</span>
              </div>
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 3px;">${this.escape(n.message)}</div>
            </div>
          `).join('');
        }
      }
    } catch (err) {
      this.showToast('Failed to load citizen dashboard: ' + err.message, 'error');
    }
  },

  // 2. Citizen Cases
  async loadCitizenCases() {
    const container = document.getElementById('citizen-cases-container');
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';

    try {
      const cases = await this.api('/api/citizen/cases');
      this.citizenCases = cases || [];
      this.renderCitizenCasesList(this.citizenCases);
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-title">Error Loading Cases</div><div class="empty-state-desc">${this.escape(err.message)}</div></div>`;
    }
  },

  renderCitizenCasesList(cases) {
    const container = document.getElementById('citizen-cases-container');
    if (!container) return;

    if (!cases || cases.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">⚖️</div>
          <div class="empty-state-title">No Legal Matters Registered</div>
          <div class="empty-state-desc">You do not have any civil or statutory matters registered. Click "+ File New Matter" to open a case file.</div>
          <button class="btn btn-primary" style="margin-top: 14px;" onclick="App.openCitizenNewCaseModal()">+ File New Matter</button>
        </div>
      `;
      return;
    }

    container.innerHTML = cases.map(c => `
      <div class="card" style="margin-bottom: 16px; border: 1px solid var(--border-subtle); transition: border-color 0.2s ease; cursor: pointer;" onclick="App.openCitizenCaseDetail(${c.case_id})">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
              <span class="badge badge-${c.status}">${c.status}</span>
              <span class="badge badge-completed">${this.escape(c.case_type || 'Civil Matter')}</span>
              ${c.case_number ? `<span style="font-size: 12px; color: var(--accent-cyan); font-family: monospace;">${this.escape(c.case_number)}</span>` : ''}
            </div>
            <h3 style="font-size: 18px; color: #F8FAFC; margin-bottom: 4px;">${this.escape(c.title)}</h3>
            <div style="font-size: 13px; color: var(--text-muted);">
              🏛️ ${this.escape(c.court || 'Court / Judicial Forum')} • Opposite Party: <strong style="color: var(--text-secondary);">${this.escape(c.opposite_party || 'Unspecified')}</strong>
            </div>
          </div>
          <div style="text-align: right;">
            ${c.lawyer_name ? `
              <div style="background: rgba(15, 23, 42, 0.6); padding: 6px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: inline-block;">
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Assigned Counsel</div>
                <div style="font-size: 12.5px; font-weight: 600; color: #818CF8;">${this.escape(c.lawyer_name)}</div>
              </div>
            ` : `
              <span class="badge" style="background: rgba(100, 116, 139, 0.2); color: #94A3B8;">Self Represented</span>
            `}
          </div>
        </div>

        ${c.description ? `
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 12px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            ${this.escape(c.description)}
          </div>
        ` : ''}

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); font-size: 12px; color: var(--text-muted);">
          <div>
            ${c.filing_date ? `Filing Date: ${c.filing_date}` : (c.created_at ? `Created: ${new Date(c.created_at).toLocaleDateString()}` : '')}
          </div>
          <div style="display: flex; gap: 14px; align-items: center;">
            <span>📄 ${c.documents_count || 0} Docs</span>
            <span>📅 ${c.hearings_count || 0} Hearings</span>
            <span style="color: var(--accent-cyan); font-weight: 500;">Open Matter Brief →</span>
          </div>
        </div>
      </div>
    `).join('');
  },

  filterCitizenCases() {
    const q = (document.getElementById('citizen-case-search')?.value || '').toLowerCase();
    const status = document.getElementById('citizen-case-status-filter')?.value || '';

    const filtered = (this.citizenCases || []).filter(c => {
      const matchQ = !q || (c.title && c.title.toLowerCase().includes(q)) ||
                     (c.court && c.court.toLowerCase().includes(q)) ||
                     (c.opposite_party && c.opposite_party.toLowerCase().includes(q));
      const matchStatus = !status || c.status === status;
      return matchQ && matchStatus;
    });

    this.renderCitizenCasesList(filtered);
  },

  openCitizenCaseDetail(caseId) {
    this.currentCaseId = caseId;
    this.navigate('citizen-case-detail');
  },

  async loadCitizenCaseDetail(caseId) {
    try {
      const c = await this.api(`/api/citizen/cases/${caseId}`);

      // Header Info
      document.getElementById('c-detail-title').innerText = c.title;
      document.getElementById('c-detail-number').innerText = c.case_number ? `CASE #${c.case_number}` : 'MATTER BRIEF';
      document.getElementById('c-detail-type').innerText = c.case_type || 'Civil Matter';
      document.getElementById('c-detail-court').innerText = `🏛️ ${c.court || 'Court / Forum Name'}`;

      const stBadge = document.getElementById('c-detail-status');
      stBadge.innerText = c.status;
      stBadge.className = `badge badge-${c.status}`;

      // Assigned Counsel
      const counselBox = document.getElementById('c-detail-lawyer-card');
      if (c.lawyer) {
        counselBox.style.display = 'block';
        document.getElementById('c-detail-lawyer-name').innerText = c.lawyer.full_name;
        document.getElementById('c-detail-lawyer-spec').innerText = c.lawyer.specializations || 'Advocate High Court';
        document.getElementById('c-detail-lawyer-contact').innerText = `📞 ${c.lawyer.phone || 'Contact via Chambers'} • 📧 ${c.lawyer.email}`;
      } else {
        counselBox.style.display = 'none';
      }

      // Facts & Details
      document.getElementById('c-detail-description').innerText = c.description || 'No description summary entered.';
      document.getElementById('c-detail-opposite').innerText = c.opposite_party || 'None specified';
      document.getElementById('c-detail-filing-date').innerText = c.filing_date || 'Pending';
      document.getElementById('c-detail-incident-date').innerText = c.incident_date || 'N/A';
      document.getElementById('c-detail-police').innerText = `${c.police_station || ''} ${c.location ? `(${c.location})` : ''}`.trim() || 'N/A';

      // Official Court Reference (eCourts)
      const cnr = c.cnr_number || (c.court_reference ? c.court_reference.cnr_number : null);
      this.currentCitizenCaseCNR = cnr;
      this.currentCitizenCaseCourtReference = c.court_reference || {
        cnr_number: c.cnr_number,
        court_source: c.court_source || 'eCourts India',
        official_case_url: c.official_case_url,
        last_verified_at: c.last_verified_at,
        external_status: c.external_status,
        external_next_hearing_date: c.external_next_hearing_date
      };

      const cnrElem = document.getElementById('c-detail-cnr');
      if (cnrElem) cnrElem.innerText = cnr || 'Not Linked';
      const cSourceElem = document.getElementById('c-detail-court-source');
      if (cSourceElem) cSourceElem.innerText = (c.court_reference?.court_source || c.court_source) || 'eCourts India';
      const extStatusElem = document.getElementById('c-detail-external-status');
      if (extStatusElem) extStatusElem.innerText = (c.court_reference?.external_status || c.external_status) || 'Not verified yet';
      const extHearingElem = document.getElementById('c-detail-external-hearing-date');
      if (extHearingElem) extHearingElem.innerText = (c.court_reference?.external_next_hearing_date || c.external_next_hearing_date) || 'None recorded';
      const lastVerElem = document.getElementById('c-detail-last-verified-at');
      if (lastVerElem) {
        const lv = c.court_reference?.last_verified_at || c.last_verified_at;
        lastVerElem.innerText = lv ? new Date(lv).toLocaleString() : 'Never';
      }

      // Counts
      const docCount = c.documents ? c.documents.length : 0;
      const hearingCount = c.hearings ? c.hearings.length : 0;
      document.getElementById('c-tab-doc-count').innerText = docCount;
      document.getElementById('c-tab-hearing-count').innerText = hearingCount;

      // Render Documents Tab
      const dList = document.getElementById('c-detail-docs-list');
      if (!c.documents || c.documents.length === 0) {
        dList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No documents uploaded for this matter yet. Click "+ Upload Document" to attach records.</div></div>';
      } else {
        dList.innerHTML = c.documents.map(d => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 500; color: #F8FAFC; font-size: 14px;">📄 ${this.escape(d.document_name)}</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                <span class="badge badge-completed">${this.escape(d.document_type)}</span>
                ${d.description ? ` • ${this.escape(d.description)}` : ''}
              </div>
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted);">
              ${new Date(d.uploaded_at).toLocaleDateString()}
            </div>
          </div>
        `).join('');
      }

      // Render Hearings Tab
      const hList = document.getElementById('c-detail-hearings-list');
      if (!c.hearings || c.hearings.length === 0) {
        hList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No court appearances or hearings scheduled for this case.</div></div>';
      } else {
        hList.innerHTML = c.hearings.map(h => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; color: #F8FAFC; font-size: 14px;">${this.escape(h.title)}</div>
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 3px;">
                🏛️ ${this.escape(h.court_name || 'Designated Court')} • Presiding: ${this.escape(h.judge_name || 'Hon\'ble Judge')}
              </div>
              ${h.notes ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">📝 ${this.escape(h.notes)}</div>` : ''}
            </div>
            <div style="text-align: right;">
              <span class="badge badge-active">${h.reminder_date}</span>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${h.reminder_time || '10:30 AM'}</div>
            </div>
          </div>
        `).join('');
      }

      // Render Updates Tab
      const uList = document.getElementById('c-detail-updates-list');
      if (!c.updates || c.updates.length === 0) {
        uList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No procedural updates logged for this matter yet.</div></div>';
      } else {
        uList.innerHTML = c.updates.map(u => `
          <div style="display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--border-subtle);">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(99, 102, 241, 0.15); color: #818CF8; display: flex; align-items: center; justify-content: center; font-size: 14px;">
              ⚡
            </div>
            <div style="flex: 1;">
              <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">${this.escape(u.update_title)}</div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">${this.escape(u.update_description)}</div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
                Logged by: ${this.escape(u.updated_by_name || 'Legal Counsel')} • ${new Date(u.update_date).toLocaleDateString()}
              </div>
            </div>
          </div>
        `).join('');
      }

      // Render Sections Tab
      const sList = document.getElementById('c-detail-sections-list');
      if (!c.legal_sections || c.legal_sections.length === 0) {
        sList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No statutory provisions have been associated with this case file.</div></div>';
      } else {
        sList.innerHTML = c.legal_sections.map(s => `
          <div class="card" style="margin-bottom: 12px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <span class="badge badge-active" style="margin-bottom: 4px;">Section ${this.escape(s.section_number)}</span>
                <h4 style="font-size: 15px; color: #F8FAFC;">${this.escape(s.section_title || 'Section Provision')}</h4>
                <div style="font-size: 13px; color: var(--accent-cyan);">${this.escape(s.law_name)}</div>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="App.viewFullProvisionDetail(${s.section_id})">Inspect Section</button>
            </div>
            ${s.explanation ? `
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 8px; background: var(--bg-primary); padding: 8px 12px; border-radius: var(--radius-sm);">
                <strong>Legal Rationale:</strong> ${this.escape(s.explanation)}
              </div>
            ` : ''}
          </div>
        `).join('');
      }

    } catch (err) {
      this.showToast('Could not load case details: ' + err.message, 'error');
    }
  },

  openCitizenNewCaseModal() {
    const form = document.getElementById('form-citizen-new-case');
    if (form) form.reset();
    document.getElementById('modal-citizen-new-case')?.classList.add('active');
  },

  async submitCitizenNewCase(e) {
    e.preventDefault();
    const cnr = document.getElementById('m-c-case-cnr')?.value.trim() || null;
    const payload = {
      title: document.getElementById('m-c-case-title').value.trim(),
      case_type: document.getElementById('m-c-case-type').value || 'Civil Litigation',
      court: document.getElementById('m-c-case-court').value.trim() || null,
      opposite_party: document.getElementById('m-c-case-opposite').value.trim() || null,
      incident_date: document.getElementById('m-c-case-incident-date').value || null,
      police_station: document.getElementById('m-c-case-police').value.trim() || null,
      location: document.getElementById('m-c-case-location').value.trim() || null,
      description: document.getElementById('m-c-case-description').value.trim(),
      cnr_number: cnr
    };

    try {
      const created = await this.api('/api/citizen/cases', 'POST', payload);
      this.showToast('Legal matter registered successfully!', 'success');
      this.closeModals();
      if (this.currentView === 'citizen-cases') {
        this.loadCitizenCases();
      } else {
        this.openCitizenCaseDetail(created.case_id);
      }
    } catch (err) {
      this.showToast('Could not file case: ' + err.message, 'error');
    }
  },

  // 3. Citizen Documents
  async loadCitizenDocuments() {
    const container = document.getElementById('citizen-docs-container');
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';

    try {
      const docs = await this.api('/api/citizen/documents');
      this.citizenDocuments = docs || [];

      if (this.citizenDocuments.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">📄</div>
            <div class="empty-state-title">No Documents Uploaded</div>
            <div class="empty-state-desc">You have not uploaded any case documents or legal filings yet. Click "+ Upload Document" to save legal files.</div>
            <button class="btn btn-primary" style="margin-top: 14px;" onclick="App.openCitizenUploadDocModal()">+ Upload Document</button>
          </div>
        `;
        return;
      }

      container.innerHTML = this.citizenDocuments.map(d => `
        <div class="card" style="margin-bottom: 12px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <strong style="color: #F8FAFC; font-size: 15px;">📄 ${this.escape(d.document_name)}</strong>
              <span class="badge badge-completed">${this.escape(d.document_type)}</span>
              ${d.case_title ? `<span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #A5B4FC;">Matter: ${this.escape(d.case_title)}</span>` : ''}
            </div>
            ${d.description ? `<div style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">${this.escape(d.description)}</div>` : ''}
            <div style="font-size: 11.5px; color: #64748B; margin-top: 4px;">
              Uploaded: ${new Date(d.uploaded_at).toLocaleDateString()}
            </div>
          </div>
          <div>
            ${d.case_id ? `
              <button class="btn btn-secondary btn-sm" onclick="App.openCitizenCaseDetail(${d.case_id})">View Matter →</button>
            ` : ''}
          </div>
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-desc">Could not load documents: ${this.escape(err.message)}</div></div>`;
    }
  },

  async openCitizenUploadDocModal(preselectedCaseId = null) {
    const select = document.getElementById('m-c-doc-case-select');
    if (select) {
      select.innerHTML = '<option value="">General / Unassigned Document</option>';
      try {
        if (!this.citizenCases || this.citizenCases.length === 0) {
          this.citizenCases = await this.api('/api/citizen/cases');
        }
        (this.citizenCases || []).forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.case_id;
          opt.innerText = `${c.title} (${c.case_number || 'Brief'})`;
          if (preselectedCaseId && c.case_id === preselectedCaseId) {
            opt.selected = true;
          }
          select.appendChild(opt);
        });
      } catch (e) {
        console.warn('Could not populate citizen cases in upload modal:', e);
      }
    }

    const form = document.getElementById('form-citizen-upload-doc');
    if (form) form.reset();
    if (preselectedCaseId && select) select.value = preselectedCaseId;
    document.getElementById('modal-citizen-upload-doc')?.classList.add('active');
  },

  async submitCitizenUploadDoc(e) {
    e.preventDefault();
    const caseSelect = document.getElementById('m-c-doc-case-select');
    const caseId = caseSelect && caseSelect.value ? parseInt(caseSelect.value) : null;
    const docName = document.getElementById('m-c-doc-name').value.trim();
    const docType = document.getElementById('m-c-doc-type').value;
    const desc = document.getElementById('m-c-doc-desc').value.trim() || null;

    try {
      await this.api('/api/citizen/documents', 'POST', {
        case_id: caseId,
        document_name: docName,
        document_type: docType,
        description: desc
      });
      this.showToast('Document uploaded successfully!', 'success');
      this.closeModals();
      if (this.currentView === 'citizen-case-detail' && this.currentCaseId) {
        this.loadCitizenCaseDetail(this.currentCaseId);
      } else if (this.currentView === 'citizen-documents') {
        this.loadCitizenDocuments();
      } else {
        this.loadCitizenDashboard();
      }
    } catch (err) {
      this.showToast('Upload failed: ' + err.message, 'error');
    }
  },

  // 4. Saved Legal Provisions (Bookmarks)
  async loadCitizenBookmarks() {
    const container = document.getElementById('citizen-bookmarks-container');
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';

    try {
      const bookmarks = await this.api('/api/citizen/bookmarks');
      this.citizenBookmarks = bookmarks || [];
      this.renderCitizenBookmarksList(this.citizenBookmarks);
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-desc">Could not load bookmarks: ${this.escape(err.message)}</div></div>`;
    }
  },

  renderCitizenBookmarksList(bookmarks) {
    const container = document.getElementById('citizen-bookmarks-container');
    if (!container) return;

    if (!bookmarks || bookmarks.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔖</div>
          <div class="empty-state-title">No Saved Provisions</div>
          <div class="empty-state-desc">You have not bookmarked any statutory sections. Search Central & State laws and bookmark key sections for quick reference.</div>
          <button class="btn btn-secondary btn-sm" style="margin-top: 14px;" onclick="App.navigate('research')">🔍 Go to Legal Research</button>
        </div>
      `;
      return;
    }

    container.innerHTML = bookmarks.map(b => `
      <div class="card" style="margin-bottom: 14px; border: 1px solid var(--border-subtle);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 4px;">
              <span class="badge badge-active">Section ${this.escape(b.section_number)}</span>
              <span class="badge badge-completed">${this.escape(b.tag || 'General')}</span>
            </div>
            <h3 style="font-size: 17px; color: #F8FAFC; margin-bottom: 2px;">${this.escape(b.section_title || 'Section Provision')}</h3>
            <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 500;">📖 ${this.escape(b.law_name)}</div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="App.viewFullProvisionDetail(${b.section_id})">📖 View Text</button>
            <button class="btn btn-danger btn-sm" onclick="App.deleteBookmark(${b.section_id})">✕ Remove</button>
          </div>
        </div>

        ${b.notes ? `
          <div style="font-size: 13px; color: #CBD5E1; background: rgba(15, 23, 42, 0.5); padding: 10px 14px; border-radius: var(--radius-sm); margin: 10px 0; border: 1px solid var(--border-subtle);">
            📝 <strong>My Reference Note:</strong> ${this.escape(b.notes)}
          </div>
        ` : ''}

        <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">
          Saved on ${new Date(b.created_at).toLocaleDateString()}
        </div>
      </div>
    `).join('');
  },

  filterBookmarks() {
    const q = (document.getElementById('citizen-bm-search')?.value || '').toLowerCase();
    const filtered = (this.citizenBookmarks || []).filter(b => {
      return !q || (b.section_number && b.section_number.toLowerCase().includes(q)) ||
                   (b.section_title && b.section_title.toLowerCase().includes(q)) ||
                   (b.law_name && b.law_name.toLowerCase().includes(q)) ||
                   (b.notes && b.notes.toLowerCase().includes(q));
    });
    this.renderCitizenBookmarksList(filtered);
  },

  async quickBookmarkSection(sectionId, note = null) {
    try {
      await this.api('/api/citizen/bookmarks', 'POST', {
        section_id: sectionId,
        notes: note,
        tag: 'General'
      });
      this.showToast('Section bookmarked to your saved provisions!', 'success');
      if (this.currentView === 'citizen-bookmarks') {
        this.loadCitizenBookmarks();
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async deleteBookmark(sectionId) {
    if (!confirm('Remove this section from your saved provisions?')) return;
    try {
      await this.api(`/api/citizen/bookmarks/${sectionId}`, 'DELETE');
      this.showToast('Bookmark removed.', 'info');
      this.loadCitizenBookmarks();
    } catch (err) {
      this.showToast('Could not delete bookmark: ' + err.message, 'error');
    }
  },

  // 5. Citizen Profile
  async loadCitizenProfile() {
    try {
      const data = await this.api('/api/citizen/profile');

      // Overview Card
      const nameEl = document.getElementById('c-prof-display-name');
      const emailEl = document.getElementById('c-prof-email-display');
      const idEl = document.getElementById('c-prof-userid');
      const dateEl = document.getElementById('c-prof-created');
      const avatarEl = document.getElementById('c-prof-avatar');

      if (nameEl) nameEl.innerText = data.full_name;
      if (emailEl) emailEl.innerText = data.email;
      if (idEl) idEl.innerText = `#USER-${data.user_id}`;
      if (dateEl) dateEl.innerText = data.created_at ? new Date(data.created_at).toLocaleDateString() : 'Active';
      if (avatarEl && data.full_name) {
        avatarEl.innerText = data.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
      }

      // Form inputs
      document.getElementById('c-prof-fullname').value = data.full_name || '';
      document.getElementById('c-prof-phone').value = data.phone || '';
      document.getElementById('c-prof-dob').value = data.date_of_birth || '';
      document.getElementById('c-prof-lang').value = data.preferred_language || 'en';
      document.getElementById('c-prof-address').value = data.address || '';
      document.getElementById('c-prof-city').value = data.city || '';
      document.getElementById('c-prof-state').value = data.state || '';
      document.getElementById('c-prof-pincode').value = data.pincode || '';
      document.getElementById('c-prof-occupation').value = data.occupation || '';
      document.getElementById('c-prof-emergency').value = data.emergency_contact || '';
    } catch (err) {
      this.showToast('Could not load profile: ' + err.message, 'error');
    }
  },

  async submitCitizenProfile(e) {
    e.preventDefault();
    const payload = {
      full_name: document.getElementById('c-prof-fullname').value.trim(),
      phone: document.getElementById('c-prof-phone').value.trim() || null,
      date_of_birth: document.getElementById('c-prof-dob').value || null,
      preferred_language: document.getElementById('c-prof-lang').value || 'en',
      address: document.getElementById('c-prof-address').value.trim() || null,
      city: document.getElementById('c-prof-city').value.trim() || null,
      state: document.getElementById('c-prof-state').value.trim() || null,
      pincode: document.getElementById('c-prof-pincode').value.trim() || null,
      occupation: document.getElementById('c-prof-occupation').value.trim() || null,
      emergency_contact: document.getElementById('c-prof-emergency').value.trim() || null
    };

    try {
      const updated = await this.api('/api/citizen/profile', 'PUT', payload);
      this.showToast('Profile updated successfully!', 'success');
      this.user.full_name = updated.full_name;
      this.updateUserUI();
      this.loadCitizenProfile();
    } catch (err) {
      this.showToast('Update failed: ' + err.message, 'error');
    }
  },

  // 6. Notifications
  async loadNotifications() {
    if (!this.token) return;
    try {
      const data = await this.api('/api/citizen/notifications');
      this.citizenNotifications = data.notifications || [];
      this.unreadNotifCount = data.unread_count || 0;

      const badge = document.getElementById('notif-badge');
      if (badge) {
        if (this.unreadNotifCount > 0) {
          badge.innerText = this.unreadNotifCount;
          badge.style.display = 'inline-block';
        } else {
          badge.style.display = 'none';
        }
      }

      this.renderNotificationsList(this.citizenNotifications);
    } catch (err) {
      console.warn('Could not load notifications:', err);
    }
  },

  renderNotificationsList(notifs) {
    const container = document.getElementById('notifications-list-container');
    if (!container) return;

    if (!notifs || notifs.length === 0) {
      container.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;">No notifications.</div>';
      return;
    }

    container.innerHTML = notifs.map(n => `
      <div style="padding: 12px 16px; border-bottom: 1px solid var(--border-subtle); background: ${n.is_read ? 'transparent' : 'rgba(99, 102, 241, 0.08)'}; display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
        <div style="flex: 1;">
          <div style="font-size: 13.5px; font-weight: 600; color: ${n.is_read ? 'var(--text-secondary)' : '#F8FAFC'};">${this.escape(n.title)}</div>
          <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 3px; line-height: 1.4;">${this.escape(n.message)}</div>
          <div style="font-size: 11px; color: #64748B; margin-top: 4px;">${new Date(n.created_at).toLocaleDateString()}</div>
        </div>
        ${!n.is_read ? `
          <button class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 3px 6px;" onclick="App.markNotificationRead(${n.notification_id})">Mark Read</button>
        ` : ''}
      </div>
    `).join('');
  },

  toggleNotificationsPopover() {
    const popover = document.getElementById('notifications-popover');
    if (!popover) return;
    if (popover.style.display === 'none' || !popover.style.display) {
      popover.style.display = 'block';
      this.loadNotifications();
    } else {
      popover.style.display = 'none';
    }
  },

  async markNotificationRead(id) {
    try {
      await this.api(`/api/citizen/notifications/${id}/read`, 'PATCH');
      this.loadNotifications();
      if (this.currentView === 'citizen-notifications') {
        this.loadNotificationsView();
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async markAllNotificationsRead() {
    try {
      await this.api('/api/citizen/notifications/read-all', 'POST');
      this.showToast('All notifications marked as read.', 'info');
      this.loadNotifications();
      if (this.currentView === 'citizen-notifications') {
        this.loadNotificationsView();
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 7. CITIZEN SEARCH HISTORY VIEW
  // -------------------------------------------------------------
  citizenSearchHistory: [],

  async loadSearchHistory() {
    const container = document.getElementById('citizen-search-history-container');
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';

    try {
      const data = await this.api('/api/citizen/search-history?limit=50');
      this.citizenSearchHistory = Array.isArray(data) ? data : [];

      const sbCount = document.getElementById('sidebar-citizen-sh-count');
      if (sbCount) sbCount.innerText = this.citizenSearchHistory.length;

      this.renderSearchHistoryList(this.citizenSearchHistory);
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-title">Error Loading History</div><div class="empty-state-desc">${this.escape(err.message)}</div></div>`;
    }
  },

  renderSearchHistoryList(items) {
    const container = document.getElementById('citizen-search-history-container');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-title">No Search History Found</div>
          <div class="empty-state-desc">You haven't searched for any statutory provisions yet. Try queries like "anticipatory bail", "cheque bounce", or "consumer grievance".</div>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(s => `
      <div class="search-history-card">
        <div>
          <div style="font-size: 15px; font-weight: 600; color: #F8FAFC; display: flex; align-items: center; gap: 8px;">
            <span>🔍</span> "${this.escape(s.query_text)}"
            ${s.filters && s.filters.jurisdiction ? `<span class="badge badge-active">${this.escape(s.filters.jurisdiction)}</span>` : ''}
          </div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
            Matched <strong>${s.results_count || 0}</strong> statutory provisions • Searched on ${new Date(s.searched_at).toLocaleString()}
          </div>
        </div>
        <div>
          <button class="search-again-btn" onclick="App.reSearchFromHistory('${this.escape(s.query_text)}', '${this.escape(s.filters && s.filters.jurisdiction ? s.filters.jurisdiction : '')}')">
            🔄 Search Again
          </button>
        </div>
      </div>
    `).join('');
  },

  filterSearchHistory() {
    const term = (document.getElementById('citizen-sh-search')?.value || '').toLowerCase().trim();
    if (!term) {
      this.renderSearchHistoryList(this.citizenSearchHistory);
      return;
    }
    const filtered = this.citizenSearchHistory.filter(s =>
      s.query_text.toLowerCase().includes(term) ||
      (s.filters && JSON.stringify(s.filters).toLowerCase().includes(term))
    );
    this.renderSearchHistoryList(filtered);
  },

  reSearchFromHistory(queryText, jurisdiction) {
    this.navigate('research');
    const qInput = document.getElementById('research-query-input');
    const jSelect = document.getElementById('research-jurisdiction-select');
    if (qInput) qInput.value = queryText;
    if (jSelect && jurisdiction) jSelect.value = jurisdiction;
    this.handleLegalSearch();
  },

  async clearSearchHistory() {
    if (!confirm('Are you sure you want to clear your entire legal search history?')) return;
    try {
      await this.api('/api/citizen/search-history', 'DELETE');
      this.showToast('Search history cleared successfully.', 'success');
      this.citizenSearchHistory = [];
      const sbCount = document.getElementById('sidebar-citizen-sh-count');
      if (sbCount) sbCount.innerText = '0';
      this.renderSearchHistoryList([]);
    } catch (err) {
      this.showToast('Failed to clear search history: ' + err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // 8. CITIZEN NOTIFICATIONS FULL VIEW
  // -------------------------------------------------------------
  notifFilterType: 'all',

  async loadNotificationsView() {
    const container = document.getElementById('citizen-notifications-view-container');
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';

    try {
      const data = await this.api('/api/citizen/notifications');
      this.citizenNotifications = data.notifications || [];
      this.unreadNotifCount = data.unread_count || 0;

      const badge = document.getElementById('sidebar-citizen-notif-count');
      if (badge) badge.innerText = this.unreadNotifCount;
      const countAll = document.getElementById('notif-view-count-all');
      if (countAll) countAll.innerText = this.citizenNotifications.length;
      const countUnread = document.getElementById('notif-view-count-unread');
      if (countUnread) countUnread.innerText = this.unreadNotifCount;

      this.renderNotificationsFullList();
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-title">Error Loading Notifications</div><div class="empty-state-desc">${this.escape(err.message)}</div></div>`;
    }
  },

  filterNotificationsView(type) {
    this.notifFilterType = type;
    document.getElementById('btn-notif-tab-all')?.classList.toggle('active', type === 'all');
    document.getElementById('btn-notif-tab-unread')?.classList.toggle('active', type === 'unread');
    this.renderNotificationsFullList();
  },

  renderNotificationsFullList() {
    const container = document.getElementById('citizen-notifications-view-container');
    if (!container) return;

    let items = this.citizenNotifications;
    if (this.notifFilterType === 'unread') {
      items = items.filter(n => !n.is_read);
    }

    if (items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔔</div>
          <div class="empty-state-title">No ${this.notifFilterType === 'unread' ? 'Unread ' : ''}Notifications</div>
          <div class="empty-state-desc">You are all caught up on case alerts and court date reminders.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(n => `
      <div class="notif-full-card ${n.is_read ? '' : 'unread'}">
        <div style="flex: 1;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            ${n.is_read ? '' : '<span class="notif-dot"></span>'}
            <strong style="font-size: 14.5px; color: ${n.is_read ? 'var(--text-secondary)' : '#F8FAFC'};">${this.escape(n.title)}</strong>
            <span class="badge ${n.is_read ? 'badge-completed' : 'badge-active'}" style="font-size: 10px;">${n.is_read ? 'Read' : 'New'}</span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 6px 0;">${this.escape(n.message)}</p>
          <div style="font-size: 11px; color: var(--text-muted);">${new Date(n.created_at).toLocaleString()} • ${this.escape(n.notification_type || 'Case Alert')}</div>
        </div>
        ${!n.is_read ? `
          <button class="btn btn-secondary btn-sm" onclick="App.markSingleNotificationRead(${n.notification_id})">
            ✓ Mark Read
          </button>
        ` : ''}
      </div>
    `).join('');
  },

  async markSingleNotificationRead(notifId) {
    try {
      await this.api(`/api/citizen/notifications/${notifId}/read`, 'PATCH');
      this.showToast('Notification marked as read.', 'success');
      const notif = this.citizenNotifications.find(n => n.notification_id === notifId);
      if (notif) notif.is_read = true;
      if (this.unreadNotifCount > 0) this.unreadNotifCount--;

      const badge = document.getElementById('notif-badge');
      if (badge) {
        badge.innerText = this.unreadNotifCount;
        badge.style.display = this.unreadNotifCount > 0 ? 'inline-block' : 'none';
      }
      const sbBadge = document.getElementById('sidebar-citizen-notif-count');
      if (sbBadge) sbBadge.innerText = this.unreadNotifCount;
      const countUnread = document.getElementById('notif-view-count-unread');
      if (countUnread) countUnread.innerText = this.unreadNotifCount;

      this.renderNotificationsFullList();
    } catch (err) {
      this.showToast('Failed to mark read: ' + err.message, 'error');
    }
  },

  // -------------------------------------------------------------
  // eCOURTS OFFICIAL REFERENCE & LOOKUP (USER-ASSISTED)
  // -------------------------------------------------------------
  openOfficialECourtsLookup(cnrOverride) {
    const cnr = cnrOverride || this.currentCaseCNR || this.currentCitizenCaseCNR;
    if (cnr) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cnr).catch(e => console.warn('Clipboard write failed:', e));
      }
      this.showToast(`CNR ${cnr} copied to clipboard! Solve CAPTCHA on official portal.`, 'info');
    } else {
      this.showToast('Opening official eCourts portal in new tab...', 'info');
    }
    window.open('https://services.ecourts.gov.in/ecourtindia_v6/', '_blank');
  },

  openUpdateCourtReferenceModal(isCitizen = false) {
    this.updatingCourtReferenceIsCitizen = isCitizen;
    const form = document.getElementById('form-update-court-reference');
    if (form) form.reset();

    const ref = isCitizen ? (this.currentCitizenCaseCourtReference || {}) : (this.currentCaseCourtReference || {});
    const cnrInput = document.getElementById('m-ref-cnr');
    const statusInput = document.getElementById('m-ref-status');
    const hearingDateInput = document.getElementById('m-ref-hearing-date');

    if (cnrInput) cnrInput.value = ref.cnr_number || (isCitizen ? (this.currentCitizenCaseCNR || '') : (this.currentCaseCNR || ''));
    if (statusInput) statusInput.value = ref.external_status || '';
    if (hearingDateInput) hearingDateInput.value = ref.external_next_hearing_date || '';

    document.getElementById('modal-update-court-reference')?.classList.add('active');
  },

  async submitUpdateCourtReference(e) {
    e.preventDefault();
    const cnr = (document.getElementById('m-ref-cnr')?.value || '').trim().toUpperCase();
    const externalStatus = (document.getElementById('m-ref-status')?.value || '').trim() || null;
    const nextHearingDate = document.getElementById('m-ref-hearing-date')?.value || null;

    if (!cnr) {
      this.showToast('Please provide a valid 16-character CNR number.', 'error');
      return;
    }

    const payload = {
      cnr_number: cnr,
      external_status: externalStatus,
      external_next_hearing_date: nextHearingDate
    };

    try {
      if (this.updatingCourtReferenceIsCitizen) {
        await this.api(`/api/citizen/cases/${this.currentCaseId}/court-reference`, 'PATCH', payload);
        this.showToast('Official court reference recorded successfully!', 'success');
        this.closeModals();
        this.loadCitizenCaseDetail(this.currentCaseId);
      } else {
        await this.api(`/api/lawyer/cases/${this.currentCaseId}/court-reference`, 'PATCH', payload);
        this.showToast('Official court reference recorded successfully!', 'success');
        this.closeModals();
        this.openCaseDetail(this.currentCaseId);
      }
    } catch (err) {
      this.showToast('Update failed: ' + err.message, 'error');
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
