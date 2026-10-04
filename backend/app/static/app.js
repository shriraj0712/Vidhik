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
  currentTheme: 'dark',
  researchFilter: 'all',
  selectedBareAct: '',
  bareActsList: [],

  // -------------------------------------------------------------
  // INITIALIZATION
  // -------------------------------------------------------------
  async init() {
    this.initTheme();
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

  // -------------------------------------------------------------
  // THEME MANAGEMENT (PERSISTED IN LOCALSTORAGE)
  // Supported themes: 'light', 'dark', 'ocean', 'emerald', 'rose', 'purple', 'amber'
  // -------------------------------------------------------------
  VALID_THEMES: ['light', 'dark', 'ocean', 'emerald', 'rose', 'purple', 'amber'],
  DEFAULT_THEME: 'light',

  initTheme() {
    try {
      const saved = localStorage.getItem('vidhik_theme') || localStorage.getItem('vidhik-theme') || this.DEFAULT_THEME;
      const themeToApply = this.VALID_THEMES.includes(saved) ? saved : this.DEFAULT_THEME;
      this.setTheme(themeToApply, false);
    } catch (e) {
      this.setTheme(this.DEFAULT_THEME, false);
    }
  },

  setTheme(themeName, notify = false) {
    if (!this.VALID_THEMES.includes(themeName)) {
      themeName = this.DEFAULT_THEME;
    }
    this.currentTheme = themeName;
    document.documentElement.setAttribute('data-theme', themeName);

    try {
      localStorage.setItem('vidhik_theme', themeName);
      localStorage.setItem('vidhik-theme', themeName);
    } catch (e) {
      console.warn('Could not persist theme preference', e);
    }

    const themeDisplayNames = {
      light: 'Legal White',
      dark: 'Midnight Legal',
      ocean: 'Ocean Intelligence',
      emerald: 'Judicial Emerald',
      rose: 'Executive Rose',
      purple: 'Royal Purple',
      amber: 'Executive Gold'
    };
    const displayName = themeDisplayNames[themeName] || themeName;

    const btn = document.getElementById('btn-theme-toggle');
    if (btn) {
      btn.setAttribute('title', `Active Theme: ${displayName} (Click to change)`);
      btn.setAttribute('aria-label', `Select Color Theme. Current: ${displayName}`);
    }

    // Update active class and radio state on palette buttons
    document.querySelectorAll('.theme-option-btn').forEach(opt => {
      const val = opt.getAttribute('data-theme-value');
      const isSelected = (val === themeName);
      opt.classList.toggle('active', isSelected);
      opt.setAttribute('aria-checked', String(isSelected));
    });

    if (notify) {
      this.showToast(`Theme: ${displayName} Mode`, 'info');
      this.closeThemePicker();
    }
  },

  toggleThemePicker() {
    const popover = document.getElementById('theme-popover');
    const btn = document.getElementById('btn-theme-toggle');
    if (!popover) return;

    const isOpen = popover.classList.contains('active');
    if (isOpen) {
      this.closeThemePicker();
    } else {
      // Close notifications popover if open
      this.closeNotificationsPopover();
      popover.style.display = 'flex';
      popover.classList.add('active');
      btn?.setAttribute('aria-expanded', 'true');

      // Boundary check to ensure popover stays within viewport on mobile
      requestAnimationFrame(() => {
        const rect = popover.getBoundingClientRect();
        if (rect.left < 8) {
          popover.style.right = 'auto';
          popover.style.left = '0';
        } else if (rect.right > window.innerWidth - 8) {
          popover.style.left = 'auto';
          popover.style.right = '0';
        }
      });
    }
  },

  closeThemePicker() {
    const popover = document.getElementById('theme-popover');
    const btn = document.getElementById('btn-theme-toggle');
    if (popover) {
      popover.classList.remove('active');
      popover.style.display = 'none';
      popover.style.left = '';
      popover.style.right = '';
    }
    if (btn) {
      btn.setAttribute('aria-expanded', 'false');
    }
  },

  toggleTheme() {
    this.toggleThemePicker();
  },

  bindEvents() {
    // Navigation clicks
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const view = item.getAttribute('data-view');
        if (view) {
          this.navigate(view);
          if (window.innerWidth <= 768) {
            this.closeMobileSidebar();
          }
        }
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

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeThemePicker();
        this.closeMobileSidebar();
        this.closeNotificationsPopover();
        this.closeModals();
      }
    });

    // Close popovers when clicking outside
    document.addEventListener('click', (e) => {
      const themePicker = document.getElementById('theme-picker-container');
      if (themePicker && !themePicker.contains(e.target)) {
        this.closeThemePicker();
      }
      const notifContainer = document.querySelector('.notif-bell-container');
      if (notifContainer && !notifContainer.contains(e.target)) {
        this.closeNotificationsPopover();
      }
    });

    // Close modal on backdrop click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay && overlay.id !== 'login-screen') {
          this.closeModals();
        }
      });
    });

    // Keep body.modal-open synchronized whenever any modal opens or closes
    try {
      const modalObserver = new MutationObserver(() => {
        const hasActiveModal = Array.from(document.querySelectorAll('.modal-overlay.active')).some(m => m.id !== 'login-screen');
        if (hasActiveModal) {
          document.body.classList.add('modal-open');
        } else {
          document.body.classList.remove('modal-open');
        }
      });
      document.querySelectorAll('.modal-overlay').forEach(m => {
        if (m.id !== 'login-screen') {
          modalObserver.observe(m, { attributes: true, attributeFilter: ['class'] });
        }
      });
    } catch (e) {}

    // Auto-close drawer ONLY when resizing from mobile width to desktop width (> 768px)
    let prevWidth = window.innerWidth;
    window.addEventListener('resize', () => {
      const currentWidth = window.innerWidth;
      if (currentWidth > 768 && prevWidth <= 768) {
        this.closeMobileSidebar();
      }
      prevWidth = currentWidth;

      // Ensure open notification popover adapts its position dynamically
      if (document.getElementById('notifications-popover')?.classList.contains('active')) {
        this.positionNotificationsPopover();
      }
    });

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
        e.preventDefault();
        this.toggleNotificationsPopover();
      });
    }
    document.getElementById('btn-mark-all-read')?.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();
      this.markAllNotificationsRead();
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
    const sidebar = document.getElementById('app-sidebar');
    const button = document.getElementById('btn-mobile-menu-toggle');
    const backdrop = document.querySelector('.mobile-backdrop');

    if (!sidebar) return;

    const isOpen = sidebar.classList.toggle('open');

    if (isOpen) {
      this.closeThemePicker();
      this.closeNotificationsPopover();
    }

    if (button) {
      button.setAttribute('aria-expanded', String(isOpen));
      button.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
      button.setAttribute('title', isOpen ? 'Close Navigation' : 'Open Navigation');
    }

    if (backdrop) {
      backdrop.classList.toggle('visible', isOpen);
      backdrop.classList.toggle('active', isOpen);
    }

    document.body.classList.toggle('sidebar-open', isOpen);
  },

  closeMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const button = document.getElementById('btn-mobile-menu-toggle');
    const backdrop = document.querySelector('.mobile-backdrop');

    if (sidebar) {
      sidebar.classList.remove('open');
    }

    if (button) {
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-label', 'Open navigation');
      button.setAttribute('title', 'Open Navigation');
    }

    if (backdrop) {
      backdrop.classList.remove('visible');
      backdrop.classList.remove('active');
    }

    document.body.classList.remove('sidebar-open');
  },

  openMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const button = document.getElementById('btn-mobile-menu-toggle');
    const backdrop = document.querySelector('.mobile-backdrop');

    if (!sidebar) return;

    sidebar.classList.add('open');

    if (button) {
      button.setAttribute('aria-expanded', 'true');
      button.setAttribute('aria-label', 'Close navigation');
      button.setAttribute('title', 'Close Navigation');
    }

    if (backdrop) {
      backdrop.classList.add('visible');
      backdrop.classList.add('active');
    }

    document.body.classList.add('sidebar-open');
  },

  handleCitizenQuickSearch(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('citizen-quick-search-input');
    const q = input ? input.value.trim() : '';
    this.navigate('research');
    const rInput = document.getElementById('research-query-input');
    if (rInput) {
      if (q) {
        rInput.value = q;
        this.handleLegalSearch();
      } else {
        rInput.focus();
      }
    }
  },

  handleLawyerQuickSearch(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('lawyer-quick-search-input');
    const q = input ? input.value.trim() : '';
    this.navigate('research');
    const rInput = document.getElementById('research-query-input');
    if (rInput) {
      if (q) {
        rInput.value = q;
        this.handleLegalSearch();
      } else {
        rInput.focus();
      }
    }
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
    this.closeNotificationsPopover();
    if (this.user && (this.user.role === 'user' || this.user.role === 'citizen')) {
      this.navigate('citizen-notifications');
    } else {
      this.navigate('hearings');
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
    if (pwdInput) {
      if (password === 'citizen' || password === 'lawyer' || !password) {
        pwdInput.value = 'password123';
      } else {
        pwdInput.value = password;
      }
    }
  },

  async logout() {
    return this.handleLogout();
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
    this.citizenNotifications = [];
    this.unreadNotifCount = 0;
    this.closeNotificationsPopover();
    this.updateNotificationBadge(0);
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
    const roleEl = document.getElementById('sidebar-lawyer-role') || document.getElementById('sidebar-lawyer-bar');

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

    // Canonical alias normalization for VIDHIK / Legal AI
    if (['legal-ai', 'ask-vidhik', 'vidhik', 'ai', 'legal-research'].includes(viewName)) {
      viewName = 'research';
    }

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

    // Update Mobile Bottom Nav Active Class
    document.querySelectorAll('.mobile-bottom-nav .bottom-nav-item').forEach(item => {
      const targetViews = (item.getAttribute('data-views') || '').split(',');
      if (targetViews.includes(viewName)) {
        item.classList.add('active');
        item.setAttribute('aria-current', 'page');
      } else {
        item.classList.remove('active');
        item.removeAttribute('aria-current');
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

  handleBottomNav(dest) {
    const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');
    switch (dest) {
      case 'home':
        this.navigate(isCitizen ? 'citizen-dashboard' : 'dashboard');
        break;
      case 'cases':
        this.navigate(isCitizen ? 'citizen-cases' : 'cases');
        break;
      case 'ai':
      case 'ask-vidhik':
      case 'legal-ai':
      case 'vidhik':
        this.navigate('research');
        break;
      case 'docs':
        this.navigate(isCitizen ? 'citizen-documents' : 'documents');
        break;
    }
  },

  handleAskVidhikChip(topic) {
    if (topic === 'My Cases') {
      const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');
      this.navigate(isCitizen ? 'citizen-cases' : 'cases');
      return;
    }
    this.navigate('research');
    if (topic === '24 Bare Acts') {
      this.applyResearchFilter('24acts');
      return;
    }
    if (['BNS', 'BNSS', 'BSA'].includes(topic)) {
      this.applyResearchFilter(topic);
      return;
    }
    if (topic === 'Legal Rights') {
      const input = document.getElementById('research-query-input');
      if (input) {
        input.value = 'Fundamental Rights';
        this.handleLegalSearch();
      }
      return;
    }
    if (topic) {
      const input = document.getElementById('research-query-input');
      if (input) {
        input.value = topic;
        this.handleLegalSearch();
      }
    }
  },

  scrollToHearings() {
    const el = document.getElementById('citizen-dash-hearings-list');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  },
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
          <div class="hearing-card-item">
            <div class="hearing-card-body">
              <div class="hearing-card-title">${this.escape(h.title)}</div>
              <div class="hearing-card-meta">
                ⚖️ ${this.escape(h.case_title)} (${this.escape(h.case_number || 'Brief')}) • 🏛️ ${this.escape(h.court_name || 'Designated Court')}
              </div>
            </div>
            <div class="hearing-card-action">
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
          <div class="matter-card" onclick="App.openCaseDetail(${c.case_id})">
            <div class="matter-card-body">
              <div class="matter-title">${this.escape(c.case_title)}</div>
              <div class="matter-meta">
                <span>👤 ${this.escape(c.client_name || 'Client')}</span>
                <span>•</span>
                <code class="matter-code">${this.escape(c.case_number || 'Brief')}</code>
                ${c.court ? `<span>• <span class="matter-court">🏛️ ${this.escape(c.court)}</span></span>` : ''}
              </div>
            </div>
            <div class="matter-card-action">
              <span class="badge badge-${c.status}">${c.status}</span>
              <div class="matter-action-btn">Open Brief →</div>
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
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(99, 102, 241, 0.15); color: var(--accent-primary); display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;">
              ⚡
            </div>
            <div style="flex: 1; min-width: 0;">
              <div style="font-size: 13.5px; font-weight: 600; color: var(--text-primary); overflow-wrap: anywhere; word-break: break-word;">${this.escape(a.update_title)}</div>
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px; overflow-wrap: anywhere; word-break: break-word;">${this.escape(a.update_description)}</div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; overflow-wrap: anywhere; word-break: break-word;">
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
          <div class="doc-row-item">
            <div class="doc-row-body">
              <div class="doc-row-name">📄 ${this.escape(d.document_name)}</div>
              <div class="doc-row-meta">
                <span>${this.escape(d.case_title)}</span>
                <span class="badge badge-completed">${d.document_type}</span>
              </div>
            </div>
            <div class="doc-row-action">
              <span class="doc-row-size">${(d.file_size_bytes / 1024 / 1024).toFixed(1)} MB</span>
            </div>
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

  async openEditCaseModal() {
    if (!this.currentCaseId) {
      this.showToast('Please select a case first.', 'error');
      return;
    }
    await this.openCreateCaseModal();
    const titleEl = document.getElementById('modal-create-case')?.querySelector('.modal-title');
    if (titleEl) titleEl.innerText = 'Edit Case Details';
    const cdTitle = document.getElementById('cd-title')?.innerText;
    const cdNumber = document.getElementById('cd-number')?.innerText;
    const cdCourt = document.getElementById('cd-court')?.innerText;
    const cdOpposite = document.getElementById('cd-opposite')?.innerText;
    if (cdTitle && cdTitle !== '-') document.getElementById('m-case-title').value = cdTitle;
    if (cdNumber && cdNumber !== '-') document.getElementById('m-case-number').value = cdNumber;
    if (cdCourt && cdCourt !== '-') document.getElementById('m-case-court').value = cdCourt;
    if (cdOpposite && cdOpposite !== '-') document.getElementById('m-case-opposite').value = cdOpposite;
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
              <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${this.escape(h.title)}</div>
              <div style="font-size: 13px; color: var(--accent-cyan); margin-top: 3px;">🏛️ ${this.escape(h.court_name || data.court_name)} • Bench: ${this.escape(h.judge_name || 'Designated Bench')}</div>
              <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 4px;">${this.escape(h.notes || '')}</div>
            </div>
            <div style="text-align: right;">
              <span class="badge badge-${h.status}">${h.status}</span>
              <div style="font-size: 14px; font-weight: 600; color: var(--accent-primary); margin-top: 4px;">${h.reminder_date}</div>
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
                <h4 style="font-size: 16px; color: var(--text-primary);">${this.escape(s.section_title || 'Section')}</h4>
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
          <td><a href="javascript:void(0)" onclick="App.openCaseDetail(${d.case_id})" style="color: var(--accent-primary); text-decoration: none;">${this.escape(d.case_title)}</a></td>
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
            <h3 style="font-size: 17px; color: var(--text-primary);">${this.escape(h.title)}</h3>
            <div style="font-size: 13.5px; color: var(--accent-cyan); margin-top: 4px;">
              ⚖️ Case: <a href="javascript:void(0)" onclick="App.openCaseDetail(${h.case_id})" style="color: var(--accent-primary); text-decoration: none;">${this.escape(h.case_title)}</a> (${this.escape(h.case_number || 'Brief')})
            </div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
              🏛️ ${this.escape(h.court_name || 'Court Room')} • Presiding: ${this.escape(h.judge_name || 'Designated Judge')}
            </div>
            ${h.notes ? `<div style="font-size: 12.5px; color: var(--text-muted); margin-top: 8px; background: var(--bg-primary); padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">📝 Notes: ${this.escape(h.notes)}</div>` : ''}
          </div>
          <div style="text-align: right;">
            <div style="font-size: 18px; font-weight: 700; color: var(--accent-primary); font-family: 'Outfit';">${h.reminder_date}</div>
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
  // 8. LEGAL RESEARCH & STATUTORY INTELLIGENCE ENGINE (PHASE 17)
  // -------------------------------------------------------------
  applyResearchFilter(filterKey) {
    this.researchFilter = filterKey;
    document.querySelectorAll('.filter-pill[id^="pill-filter-"]').forEach(p => p.classList.remove('active'));
    const activePill = document.getElementById(`pill-filter-${filterKey.toLowerCase()}`);
    if (activePill) activePill.classList.add('active');

    const actSelect = document.getElementById('research-act-select');
    if (actSelect) {
      if (['BNS', 'BNSS', 'BSA'].includes(filterKey)) {
        actSelect.value = filterKey;
        this.selectedBareAct = filterKey;
      } else if (filterKey === 'all') {
        actSelect.value = '';
        this.selectedBareAct = '';
      }
    }

    const input = document.getElementById('research-query-input');
    if (input && input.value.trim()) {
      this.handleLegalSearch();
    }
  },

  handleActFilterChange(actValue) {
    this.selectedBareAct = actValue;
    if (['BNS', 'BNSS', 'BSA'].includes(actValue)) {
      this.applyResearchFilter(actValue);
    } else if (actValue) {
      this.researchFilter = '24acts';
      document.querySelectorAll('.filter-pill[id^="pill-filter-"]').forEach(p => p.classList.remove('active'));
      document.getElementById('pill-filter-24acts')?.classList.add('active');
    } else {
      this.applyResearchFilter('all');
    }
    const input = document.getElementById('research-query-input');
    if (input && input.value.trim()) {
      this.handleLegalSearch();
    }
  },

  getStatuteBadge(lawName) {
    const ln = (lawName || '').toLowerCase();
    if (ln.includes('nyaya sanhita') || ln.includes('bns')) {
      return '<span class="badge badge-bns" style="margin-left: 6px;">BNS 2023</span>';
    }
    if (ln.includes('nagarik suraksha') || ln.includes('bnss')) {
      return '<span class="badge badge-bnss" style="margin-left: 6px;">BNSS 2023</span>';
    }
    if (ln.includes('sakshya') || ln.includes('bsa')) {
      return '<span class="badge badge-bsa" style="margin-left: 6px;">BSA 2023</span>';
    }
    if (ln.includes('penal code') || ln.includes('criminal procedure') || ln.includes('evidence act')) {
      return '<span class="badge badge-predecessor" style="margin-left: 6px;">Predecessor</span>';
    }
    return '';
  },

  async handleLegalSearch() {
    const q = document.getElementById('research-query-input').value.trim();
    const jurisdiction = document.getElementById('research-jurisdiction-select')?.value || '';
    const container = document.getElementById('research-results-container');

    if (!q) {
      this.showToast('Please enter a legal search query.', 'error');
      return;
    }

    container.innerHTML = `<div class="spinner"></div>`;

    // 1. AUTHORITIES RECOMMENDATION MODE
    if (this.researchFilter === 'authorities') {
      try {
        const authData = await this.api(`/api/authorities/recommend?q=${encodeURIComponent(q)}&limit=15`);
        if (!authData.recommendations || authData.recommendations.length === 0) {
          container.innerHTML = `
            <div class="empty-state">
              <div class="empty-state-title">No verified judicial authorities found</div>
              <div class="empty-state-desc">No controlling judicial precedents matched "${this.escape(q)}". Try broader search terms.</div>
            </div>
          `;
          return;
        }

        container.innerHTML = `
          <div style="margin-bottom: 16px; font-size: 13.5px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <span>Found <strong>${authData.total || authData.recommendations.length}</strong> verified judicial authorities (${authData.source_status || 'verified'}).</span>
            <span class="badge badge-active" style="font-size: 11px;">Zero Hallucination Guaranteed</span>
          </div>
          ${authData.recommendations.map(a => `
            <div class="card" style="margin-bottom: 16px; border: 1px solid var(--border-subtle); border-left: 4px solid var(--accent-amber);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; flex-wrap: wrap; gap: 10px;">
                <div>
                  <span class="badge badge-predecessor" style="margin-bottom: 6px;">${this.escape(a.citation || 'Landmark Decision')}</span>
                  <h3 style="font-size: 16.5px; color: var(--text-primary); margin: 2px 0 4px;">${this.escape(a.case_name)}</h3>
                  <div style="font-size: 12.5px; color: var(--accent-cyan); font-weight: 500;">🏛️ ${this.escape(a.court)}${a.judgment_date ? ` • ${a.judgment_date}` : ''}</div>
                </div>
                <div style="text-align: right;">
                  <span class="badge badge-active">Relevance: ${Math.round((a.relevance_score || 0) * 100)}%</span>
                  <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${this.escape(a.match_type || 'controlling')}</div>
                </div>
              </div>

              <div style="font-size: 13.5px; line-height: 1.6; color: var(--text-secondary); background: var(--bg-primary); padding: 12px 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin: 12px 0;">
                <strong>Legal Proposition:</strong> ${this.escape(a.legal_proposition || a.reason || 'Authoritative judicial holding.')}
              </div>

              ${a.matched_sections && a.matched_sections.length > 0 ? `
                <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 8px;">
                  <span style="font-size: 11.5px; color: var(--text-muted);">Associated Sections:</span>
                  ${a.matched_sections.map(s => `<span class="badge badge-completed" style="font-size: 11px;">${this.escape(s)}</span>`).join('')}
                </div>
              ` : ''}
            </div>
          `).join('')}
        `;
        return;
      } catch (err) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-title">Authority Search Error</div><div class="empty-state-desc">${this.escape(err.message)}</div></div>`;
        return;
      }
    }

    // 2. STATUTORY CORPUS SEARCH MODE
    try {
      let searchQuery = q;
      if (this.selectedBareAct && !['all', '24acts'].includes(this.selectedBareAct)) {
        searchQuery = `${q} ${this.selectedBareAct}`;
      }

      const query = new URLSearchParams({ q: searchQuery, limit: 18 });
      if (jurisdiction) query.append('jurisdiction', jurisdiction);

      // Call legal search endpoint
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
            <div class="empty-state-desc">No provisions matched "${this.escape(q)}". Try broader legal search terms or clear filters.</div>
          </div>
        `;
        return;
      }

      const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');

      container.innerHTML = `
        <div style="margin-bottom: 16px; font-size: 13.5px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <span>Found <strong>${data.total}</strong> provisions in legal corpus. Displaying top ranked matches:</span>
          ${this.selectedBareAct ? `<span class="badge badge-bns">Filter: ${this.escape(this.selectedBareAct)}</span>` : ''}
        </div>
        ${data.results.map(r => `
          <div class="card" style="margin-bottom: 16px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
              <div>
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 6px;">
                  <span class="badge badge-active">Section ${this.escape(r.section_number)}</span>
                  ${this.getStatuteBadge(r.law_name)}
                </div>
                <h3 style="font-size: 17px; color: var(--text-primary); margin: 2px 0 4px;">${this.escape(r.section_title || 'Section Provision')}</h3>
                <div style="font-size: 13px; color: var(--accent-cyan); font-weight: 500;">📖 ${this.escape(r.law_name)}</div>
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
              <button class="btn btn-secondary btn-sm" onclick="App.inspectSectionContextGraph('${this.escape(r.section_number)}', '${this.escape(r.law_name)}')">
                ⚡ Context Graph
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

      // Reset context container
      const contextContainer = document.getElementById('m-prov-context-container');
      const contextContent = document.getElementById('m-prov-context-content');
      const contextBtn = document.getElementById('m-prov-btn-context');
      if (contextContainer) contextContainer.style.display = 'none';
      if (contextContent) contextContent.innerHTML = '';
      if (contextBtn) {
        contextBtn.style.display = 'inline-flex';
        contextBtn.innerText = '⚡ Inspect Context Graph';
        contextBtn.onclick = () => this.toggleProvisionContext(sec.section_number, sec.law_name);
      }

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

  async toggleProvisionContext(sectionNumber, lawName) {
    const container = document.getElementById('m-prov-context-container');
    const content = document.getElementById('m-prov-context-content');
    const btn = document.getElementById('m-prov-btn-context');
    if (!container || !content) return;

    if (container.style.display === 'block') {
      container.style.display = 'none';
      if (btn) btn.innerText = '⚡ Inspect Context Graph';
      return;
    }

    container.style.display = 'block';
    content.innerHTML = '<div class="spinner" style="margin: 20px auto;"></div>';
    if (btn) btn.innerText = '✕ Hide Context Graph';

    let lawCode = 'BNS';
    const ln = (lawName || '').toLowerCase();
    if (ln.includes('nagarik') || ln.includes('bnss')) lawCode = 'BNSS';
    else if (ln.includes('sakshya') || ln.includes('bsa')) lawCode = 'BSA';

    try {
      const graph = await this.api(`/api/knowledge/sections/${encodeURIComponent(sectionNumber)}/context?law=${encodeURIComponent(lawCode)}`);
      
      let html = '';
      
      // Predecessor mapping
      if (graph.predecessors && graph.predecessors.length > 0) {
        html += `
          <div style="margin-bottom: 14px; padding: 12px; background: rgba(245, 158, 11, 0.08); border-radius: var(--radius-sm); border: 1px solid rgba(245, 158, 11, 0.25);">
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-amber); text-transform: uppercase; margin-bottom: 6px;">Predecessor Correlation:</div>
            ${graph.predecessors.map(p => `
              <div style="font-size: 13px; color: var(--text-primary);">
                Replaces <strong>${this.escape(p.old_law_name)} Section ${this.escape(p.old_section_number)}</strong>: ${this.escape(p.summary || '')}
              </div>
            `).join('')}
          </div>
        `;
      }

      // Offence & Punishments
      if (graph.offence) {
        html += `
          <div style="margin-bottom: 14px; padding: 12px; background: var(--bg-primary); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase; margin-bottom: 6px;">Offence Classification:</div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
              <span class="badge ${graph.offence.cognizable_status === 'Cognizable' ? 'badge-high' : 'badge-completed'}">${this.escape(graph.offence.cognizable_status || 'Cognizable')}</span>
              <span class="badge ${graph.offence.bailable_status === 'Bailable' ? 'badge-active' : 'badge-pending'}">${this.escape(graph.offence.bailable_status || 'Non-Bailable')}</span>
              <span class="badge badge-completed">Triable: ${this.escape(graph.offence.triable_by || 'Court of Session')}</span>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary);">${this.escape(graph.offence.description || graph.offence.offence_name || '')}</div>
          </div>
        `;
      }

      // Punishments
      if (graph.punishments && graph.punishments.length > 0) {
        html += `
          <div style="margin-bottom: 14px;">
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-rose); text-transform: uppercase; margin-bottom: 6px;">Statutory Punishments:</div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              ${graph.punishments.map(pu => `
                <div style="font-size: 12.5px; color: var(--text-secondary); background: var(--bg-primary); padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                  ⚖️ ${this.escape(pu.punishment_type || '')}: ${this.escape(pu.description || '')}
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      // Controlling Judgments
      if (graph.controlling_judgments && graph.controlling_judgments.length > 0) {
        html += `
          <div>
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-emerald); text-transform: uppercase; margin-bottom: 6px;">Controlling Judicial Authorities:</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${graph.controlling_judgments.map(j => `
                <div style="font-size: 12.5px; background: var(--bg-primary); padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                  <strong style="color: var(--text-primary);">${this.escape(j.case_title)}</strong> (${this.escape(j.citation || '')})
                  <div style="color: var(--text-muted); font-size: 11.5px; margin-top: 2px;">${this.escape(j.headnotes || j.ratio_decidendi || '')}</div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (!html) {
        html = '<div style="color: var(--text-muted); font-size: 12.5px; font-style: italic;">No specific Phase 17 correlation entries for this provision. General statutory text applies.</div>';
      }

      content.innerHTML = html;
    } catch (err) {
      content.innerHTML = `<div style="color: var(--accent-rose); font-size: 12.5px;">Could not retrieve context graph: ${this.escape(err.message)}</div>`;
    }
  },

  async inspectSectionContextGraph(sectionNumber, lawName) {
    try {
      // Find section details
      document.getElementById('m-prov-title').innerText = `Section ${sectionNumber} Intelligence Graph`;
      document.getElementById('m-prov-law-name').innerText = lawName || 'Indian Statute';
      document.getElementById('m-prov-sec-no').innerText = sectionNumber;
      document.getElementById('m-prov-chapter').innerText = 'Phase 17 Knowledge';
      document.getElementById('m-prov-pages').innerText = 'Authoritative';
      document.getElementById('m-prov-fulltext').innerText = `Loading full context and controlling interpretations for Section ${sectionNumber}...`;

      document.getElementById('modal-provision-detail').classList.add('active');

      const contextBtn = document.getElementById('m-prov-btn-context');
      if (contextBtn) contextBtn.style.display = 'none';

      const contextContainer = document.getElementById('m-prov-context-container');
      const contextContent = document.getElementById('m-prov-context-content');
      if (contextContainer && contextContent) {
        contextContainer.style.display = 'block';
        contextContent.innerHTML = '<div class="spinner" style="margin: 20px auto;"></div>';
      }

      let lawCode = 'BNS';
      const ln = (lawName || '').toLowerCase();
      if (ln.includes('nagarik') || ln.includes('bnss')) lawCode = 'BNSS';
      else if (ln.includes('sakshya') || ln.includes('bsa')) lawCode = 'BSA';

      const graph = await this.api(`/api/knowledge/sections/${encodeURIComponent(sectionNumber)}/context?law=${encodeURIComponent(lawCode)}`);
      
      document.getElementById('m-prov-fulltext').innerText = graph.full_text || graph.section_title || 'Statutory enactment active under Gazette of India notification.';

      let html = '';
      if (graph.predecessors && graph.predecessors.length > 0) {
        html += `
          <div style="margin-bottom: 14px; padding: 12px; background: rgba(245, 158, 11, 0.08); border-radius: var(--radius-sm); border: 1px solid rgba(245, 158, 11, 0.25);">
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-amber); text-transform: uppercase; margin-bottom: 6px;">Predecessor Correlation:</div>
            ${graph.predecessors.map(p => `
              <div style="font-size: 13px; color: var(--text-primary);">
                Replaces <strong>${this.escape(p.old_law_name)} Section ${this.escape(p.old_section_number)}</strong>: ${this.escape(p.summary || '')}
              </div>
            `).join('')}
          </div>
        `;
      }

      if (graph.offence) {
        html += `
          <div style="margin-bottom: 14px; padding: 12px; background: var(--bg-primary); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase; margin-bottom: 6px;">Offence Classification:</div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
              <span class="badge ${graph.offence.cognizable_status === 'Cognizable' ? 'badge-high' : 'badge-completed'}">${this.escape(graph.offence.cognizable_status || 'Cognizable')}</span>
              <span class="badge ${graph.offence.bailable_status === 'Bailable' ? 'badge-active' : 'badge-pending'}">${this.escape(graph.offence.bailable_status || 'Non-Bailable')}</span>
              <span class="badge badge-completed">Triable: ${this.escape(graph.offence.triable_by || 'Court of Session')}</span>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary);">${this.escape(graph.offence.description || graph.offence.offence_name || '')}</div>
          </div>
        `;
      }

      if (graph.controlling_judgments && graph.controlling_judgments.length > 0) {
        html += `
          <div>
            <div style="font-size: 12px; font-weight: 700; color: var(--accent-emerald); text-transform: uppercase; margin-bottom: 6px;">Controlling Judicial Authorities:</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${graph.controlling_judgments.map(j => `
                <div style="font-size: 12.5px; background: var(--bg-primary); padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                  <strong style="color: var(--text-primary);">${this.escape(j.case_title)}</strong> (${this.escape(j.citation || '')})
                  <div style="color: var(--text-muted); font-size: 11.5px; margin-top: 2px;">${this.escape(j.headnotes || j.ratio_decidendi || '')}</div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (contextContent) {
        contextContent.innerHTML = html || '<div style="color: var(--text-muted); font-size: 12.5px; font-style: italic;">No specific predecessor mapping registered. Primary statute text is authoritative.</div>';
      }
    } catch (err) {
      this.showToast('Could not load context graph: ' + err.message, 'error');
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
        <span style="font-size: 13px; color: var(--text-secondary); margin-right: 4px; font-weight: 500;">Filter Category:</span>
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
            ${proc.estimated_processing_days ? `<span style="font-size: 11.5px; color: var(--text-secondary);">⏱️ ~${proc.estimated_processing_days} Days</span>` : ''}
          </div>
          <h4 class="procedure-card-title">${this.escape(proc.procedure_name)}</h4>
          <p class="procedure-card-desc">${this.escape(proc.description)}</p>
        </div>

        <div class="procedure-card-meta">
          <div style="color: var(--text-secondary);">
            🏛️ <strong>Authority:</strong> ${this.escape(proc.authority_type)}
          </div>
          <div style="color: var(--text-secondary);">
            📍 <strong>Jurisdiction:</strong> ${this.escape(proc.jurisdiction)}
          </div>
          ${proc.governing_law_name ? `
            <div style="color: var(--accent-primary); font-size: 11.5px;">
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
        mandContainer.innerHTML = '<div style="font-size: 13px; color: var(--text-secondary); font-style: italic;">No mandatory documents specified.</div>';
      }

      const supContainer = document.getElementById('chk-supporting-docs-list');
      if (data.supporting_documents && data.supporting_documents.length > 0) {
        supContainer.innerHTML = data.supporting_documents.map(d => this.renderChecklistItem(data.procedure_id, d, false)).join('');
      } else {
        supContainer.innerHTML = '<div style="font-size: 13px; color: var(--text-secondary); font-style: italic;">No optional or supporting documents.</div>';
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
              <label for="chk-doc-${doc.doc_req_id}" style="font-size: 14.5px; font-weight: 600; color: var(--text-primary); cursor: pointer;">
                ${this.escape(doc.document_name)}
              </label>
              <div style="display: flex; gap: 6px; align-items: center;">
                <span class="badge badge-info" style="font-size: 11px;">${this.escape(doc.document_type)}</span>
                <span class="badge ${isMandatory ? 'badge-mandatory' : 'badge-supporting'}" style="font-size: 11px;">
                  ${isMandatory ? 'Mandatory' : 'Supporting'}
                </span>
              </div>
            </div>
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 6px;">
              <strong>Purpose:</strong> ${this.escape(doc.purpose)}
            </p>
            ${doc.preparation_guidance ? `
              <div style="font-size: 12.5px; color: var(--text-secondary); background: rgba(0,0,0,0.25); padding: 8px 10px; border-radius: 6px; margin-bottom: 6px;">
                💡 <strong>Preparation Guidance:</strong> ${this.escape(doc.preparation_guidance)}
              </div>
            ` : ''}
            ${doc.statutory_reference_id ? `
              <div style="margin-top: 6px;">
                <span style="font-size: 11.5px; color: var(--text-secondary); margin-right: 6px;">Statutory Basis:</span>
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
        <span style="color: var(--accent-primary); font-weight: bold;">•</span> ${this.escape(t)}
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
            <strong style="color: var(--text-primary); font-size: 14px;">${this.escape(d.label)}</strong>
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
            <strong style="color: var(--text-primary); font-size: 14px;">${this.escape(v.label)}</strong>
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
            <strong style="font-size: 15px; color: var(--text-primary);">${this.escape(c.title)}</strong>
            <span class="badge badge-active">${this.escape(c.category)}</span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.5;">${this.escape(c.explanation || '')}</p>
          <div style="background: rgba(15, 23, 42, 0.7); border-left: 3px solid var(--accent-primary); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 12.5px; color: var(--text-secondary); font-style: italic; line-height: 1.6;">
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
            <strong style="font-size: 13px; color: var(--text-primary);">${this.escape(o.party)}:</strong>
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
            <strong style="font-size: 15px; color: var(--text-primary);">${this.escape(r.title)}</strong>
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
            <strong style="font-size: 14px; color: var(--text-primary);">${this.escape(a.task)}</strong>
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
                <strong style="font-size: 16px; color: var(--text-primary);">${this.escape(s.citation_text)}</strong>
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
            <div style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px;">
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
              <strong style="color: var(--text-primary); font-size: 15px;">${this.escape(h.document_name)}</strong>
              <span class="badge badge-active">${this.escape(h.document_type)}</span>
              ${h.case_title ? `<span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #A5B4FC;">Case: ${this.escape(h.case_title)}</span>` : ''}
            </div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">
              ${this.escape(h.summary_preview)}
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">
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

      // Dynamic Personalized Greeting
      const hour = new Date().getHours();
      let timeOfDay = 'evening';
      if (hour < 12) timeOfDay = 'morning';
      else if (hour < 17) timeOfDay = 'afternoon';
      const fullName = this.user?.full_name || 'Citizen';
      const titleEl = document.getElementById('dash-citizen-welcome-title');
      if (titleEl) {
        titleEl.innerHTML = `Good ${timeOfDay}, <span id="dash-citizen-greeting-name">${this.escape(fullName)}</span>`;
      }

      // Render NEXT IMPORTANT DATE Hero
      const nextDateContainer = document.getElementById('citizen-next-date-container');
      if (nextDateContainer) {
        const hearings = data.upcoming_hearings || [];
        if (hearings.length > 0) {
          const nextH = hearings[0];
          let monthPart = 'DATE';
          let dayPart = '';
          const dStr = String(nextH.reminder_date || '');
          try {
            const parsed = new Date(dStr);
            if (!isNaN(parsed.getTime())) {
              monthPart = parsed.toLocaleString('en-US', { month: 'short' }).toUpperCase();
              dayPart = parsed.getDate();
            } else {
              const parts = dStr.split(/[-\s/]/);
              if (parts.length >= 2) {
                dayPart = parts[0];
                monthPart = parts[1].toUpperCase();
              } else {
                dayPart = dStr;
              }
            }
          } catch (e) {
            dayPart = dStr;
          }

          nextDateContainer.innerHTML = `
            <div class="next-date-hero">
              <div class="next-date-header">
                <span class="next-date-badge-label">⚡ NEXT IMPORTANT DATE</span>
                <span class="badge badge-active">${this.escape(nextH.reminder_time || '10:30 AM')}</span>
              </div>
              <div class="next-date-content">
                <div class="next-date-badge-box">
                  <span class="next-date-day">${this.escape(dayPart)}</span>
                  <span class="next-date-month">${this.escape(monthPart)}</span>
                </div>
                <div class="next-date-details">
                  <h4 class="next-date-title">${this.escape(nextH.title || nextH.case_title || 'Scheduled Court Appearance')}</h4>
                  <div class="next-date-meta">
                    <span>⚖️ ${this.escape(nextH.case_title || 'Legal Matter')}</span>
                    <span>•</span>
                    <span>🏛️ ${this.escape(nextH.court_name || 'Designated Court / Forum')}</span>
                  </div>
                </div>
                <div class="next-date-action">
                  <button class="btn btn-primary btn-sm" onclick="${nextH.case_id ? `App.openCitizenCaseDetail(${nextH.case_id})` : `App.navigate('citizen-cases')`}">
                    View Case →
                  </button>
                </div>
              </div>
            </div>
          `;
        } else {
          nextDateContainer.innerHTML = `
            <div class="next-date-empty-hero">
              <div class="next-date-empty-icon">📅</div>
              <div class="next-date-empty-body">
                <div class="next-date-empty-title">You're all clear for now</div>
                <div class="next-date-empty-desc">No upcoming court hearings or procedural deadlines are currently scheduled for your matters.</div>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="App.openCitizenNewCaseModal()">+ File Matter</button>
            </div>
          `;
        }
      }

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
      const sbCases = document.getElementById('sidebar-citizen-case-count') || document.getElementById('sidebar-c-case-count');
      const sbDocs = document.getElementById('sidebar-citizen-doc-count') || document.getElementById('sidebar-c-doc-count');
      const sbBm = document.getElementById('sidebar-citizen-bm-count') || document.getElementById('sidebar-c-bm-count');
      if (sbCases) sbCases.innerText = data.metrics.active_cases;
      if (sbDocs) sbDocs.innerText = data.metrics.total_documents;
      if (sbBm) sbBm.innerText = data.metrics.saved_sections;

      // Render Active Cases List
      const cList = document.getElementById('citizen-dash-cases-list');
      if (cList) {
        if (!data.recent_cases || data.recent_cases.length === 0) {
          cList.innerHTML = `
            <div class="empty-state">
              <div class="empty-state-title">No active legal matters</div>
              <div class="empty-state-desc">No legal matters are currently active. Register a matter to begin tracking court appearances and briefs.</div>
              <button class="btn btn-primary btn-sm" onclick="App.openCitizenNewCaseModal()" style="margin-top: 10px;">+ File New Matter</button>
            </div>
          `;
        } else {
          cList.innerHTML = data.recent_cases.map(c => `
            <div class="matter-card" onclick="App.openCitizenCaseDetail(${c.case_id})">
              <div class="matter-card-body">
                <div class="matter-title">${this.escape(c.title)}</div>
                <div class="matter-meta">
                  <span class="matter-court">🏛️ ${this.escape(c.court || 'Court / Forum')}</span>
                  ${c.case_number ? `<span>• <code class="matter-code">${this.escape(c.case_number)}</code></span>` : ''}
                </div>
                ${c.lawyer_name ? `<div class="matter-counsel">Assigned Counsel: ${this.escape(c.lawyer_name)}</div>` : ''}
              </div>
              <div class="matter-card-action">
                <span class="badge badge-${c.status}">${c.status}</span>
                <div class="matter-action-btn">View Matter →</div>
              </div>
            </div>
          `).join('');
        }
      }

      // Render Upcoming Hearings
      const hList = document.getElementById('citizen-dash-hearings-list');
      if (hList) {
        if (!data.upcoming_hearings || data.upcoming_hearings.length === 0) {
          hList.innerHTML = `
            <div class="empty-state">
              <div class="empty-state-title">No upcoming court hearings</div>
              <div class="empty-state-desc">You're all clear for now. When court appearances or dates are scheduled, they will appear here.</div>
            </div>
          `;
        } else {
          hList.innerHTML = data.upcoming_hearings.map(h => `
            <div class="hearing-card-item">
              <div class="hearing-card-body">
                <div class="hearing-card-title">${this.escape(h.title)}</div>
                <div class="hearing-card-meta">
                  ⚖️ ${this.escape(h.case_title || 'Legal Matter')} • 🏛️ ${this.escape(h.court_name || 'Designated Court')}
                </div>
              </div>
              <div class="hearing-card-action">
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
            <div class="doc-row-item" style="cursor: pointer;" onclick="App.navigate('document-analysis'); App.loadAnalysisById(${a.analysis_id});">
              <div class="doc-row-body">
                <div class="doc-row-name">📄 ${this.escape(a.document_name)}</div>
                <div class="doc-row-meta">
                  <span class="badge badge-completed">${this.escape(a.document_type)}</span>
                  <span>${new Date(a.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div class="doc-row-action">
                <span style="font-size: 12px; color: var(--accent-cyan); white-space: nowrap;">View Report →</span>
              </div>
            </div>
          `).join('');
        }
      }

      // Render Recent Documents
      const dList = document.getElementById('citizen-dash-documents-list');
      if (dList) {
        if (!data.recent_documents || data.recent_documents.length === 0) {
          dList.innerHTML = `
            <div class="empty-state">
              <div class="empty-state-title">No documents uploaded</div>
              <div class="empty-state-desc">Your legal documents, contracts, and case briefs will appear here.</div>
              <button class="btn btn-secondary btn-sm" onclick="App.openCitizenUploadDocModal()" style="margin-top: 10px;">+ Upload Document</button>
            </div>
          `;
        } else {
          dList.innerHTML = data.recent_documents.map(d => `
            <div class="doc-row-item">
              <div class="doc-row-body">
                <div class="doc-row-name">📄 ${this.escape(d.document_name)}</div>
                <div class="doc-row-meta">
                  <span class="badge badge-completed">${d.document_type || 'Attached'}</span>
                  <span>${this.escape(d.case_title || 'Legal Matter')}</span>
                </div>
              </div>
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
                  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                    <strong style="font-size: 13.5px; color: var(--text-primary); overflow-wrap: anywhere; word-break: break-word;">${this.escape(p.procedure_name)}</strong>
                    <span style="font-size: 12px; color: var(--accent-cyan); font-weight: 600;">${pct}% Complete</span>
                  </div>
                  <div class="progress-track">
                    <div class="progress-fill" style="width: ${pct}%;"></div>
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-top: 6px; flex-wrap: wrap; gap: 4px;">
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
              <div class="doc-row-item" style="cursor: pointer;" onclick="App.viewFullProvisionDetail(${b.section_id})">
                <div class="doc-row-body">
                  <div class="doc-row-name">Section ${this.escape(b.section_number)}: ${this.escape(b.section_title || '')}</div>
                  <div class="doc-row-meta">
                    <span style="color: var(--accent-cyan);">📖 ${this.escape(b.law_name || 'Statute')}</span>
                  </div>
                </div>
                <div class="doc-row-action">
                  <span style="font-size: 11.5px; color: var(--accent-primary); white-space: nowrap;">View →</span>
                </div>
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
                  <div class="search-history-item">
                    <div style="flex: 1; min-width: 0;">
                      <div class="search-history-query">🔍 "${this.escape(s.query_text)}"</div>
                      <div class="search-history-meta">
                        <span>${s.results_count || 0} provisions matched</span>
                        <span>•</span>
                        <span>${new Date(s.searched_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div class="search-history-action">
                      <button class="search-again-btn" onclick="App.reSearchFromHistory('${this.escape(s.query_text)}', '${this.escape(s.filters && s.filters.jurisdiction ? s.filters.jurisdiction : '')}')">Search Again</button>
                    </div>
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
                <strong style="font-size: 13.5px; color: ${n.is_read ? 'var(--text-secondary)' : 'var(--text-primary)'};">${this.escape(n.title)}</strong>
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
          <div style="flex: 1 1 260px; min-width: 0;">
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 6px;">
              <span class="badge badge-${c.status}">${c.status}</span>
              <span class="badge badge-completed">${this.escape(c.case_type || 'Civil Matter')}</span>
              ${c.case_number ? `<span style="font-size: 12px; color: var(--accent-cyan); font-family: monospace; word-break: break-all;">${this.escape(c.case_number)}</span>` : ''}
            </div>
            <h3 style="font-size: 18px; color: var(--text-primary); margin-bottom: 4px; overflow-wrap: anywhere; word-break: break-word;">${this.escape(c.title)}</h3>
            <div style="font-size: 13px; color: var(--text-muted); overflow-wrap: anywhere; word-break: break-word;">
              🏛️ ${this.escape(c.court || 'Court / Judicial Forum')} • Opposite Party: <strong style="color: var(--text-secondary);">${this.escape(c.opposite_party || 'Unspecified')}</strong>
            </div>
          </div>
          <div style="text-align: right; flex-shrink: 0;">
            ${c.lawyer_name ? `
              <div style="background: rgba(15, 23, 42, 0.6); padding: 6px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: inline-block;">
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Assigned Counsel</div>
                <div style="font-size: 12.5px; font-weight: 600; color: var(--accent-primary);">${this.escape(c.lawyer_name)}</div>
              </div>
            ` : `
              <span class="badge" style="background: rgba(100, 116, 139, 0.2); color: var(--text-secondary);">Self Represented</span>
            `}
          </div>
        </div>

        ${c.description ? `
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 12px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            ${this.escape(c.description)}
          </div>
        ` : ''}

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); font-size: 12px; color: var(--text-muted); flex-wrap: wrap; gap: 8px;">
          <div>
            ${c.filing_date ? `Filing Date: ${c.filing_date}` : (c.created_at ? `Created: ${new Date(c.created_at).toLocaleDateString()}` : '')}
          </div>
          <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
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
              <div style="font-weight: 500; color: var(--text-primary); font-size: 14px;">📄 ${this.escape(d.document_name)}</div>
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
              <div style="font-weight: 600; color: var(--text-primary); font-size: 14px;">${this.escape(h.title)}</div>
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
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(99, 102, 241, 0.15); color: var(--accent-primary); display: flex; align-items: center; justify-content: center; font-size: 14px;">
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
                <h4 style="font-size: 15px; color: var(--text-primary);">${this.escape(s.section_title || 'Section Provision')}</h4>
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
    const payload = {
      title: document.getElementById('m-c-case-title').value.trim(),
      case_type: document.getElementById('m-c-case-type').value || 'Civil Litigation',
      court: document.getElementById('m-c-case-court').value.trim() || null,
      opposite_party: document.getElementById('m-c-case-opposite').value.trim() || null,
      incident_date: document.getElementById('m-c-case-incident-date').value || null,
      police_station: document.getElementById('m-c-case-police').value.trim() || null,
      location: document.getElementById('m-c-case-location').value.trim() || null,
      description: document.getElementById('m-c-case-description').value.trim()
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
              <strong style="color: var(--text-primary); font-size: 15px;">📄 ${this.escape(d.document_name)}</strong>
              <span class="badge badge-completed">${this.escape(d.document_type)}</span>
              ${d.case_title ? `<span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #A5B4FC;">Matter: ${this.escape(d.case_title)}</span>` : ''}
            </div>
            ${d.description ? `<div style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">${this.escape(d.description)}</div>` : ''}
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">
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
            <h3 style="font-size: 17px; color: var(--text-primary); margin-bottom: 2px;">${this.escape(b.section_title || 'Section Provision')}</h3>
            <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 500;">📖 ${this.escape(b.law_name)}</div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="App.viewFullProvisionDetail(${b.section_id})">📖 View Text</button>
            <button class="btn btn-danger btn-sm" onclick="App.deleteBookmark(${b.section_id})">✕ Remove</button>
          </div>
        </div>

        ${b.notes ? `
          <div style="font-size: 13px; color: var(--text-secondary); background: rgba(15, 23, 42, 0.5); padding: 10px 14px; border-radius: var(--radius-sm); margin: 10px 0; border: 1px solid var(--border-subtle);">
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

  // 6. NOTIFICATIONS & ALERTS MANAGER
  updateNotificationBadge(unreadCount) {
    const badge = document.getElementById('notif-badge');
    const headerCount = document.getElementById('notif-header-count');
    const count = parseInt(unreadCount, 10) || 0;
    this.unreadNotifCount = count;

    if (badge) {
      if (count > 0) {
        badge.innerText = count > 99 ? '99+' : count;
        badge.style.display = 'inline-flex';
        badge.setAttribute('aria-label', `${count} unread notifications`);
      } else {
        badge.innerText = '0';
        badge.style.display = 'none';
        badge.removeAttribute('aria-label');
      }
    }

    if (headerCount) {
      if (count > 0) {
        headerCount.innerText = `${count} unread`;
        headerCount.style.display = 'inline-block';
      } else {
        headerCount.innerText = '';
        headerCount.style.display = 'none';
      }
    }

    // Synchronize sidebar badge
    const sbBadge = document.getElementById('sidebar-citizen-notif-count');
    if (sbBadge) {
      sbBadge.innerText = count > 0 ? count : '0';
    }
  },

  formatRelativeTime(dateStr) {
    if (!dateStr) return 'Recently';
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      const now = new Date();
      const diffSec = Math.floor((now - date) / 1000);
      if (diffSec < 60) return 'Just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h ago`;
      const diffDays = Math.floor(diffHr / 24);
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  },

  getNotificationMeta(type, title) {
    const raw = (type || title || '').toLowerCase();
    if (raw.includes('hear') || raw.includes('court') || raw.includes('bench') || raw.includes('trial')) {
      return { icon: '⚖️', label: 'Hearing', className: 'hearing' };
    }
    if (raw.includes('case') || raw.includes('matter') || raw.includes('registered') || raw.includes('brief') || raw.includes('status')) {
      return { icon: '📁', label: 'Case Update', className: 'case_update' };
    }
    if (raw.includes('doc') || raw.includes('file') || raw.includes('pdf') || raw.includes('affidavit') || raw.includes('petition')) {
      return { icon: '📄', label: 'Document', className: 'document' };
    }
    return { icon: 'ℹ️', label: 'System', className: 'system' };
  },

  toggleNotificationsPopover() {
    const popover = document.getElementById('notifications-popover');
    if (!popover) return;
    if (popover.classList.contains('active')) {
      this.closeNotificationsPopover();
    } else {
      this.openNotificationsPopover();
    }
  },

  openNotificationsPopover() {
    const popover = document.getElementById('notifications-popover');
    const btn = document.getElementById('btn-notifications-bell');
    if (!popover) return;

    // Close any competing overlays
    this.closeThemePicker();
    this.closeMobileSidebar();

    popover.classList.add('active');
    popover.setAttribute('aria-hidden', 'false');
    btn?.setAttribute('aria-expanded', 'true');

    // Fetch and render latest notifications
    this.loadNotifications();

    // Position securely within the viewport
    requestAnimationFrame(() => {
      this.positionNotificationsPopover();
    });
  },

  closeNotificationsPopover() {
    const popover = document.getElementById('notifications-popover');
    const btn = document.getElementById('btn-notifications-bell');
    if (popover) {
      popover.classList.remove('active');
      popover.setAttribute('aria-hidden', 'true');
    }
    if (btn) {
      btn.setAttribute('aria-expanded', 'false');
    }
  },

  positionNotificationsPopover() {
    const popover = document.getElementById('notifications-popover');
    if (!popover || !popover.classList.contains('active')) return;

    // Reset offsets to measure unconstrained dimensions
    popover.style.left = 'auto';
    popover.style.right = '0';

    const popoverRect = popover.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const padding = 10;

    // Check left viewport overflow
    if (popoverRect.left < padding) {
      const shift = padding - popoverRect.left;
      popover.style.right = `${-shift}px`;
    }

    // Check right viewport overflow
    const updatedRect = popover.getBoundingClientRect();
    if (updatedRect.right > viewportWidth - padding) {
      const overflowRight = updatedRect.right - (viewportWidth - padding);
      const currentRight = parseFloat(popover.style.right) || 0;
      popover.style.right = `${currentRight + overflowRight}px`;
    }
  },

  async loadNotifications() {
    if (!this.token) return;

    const isCitizen = !this.user || this.user.role === 'citizen' || this.user.role === 'user';
    if (isCitizen) {
      try {
        const data = await this.api('/api/citizen/notifications');
        this.citizenNotifications = data.notifications || [];
        this.updateNotificationBadge(data.unread_count || 0);
        this.renderNotificationsList(this.citizenNotifications);
      } catch (err) {
        console.warn('Could not load citizen notifications:', err);
      }
    } else {
      // Lawyer mode
      this.loadLawyerNotifications();
    }
  },

  async loadLawyerNotifications() {
    try {
      const data = await this.api('/api/lawyer/dashboard');
      const notifs = [];
      const hearings = data.upcoming_hearings_list || [];
      hearings.forEach((h, idx) => {
        notifs.push({
          notification_id: `lawyer_h_${idx}`,
          title: h.title || 'Upcoming Court Hearing',
          message: `${h.case_title || 'Case Brief'} at ${h.court_name || 'Designated Court'} • ${h.reminder_date} ${h.reminder_time || '10:30 AM'}`,
          notification_type: 'hearing',
          is_read: false,
          created_at: h.reminder_date || new Date().toISOString(),
          target_view: 'hearings'
        });
      });

      const cases = (data.recent_cases || []).slice(0, 3);
      cases.forEach((c, idx) => {
        notifs.push({
          notification_id: `lawyer_c_${idx}`,
          title: `Case Matter: ${c.case_title}`,
          message: `Client: ${c.client_name || 'Client'} (${c.case_number || 'Brief'}) • Status: ${c.status}`,
          notification_type: 'case_update',
          is_read: true,
          created_at: new Date().toISOString(),
          target_view: 'cases',
          case_id: c.case_id
        });
      });

      this.citizenNotifications = notifs;
      const unreadCount = notifs.filter(n => !n.is_read).length;
      this.updateNotificationBadge(unreadCount);
      this.renderNotificationsList(notifs);
    } catch (err) {
      console.warn('Could not load lawyer notifications:', err);
    }
  },

  renderNotificationsList(notifs) {
    const container = document.getElementById('notifications-list-container');
    if (!container) return;

    if (!notifs || notifs.length === 0) {
      container.innerHTML = `
        <div class="notif-empty-state">
          <div class="notif-empty-icon">✓</div>
          <div class="notif-empty-title">You're all caught up</div>
          <div class="notif-empty-desc">No new notifications at this time.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = notifs.map(n => {
      const meta = this.getNotificationMeta(n.notification_type, n.title);
      const isUnread = !n.is_read;
      const timeStr = this.formatRelativeTime(n.created_at || n.sent_at);
      const safeId = typeof n.notification_id === 'string' ? `'${n.notification_id}'` : n.notification_id;

      return `
        <div class="notif-item ${isUnread ? 'unread' : ''}"
             onclick="App.handleNotificationClick(${safeId}, '${meta.className}', event)"
             role="article"
             tabindex="0"
             aria-label="${this.escape(n.title)}">
          <div class="notif-icon-box ${meta.className}" aria-hidden="true">
            ${meta.icon}
          </div>
          <div class="notif-body">
            <div class="notif-item-top">
              <span class="notif-item-title">${this.escape(n.title)}</span>
              <span class="notif-item-badge">${meta.label}</span>
            </div>
            <div class="notif-item-msg">${this.escape(n.message)}</div>
            <div class="notif-item-bottom">
              <span class="notif-item-time">
                ${isUnread ? '<span class="notif-item-unread-dot" title="Unread"></span>' : ''}
                ${timeStr}
              </span>
              <span class="notif-item-action">Open →</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  },

  async handleNotificationClick(id, type, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    // Mark as read if it is a citizen notification with numeric ID
    if (typeof id === 'number') {
      try {
        await this.api(`/api/citizen/notifications/${id}/read`, 'PATCH');
        const notif = this.citizenNotifications.find(n => n.notification_id === id);
        if (notif && !notif.is_read) {
          notif.is_read = true;
          this.unreadNotifCount = Math.max(0, this.unreadNotifCount - 1);
          this.updateNotificationBadge(this.unreadNotifCount);
        }
      } catch (err) {
        console.warn('Could not mark notification read:', err);
      }
    } else if (typeof id === 'string') {
      const notif = this.citizenNotifications.find(n => n.notification_id === id);
      if (notif && !notif.is_read) {
        notif.is_read = true;
        this.unreadNotifCount = Math.max(0, this.unreadNotifCount - 1);
        this.updateNotificationBadge(this.unreadNotifCount);
      }
    }

    // Close the popover
    this.closeNotificationsPopover();

    // Navigate to appropriate section based on type and user role
    const isCitizen = !this.user || this.user.role === 'citizen' || this.user.role === 'user';
    if (isCitizen) {
      if (type === 'hearing' || type === 'case_update' || type === 'case') {
        this.navigate('citizen-cases');
      } else if (type === 'document') {
        this.navigate('citizen-docs');
      } else {
        this.navigate('citizen-notifications');
      }
    } else {
      if (type === 'hearing') {
        this.navigate('hearings');
      } else if (type === 'case_update' || type === 'case') {
        this.navigate('cases');
      } else if (type === 'document') {
        this.navigate('documents');
      }
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
    const isCitizen = !this.user || this.user.role === 'citizen' || this.user.role === 'user';
    if (isCitizen) {
      try {
        await this.api('/api/citizen/notifications/read-all', 'POST');
        this.showToast('All notifications marked as read.', 'info');
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    } else {
      this.showToast('All notifications marked as read.', 'info');
    }

    this.citizenNotifications.forEach(n => { n.is_read = true; });
    this.updateNotificationBadge(0);
    this.renderNotificationsList(this.citizenNotifications);
    if (this.currentView === 'citizen-notifications') {
      this.loadNotificationsView();
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
          <div style="font-size: 15px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
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
            <strong style="font-size: 14.5px; color: ${n.is_read ? 'var(--text-secondary)' : 'var(--text-primary)'};">${this.escape(n.title)}</strong>
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
  // UI UTILITIES & TOASTS
  // -------------------------------------------------------------
  closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => {
      if (m.id !== 'login-screen') {
        m.classList.remove('active');
      }
    });
    document.body.classList.remove('modal-open');
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
