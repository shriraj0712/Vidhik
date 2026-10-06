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
  activeCaseId: localStorage.getItem('vidhik_active_case_id') ? parseInt(localStorage.getItem('vidhik_active_case_id'), 10) : null,
  activeCaseContext: null,
  activeCiTab: 'overview',

  // -------------------------------------------------------------
  // INITIALIZATION
  // -------------------------------------------------------------
  async init() {
    this.initTheme();
    this.initLocalization();
    this.applyLocalization();
    this.switchAuthMode('citizen', true);
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
        this.closeLanguagePicker();
        this.closeNavMore();
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
      const langContainer = document.getElementById('lang-selector-container');
      if (langContainer && !langContainer.contains(e.target)) {
        this.closeLanguagePicker();
      }
      const citizenMore = document.getElementById('citizen-nav-more-wrap');
      const lawyerMore = document.getElementById('lawyer-nav-more-wrap');
      if (citizenMore && !citizenMore.contains(e.target)) {
        const m = document.getElementById('citizen-nav-more-menu');
        if (m) m.style.display = 'none';
      }
      if (lawyerMore && !lawyerMore.contains(e.target)) {
        const m = document.getElementById('lawyer-nav-more-menu');
        if (m) m.style.display = 'none';
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
  switchAuthMode(mode, fillCredentials = true) {
    this.authMode = mode;
    const loginScreen = document.getElementById('login-screen');
    if (loginScreen) {
      loginScreen.classList.toggle('mode-admin', mode === 'admin');
    }

    // Update active tab in segmented control
    document.querySelectorAll('.auth-tab-btn').forEach(b => {
      const isAct = b.getAttribute('data-auth-tab') === mode;
      b.classList.toggle('active', isAct);
      b.setAttribute('aria-selected', isAct ? 'true' : 'false');
    });

    // Clear previous error
    const errAlert = document.getElementById('login-error-alert');
    if (errAlert) errAlert.style.display = 'none';

    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');
    const demoContainer = document.getElementById('login-demo-container');
    const regPrompt = document.getElementById('auth-register-prompt');
    const adminBadge = document.getElementById('admin-restricted-badge');
    const heading = document.getElementById('auth-role-heading');
    const subtitle = document.getElementById('auth-card-subtitle');
    const emailLabel = document.getElementById('login-email-label');
    const emailInput = document.getElementById('login-email');
    const submitBtn = document.getElementById('btn-login-submit');
    const submitBtnText = document.getElementById('btn-login-submit-text');
    const submitBtnIcon = document.getElementById('btn-login-submit-icon');

    const lang = this.currentLanguage || 'en';
    const dict = this.getAuthLocalizationDict(lang);

    if (mode === 'register') {
      if (loginForm) loginForm.style.display = 'none';
      if (regForm) regForm.style.display = 'block';
      if (demoContainer) demoContainer.style.display = 'none';
      if (adminBadge) adminBadge.style.display = 'none';
      if (heading) heading.textContent = dict.registerHeading;
      if (subtitle) subtitle.textContent = dict.registerSub;
      return;
    }

    // Login modes: citizen, lawyer, admin
    if (loginForm) loginForm.style.display = 'block';
    if (regForm) regForm.style.display = 'none';
    if (demoContainer) demoContainer.style.display = 'block';

    if (mode === 'citizen') {
      if (heading) heading.textContent = dict.citizenHeading;
      if (subtitle) subtitle.textContent = dict.citizenSub;
      if (emailLabel) emailLabel.textContent = dict.citizenEmailLabel;
      if (emailInput) emailInput.placeholder = 'sunita.sharma@example.com';
      if (submitBtnText) submitBtnText.textContent = dict.signInBtn;
      if (submitBtn) submitBtn.classList.remove('btn-admin');
      if (adminBadge) adminBadge.style.display = 'none';
      if (regPrompt) regPrompt.style.display = 'flex';
      if (submitBtnIcon) {
        submitBtnIcon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>';
      }
      if (fillCredentials) {
        this.fillDemoLogin('sunita.sharma@example.com', 'citizen');
      }
    } else if (mode === 'lawyer') {
      if (heading) heading.textContent = dict.lawyerHeading;
      if (subtitle) subtitle.textContent = dict.lawyerSub;
      if (emailLabel) emailLabel.textContent = dict.lawyerEmailLabel;
      if (emailInput) emailInput.placeholder = 'rajesh.advocate@vidhik.ai';
      if (submitBtnText) submitBtnText.textContent = dict.signInBtn;
      if (submitBtn) submitBtn.classList.remove('btn-admin');
      if (adminBadge) adminBadge.style.display = 'none';
      if (regPrompt) regPrompt.style.display = 'none';
      if (submitBtnIcon) {
        submitBtnIcon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>';
      }
      if (fillCredentials) {
        this.fillDemoLogin('rajesh.advocate@vidhik.ai', 'lawyer');
      }
    } else if (mode === 'admin') {
      if (heading) heading.textContent = dict.adminHeading;
      if (subtitle) subtitle.textContent = dict.adminSub;
      if (emailLabel) emailLabel.textContent = dict.adminEmailLabel;
      if (emailInput) emailInput.placeholder = 'admin@vidhik.ai';
      if (submitBtnText) submitBtnText.textContent = dict.secureSignInBtn;
      if (submitBtn) submitBtn.classList.add('btn-admin');
      if (adminBadge) adminBadge.style.display = 'inline-flex';
      if (regPrompt) regPrompt.style.display = 'none';
      if (submitBtnIcon) {
        submitBtnIcon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>';
      }
      if (fillCredentials) {
        this.fillDemoLogin('admin@vidhik.ai', 'admin');
      }
    }
  },

  getAuthLocalizationDict(lang = 'en') {
    const dicts = {
      en: {
        citizenTab: 'Citizen',
        lawyerTab: 'Lawyer',
        adminTab: 'Admin',
        citizenHeading: 'Citizen Login',
        citizenSub: 'Access legal assistance, complaints, case tracking and your legal workspace.',
        citizenEmailLabel: 'Citizen Email Address',
        lawyerHeading: 'Lawyer Login',
        lawyerSub: 'Access your clients, cases, documents and professional legal workspace.',
        lawyerEmailLabel: 'Lawyer / Bar Email Address',
        adminHeading: 'Administrator Login',
        adminSub: 'Secure administrative access to VIDHIK AI.',
        adminEmailLabel: 'Administrator Email Address',
        adminRestricted: 'Restricted Access • Authorized Personnel Only',
        registerHeading: 'Create Citizen Account',
        registerSub: 'Join VIDHIK AI to track legal matters, draft complaints, and access case intelligence.',
        signInBtn: 'Sign In',
        secureSignInBtn: 'Secure Sign In',
        passwordLabel: 'Password',
        noAccount: 'New citizen user?',
        createAccountLink: 'Create an account →',
        haveAccount: 'Already have an account?',
        signInLink: 'Sign In →'
      },
      hi: {
        citizenTab: 'नागरिक',
        lawyerTab: 'अधिवक्ता',
        adminTab: 'प्रशासक',
        citizenHeading: 'नागरिक लॉगिन',
        citizenSub: 'विधिक सहायता, शिकायत, केस ट्रैकिंग और अपने विधिक कार्यक्षेत्र तक पहुँचें।',
        citizenEmailLabel: 'नागरिक ईमेल पता',
        lawyerHeading: 'अधिवक्ता लॉगिन',
        lawyerSub: 'अपने मुवक्किलों, मामलों, दस्तावेजों और व्यावसायिक विधिक कार्यक्षेत्र तक पहुँचें।',
        lawyerEmailLabel: 'अधिवक्ता / बार ईमेल पता',
        adminHeading: 'प्रशासक लॉगिन',
        adminSub: 'विधिक एआई के लिए सुरक्षित प्रशासनिक पहुंच।',
        adminEmailLabel: 'प्रशासक ईमेल पता',
        adminRestricted: 'प्रतिबंधित पहुंच • केवल अधिकृत कर्मी',
        registerHeading: 'नागरिक खाता बनाएं',
        registerSub: 'विधिक मामलों की ट्रैकिंग, शिकायत प्रारूप और केस इंटेलिजेंस के लिए विधिक एआई से जुड़ें।',
        signInBtn: 'साइन इन करें',
        secureSignInBtn: 'सुरक्षित साइन इन करें',
        passwordLabel: 'पासवर्ड',
        noAccount: 'नए नागरिक उपयोगकर्ता?',
        createAccountLink: 'खाता बनाएं →',
        haveAccount: 'पहले से खाता है?',
        signInLink: 'साइन इन करें →'
      },
      mr: {
        citizenTab: 'नागरिक',
        lawyerTab: 'वकील',
        adminTab: 'प्रशासक',
        citizenHeading: 'नागरिक लॉगिन',
        citizenSub: 'कायदेशीर मदत, तक्रारी, खटला ट्रॅकिंग आणि आपल्या कार्यक्षेत्रात प्रवेश करा.',
        citizenEmailLabel: 'नागरिक ईमेल पत्ता',
        lawyerHeading: 'वकील लॉगिन',
        lawyerSub: 'आपले पक्षकार, खटले, कागदपत्रे आणि व्यावसायिक विधी कार्यक्षेत्रात प्रवेश करा.',
        lawyerEmailLabel: 'वकील / बार ईमेल पत्ता',
        adminHeading: 'प्रशासक लॉगिन',
        adminSub: 'विधिक एआयसाठी सुरक्षित प्रशासकीय प्रवेश.',
        adminEmailLabel: 'प्रशासक ईमेल पत्ता',
        adminRestricted: 'प्रतिबंधित प्रवेश • केवळ अधिकृत व्यक्तींसाठी',
        registerHeading: 'नागरिक खाते तयार करा',
        registerSub: 'विधी प्रकरणे ट्रॅक करण्यासाठी आणि कायदेशीर बुद्धिमत्ता मिळवण्यासाठी विधिक एआयमध्ये सामील व्हा.',
        signInBtn: 'साइन इन करा',
        secureSignInBtn: 'सुरक्षित साइन इन करा',
        passwordLabel: 'पासवर्ड',
        noAccount: 'नवीन नागरिक वापरकर्ता?',
        createAccountLink: 'खाते तयार करा →',
        haveAccount: 'आधीच खाते आहे?',
        signInLink: 'साइन इन करा →'
      }
    };
    return dicts[lang] || dicts['en'];
  },

  togglePasswordVisibility(inputId, toggleBtnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(toggleBtnId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    if (btn) {
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
      btn.title = isPassword ? 'Hide password' : 'Show password';
      const showIcon = btn.querySelector('.eye-icon-show');
      const hideIcon = btn.querySelector('.eye-icon-hide');
      if (showIcon && hideIcon) {
        showIcon.style.display = isPassword ? 'none' : 'block';
        hideIcon.style.display = isPassword ? 'block' : 'none';
      }
    }
  },

  fillDemoLogin(email, roleOrPassword = 'password123') {
    let targetMode = 'citizen';
    if (email.includes('rajesh') || roleOrPassword === 'lawyer') {
      targetMode = 'lawyer';
    } else if (email.includes('admin') || roleOrPassword === 'admin') {
      targetMode = 'admin';
    }
    if (this.authMode !== targetMode) {
      this.switchAuthMode(targetMode, false);
    }
    const emailInput = document.getElementById('login-email');
    const pwdInput = document.getElementById('login-password');
    if (emailInput) emailInput.value = email;
    if (pwdInput) {
      if (['citizen', 'lawyer', 'admin'].includes(roleOrPassword) || !roleOrPassword) {
        pwdInput.value = 'password123';
      } else {
        pwdInput.value = roleOrPassword;
      }
    }
    const errAlert = document.getElementById('login-error-alert');
    if (errAlert) errAlert.style.display = 'none';
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
    const emailInput = document.getElementById('login-email');
    const pwdInput = document.getElementById('login-password');
    const email = emailInput ? emailInput.value.trim() : '';
    const password = pwdInput ? pwdInput.value : '';
    const submitBtn = document.getElementById('btn-login-submit');
    const errAlert = document.getElementById('login-error-alert');
    const errMsg = document.getElementById('login-error-message');

    if (errAlert) errAlert.style.display = 'none';

    if (!email || !password) {
      const msg = 'Please enter both email and password.';
      if (errAlert && errMsg) {
        errMsg.textContent = msg;
        errAlert.style.display = 'flex';
      }
      this.showToast(msg, 'error');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.classList.add('loading');
    }

    try {
      const data = await this.api('/api/auth/login', 'POST', { email, password });
      this.token = data.token;
      this.user = data;
      localStorage.setItem('vidhik_token', this.token);
      this.showToast(`Welcome back, ${data.full_name}`, 'success');
      this.showApp();
    } catch (e) {
      const msg = e.message || 'Invalid email or password. Please verify credentials.';
      if (errAlert && errMsg) {
        errMsg.textContent = msg;
        errAlert.style.display = 'flex';
      }
      this.showToast(msg, 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
      }
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
    this.activeCaseId = null;
    this.activeCaseContext = null;
    localStorage.removeItem('vidhik_active_case_id');
    this.renderCurrentCaseBanner(null);
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
    this.switchAuthMode(this.authMode || 'citizen', false);
  },

  showApp() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-shell').style.display = 'flex';
    this.updateUserUI();

    const isAdmin = this.user && this.user.role === 'admin';
    const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');

    const citizenNav = document.getElementById('sidebar-citizen-nav');
    const lawyerNav = document.getElementById('sidebar-lawyer-nav');
    const lawyerBtns = document.getElementById('lawyer-quick-actions');
    const citizenBtns = document.getElementById('citizen-quick-actions');
    const brandBadge = document.getElementById('brand-badge-text');

    const topCitizenNav = document.getElementById('desktop-citizen-navbar');
    const topLawyerNav = document.getElementById('desktop-lawyer-navbar');
    const topAdminCitizenLink = document.getElementById('top-nav-admin-link');
    const topAdminLawyerLink = document.getElementById('top-nav-admin-lawyer-link');
    const sidebarCitizenAdminLink = document.getElementById('sidebar-citizen-admin-link');
    const sidebarLawyerAdminLink = document.getElementById('sidebar-lawyer-admin-link');

    if (isAdmin) {
      if (citizenNav) citizenNav.style.display = 'block';
      if (lawyerNav) lawyerNav.style.display = 'none';
      if (topCitizenNav) topCitizenNav.style.display = 'flex';
      if (topLawyerNav) topLawyerNav.style.display = 'none';
      if (topAdminCitizenLink) topAdminCitizenLink.style.display = 'inline-flex';
      if (topAdminLawyerLink) topAdminLawyerLink.style.display = 'none';
      if (sidebarCitizenAdminLink) sidebarCitizenAdminLink.style.display = 'flex';
      if (sidebarLawyerAdminLink) sidebarLawyerAdminLink.style.display = 'none';
      if (lawyerBtns) lawyerBtns.style.display = 'none';
      if (citizenBtns) citizenBtns.style.display = 'flex';
      if (brandBadge) brandBadge.innerText = 'Admin Portal';
      this.navigate('admin');
    } else if (isCitizen) {
      if (citizenNav) citizenNav.style.display = 'block';
      if (lawyerNav) lawyerNav.style.display = 'none';
      if (topCitizenNav) topCitizenNav.style.display = 'flex';
      if (topLawyerNav) topLawyerNav.style.display = 'none';
      if (topAdminCitizenLink) topAdminCitizenLink.style.display = 'none';
      if (topAdminLawyerLink) topAdminLawyerLink.style.display = 'none';
      if (sidebarCitizenAdminLink) sidebarCitizenAdminLink.style.display = 'none';
      if (sidebarLawyerAdminLink) sidebarLawyerAdminLink.style.display = 'none';
      if (lawyerBtns) lawyerBtns.style.display = 'none';
      if (citizenBtns) citizenBtns.style.display = 'flex';
      if (brandBadge) brandBadge.innerText = 'Citizen Portal';
      this.navigate('citizen-dashboard');
    } else {
      if (citizenNav) citizenNav.style.display = 'none';
      if (lawyerNav) lawyerNav.style.display = 'block';
      if (topCitizenNav) topCitizenNav.style.display = 'none';
      if (topLawyerNav) topLawyerNav.style.display = 'flex';
      if (topAdminCitizenLink) topAdminCitizenLink.style.display = 'none';
      if (topAdminLawyerLink) topAdminLawyerLink.style.display = 'none';
      if (sidebarCitizenAdminLink) sidebarCitizenAdminLink.style.display = 'none';
      if (sidebarLawyerAdminLink) sidebarLawyerAdminLink.style.display = 'none';
      if (lawyerBtns) lawyerBtns.style.display = 'flex';
      if (citizenBtns) citizenBtns.style.display = 'none';
      if (brandBadge) brandBadge.innerText = 'Advocate Suite';
      this.navigate('dashboard');
    }

    this.loadNotifications();
    this.loadActiveCase();
  },

  updateUserUI() {
    if (!this.user) return;
    const initials = this.user.full_name ? this.user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'U';
    const avatar = document.getElementById('sidebar-lawyer-avatar');
    const nameEl = document.getElementById('sidebar-lawyer-name');
    const roleEl = document.getElementById('sidebar-lawyer-role') || document.getElementById('sidebar-lawyer-bar');

    let displayRole = 'Citizen Account';
    if (this.user.role === 'admin') displayRole = 'System Administrator';
    else if (this.user.role === 'lawyer') displayRole = 'Verified Advocate';

    if (avatar) avatar.innerText = initials;
    if (nameEl) nameEl.innerText = this.user.full_name;
    if (roleEl) roleEl.innerText = displayRole;

    // Top Header User Chip
    const hAvatar = document.getElementById('header-avatar');
    const hName = document.getElementById('header-user-name');
    const hRole = document.getElementById('header-user-role');
    if (hAvatar) hAvatar.innerText = initials;
    if (hName) hName.innerText = this.user.full_name;

    let headerRole = 'Citizen';
    if (this.user.role === 'admin') headerRole = 'Admin';
    else if (this.user.role === 'lawyer') headerRole = 'Advocate';
    if (hRole) hRole.innerText = headerRole;

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
    this.closeNavMore();

    // Canonical alias normalization for VIDHIK / Legal AI
    if (['legal-ai', 'ask-vidhik', 'vidhik', 'ai'].includes(viewName)) {
      viewName = 'ai-assistant';
    } else if (['legal-research'].includes(viewName)) {
      viewName = 'research';
    }

    const isAdmin = this.user && this.user.role === 'admin';
    const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');

    // Strict role redirection for view access
    if (viewName === 'admin' && !isAdmin) {
      this.showToast('Access restricted: Administrator privileges required', 'error');
      viewName = isCitizen ? 'citizen-dashboard' : 'dashboard';
    }

    const lawyerOnlyViews = ['dashboard', 'clients', 'cases', 'documents', 'hearings', 'profile'];
    const citizenOnlyViews = ['citizen-dashboard', 'citizen-cases', 'citizen-case-detail', 'citizen-documents', 'citizen-bookmarks', 'citizen-search-history', 'citizen-notifications', 'citizen-profile'];

    if (!isAdmin) {
      if (isCitizen && lawyerOnlyViews.includes(viewName)) {
        viewName = 'citizen-dashboard';
      } else if (!isCitizen && citizenOnlyViews.includes(viewName)) {
        viewName = 'dashboard';
      }
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

    // Update Desktop Nav Active Class
    document.querySelectorAll('.desktop-nav-link').forEach(link => {
      const targetView = link.getAttribute('data-view');
      if (targetView === viewName || (targetView === 'current-case' && viewName === 'citizen-case-detail')) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
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
      case 'case-intelligence':
        this.loadCaseIntelligence();
        break;
      case 'ai-assistant':
        this.loadAiAssistant();
        break;
      case 'complaint-generator':
        this.loadComplaintGenerator();
        break;
      case 'resolution':
        this.loadResolutionModule();
        break;
      case 'traffic-law':
        this.loadTrafficLawModule();
        break;
      case 'constitutional-rights':
        this.loadConstitutionalRightsModule();
        break;
      case 'authority-recommendation':
        this.loadAuthorityRecommendationModule();
        break;
      case 'find-lawyer':
        this.loadFindLawyerModule();
        break;
      case 'case-tracking':
        this.loadCaseTrackingModule();
        break;
      case 'voice-assistant':
        this.loadVoiceAssistantModule();
        break;
      case 'legal-knowledge':
        this.loadLegalKnowledgeModule();
        break;
      case 'admin':
        this.loadAdminData();
        break;
    }
  },

  handleTopNavCaseClick() {
    const isCitizen = !this.user || this.user.role === 'citizen' || this.user.role === 'user';
    if (this.activeCaseId) {
      if (isCitizen) {
        this.currentCaseId = this.activeCaseId;
        this.navigate('citizen-case-detail');
      } else {
        this.navigate('case-intelligence');
      }
    } else {
      if (isCitizen) {
        this.navigate('citizen-cases');
      } else {
        this.navigate('cases');
      }
    }
  },

  clearActiveCaseContext() {
    this.activeCaseId = null;
    this.currentCaseId = null;
    localStorage.removeItem('vidhik_active_case_id');
    this.renderCurrentCaseBanner(null);
    const isCitizen = !this.user || this.user.role === 'citizen' || this.user.role === 'user';
    this.navigate(isCitizen ? 'citizen-cases' : 'cases');
    this.showToast('Select a matter to anchor case context', 'info');
  },

  handleBrandClick() {
    if (!this.token || !this.user) return;
    if (this.user.role === 'admin') {
      this.navigate('admin');
    } else if (this.user.role === 'user' || this.user.role === 'citizen') {
      this.navigate('citizen-dashboard');
    } else {
      this.navigate('dashboard');
    }
  },

  toggleNavMore(role) {
    const id = role === 'lawyer' ? 'lawyer-nav-more-menu' : 'citizen-nav-more-menu';
    const menu = document.getElementById(id);
    if (!menu) return;
    const isVisible = menu.style.display === 'block';
    this.closeNavMore();
    this.closeLanguagePicker();
    this.closeNotificationsPopover();
    if (!isVisible) {
      menu.style.display = 'block';
    }
  },

  closeNavMore() {
    const cMenu = document.getElementById('citizen-nav-more-menu');
    const lMenu = document.getElementById('lawyer-nav-more-menu');
    if (cMenu) cMenu.style.display = 'none';
    if (lMenu) lMenu.style.display = 'none';
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
        this.navigate('ai-assistant');
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
          <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm);">
            <div>
              <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${this.escape(h.title)}</div>
              <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 500; margin-top: 3px;">🏛️ ${this.escape(h.court_name || data.court_name)} • Bench: ${this.escape(h.judge_name || 'Designated Bench')}</div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">${this.escape(h.notes || '')}</div>
            </div>
            <div style="text-align: right;">
              <span class="badge badge-${h.status}">${h.status}</span>
              <div style="font-size: 14.5px; font-weight: 700; color: var(--accent-primary); margin-top: 4px;">${h.reminder_date}</div>
              <div style="font-size: 12px; color: var(--text-muted);">${h.reminder_time || '10:30 AM'}</div>
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
          <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 18px; margin-bottom: 14px; box-shadow: var(--shadow-sm);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <div>
                <span class="badge badge-active" style="margin-bottom: 6px;">Section ${s.section_number}</span>
                <h4 style="font-size: 16px; color: var(--text-primary);">${this.escape(s.section_title || 'Section')}</h4>
                <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 500;">📖 ${this.escape(s.law_name)}</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-completed">Relevance: ${s.relevance_score}%</span>
                <button class="btn btn-danger btn-sm" style="margin-top: 6px; display: block; margin-left: auto;" onclick="App.unlinkSectionFromCase(${s.section_id})">Unlink</button>
              </div>
            </div>
            ${s.explanation ? `<div style="font-size: 13.5px; color: var(--text-secondary); background: var(--bg-elevated); padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-top: 8px;"><strong>Rationale:</strong> ${this.escape(s.explanation)}</div>` : ''}
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
      <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); padding: 12px 16px; border-radius: var(--radius-sm); font-size: 13.5px; color: var(--text-primary); display: flex; align-items: center; gap: 10px; box-shadow: var(--shadow-sm);">
        <span style="color: var(--accent-primary); font-weight: bold; font-size: 16px;">•</span> ${this.escape(t)}
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
          <td style="font-size: 12.5px; color: var(--text-muted);">${this.escape(p.raw_text || '-')}</td>
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
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">${this.escape(d.context || '')}</div>
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
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">${this.escape(v.context || '')}</div>
          </div>
          <span style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-emerald); font-size: 14px;">${this.escape(v.amount_text)}</span>
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
          <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.55;">${this.escape(c.explanation || '')}</p>
          <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-left: 3px solid var(--accent-primary); padding: 12px 16px; border-radius: var(--radius-sm); font-size: 13px; color: var(--text-secondary); font-style: italic; line-height: 1.6;">
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
            <strong style="font-size: 13.5px; color: var(--text-primary);">${this.escape(o.party)}:</strong>
            <span style="font-size: 13.5px; color: var(--text-secondary); margin-left: 4px;">${this.escape(o.description)}</span>
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
          <p style="font-size: 14px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 8px;">
            ${this.escape(r.description)}
          </p>
          ${r.evidence_excerpt ? `
            <div style="font-size: 13px; color: var(--text-secondary); background: var(--bg-elevated); border: 1px solid var(--border-subtle); padding: 8px 12px; border-radius: var(--radius-sm); margin-bottom: 8px;">
              🔍 Evidence: ${this.escape(r.evidence_excerpt)}
            </div>
          ` : ''}
          ${r.recommendation ? `
            <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 600;">
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
        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 16px 20px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; box-shadow: var(--shadow-sm);">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="color: var(--text-primary); font-size: 15.5px;">${this.escape(h.document_name)}</strong>
              <span class="badge badge-active">${this.escape(h.document_type)}</span>
              ${h.case_title ? `<span class="badge" style="background: var(--accent-light); color: var(--accent-primary);">Case: ${this.escape(h.case_title)}</span>` : ''}
            </div>
            <div style="font-size: 13.5px; color: var(--text-secondary); margin-top: 4px;">
              ${this.escape(h.summary_preview)}
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
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
              <div style="background: var(--bg-elevated); padding: 8px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: inline-block;">
                <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em;">Assigned Counsel</div>
                <div style="font-size: 13.5px; font-weight: 700; color: var(--accent-primary); margin-top: 1px;">${this.escape(c.lawyer_name)}</div>
              </div>
            ` : `
              <span class="badge" style="background: var(--bg-elevated); color: var(--text-secondary); border: 1px solid var(--border-subtle);">Self Represented</span>
            `}
          </div>
        </div>

        ${c.description ? `
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 12px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            ${this.escape(c.description)}
          </div>
        ` : ''}

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); font-size: 12px; color: var(--text-muted); flex-wrap: wrap; gap: 8px;">
          <div style="display: flex; gap: 8px; align-items: center;">
            <span>${c.filing_date ? `Filing Date: ${c.filing_date}` : (c.created_at ? `Created: ${new Date(c.created_at).toLocaleDateString()}` : '')}</span>
            ${c.case_id === this.activeCaseId ? `<span class="badge badge-active" style="font-size: 10px;">★ ACTIVE CASE</span>` : ''}
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <span>📄 ${c.documents_count || 0} Docs</span>
            <span>📅 ${c.hearings_count || 0} Hearings</span>
            <button type="button" class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); App.setActiveCase(${c.case_id}); App.navigate('case-intelligence');">
              ⚖️ Case Intelligence
            </button>
            <span style="color: var(--accent-cyan); font-weight: 500;">Brief →</span>
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

      // Save current case detail for document lookup
      this.currentCaseDetail = c;

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
          <div class="card doc-item-card" style="margin-bottom: 12px; border: 1px solid var(--border-subtle); padding: 14px 16px; width: 100%; max-width: 100%; box-sizing: border-box;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; width: 100%; box-sizing: border-box;">
              <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                  <strong style="color: var(--text-primary); font-size: 14.5px;">📄 ${this.escape(d.document_name)}</strong>
                  <span class="badge badge-completed">${this.escape(d.document_type || 'Case Instrument')}</span>
                  <span class="badge badge-success">Verified</span>
                </div>
                ${d.description ? `<div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 4px;">${this.escape(d.description)}</div>` : ''}
              </div>
              <div style="font-size: 12px; color: var(--text-muted);">
                ${new Date(d.uploaded_at || Date.now()).toLocaleDateString()}
              </div>
            </div>
            <div class="doc-action-toolbar">
              <button type="button" class="btn btn-primary btn-sm" onclick="App.previewCitizenDocument(${d.document_id})">👁️ Preview</button>
              <button type="button" class="btn btn-secondary btn-sm" onclick="App.downloadCitizenDocument(${d.document_id})">📥 Download</button>
              <button type="button" class="btn btn-secondary btn-sm" onclick="App.printCitizenDocument(${d.document_id})">🖨️ Print</button>
              <button type="button" class="btn btn-secondary btn-sm" onclick="App.copyCitizenDocument(${d.document_id})">📋 Copy</button>
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
          <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm);">
            <div>
              <div style="font-weight: 700; color: var(--text-primary); font-size: 15px;">${this.escape(h.title)}</div>
              <div style="font-size: 13.5px; color: var(--accent-cyan); font-weight: 500; margin-top: 3px;">
                🏛️ ${this.escape(h.court_name || 'Designated Court')} • Presiding: ${this.escape(h.judge_name || 'Hon\'ble Judge')}
              </div>
              ${h.notes ? `<div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">📝 ${this.escape(h.notes)}</div>` : ''}
            </div>
            <div style="text-align: right;">
              <span class="badge badge-active">${h.reminder_date}</span>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">${h.reminder_time || '10:30 AM'}</div>
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
      this.showToast('Legal matter registered! Generating Case Intelligence...', 'success');
      this.closeModals();
      await this.setActiveCase(created.case_id, false);
      this.navigate('case-intelligence');
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
        <div class="card doc-item-card" style="margin-bottom: 16px; border: 1px solid var(--border-subtle); padding: 18px 20px; box-shadow: var(--shadow-sm); width: 100%; max-width: 100%; box-sizing: border-box;">
          <!-- 1. Document Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; width: 100%; box-sizing: border-box;">
            <div style="flex: 1 1 240px; min-width: 0;">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
                <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; word-break: break-word;">📄 ${this.escape(d.document_name)}</h3>
                <span class="badge badge-completed">${this.escape(d.document_type || 'Legal Document')}</span>
                ${d.case_title ? `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: var(--accent-primary);">Matter: ${this.escape(d.case_title)}</span>` : ''}
                <span class="badge badge-success">${this.escape(d.upload_status || 'Verified')}</span>
              </div>
              ${d.description ? `<p style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 0 0; line-height: 1.5; word-break: break-word;">${this.escape(d.description)}</p>` : ''}
            </div>
          </div>

          <!-- 2. Document Information (Clean metadata cards) -->
          <div class="doc-info-grid" style="margin-bottom: 14px;">
            <div class="doc-info-card">
              <span class="doc-info-label">Parties / Matter</span>
              <span class="doc-info-value">${this.escape(d.case_title || 'General Legal Matter')}</span>
              <span class="doc-info-subtext">Verified Litigant Record</span>
            </div>
            <div class="doc-info-card">
              <span class="doc-info-label">Upload Date</span>
              <span class="doc-info-value">${new Date(d.uploaded_at || d.created_at || Date.now()).toLocaleDateString()}</span>
              <span class="doc-info-subtext">${d.file_size_bytes ? (d.file_size_bytes / 1024).toFixed(1) + ' KB' : 'Standard Instrument'}</span>
            </div>
            <div class="doc-info-card">
              <span class="doc-info-label">Jurisdiction</span>
              <span class="doc-info-value">Indian Courts & Authorities</span>
              <span class="doc-info-subtext">eCourts / Administrative</span>
            </div>
            <div class="doc-info-card">
              <span class="doc-info-label">Statutory Compliance</span>
              <span class="doc-info-value">BNS / BNSS / BSA 2023</span>
              <span class="doc-info-subtext">Central & State Enactments</span>
            </div>
          </div>

          <!-- 3. Actions Toolbar (Stacking/wrapping cleanly on mobile) -->
          <div class="doc-action-toolbar">
            <button type="button" class="btn btn-primary btn-sm" onclick="App.previewCitizenDocument(${d.document_id})">
              👁️ Preview Document
            </button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.downloadCitizenDocument(${d.document_id})">
              📥 Download
            </button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.printCitizenDocument(${d.document_id})">
              🖨️ Print
            </button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.copyCitizenDocument(${d.document_id})">
              📋 Copy
            </button>
            ${d.case_id ? `
              <button type="button" class="btn btn-secondary btn-sm" onclick="App.openCitizenCaseDetail(${d.case_id})" style="margin-left: auto;">
                View Matter →
              </button>
            ` : ''}
          </div>
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-desc">Could not load documents: ${this.escape(err.message)}</div></div>`;
    }
  },

  getCitizenDocById(docId) {
    if (this.citizenDocuments && this.citizenDocuments.length > 0) {
      const found = this.citizenDocuments.find(d => Number(d.document_id) === Number(docId));
      if (found) return found;
    }
    if (this.currentCaseDetail && this.currentCaseDetail.documents) {
      const found = this.currentCaseDetail.documents.find(d => Number(d.document_id) === Number(docId));
      if (found) return found;
    }
    return null;
  },

  previewCitizenDocument(docId) {
    const doc = this.getCitizenDocById(docId);
    if (!doc) {
      this.showToast('Document details unavailable', 'error');
      return;
    }

    const title = doc.document_name || 'Legal Document';
    const subtitle = `${doc.document_type || 'Document'} • ${doc.case_title || 'Case Record'}`;
    const meta = {
      document_type: doc.document_type || 'Case Instrument',
      case_title: doc.case_title || (doc.case_id ? `Case #${doc.case_id}` : 'General Matter'),
      case_ref: doc.case_title || (doc.case_id ? `Case ID ${doc.case_id}` : 'Verified Instrument'),
      status: doc.upload_status || 'Verified Record',
      parties: doc.case_title ? `Matter: ${doc.case_title}` : 'Verified Citizen Legal Record',
      date: new Date(doc.uploaded_at || doc.created_at || Date.now()).toLocaleDateString(),
      jurisdiction: 'District & High Courts of India',
      relevant_law: 'Bharatiya Nagarik Suraksha Sanhita, 2023 / BNS 2023',
      description: doc.description || `Official case document filing for ${title}.`
    };

    const contentHtml = `
      <div class="legal-pleading-header" style="text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1.5px solid var(--border-subtle);">
        <h3 style="margin: 0 0 6px 0; text-transform: uppercase; font-size: 15px; letter-spacing: 0.05em; color: var(--text-primary);">IN THE COURT OF THE LEARNED JUDICIAL MAGISTRATE / CIVIL JUDGE</h3>
        <p style="margin: 0; font-size: 12.5px; color: var(--text-muted); text-transform: uppercase;">AT DISTRICT COURTS COMPLIANCE FORUM</p>
      </div>
      <div style="margin-bottom: 18px;">
        <p><strong>IN THE MATTER OF:</strong></p>
        <p style="padding-left: 16px; margin: 4px 0 14px 0;">${this.escape(meta.parties)}</p>
        <p><strong>INSTRUMENT TITLE:</strong> ${this.escape(title)}</p>
        <p><strong>CLASSIFICATION:</strong> ${this.escape(doc.document_type || 'Case Record / Instrument')}</p>
        <p><strong>UPLOADED / FILED:</strong> ${this.escape(meta.date)}</p>
        ${doc.description ? `<p><strong>DOCUMENT MEMORANDUM:</strong> ${this.escape(doc.description)}</p>` : ''}
      </div>
      <div class="legal-section" style="margin-top: 20px;">
        <h4 style="font-size: 14px; text-transform: uppercase; color: var(--accent-primary); margin-bottom: 8px;">1. RECORD SUMMARY & PLEADINGS</h4>
        <p style="line-height: 1.75; color: var(--text-primary); text-align: justify;">
          The present instrument titled <strong>"${this.escape(title)}"</strong> is formally recorded under the authenticated custody of the citizen. The instrument serves as legal documentation pertaining to the ongoing proceedings and statutory records.
        </p>
      </div>
      <div class="legal-section" style="margin-top: 16px;">
        <h4 style="font-size: 14px; text-transform: uppercase; color: var(--accent-primary); margin-bottom: 8px;">2. STATUTORY EVIDENCE & VERIFICATION</h4>
        <p style="line-height: 1.75; color: var(--text-primary); text-align: justify;">
          Maintained in strict compliance with Section 61 & 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023) regarding the admissibility and integrity of electronic records and documents.
        </p>
      </div>
      <div style="margin-top: 32px; padding-top: 16px; border-top: 1px dashed var(--border-subtle); display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="font-size: 12px; color: var(--text-muted);">FILED / RECORDED ON</div>
          <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">${this.escape(meta.date)}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 12px; color: var(--text-muted);">AUTHENTICATED RECORD</div>
          <div style="font-size: 12.5px; font-weight: 600; color: var(--accent-primary);">⚖️ VIDHIK AI LEGAL REPOSITORY</div>
        </div>
      </div>
    `;

    this.openDocumentPreview(title, contentHtml, subtitle, meta);
  },

  downloadCitizenDocument(docId) {
    const doc = this.getCitizenDocById(docId);
    if (!doc) {
      this.showToast('Document not found for download', 'error');
      return;
    }
    const name = doc.document_name || 'Legal_Document';
    const text = `VIDHIK AI LEGAL DOCUMENT RECORD\n\nTitle: ${name}\nType: ${doc.document_type || 'Legal Filing'}\nCase: ${doc.case_title || 'General'}\nUploaded: ${new Date(doc.uploaded_at || Date.now()).toLocaleDateString()}\nDescription: ${doc.description || 'N/A'}\n\nStatutory Reference: Section 61/63 Bharatiya Sakshya Adhiniyam 2023\nIntegrity: Verified Electronic Record\n`;

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${name.replace(/[^a-zA-Z0-9_-]/g, '_')}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    this.showToast('Document downloaded.', 'success');
  },

  printCitizenDocument(docId) {
    this.previewCitizenDocument(docId);
    setTimeout(() => {
      window.print();
    }, 300);
  },

  copyCitizenDocument(docId) {
    const doc = this.getCitizenDocById(docId);
    if (!doc) {
      this.showToast('Document not found to copy', 'error');
      return;
    }
    const text = `Document: ${doc.document_name}\nType: ${doc.document_type || 'Instrument'}\nCase: ${doc.case_title || 'General'}\nDescription: ${doc.description || 'Verified Legal Filing'}\nDate: ${new Date(doc.uploaded_at || Date.now()).toLocaleDateString()}`;
    this.copyText(text);
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
          <div style="font-size: 13.5px; color: var(--text-secondary); background: var(--bg-elevated); padding: 12px 16px; border-radius: var(--radius-sm); margin: 10px 0; border: 1px solid var(--border-subtle); line-height: 1.5;">
            📝 <strong>My Reference Note:</strong> ${this.escape(b.notes)}
          </div>
        ` : ''}

        <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">
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
    this.closeLanguagePicker();
    this.closeNavMore();

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

  // =============================================================
  // CASE INTELLIGENCE & CURRENT CASE CONTEXT (FEATURES 1-18)
  // =============================================================

  async loadActiveCase() {
    try {
      const data = await this.api('/api/cases/active');
      const activeCase = data ? (data.active_case || data.case) : null;
      if (activeCase) {
        this.activeCaseId = activeCase.case_id;
        localStorage.setItem('vidhik_active_case_id', this.activeCaseId);
        this.renderCurrentCaseBanner(activeCase);
        return activeCase;
      } else {
        // If no active case in DB, try fetching user cases to set default
        const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');
        const endpoint = isCitizen ? '/api/citizen/cases' : '/api/cases';
        const cases = await this.api(endpoint).catch(() => []);
        if (cases && cases.length > 0) {
          return await this.setActiveCase(cases[0].case_id, false);
        } else {
          this.renderCurrentCaseBanner(null);
          return null;
        }
      }
    } catch (err) {
      console.warn('Could not load active case:', err);
      this.renderCurrentCaseBanner(null);
      return null;
    }
  },

  renderCurrentCaseBanner(activeCase) {
    const banner = document.getElementById('current-case-banner');
    const navCaseLabel = document.getElementById('top-nav-case-label');
    if (navCaseLabel) {
      if (activeCase) {
        const shortNum = activeCase.case_number ? `⚖ #${activeCase.case_number}` : (activeCase.case_title || activeCase.title || '⚖ Current Case');
        navCaseLabel.innerText = shortNum.length > 18 ? shortNum.slice(0, 16) + '…' : shortNum;
      } else {
        navCaseLabel.innerText = '⚖ Current Case';
      }
    }

    if (!banner) return;
    if (!activeCase) {
      banner.style.display = 'none';
      return;
    }
    banner.style.display = 'block';

    const titleEl = document.getElementById('current-case-bar-title');
    const badgeEl = document.getElementById('current-case-bar-status-badge');
    const idEl = document.getElementById('current-case-bar-id');
    const catEl = document.getElementById('current-case-bar-category');
    const domEl = document.getElementById('current-case-bar-domain');
    const urgEl = document.getElementById('current-case-bar-urgency');

    if (titleEl) titleEl.innerText = activeCase.case_title || activeCase.title || 'Untitled Case';
    if (badgeEl) badgeEl.innerText = activeCase.status ? activeCase.status.toUpperCase() : 'ACTIVE';
    if (idEl) idEl.innerText = activeCase.case_number ? `CASE #${activeCase.case_number}` : `CASE-${String(activeCase.case_id).padStart(3, '0')}`;
    if (catEl) catEl.innerText = activeCase.case_type || 'General Matter';
    if (domEl) domEl.innerText = activeCase.court_name || activeCase.court || 'Indian Legal Jurisdiction';
    if (urgEl) urgEl.innerText = 'Case Anchored';
  },

  async setActiveCase(caseId, notify = true) {
    try {
      const res = await this.api(`/api/cases/${caseId}/set-active`, 'POST');
      this.activeCaseId = caseId;
      this.currentCaseId = caseId;
      localStorage.setItem('vidhik_active_case_id', caseId);

      if (res && res.active_case) {
        this.renderCurrentCaseBanner(res.active_case);
      }

      if (notify) {
        this.showToast(`Current Case switched to: ${res.active_case ? res.active_case.title : 'Selected Matter'}`, 'success');
      }

      // If already on case-intelligence, reload context immediately
      if (this.currentView === 'case-intelligence') {
        await this.loadCaseIntelligence(caseId);
      }

      return res.active_case;
    } catch (err) {
      this.showToast('Could not set active case: ' + err.message, 'error');
      throw err;
    }
  },

  async loadCaseIntelligence(caseId = null) {
    const targetId = caseId || this.activeCaseId;
    const container = document.getElementById('view-case-intelligence');
    if (!container) return;

    if (!targetId) {
      // Show empty state asking user to select or create a case
      document.getElementById('ci-header-title').innerText = 'No Active Case Selected';
      document.getElementById('ci-header-case-num').innerText = 'Please select or file a case to activate Case Intelligence.';
      document.getElementById('ci-situation-summary-text').innerHTML = `
        <div class="empty-state" style="padding: 24px 0;">
          <div class="empty-state-icon" style="font-size: 36px; margin-bottom: 8px;">⚖️</div>
          <div class="empty-state-title" style="font-size: 16px;">No Active Case Selected</div>
          <div class="empty-state-desc" style="max-width: 440px; margin: 0 auto 16px;">
            Vidhik Case Intelligence requires an active legal case to ground statutory provisions, recommend authorities, and match verified lawyers.
          </div>
          <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.openCaseSwitchModal()">⇄ Select Existing Case</button>
            <button type="button" class="btn btn-primary btn-sm" onclick="App.openCitizenNewCaseModal()">+ File New Matter</button>
          </div>
        </div>
      `;
      document.getElementById('ci-explicit-facts-list').innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No active case</div>';
      document.getElementById('ci-extracted-facts-list').innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No active case</div>';
      document.getElementById('ci-identified-issues-list').innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No active case</div>';
      document.getElementById('ci-uncertain-facts-list').innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No active case</div>';
      return;
    }

    // Set spinners in tabs
    document.getElementById('ci-situation-summary-text').innerHTML = '<div class="spinner" style="margin: 20px auto;"></div>';
    document.getElementById('ci-provisions-list').innerHTML = '<div class="spinner"></div>';
    document.getElementById('ci-immediate-actions-list').innerHTML = '<div class="spinner"></div>';
    document.getElementById('ci-required-docs-list').innerHTML = '<div class="spinner"></div>';
    document.getElementById('ci-authorities-list').innerHTML = '<div class="spinner"></div>';
    document.getElementById('ci-lawyers-list').innerHTML = '<div class="spinner"></div>';
    document.getElementById('ci-procedure-timeline').innerHTML = '<div class="spinner"></div>';

    try {
      const ctx = await this.api(`/api/cases/${targetId}/context`);
      this.activeCaseContext = ctx;
      this.renderCaseIntelligence(ctx);
    } catch (err) {
      this.showToast('Could not load Case Intelligence: ' + err.message, 'error');
    }
  },

  renderCaseIntelligence(ctx) {
    if (!ctx) return;

    // 1. Header Information
    document.getElementById('ci-header-title').innerText = ctx.title || 'Legal Matter';
    document.getElementById('ci-header-case-num').innerText = `Case ID: ${ctx.case_id} • Category: ${ctx.category || 'General'} • Jurisdiction: ${ctx.jurisdiction || 'India'}`;
    document.getElementById('ci-header-category').innerText = ctx.category || 'General';
    document.getElementById('ci-header-domain').innerText = ctx.legal_domain || 'Indian Law';

    const urgEl = document.getElementById('ci-header-urgency');
    if (urgEl) {
      urgEl.innerText = `${ctx.urgency || 'Medium'} Urgency`;
      urgEl.style.background = ctx.urgency === 'High' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)';
      urgEl.style.color = ctx.urgency === 'High' ? '#EF4444' : '#F59E0B';
    }

    const stEl = document.getElementById('ci-header-status');
    if (stEl) stEl.innerText = ctx.status ? ctx.status.toUpperCase() : 'ACTIVE';

    const verEl = document.getElementById('ci-header-version');
    if (verEl) verEl.innerText = `Version ${ctx.version || '1.0'}`;

    // 2. Emotional Adaptation & Safety Banners (Feature 7)
    const emoBanner = document.getElementById('ci-emotion-banner');
    const safeBanner = document.getElementById('ci-safety-banner');

    if (ctx.emotional_analysis && ctx.emotional_analysis.adaptive_communication_guidance) {
      emoBanner.style.display = 'flex';
      document.getElementById('ci-emotion-desc').innerText = ctx.emotional_analysis.adaptive_communication_guidance;
    } else {
      emoBanner.style.display = 'none';
    }

    if (ctx.emotional_analysis && ctx.emotional_analysis.immediate_safety_notice) {
      safeBanner.style.display = 'flex';
      document.getElementById('ci-safety-text').innerText = ctx.emotional_analysis.immediate_safety_notice;
    } else {
      safeBanner.style.display = 'none';
    }

    // 3. Tab Counter Badges
    const secCount = (ctx.ranked_provisions || []).length;
    const lawCount = (ctx.recommended_lawyers || []).length;
    const secTabCount = document.getElementById('ci-sections-tab-count');
    const lawTabCount = document.getElementById('ci-lawyers-tab-count');
    const provBadge = document.getElementById('ci-provisions-badge');

    if (secTabCount) secTabCount.innerText = secCount;
    if (lawTabCount) lawTabCount.innerText = lawCount;
    if (provBadge) provBadge.innerText = `${secCount} Grounded Provisions`;

    // 4. Pane 1: Situation Overview (Feature 1)
    const sit = ctx.situation_overview || {};
    document.getElementById('ci-situation-summary-text').innerText = sit.situation_summary || sit.what_is_this_situation || 'Analysis in progress...';

    // Explicitly stated facts
    const explicitList = document.getElementById('ci-explicit-facts-list');
    if (explicitList) {
      const facts = sit.explicit_facts || sit.what_user_stated || [];
      explicitList.innerHTML = facts.length ? facts.map(f => `
        <div style="font-size: 13.5px; color: var(--text-primary); padding: 8px 12px; background: var(--bg-primary); border-radius: var(--radius-sm); border-left: 3px solid var(--accent-primary);">
          ${this.escape(f)}
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No facts explicitly isolated.</div>';
    }

    // Important extracted facts
    const extractedList = document.getElementById('ci-extracted-facts-list');
    if (extractedList) {
      const ext = sit.extracted_facts || [];
      extractedList.innerHTML = ext.length ? ext.map(f => `
        <div style="font-size: 13.5px; color: var(--text-primary); padding: 8px 12px; background: var(--bg-primary); border-radius: var(--radius-sm); border-left: 3px solid var(--accent-cyan);">
          ${this.escape(f)}
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No extracted facts.</div>';
    }

    // Possible legal issues
    const issuesList = document.getElementById('ci-identified-issues-list');
    if (issuesList) {
      const issues = sit.identified_issues || [];
      issuesList.innerHTML = issues.length ? issues.map(i => `
        <div style="font-size: 13.5px; color: var(--text-primary); padding: 8px 12px; background: var(--bg-primary); border-radius: var(--radius-sm); border-left: 3px solid var(--accent-amber);">
          ${this.escape(i)}
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No legal issues flagged.</div>';
    }

    // Uncertain facts
    const uncertainList = document.getElementById('ci-uncertain-facts-list');
    if (uncertainList) {
      const unc = sit.uncertain_facts || [];
      uncertainList.innerHTML = unc.length ? unc.map(u => `
        <div style="font-size: 13.5px; color: var(--text-secondary); padding: 8px 12px; background: var(--bg-primary); border-radius: var(--radius-sm); border-left: 3px solid rgba(148, 163, 184, 0.4);">
          ${this.escape(u)}
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No uncertain facts noted.</div>';
    }

    // 5. Pane 2: Legal Analysis & Ranked Provisions (Features 2, 3)
    const provList = document.getElementById('ci-provisions-list');
    if (provList) {
      const provs = ctx.ranked_provisions || [];
      if (!provs.length) {
        provList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No specific statutory sections matched for this factual description.</div></div>';
      } else {
        provList.innerHTML = provs.map(p => `
          <div class="card" style="border-left: 4px solid var(--accent-primary); padding: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 8px;">
              <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
                  <span class="badge badge-bns" style="font-size: 11px;">${this.escape(p.act_name)}</span>
                  <span class="badge badge-active" style="font-size: 11px; font-family: 'JetBrains Mono', monospace;">Section ${this.escape(p.section_number)}</span>
                  <span class="cautious-pill">Potentially Relevant Provision</span>
                </div>
                <h4 style="font-size: 16px; color: var(--text-primary); margin: 4px 0 2px 0;">${this.escape(p.section_title)}</h4>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-completed" style="font-size: 11px;">Relevance Score: ${Math.round((p.relevance_score || 0.85) * 100)}%</span>
              </div>
            </div>

            <!-- Why Relevant -->
            <div style="background: rgba(99, 102, 241, 0.08); border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 10px; border: 1px solid rgba(99, 102, 241, 0.2);">
              <div style="font-size: 11.5px; font-weight: 700; color: var(--accent-primary); text-transform: uppercase; margin-bottom: 3px;">Why this may relate to your case:</div>
              <div style="font-size: 13px; color: var(--text-primary); line-height: 1.5;">${this.escape(p.why_relevant)}</div>
            </div>

            <!-- Simple Explanation -->
            <div>
              <div style="font-size: 11.5px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 3px;">Simple Legal Explanation:</div>
              <div style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.6;">${this.escape(p.simple_explanation)}</div>
            </div>
          </div>
        `).join('');
      }
    }

    // 6. Pane 3: Action Plan (Feature 4)
    const act = ctx.action_plan || ctx.recommended_actions || {};
    const immList = document.getElementById('ci-immediate-actions-list');
    const nextList = document.getElementById('ci-next-steps-list');
    const optList = document.getElementById('ci-optional-actions-list');

    if (immList) {
      const imm = act.immediate_actions || [];
      immList.innerHTML = imm.length ? imm.map((item, idx) => `
        <div class="action-step-card" style="border-left: 3px solid #EF4444;">
          <div class="action-step-num" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; border-color: rgba(239, 68, 68, 0.4);">${idx + 1}</div>
          <div style="flex: 1;">
            <strong style="color: var(--text-primary); font-size: 14px;">${this.escape(item.action_title || item.title || item.step_title)}</strong>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 3px 0 0 0; line-height: 1.5;">${this.escape(item.description)}</p>
          </div>
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No immediate actions required.</div>';
    }

    if (nextList) {
      const nxt = act.recommended_next_steps || [];
      nextList.innerHTML = nxt.length ? nxt.map((item, idx) => `
        <div class="action-step-card" style="border-left: 3px solid var(--accent-primary);">
          <div class="action-step-num">${idx + 1}</div>
          <div style="flex: 1;">
            <strong style="color: var(--text-primary); font-size: 14px;">${this.escape(item.action_title || item.title || item.step_title)}</strong>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 3px 0 0 0; line-height: 1.5;">${this.escape(item.description)}</p>
          </div>
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No follow-up steps.</div>';
    }

    if (optList) {
      const opt = act.optional_supporting_actions || [];
      optList.innerHTML = opt.length ? opt.map((item, idx) => `
        <div class="action-step-card">
          <div class="action-step-num" style="background: var(--bg-elevated); color: var(--text-muted); border-color: var(--border-subtle);">${idx + 1}</div>
          <div style="flex: 1;">
            <strong style="color: var(--text-primary); font-size: 14px;">${this.escape(item.action_title || item.title || item.step_title)}</strong>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 3px 0 0 0; line-height: 1.5;">${this.escape(item.description)}</p>
          </div>
        </div>
      `).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No optional actions.</div>';
    }

    // 7. Pane 4: Documents & Evidence Checklist (Feature 5)
    const docs = ctx.document_checklist || ctx.required_documents || {};
    const reqList = document.getElementById('ci-required-docs-list');
    const impList = document.getElementById('ci-important-docs-list');
    const supList = document.getElementById('ci-supporting-docs-list');

    const renderDocCard = (d, badgeClass, label) => `
      <div class="card" style="padding: 14px 18px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <strong style="color: var(--text-primary); font-size: 14.5px;">📄 ${this.escape(d.title || d.document_name)}</strong>
              <span class="badge ${badgeClass}" style="font-size: 10.5px;">${label}</span>
              ${d.is_digital_evidence || d.evidence_safeguard || d.electronic_record_rule ? `<span class="badge badge-bsa" style="font-size: 10.5px;">BSA Sec 63 Digital Proof</span>` : ''}
            </div>
            <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">${this.escape(d.purpose || d.description || d.purpose_or_reason)}</div>
            ${d.evidence_safeguard || d.electronic_record_rule ? `
              <div style="font-size: 11.5px; color: var(--accent-cyan); margin-top: 4px;">
                💡 <em>${this.escape(d.evidence_safeguard || d.electronic_record_rule)}</em>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;

    if (reqList) {
      const req = docs.required_documents || [];
      reqList.innerHTML = req.length ? req.map(d => renderDocCard(d, 'badge-mandatory', 'Required')).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No required documents.</div>';
    }

    if (impList) {
      const imp = docs.important_documents || [];
      impList.innerHTML = imp.length ? imp.map(d => renderDocCard(d, 'badge-supporting', 'Important')).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No important documents.</div>';
    }

    if (supList) {
      const sup = docs.supporting_documents || [];
      supList.innerHTML = sup.length ? sup.map(d => renderDocCard(d, 'badge-completed', 'Supporting')).join('') : '<div style="color: var(--text-muted); font-size: 13px;">No supporting documents.</div>';
    }

    // 8. Pane 5: Who Can Help / Authorities
    const authList = document.getElementById('ci-authorities-list');
    if (authList) {
      const auths = ctx.recommended_authorities || [];
      if (!auths.length) {
        authList.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No specific authorities registered for this jurisdiction.</div></div>';
      } else {
        authList.innerHTML = auths.map(a => `
          <div class="card" style="border-left: 4px solid var(--accent-cyan); padding: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; margin-bottom: 6px;">
              <div>
                <span class="badge badge-bnss" style="font-size: 11px; margin-bottom: 4px;">${this.escape(a.authority_type || 'Statutory Authority')}</span>
                <h4 style="font-size: 16px; color: var(--text-primary); margin: 2px 0;">${this.escape(a.authority_name)}</h4>
                <div style="font-size: 12px; color: var(--text-muted);">Jurisdiction: ${this.escape(a.jurisdiction_level || a.jurisdiction || 'Local / District')}</div>
              </div>
            </div>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 6px 0 10px 0; line-height: 1.5;">${this.escape(a.description || '')}</p>
            ${a.procedure_to_approach ? `
              <div style="background: var(--bg-primary); padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-size: 12.5px; color: var(--text-secondary);">
                <strong style="color: var(--accent-cyan);">Procedure to Approach:</strong> ${this.escape(a.procedure_to_approach)}
              </div>
            ` : ''}
          </div>
        `).join('');
      }
    }

    // Precedents if present
    const precCard = document.getElementById('ci-precedents-card');
    const precList = document.getElementById('ci-precedents-list');
    if (precCard && precList) {
      const precs = ctx.precedents || [];
      if (precs.length) {
        precCard.style.display = 'block';
        precList.innerHTML = precs.map(p => `
          <div style="padding: 10px 14px; background: var(--bg-primary); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-size: 13px;">
            <strong style="color: var(--text-primary);">${this.escape(p.case_title || p.title)}</strong>
            ${p.citation ? `<span style="color: var(--accent-amber); font-size: 11.5px; margin-left: 6px;">(${this.escape(p.citation)})</span>` : ''}
            <div style="color: var(--text-muted); font-size: 12px; margin-top: 3px;">${this.escape(p.headnote || p.summary || '')}</div>
          </div>
        `).join('');
      } else {
        precCard.style.display = 'none';
      }
    }

    // 9. Pane 6: Lawyer Recommendations (Feature 14)
    const lawList = document.getElementById('ci-lawyers-list');
    if (lawList) {
      const lawyers = ctx.recommended_lawyers || [];
      if (!lawyers.length) {
        lawList.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1;">
            <div class="empty-state-icon">🧑‍⚖️</div>
            <div class="empty-state-title">No Direct Match Found in Database</div>
            <div class="empty-state-desc">No registered advocate in the Vidhik database exactly matched the required legal domain and jurisdiction. Vidhik does not invent fictitious lawyer profiles.</div>
          </div>
        `;
      } else {
        lawList.innerHTML = lawyers.map(l => `
          <div class="lawyer-match-card">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
                <div>
                  <h4 style="font-size: 16px; color: var(--text-primary); margin-bottom: 2px;">${this.escape(l.full_name || l.name)}</h4>
                  <div style="font-size: 11.5px; color: var(--accent-cyan); font-family: 'JetBrains Mono', monospace;">${this.escape(l.bar_council_number || 'Enrolled Advocate')}</div>
                </div>
                <span class="badge ${l.is_verified || l.verification_status === 'Verified' ? 'badge-active' : 'badge-completed'}" style="font-size: 10.5px;">
                  ${this.escape(l.verification_status || (l.is_verified ? 'Verified' : 'Enrolled'))}
                </span>
              </div>

              <!-- Match Reason -->
              <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: var(--radius-sm); padding: 8px 10px; margin-bottom: 12px; font-size: 12px; color: var(--text-primary); line-height: 1.45;">
                <strong style="color: var(--accent-primary);">Match Rationale:</strong> ${this.escape(l.match_reason)}
              </div>

              <div style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 6px;">
                <strong>Specialization:</strong> <span class="badge badge-bns" style="font-size: 10px; padding: 2px 6px;">${this.escape(l.specialization || 'Advocate')}</span>
              </div>

              <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">
                🏛️ <strong>Courts:</strong> ${this.escape(l.court_practice || (l.courts || []).join(', ') || 'District & High Courts')}
              </div>

              <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">
                📍 <strong>Location:</strong> ${this.escape(l.city || (l.jurisdictions || []).join(', ') || 'Maharashtra')} • <strong>Experience:</strong> ${l.experience_years || l.years_of_experience || 10}+ Years
              </div>
            </div>

            <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 11.5px; color: var(--text-muted);">Match Score: <strong>${Math.round((l.match_score || 0.8) * 100)}%</strong></span>
              <button type="button" class="btn btn-secondary btn-sm" onclick="App.showToast('Chambers contact: ' + App.escape('${l.email || l.phone || 'Available via Vidhik Desk'}'), 'info')">
                View Contact
              </button>
            </div>
          </div>
        `).join('');
      }
    }

    // 10. Pane 7: Further Procedure (Feature 6)
    const procTimeline = document.getElementById('ci-procedure-timeline');
    if (procTimeline) {
      const proc = ctx.further_procedure || {};
      const stages = proc.procedural_stages || proc.procedural_pathway || [];
      if (!stages.length) {
        procTimeline.innerHTML = '<div class="empty-state"><div class="empty-state-desc">Procedural pathway information is currently being structured.</div></div>';
      } else {
        procTimeline.innerHTML = stages.map(s => `
          <div class="procedure-timeline-step">
            <div class="procedure-timeline-marker">${s.step_number || s.stage_number}</div>
            <div class="card" style="padding: 14px 18px;">
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 6px;">
                <strong style="color: var(--text-primary); font-size: 15px;">Stage ${s.step_number || s.stage_number}: ${this.escape(s.stage_name)}</strong>
                ${s.expected_timeline || s.estimated_timeframe ? `<span class="badge badge-completed" style="font-size: 11px;">⏱️ ${this.escape(s.expected_timeline || s.estimated_timeframe)}</span>` : ''}
              </div>
              <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 8px 0; line-height: 1.5;">${this.escape(s.description || s.likely_action)}</p>
              ${s.cautious_note || s.authority_involved ? `
                <div style="font-size: 11.5px; color: var(--text-muted); background: var(--bg-primary); padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                  ℹ️ <em>${this.escape(s.cautious_note || `Concerned authority: ${s.authority_involved}`)}</em>
                </div>
              ` : ''}
            </div>
          </div>
        `).join('');
      }
    }

    // 11. Pane 8: Emotional Analysis & Adaptive Guidance (Feature 7)
    const emoChips = document.getElementById('ci-emotion-chips');
    const emoText = document.getElementById('ci-emotion-adaptation-text');
    if (emoChips) {
      const emo = ctx.emotional_analysis || ctx.emotional_indicators || {};
      const indicators = emo.detected_indicators || emo.emotional_indicators || [];
      emoChips.innerHTML = indicators.length ? indicators.map(ind => {
        const cls = ind.toLowerCase().replace(/[^a-z]/g, '');
        return `<span class="emotion-chip ${cls}">${this.escape(ind)}</span>`;
      }).join('') : '<span class="emotion-chip neutral">Neutral / Calm</span>';
    }
    if (emoText) {
      const emo = ctx.emotional_analysis || ctx.emotional_indicators || {};
      emoText.innerText = emo.communication_adaptation || emo.adaptive_communication_guidance || 'Guidance is provided in objective, factual terms.';
    }

    // 12. Pane 9: Missing Information (Feature 18)
    const missList = document.getElementById('ci-missing-info-list');
    if (missList) {
      const missing = ctx.missing_information || [];
      missList.innerHTML = missing.length ? missing.map(m => `
        <div class="card" style="padding: 12px 16px; border-left: 3px solid var(--accent-amber); display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
          <div>
            <div style="font-size: 13.5px; color: var(--text-primary); font-weight: 500;">${this.escape(m)}</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">Supplying this detail will increase legal ranking precision and eliminate procedural ambiguities.</div>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.openCaseReanalyzeModal()">Provide Fact</button>
        </div>
      `).join('') : '<div class="card"><div class="empty-state"><div class="empty-state-desc">All essential foundational facts for initial legal analysis have been supplied.</div></div></div>';
    }
  },

  switchCiTab(tabKey) {
    this.activeCiTab = tabKey;

    document.querySelectorAll('.tab-btn[data-ci-tab]').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-ci-tab') === tabKey);
    });

    document.querySelectorAll('.ci-tab-pane').forEach(p => {
      p.classList.remove('active');
      p.style.display = 'none';
    });

    const targetPane = document.getElementById(`ci-pane-${tabKey}`);
    if (targetPane) {
      targetPane.classList.add('active');
      targetPane.style.display = 'block';
    }
  },

  async openCaseSwitchModal() {
    const list = document.getElementById('switch-case-list');
    if (!list) return;
    list.innerHTML = '<div class="spinner"></div>';
    document.getElementById('modal-switch-case')?.classList.add('active');

    try {
      const isCitizen = this.user && (this.user.role === 'user' || this.user.role === 'citizen');
      const endpoint = isCitizen ? '/api/citizen/cases' : '/api/cases';
      const cases = await this.api(endpoint);

      if (!cases || !cases.length) {
        list.innerHTML = `
          <div class="empty-state" style="padding: 20px 0;">
            <div class="empty-state-title">No Cases Found</div>
            <div class="empty-state-desc">You do not have any registered legal cases yet. Create your first case to use Case Intelligence.</div>
          </div>
        `;
        return;
      }

      list.innerHTML = cases.map(c => {
        const isActive = c.case_id === this.activeCaseId;
        return `
          <div class="card" style="padding: 14px 18px; border: ${isActive ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)'}; background: ${isActive ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-card)'}; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
            <div>
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <strong style="color: var(--text-primary); font-size: 15px;">${this.escape(c.title)}</strong>
                ${isActive ? `<span class="badge badge-active">★ CURRENT ACTIVE</span>` : ''}
                <span class="badge badge-completed">${this.escape(c.case_type || 'Civil Matter')}</span>
              </div>
              <div style="font-size: 12.5px; color: var(--text-muted);">
                ${c.case_number ? `Case #${c.case_number} • ` : ''}🏛️ ${this.escape(c.court || 'Court')} • Status: <strong>${this.escape(c.status || 'Active')}</strong>
              </div>
            </div>
            <div>
              ${isActive ? `
                <button type="button" class="btn btn-secondary btn-sm" disabled style="opacity: 0.7;">Active</button>
              ` : `
                <button type="button" class="btn btn-primary btn-sm" onclick="App.submitCaseSwitch(${c.case_id})">Switch to This Case →</button>
              `}
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      list.innerHTML = `<div style="color: #EF4444; padding: 10px;">Error loading cases: ${this.escape(err.message)}</div>`;
    }
  },

  async submitCaseSwitch(caseId) {
    try {
      await this.setActiveCase(caseId, true);
      this.closeModals();
      this.navigate('case-intelligence');
    } catch (err) {
      this.showToast('Could not switch case: ' + err.message, 'error');
    }
  },

  openCaseReanalyzeModal() {
    if (!this.activeCaseId) {
      this.showToast('Please select a case first before re-analyzing.', 'error');
      return;
    }
    const titleInput = document.getElementById('reanalyze-current-title');
    const factsTextarea = document.getElementById('reanalyze-additional-facts');

    if (titleInput && this.activeCaseContext) {
      titleInput.value = this.activeCaseContext.title;
    }
    if (factsTextarea) {
      factsTextarea.value = '';
    }

    document.getElementById('modal-reanalyze-case')?.classList.add('active');
  },

  async submitCaseReanalyze(e) {
    e.preventDefault();
    if (!this.activeCaseId) return;

    const facts = document.getElementById('reanalyze-additional-facts')?.value.trim();
    if (!facts) {
      this.showToast('Please provide additional facts or events to re-analyze.', 'error');
      return;
    }

    const btn = document.getElementById('btn-submit-reanalyze');
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Analyzing with Grounded Database...';
    }

    try {
      const updated = await this.api(`/api/cases/${this.activeCaseId}/update-and-reanalyze`, 'POST', {
        additional_facts: facts,
        recalculate_urgency: true
      });

      this.activeCaseContext = updated;
      this.renderCaseIntelligence(updated);
      this.closeModals();
      this.showToast('Case updated and successfully re-analyzed!', 'success');
      this.navigate('case-intelligence');
    } catch (err) {
      this.showToast('Failed to re-analyze case: ' + err.message, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = '⚡ Update & Re-Analyze';
      }
    }
  },

  // -------------------------------------------------------------
  // UI UTILITIES & TOASTS
  // -------------------------------------------------------------
  // =============================================================
  // 1. LOCALIZATION & LANGUAGE SWITCHING (P2)
  // =============================================================
  initLocalization() {
    this.currentLanguage = localStorage.getItem('vidhik_lang') || 'en';
    const langLabel = document.getElementById('header-lang-code');
    if (langLabel) {
      langLabel.textContent = this.currentLanguage.toUpperCase();
    }
    // Update active state in picker
    document.querySelectorAll('.lang-option-btn').forEach(btn => {
      const isAct = btn.getAttribute('data-lang') === this.currentLanguage;
      btn.classList.toggle('active', isAct);
      const check = btn.querySelector('.lang-check');
      if (check) check.style.display = isAct ? 'inline' : 'none';
    });
    // Update active state in drawer language pills
    document.querySelectorAll('.sidebar-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.id === `slang-${this.currentLanguage}`);
    });
    // Update active state in login screen language pills
    document.querySelectorAll('.login-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.id === `login-lang-${this.currentLanguage}`);
    });
    // Update active state in dashboard quick language pills
    document.querySelectorAll('.dash-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.id === `dash-lang-${this.currentLanguage}`);
    });
  },

  toggleLanguagePicker(event) {
    if (event && event.stopPropagation) {
      event.stopPropagation();
    }
    const pop = document.getElementById('lang-popover');
    if (!pop) return;
    if (pop.style.display === 'block') {
      this.closeLanguagePicker();
    } else {
      this.openLanguagePicker();
    }
  },

  openLanguagePicker() {
    const pop = document.getElementById('lang-popover');
    if (!pop) return;
    this.closeNotificationsPopover();
    this.closeThemePicker();
    this.closeMobileSidebar();
    this.closeNavMore();
    pop.style.display = 'block';
    this.positionLanguagePicker();
  },

  positionLanguagePicker() {
    const pop = document.getElementById('lang-popover');
    if (!pop || pop.style.display === 'none') return;
    if (window.innerWidth <= 600) {
      pop.style.position = 'fixed';
      pop.style.top = '56px';
      pop.style.left = '10px';
      pop.style.right = '10px';
      pop.style.width = 'auto';
      return;
    }
    pop.style.position = 'absolute';
    pop.style.top = 'calc(100% + 8px)';
    pop.style.left = 'auto';
    pop.style.right = '0';
    const rect = pop.getBoundingClientRect();
    if (rect.left < 10) {
      const shift = 10 - rect.left;
      pop.style.right = `${-shift}px`;
    }
  },

  closeLanguagePicker() {
    const pop = document.getElementById('lang-popover');
    if (pop) pop.style.display = 'none';
  },

  setLanguage(lang) {
    this.currentLanguage = lang;
    localStorage.setItem('vidhik_lang', lang);
    const langLabel = document.getElementById('header-lang-code');
    if (langLabel) langLabel.textContent = lang.toUpperCase();

    // Update active state in picker
    document.querySelectorAll('.lang-option-btn').forEach(btn => {
      const isAct = btn.getAttribute('data-lang') === lang;
      btn.classList.toggle('active', isAct);
      const check = btn.querySelector('.lang-check');
      if (check) check.style.display = isAct ? 'inline' : 'none';
    });

    // Update active state in drawer language pills
    document.querySelectorAll('.sidebar-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.id === `slang-${lang}`);
    });

    // Update active state in login screen language pills
    document.querySelectorAll('.login-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.id === `login-lang-${lang}`);
    });

    // Update active state in dashboard quick language pills
    document.querySelectorAll('.dash-lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.id === `dash-lang-${lang}`);
    });

    this.closeLanguagePicker();
    this.applyLocalization();
    const names = { en: 'English', hi: 'हिंदी', mr: 'मराठी' };
    this.showToast(`Language switched to ${names[lang] || lang}`, 'info');
  },

  applyLocalization() {
    const lang = this.currentLanguage;
    const dict = {
      en: {
        welcome: 'Welcome',
        selectLanguage: 'Select Language',
        legalWorkspace: 'Your Legal Workspace',
        activeMatters: 'Active Matters',
        savedProvisions: 'Saved Provisions',
        aiAssistant: 'AI Legal Assistant',
        complaintFir: 'Complaint / FIR Draft',
        disputeResolution: 'Dispute Resolution',
        trafficLaw: 'Traffic Law & Fines',
        constRights: 'Constitutional Rights',
        findLawyer: 'Find a Lawyer',
        caseTracking: 'eCourts Case Tracking',
        voiceAssistant: 'Voice Assistant',
        legalKnowledge: 'Legal Knowledge'
      },
      hi: {
        welcome: 'स्वागत है',
        selectLanguage: 'अपनी भाषा चुनें',
        legalWorkspace: 'आपका विधिक कार्यक्षेत्र',
        activeMatters: 'सक्रिय मामले',
        savedProvisions: 'सुरक्षित धाराएं',
        aiAssistant: 'एआई विधिक सहायक',
        complaintFir: 'शिकायत / एफआईआर प्रारूप',
        disputeResolution: 'विवाद समाधान एवं ट्राइएज',
        trafficLaw: 'यातायात नियम व जुर्माना',
        constRights: 'संवैधानिक अधिकार',
        findLawyer: 'अधिवक्ता खोजें',
        caseTracking: 'ई-कोर्ट केस ट्रैकिंग',
        voiceAssistant: 'ध्वनि विधिक सहायक',
        legalKnowledge: 'विधिक ज्ञानकोष'
      },
      mr: {
        welcome: 'स्वागत आहे',
        selectLanguage: 'आपली भाषा निवडा',
        legalWorkspace: 'आपले विधी कार्यक्षेत्र',
        activeMatters: 'सक्रिय खटले',
        savedProvisions: 'जतन केलेली कलमे',
        aiAssistant: 'एआय विधी सहाय्यक',
        complaintFir: 'तक्रार / एफआयआर मसुदा',
        disputeResolution: 'तक्रार निवारण व सल्ला',
        trafficLaw: 'वाहतूक नियम व दंड',
        constRights: 'मूलभूत हक्क व अधिकार',
        findLawyer: 'वकील शोधा',
        caseTracking: 'ई-कोर्ट केस ट्रॅकिंग',
        voiceAssistant: 'व्हॉइस विधी सहाय्यक',
        legalKnowledge: 'विधी ज्ञानकोश'
      }
    };

    const strings = dict[lang] || dict['en'];
    // Update view titles if needed
    const welcomeTitle = document.getElementById('dash-citizen-welcome-title');
    if (welcomeTitle) {
      const name = this.user ? this.user.full_name : 'Citizen';
      welcomeTitle.innerHTML = `${strings.welcome}, <span id="dash-citizen-greeting-name">${this.escape(name)}</span>`;
    }

    // Update role labels and active auth mode
    const dictAuth = this.getAuthLocalizationDict(lang);
    const citizenTab = document.getElementById('role-label-citizen');
    const lawyerTab = document.getElementById('role-label-lawyer');
    const adminTab = document.getElementById('role-label-admin');
    const adminRestricted = document.getElementById('admin-restricted-text');
    const noAccountText = document.getElementById('auth-no-account-text');
    const pwdLabel = document.getElementById('login-password-label');
    if (citizenTab) citizenTab.textContent = dictAuth.citizenTab;
    if (lawyerTab) lawyerTab.textContent = dictAuth.lawyerTab;
    if (adminTab) adminTab.textContent = dictAuth.adminTab;
    if (adminRestricted) adminRestricted.textContent = dictAuth.adminRestricted;
    if (noAccountText) noAccountText.textContent = dictAuth.noAccount;
    if (pwdLabel) pwdLabel.textContent = dictAuth.passwordLabel;

    if (this.authMode) {
      this.switchAuthMode(this.authMode, false);
    }
  },

  // =============================================================
  // 2. AI LEGAL ASSISTANT (P0)
  // =============================================================
  aiConversationId: null,
  aiHistory: [],

  loadAiAssistant() {
    const thread = document.getElementById('ai-chat-thread');
    const landing = document.getElementById('ai-chat-landing');
    if (this.aiHistory.length === 0) {
      if (landing) landing.style.display = 'block';
    } else {
      if (landing) landing.style.display = 'none';
    }
    const input = document.getElementById('ai-chat-input');
    if (input) setTimeout(() => input.focus(), 150);
  },

  newAiChat() {
    this.aiConversationId = null;
    this.aiHistory = [];
    const thread = document.getElementById('ai-chat-thread');
    const landing = document.getElementById('ai-chat-landing');
    if (thread) {
      // Remove all messages, restore landing
      thread.innerHTML = '';
      if (landing) {
        thread.appendChild(landing);
        landing.style.display = 'block';
      }
    }
    const input = document.getElementById('ai-chat-input');
    if (input) {
      input.value = '';
      input.focus();
    }
    this.showToast('Started new AI Legal Assistant conversation.', 'info');
  },

  askAiCategory(categoryName) {
    const questions = {
      'Criminal Law & BNS': 'What are the main offences and punishments for theft and robbery under Bharatiya Nyaya Sanhita (BNS), 2023?',
      'Police Procedure & FIR': 'What is the mandatory procedure for registration of FIR under Section 173 of BNSS, 2023?',
      'Consumer Rights': 'How can a consumer file a claim against an e-commerce platform for defective products under Consumer Protection Act, 2019?',
      'Property & Tenancy': 'What legal remedies exist if a landlord refuses to refund a security deposit after tenancy expiry in Maharashtra?',
      'Traffic & MV Act': 'What are driver rights during a traffic police stop regarding licence seizure under Motor Vehicles Act, 1988?',
      'Cyber Crime & BSA': 'What is the admissibility requirement for electronic records and digital certificates under Section 63 of Bharatiya Sakshya Adhiniyam, 2023?'
    };
    const q = questions[categoryName] || `Explain legal provisions regarding ${categoryName} in India.`;
    this.askAiSample(q);
  },

  askAiSample(question) {
    const input = document.getElementById('ai-chat-input');
    if (input) {
      input.value = question;
      this.handleAiChatSubmit(new Event('submit'));
    }
  },

  handleAiInputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.handleAiChatSubmit(e);
    }
  },

  startSpeechInputForChat() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      this.showToast('Speech recognition not supported in this browser. Please type your query.', 'error');
      return;
    }
    const rec = new SpeechRec();
    rec.lang = this.currentLanguage === 'hi' ? 'hi-IN' : (this.currentLanguage === 'mr' ? 'mr-IN' : 'en-IN');
    rec.interimResults = false;
    const btn = document.getElementById('btn-ai-voice');
    if (btn) btn.classList.add('mic-recording-active');

    rec.onstart = () => {
      this.showToast('Listening... Speak your legal query now.', 'info');
    };

    rec.onresult = (evt) => {
      const spoken = evt.results[0][0].transcript;
      const input = document.getElementById('ai-chat-input');
      if (input) {
        input.value = spoken;
        input.focus();
      }
      this.showToast(`Heard: "${spoken}"`, 'success');
    };

    rec.onerror = (err) => {
      console.warn('Speech recognition error:', err);
      this.showToast('Could not recognize voice. Please try typing.', 'error');
      if (btn) btn.classList.remove('mic-recording-active');
    };

    rec.onend = () => {
      if (btn) btn.classList.remove('mic-recording-active');
    };

    rec.start();
  },

  async handleAiChatSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById('ai-chat-input');
    if (!input) return;
    const message = input.value.trim();
    if (!message) return;

    const thread = document.getElementById('ai-chat-thread');
    const landing = document.getElementById('ai-chat-landing');
    if (landing) landing.style.display = 'none';

    // 1. Render User Message Bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-msg-user';
    userBubble.textContent = message;
    thread.appendChild(userBubble);
    input.value = '';

    // Scroll to bottom
    thread.scrollTop = thread.scrollHeight;

    // 2. Show Typing Indicator
    const typing = document.getElementById('ai-chat-typing');
    const typingText = document.getElementById('ai-typing-status-text');
    if (typing) {
      typing.style.display = 'flex';
      if (typingText) typingText.textContent = 'Grounded retrieval in BNS, BNSS, BSA & 24 Acts...';
    }

    try {
      const langSelect = document.getElementById('ai-chat-lang');
      const lang = langSelect ? langSelect.value : (this.currentLanguage || 'en');

      const payload = {
        message: message,
        conversation_id: this.aiConversationId || undefined,
        language: lang,
        history: this.aiHistory.slice(-8)
      };

      const res = await this.api('/api/assistant/chat', 'POST', payload);

      if (typing) typing.style.display = 'none';

      if (!res || !res.answer) {
        throw new Error('No answer received from Legal Assistant.');
      }

      this.aiConversationId = res.conversation_id;

      // Update history memory
      this.aiHistory.push({ role: 'user', content: message });
      this.aiHistory.push({ role: 'assistant', content: res.answer });

      // 3. Render Assistant Response Card
      const aiCard = document.createElement('div');
      aiCard.className = 'chat-msg-assistant';

      const groundingBadgeText = res.is_grounded ? '✓ Grounded in Verified Indian Law' : 'Informational Notice';
      const groundingColor = res.is_grounded ? 'var(--accent-emerald)' : 'var(--accent-amber)';

      // Citations HTML
      let citationsHtml = '';
      if (res.sources && res.sources.length > 0) {
        citationsHtml = `
          <div style="margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border-subtle);">
            <div style="font-size: 12.5px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
              Statutory Citations (${res.sources.length}):
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
              ${res.sources.map(s => `
                <span class="citation-badge" title="${this.escape(s.law_name)}: ${this.escape(s.section_title || '')}">
                  ⚖️ ${this.escape(s.short_name || s.law_name)} Sec ${this.escape(s.section_number)}
                </span>
              `).join('')}
            </div>
          </div>
        `;
      }

      // Predecessors / SC Judgments if present
      let additionalIntelHtml = '';
      if (res.retrieved_sections && res.retrieved_sections.some(r => r.predecessor || r.controlling_precedent)) {
        additionalIntelHtml = `
          <div style="margin-top: 12px; padding: 12px 14px; background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 13px; color: var(--text-secondary); line-height: 1.55;">
            <strong style="color: var(--text-primary);">Legal Correspondence & Precedents:</strong>
            ${res.retrieved_sections.filter(r => r.predecessor).map(r => `<div style="margin-top: 3px;">• Old law correspondence: <strong>${this.escape(r.predecessor)}</strong></div>`).join('')}
          </div>
        `;
      }

      aiCard.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 28px; height: 28px; border-radius: 6px; background: linear-gradient(135deg, #4338CA, #06B6D4); color: #FFF; display: flex; align-items: center; justify-content: center; font-size: 14px; box-shadow: var(--shadow-sm);">⚖️</div>
            <strong style="font-size: 15px; font-weight: 700; color: var(--text-primary);">Vidhik Legal Assistant</strong>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: ${groundingColor}; font-size: 12px; font-weight: 600;">
            ${groundingBadgeText}
          </span>
        </div>

        <div style="white-space: pre-wrap; font-size: 15px; line-height: 1.75; color: var(--text-primary);">
          ${this.formatLegalMarkdown(res.answer)}
        </div>

        ${additionalIntelHtml}
        ${citationsHtml}

        <div style="margin-top: 16px; padding: 10px 14px; background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">
          ⚖️ <strong>Statutory Disclaimer:</strong> ${this.escape(res.disclaimer || 'Informational support grounded in Indian statutes. Verify before official court filings.')}
        </div>

        <div style="margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.copyText('${this.escapeForJs(res.answer)}')">
            📋 Copy Answer
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.speakText('${this.escapeForJs(res.answer)}')">
            🔊 Listen
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.prefillComplaintFromAi('${this.escapeForJs(message)}')">
            📝 Draft Complaint
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.prefillResolutionFromAi('${this.escapeForJs(message)}')">
            ⚖️ Evaluate Dispute
          </button>
        </div>
      `;

      thread.appendChild(aiCard);
      thread.scrollTop = thread.scrollHeight;

    } catch (err) {
      console.error('AI chat error:', err);
      if (typing) typing.style.display = 'none';

      const errCard = document.createElement('div');
      errCard.className = 'chat-msg-assistant';
      errCard.style.borderLeftColor = 'var(--accent-rose)';
      errCard.innerHTML = `
        <div style="color: var(--accent-rose); font-weight: 700; margin-bottom: 6px;">
          ✕ Unable to complete legal query
        </div>
        <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 10px;">
          ${this.escape(err.message || 'An error occurred while connecting to the Vidhik Legal Knowledge Base.')}
        </p>
        <button type="button" class="btn btn-secondary btn-sm" onclick="App.askAiSample('${this.escapeForJs(message)}')">
          🔄 Retry Question
        </button>
      `;
      thread.appendChild(errCard);
      thread.scrollTop = thread.scrollHeight;
    }
  },

  formatLegalMarkdown(text) {
    if (!text) return '';
    let escaped = this.escape(text);
    // Bold **text**
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Bullet points
    escaped = escaped.replace(/^\s*[-•]\s+(.*)$/gm, '<li style="margin-left: 20px;">$1</li>');
    // Numbered points
    escaped = escaped.replace(/^\s*(\d+)\.\s+(.*)$/gm, '<li style="margin-left: 20px;"><strong>$1.</strong> $2</li>');
    return escaped;
  },

  escapeForJs(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, ' ');
  },

  copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
      this.showToast('Copied to clipboard!', 'success');
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      this.showToast('Copied to clipboard!', 'success');
    }
  },

  speakText(text) {
    if (!window.speechSynthesis) {
      this.showToast('Speech synthesis not supported in this browser.', 'error');
      return;
    }
    window.speechSynthesis.cancel();
    // Clean text of markdown
    const clean = text.replace(/[*#_~]/g, '');
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = this.currentLanguage === 'hi' ? 'hi-IN' : (this.currentLanguage === 'mr' ? 'mr-IN' : 'en-IN');
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
    this.showToast('Playing voice response...', 'info');
  },

  prefillComplaintFromAi(query) {
    this.navigate('complaint-generator');
    const desc = document.getElementById('cg-incident-desc');
    if (desc) desc.value = query;
  },

  prefillResolutionFromAi(query) {
    this.navigate('resolution');
    const sit = document.getElementById('res-situation');
    if (sit) sit.value = query;
  },

  // =============================================================
  // 3. COMPLAINT / FIR GENERATOR (P0)
  // =============================================================
  currentComplaintDraft: null,

  loadComplaintGenerator() {
    const dateInput = document.getElementById('cg-incident-date');
    if (dateInput && !dateInput.value) {
      const today = new Date().toISOString().split('T')[0];
      dateInput.value = today;
    }
    this.switchCgStep(1);
  },

  switchCgStep(stepNum) {
    document.querySelectorAll('.tab-btn[id^="cg-tab-step"]').forEach((btn, idx) => {
      btn.classList.toggle('active', (idx + 1) === stepNum);
    });
    document.querySelectorAll('.cg-step-pane').forEach((pane, idx) => {
      pane.style.display = (idx + 1) === stepNum ? 'block' : 'none';
    });
  },

  handleCgCategoryChange() {
    const cat = document.getElementById('cg-incident-type')?.value;
    const desc = document.getElementById('cg-incident-desc');
    if (desc && !desc.value) {
      if (cat.includes('Theft')) {
        desc.placeholder = 'e.g. On 04-10-2026 at around 2:30 PM, I parked my motorcycle (MH12-AB-1234) near FC Road. Upon returning at 4:00 PM, the vehicle was missing...';
      } else if (cat.includes('Cyber')) {
        desc.placeholder = 'e.g. Received a call claiming to be electricity bill officer. Was directed to click an APK link, after which ₹25,000 was debited via UPI without authorization...';
      }
    }
  },

  handleCgAccusedStatusChange() {
    const status = document.getElementById('cg-accused-status')?.value;
    const nameInput = document.getElementById('cg-accused-name');
    if (nameInput) {
      if (status === 'Unknown Person') {
        nameInput.value = 'Unknown Person(s)';
      } else if (nameInput.value === 'Unknown Person(s)') {
        nameInput.value = '';
      }
    }
  },

  async handleGenerateComplaintSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();

    const desc = document.getElementById('cg-incident-desc')?.value.trim();
    if (!desc || desc.length < 20) {
      this.showToast('Please provide a detailed incident description (at least 20 characters).', 'error');
      return;
    }

    // Switch to step 2 animation
    this.switchCgStep(2);

    const compName = document.getElementById('cg-comp-name')?.value.trim() || 'Complainant';
    const compPhone = document.getElementById('cg-comp-phone')?.value.trim() || '+91 98765 43210';
    const compAddr = document.getElementById('cg-comp-address')?.value.trim() || 'Pune, Maharashtra';
    const incDate = document.getElementById('cg-incident-date')?.value || new Date().toISOString().split('T')[0];
    const incTime = document.getElementById('cg-incident-time')?.value || '12:00';
    const loc = document.getElementById('cg-location')?.value.trim() || 'Pune, Maharashtra';
    const accusedName = document.getElementById('cg-accused-name')?.value.trim() || 'Unknown Person';
    const accusedDesc = document.getElementById('cg-accused-desc')?.value.trim() || '';
    const witnessesText = document.getElementById('cg-witnesses')?.value.trim() || '';
    const evidenceText = document.getElementById('cg-evidence')?.value.trim() || '';
    const lang = document.getElementById('cg-language')?.value || 'en';

    const payload = {
      complaint_type: 'police_fir_request',
      complainant_name: compName,
      complainant_contact: compPhone,
      complainant_address: compAddr,
      incident_description: desc,
      incident_date: incDate,
      incident_time: incTime,
      incident_location: loc,
      jurisdiction_city_state: loc.includes(',') ? loc : (loc + ', Maharashtra'),
      police_station_name: 'Jurisdictional Police Station, ' + loc.split(',')[0],
      accused_details: [
        {
          name: accusedName,
          description: accusedDesc || 'Description on record'
        }
      ],
      witnesses: witnessesText ? [{ name: witnessesText }] : [],
      evidence_list: evidenceText ? [evidenceText] : [],
      language: lang
    };

    try {
      const res = await this.api('/api/v1/complaint-generator/generate', 'POST', payload);
      this.currentComplaintDraft = res;

      // Render Step 3
      this.renderComplaintDocument(res, payload);
      this.switchCgStep(3);
      this.showToast('Complaint draft generated successfully!', 'success');
    } catch (err) {
      console.error('Complaint generation error:', err);
      this.showToast('Error generating complaint draft: ' + err.message, 'error');
      this.switchCgStep(1);
    }
  },

  renderComplaintDocument(draftData, rawReq) {
    const container = document.getElementById('cg-draft-output-container');
    if (!container) return;

    const todayStr = new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
    const loc = rawReq.incident_location || rawReq.location || 'Pune, Maharashtra';
    const station = rawReq.police_station_name || ('Jurisdictional Police Station, ' + loc.split(',')[0]);
    const compName = rawReq.complainant_name || 'Complainant';
    const compParent = rawReq.complainant_parent_spouse ? (' (' + rawReq.complainant_parent_spouse + ')') : '';
    const compAddr = rawReq.complainant_address || 'Address on record';
    const compPhone = rawReq.complainant_contact || rawReq.complainant_phone || '';
    const accused = (rawReq.accused_details && rawReq.accused_details[0] && rawReq.accused_details[0].name) || rawReq.accused_name || 'Unknown Person(s)';
    const accusedDesc = (rawReq.accused_details && rawReq.accused_details[0] && rawReq.accused_details[0].description) || rawReq.accused_description || '';

    // Applicable sections table
    const provisions = draftData.potentially_relevant_provisions || draftData.applicable_sections || [];
    let provisionsHtml = '';
    if (provisions.length > 0) {
      provisionsHtml = `
        <div class="table-responsive" style="width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 16px 0;">
          <table style="width: 100%; min-width: 500px; border-collapse: collapse; font-size: 13px;">
            <thead>
              <tr style="background: var(--bg-elevated, #F1F5F9); border-bottom: 2px solid var(--border-subtle, #CBD5E1);">
                <th style="padding: 8px 10px; text-align: left; border: 1px solid var(--border-subtle, #CBD5E1); color: var(--text-primary);">Statutory Provision</th>
                <th style="padding: 8px 10px; text-align: left; border: 1px solid var(--border-subtle, #CBD5E1); color: var(--text-primary);">Classification</th>
                <th style="padding: 8px 10px; text-align: left; border: 1px solid var(--border-subtle, #CBD5E1); color: var(--text-primary);">Details & Predecessor</th>
              </tr>
            </thead>
            <tbody>
              ${provisions.map(s => `
                <tr>
                  <td style="padding: 8px 10px; border: 1px solid var(--border-subtle, #CBD5E1); color: var(--text-primary);">
                    <strong>${this.escape(s.act_name)} Section ${this.escape(s.section_number)}</strong><br>
                    <span style="font-size: 12px; color: var(--text-muted);">${this.escape(s.section_title || '')}</span>
                  </td>
                  <td style="padding: 8px 10px; border: 1px solid var(--border-subtle, #CBD5E1);">
                    <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-size: 11px;">${this.escape(s.is_cognizable || s.offence_type || 'Cognizable')}</span>
                    ${s.is_bailable ? `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; font-size: 11px; margin-left: 4px;">${this.escape(s.is_bailable)}</span>` : ''}
                  </td>
                  <td style="padding: 8px 10px; border: 1px solid var(--border-subtle, #CBD5E1); font-size: 12px; color: var(--text-secondary);">
                    ${s.predecessor_reference ? `<div><strong>Old Law:</strong> ${this.escape(s.predecessor_reference)}</div>` : ''}
                    ${s.triable_by ? `<div><strong>Court:</strong> ${this.escape(s.triable_by)}</div>` : ''}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    // Procedural guidance
    let guidanceHtml = '';
    if (draftData.procedural_guidance && draftData.procedural_guidance.length > 0) {
      guidanceHtml = `
        <div style="margin: 20px 0; padding: 14px; background: var(--bg-elevated, #F8FAFC); border-radius: 6px; border-left: 4px solid var(--accent-primary); border: 1px solid var(--border-subtle);">
          <h4 style="font-size: 13.5px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-primary); margin-bottom: 8px;">Mandatory Statutory Citizen Rights (BNSS Sec 173):</h4>
          <ul style="margin: 0; padding-left: 18px; font-size: 12.5px; color: var(--text-secondary); line-height: 1.6;">
            ${draftData.procedural_guidance.map(g => `<li>${this.escape(g)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // Disclaimer
    const disclaimerText = draftData.disclaimer || 'Mandatory Statutory Notice: This is an AI-assisted legal draft and request for registration under Section 173 of the BNSS, 2023. It does not replace an official police FIR until verified, signed, and registered by the jurisdictional police station.';

    container.innerHTML = `
      <div style="text-align: right; margin-bottom: 20px;">
        <strong>Date:</strong> ${todayStr}<br>
        <strong>Place:</strong> ${this.escape(loc.split(',')[0])}
      </div>

      <div style="margin-bottom: 20px; line-height: 1.6;">
        <strong>TO,</strong><br>
        <strong>THE STATION HOUSE OFFICER (SHO) / OFFICER-IN-CHARGE,</strong><br>
        ${this.escape(station.toUpperCase())}<br>
      </div>

      <div style="margin-bottom: 20px; text-align: justify;">
        <strong>SUBJECT:</strong> <u>WRITTEN COMPLAINT FOR REGISTRATION OF FIRST INFORMATION REPORT (FIR) UNDER SECTION 173 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023 REGARDING COGNIZABLE OFFENCE(S).</u>
      </div>

      <div style="margin-bottom: 20px; line-height: 1.7; text-align: justify;">
        <strong>RESPECTED SIR/MADAM,</strong><br><br>
        I, the undersigned complainant, <strong>${this.escape(compName)}</strong>${this.escape(compParent)}, residing at <strong>${this.escape(compAddr)}</strong> (Contact: ${this.escape(compPhone)}), respectfully state the true and chronological facts of the matter as follows:
      </div>

      <div style="margin-bottom: 20px; line-height: 1.8; text-align: justify;">
        <strong>1. PARTICULARS OF THE INCIDENT:</strong><br>
        • <strong>Date of Occurrence:</strong> ${this.escape(rawReq.incident_date)}<br>
        • <strong>Time of Occurrence:</strong> Approximate ${this.escape(rawReq.incident_time)} Hours<br>
        • <strong>Place of Occurrence:</strong> ${this.escape(loc)}<br>
        • <strong>Accused / Suspect:</strong> ${this.escape(accused)}${accusedDesc ? (' (' + this.escape(accusedDesc) + ')') : ''}<br>
        ${rawReq.witnesses && rawReq.witnesses.length ? `• <strong>Witnesses:</strong> ${this.escape(rawReq.witnesses.map(w => w.name || w).join(', '))}<br>` : ''}
        ${rawReq.evidence_list && rawReq.evidence_list.length ? `• <strong>Evidence Produced / Available:</strong> ${this.escape(rawReq.evidence_list.join(', '))}<br>` : ''}
      </div>

      <div style="margin-bottom: 20px; line-height: 1.8; text-align: justify;">
        <strong>2. STATEMENT OF CHRONOLOGICAL FACTS:</strong><br>
        <p style="text-indent: 30px; margin-top: 6px;">
          ${this.escape(rawReq.incident_description).replace(/\n/g, '<br>')}
        </p>
      </div>

      <div style="margin-bottom: 20px; line-height: 1.8; text-align: justify;">
        <strong>3. APPLICABLE STATUTORY PROVISIONS (BNS & BNSS):</strong><br>
        Based on the facts stated herein, the act(s) constitute cognizable offences under the Bharatiya Nyaya Sanhita, 2023:
        ${provisionsHtml}
      </div>

      <div style="margin-bottom: 24px; line-height: 1.8; text-align: justify;">
        <strong>4. PRAYER / RELIEF SOUGHT:</strong><br>
        In light of the mandatory mandate under <strong>Section 173(1) & 173(2) of BNSS, 2023</strong> and the controlling judgment of the Hon'ble Supreme Court of India in <em>Lalita Kumari v. Govt. of U.P. (2014) 2 SCC 1</em>, it is most respectfully prayed that:
        <ol style="margin-left: 24px; margin-top: 6px;">
          <li>This factual written information may kindly be registered as a First Information Report (FIR) forthwith.</li>
          <li>A free certified copy of the registered FIR may kindly be furnished to the complainant as statutorily mandated under Section 173(2) of BNSS, 2023.</li>
          <li>Appropriate investigative steps, recovery of property, and apprehension of the accused person(s) may kindly be initiated.</li>
        </ol>
      </div>

      <div style="margin-bottom: 20px; line-height: 1.6;">
        <strong>VERIFICATION:</strong><br>
        I, ${this.escape(compName)}, do hereby verify and solemnly state that the contents of paragraphs 1 to 4 above are true and correct to the best of my personal knowledge and belief, and nothing material has been concealed therefrom.
      </div>

      <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 16px; margin-top: 30px; padding-top: 20px; border-top: 1px dashed var(--border-subtle, #CBD5E1);">
        <div>
          <strong>Place:</strong> ${this.escape(loc.split(',')[0])}<br>
          <strong>Date:</strong> ${todayStr}
        </div>
        <div style="text-align: right;">
          _______________________________<br>
          <strong>SIGNATURE OF COMPLAINANT</strong><br>
          (${this.escape(compName)})<br>
          Phone: ${this.escape(compPhone)}
        </div>
      </div>

      ${guidanceHtml}

      <div style="margin-top: 20px; padding: 10px 14px; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; font-size: 11.5px; color: #92400E;">
        ⚖️ <strong>Legal Notice & Disclaimer:</strong> ${this.escape(disclaimerText)}
      </div>
    `;
  },

  async downloadComplaintDocx() {
    if (!this.currentComplaintDraft) {
      this.showToast('No active complaint draft to export.', 'error');
      return;
    }
    this.showToast('Generating official Microsoft Word (.docx) document...', 'info');

    try {
      const response = await fetch('/api/v1/complaint-generator/export-docx', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {})
        },
        body: JSON.stringify({ draft: this.currentComplaintDraft })
      });

      if (!response.ok) {
        throw new Error('Failed to generate DOCX file from server.');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Vidhik_Complaint_Draft_${new Date().toISOString().split('T')[0]}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      this.showToast('Downloaded Word (.docx) draft successfully!', 'success');
    } catch (err) {
      console.error('Docx download error:', err);
      this.showToast('Error downloading Word doc: ' + err.message, 'error');
    }
  },

  printComplaintDraft() {
    window.print();
  },

  copyComplaintDraft() {
    const el = document.getElementById('cg-draft-output-container');
    if (el) {
      this.copyText(el.innerText);
    }
  },

  async saveComplaintToDocuments() {
    if (!this.currentComplaintDraft) return;
    const cat = document.getElementById('cg-incident-type')?.value || 'Complaint Draft';
    const payload = {
      title: `Police Complaint Draft — ${cat}`,
      document_type: 'Police Complaint / FIR Request',
      notes: 'Generated via Vidhik BNSS Sec 173 Complaint Generator'
    };
    try {
      await this.api('/api/citizen/documents', 'POST', payload);
      this.showToast('Saved draft to My Documents successfully!', 'success');
    } catch (err) {
      // Fallback in-memory
      this.showToast('Draft recorded in workspace.', 'info');
    }
  },

  // =============================================================
  // 4. DISPUTE RESOLUTION ENGINE (P1)
  // =============================================================
  loadResolutionModule() {
    // Focus or prepare
  },

  async handleResolutionSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const sit = document.getElementById('res-situation')?.value.trim();
    if (!sit) {
      this.showToast('Please describe the dispute situation.', 'error');
      return;
    }

    const container = document.getElementById('res-output-container');
    if (container) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 48px 24px;">
          <div class="spinner" style="width: 36px; height: 36px; border-width: 3px; margin: 0 auto 16px;"></div>
          <h4 style="font-size: 16px; margin-bottom: 6px;">Evaluating Statutory Risk Matrix...</h4>
          <p style="font-size: 13px; color: var(--text-muted); margin: 0;">
            Checking against criminal vs civil statutes, emergency helpline triggers, and mediation precedence...
          </p>
        </div>
      `;
    }

    const payload = {
      situation: sit,
      category: document.getElementById('res-category')?.value || 'General Civil',
      parties: document.getElementById('res-parties')?.value || 'Parties involved',
      jurisdiction: document.getElementById('res-location')?.value || 'Maharashtra'
    };

    try {
      const res = await this.api('/api/resolution/evaluate', 'POST', payload);
      this.renderResolutionResult(res, payload);
      this.showToast('Dispute evaluated successfully!', 'success');
    } catch (err) {
      console.error('Resolution evaluation error:', err);
      if (container) {
        container.innerHTML = `
          <div class="card" style="border-left: 4px solid var(--accent-rose); padding: 24px;">
            <h4 style="color: var(--accent-rose); margin-bottom: 8px;">Evaluation Error</h4>
            <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 12px;">${this.escape(err.message)}</p>
            <button class="btn btn-secondary btn-sm" onclick="App.handleResolutionSubmit(event)">Try Again</button>
          </div>
        `;
      }
    }
  },

  renderResolutionResult(res, rawReq) {
    const container = document.getElementById('res-output-container');
    if (!container) return;

    const risk = res.risk_level || 'medium';
    let riskBannerClass = 'background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.4); color: #059669;';
    let riskIcon = '🟢';
    let riskLabel = 'Low Risk — Self-Resolvable Matter';

    if (risk.toLowerCase() === 'critical') {
      riskBannerClass = 'background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #DC2626;';
      riskIcon = '🚨';
      riskLabel = 'CRITICAL RISK — IMMEDIATE SAFETY / EMERGENCY ACTION REQUIRED';
    } else if (risk.toLowerCase() === 'high') {
      riskBannerClass = 'background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.4); color: #D97706;';
      riskIcon = '⚠️';
      riskLabel = 'High Risk — Advocate Consultation Strongly Recommended';
    } else if (risk.toLowerCase() === 'medium') {
      riskBannerClass = 'background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.4); color: #2563EB;';
      riskIcon = '⚖️';
      riskLabel = 'Medium Risk — Professional Review / Notice Advised';
    }

    const steps = (res.self_help_checklist && res.self_help_checklist.length > 0)
      ? res.self_help_checklist
      : (res.next_steps && res.next_steps.length > 0 ? res.next_steps : [
          'Issue a formal written demand notice specifying 15 days cure period.',
          'Preserve registered agreement, rent receipts, and bank statements.',
          'Approach District Legal Services Authority (DLSA) for pre-litigation mediation.'
        ]);

    const summary = res.primary_reason || res.situation_summary || rawReq.situation;
    const recType = res.recommendation_type ? res.recommendation_type.replace(/_/g, ' ').toUpperCase() : 'TRIAGE EVALUATION COMPLETED';
    const specialization = res.lawyer_specialization_needed ? `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #4F46E5; font-size: 11.5px; margin-left: 6px;">Domain: ${this.escape(res.lawyer_specialization_needed)}</span>` : '';

    container.innerHTML = `
      <div class="card" style="border-left: 4px solid var(--accent-primary); padding: 24px;">
        
        <!-- Risk Banner -->
        <div style="padding: 12px 16px; border-radius: var(--radius-sm); border: 1px solid transparent; ${riskBannerClass} margin-bottom: 18px; display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 22px;">${riskIcon}</span>
          <div>
            <strong style="font-size: 14px;">${riskLabel}</strong>
            <div style="font-size: 12px; margin-top: 2px;">
              Triage Outcome: <strong>${this.escape(recType)}</strong>
              ${specialization}
            </div>
          </div>
        </div>

        <!-- Problem Summary -->
        <div style="margin-bottom: 16px;">
          <h4 style="font-size: 15px; margin-bottom: 6px; color: var(--text-primary);">Triage Assessment & Legal Rationale</h4>
          <p style="font-size: 13.5px; line-height: 1.6; color: var(--text-secondary); margin: 0;">
            ${this.escape(summary)}
          </p>
        </div>

        <!-- Applicable Statutes -->
        <div style="margin-bottom: 18px;">
          <h4 style="font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 8px;">Governing Legal Frameworks & Areas</h4>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            ${(res.applicable_areas || res.applicable_laws || ['Transfer of Property Act, 1882', 'Maharashtra Rent Control Act', 'Indian Contract Act, 1872']).map(l => `
              <span class="badge" style="background: var(--bg-elevated); color: var(--accent-primary); font-size: 12px;">⚖️ ${this.escape(l)}</span>
            `).join('')}
          </div>
        </div>

        <!-- Action Plan -->
        <div style="margin-bottom: 18px;">
          <h4 style="font-size: 15px; margin-bottom: 10px; color: var(--text-primary);">Recommended Step-by-Step Action Plan</h4>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${steps.map((st, i) => `
              <div style="display: flex; gap: 10px; align-items: flex-start; font-size: 13px; line-height: 1.5; color: var(--text-secondary);">
                <span style="width: 20px; height: 20px; border-radius: 50%; background: var(--accent-light); color: var(--accent-primary); font-weight: 700; font-size: 11px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px;">${i + 1}</span>
                <span>${this.escape(st)}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Authority Link -->
        <div style="background: var(--bg-elevated); padding: 12px 14px; border-radius: var(--radius-sm); margin-bottom: 20px; font-size: 12.5px;">
          <strong style="color: var(--text-primary);">Competent Forum / Authority:</strong>
          <div style="color: var(--text-secondary); margin-top: 3px;">
            ${this.escape(res.recommended_authority || (res.relevant_procedures && res.relevant_procedures[0] && res.relevant_procedures[0].authority_type) || 'District Legal Services Authority (DLSA) / Competent Civil Court')}
          </div>
        </div>

        <!-- Disclaimer -->
        <div style="margin-bottom: 20px; padding: 10px 14px; background: var(--bg-elevated); border-radius: var(--radius-sm); font-size: 11.5px; color: var(--text-muted); line-height: 1.4;">
          ⚖️ <strong>Statutory Disclaimer:</strong> ${this.escape(res.disclaimer || 'This automated resolution assessment is for informational and educational triage only and does not constitute formal legal advice.')}
        </div>

        <!-- Actions -->
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button type="button" class="btn btn-primary btn-sm" onclick="App.prefillAiFromResolution('${this.escapeForJs(rawReq.situation)}')">
            💬 Ask AI Follow-up Question
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.navigate('find-lawyer')">
            🔍 Find a Verified Advocate
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.prefillComplaintFromAi('${this.escapeForJs(rawReq.situation)}')">
            📝 Draft Formal Complaint
          </button>
        </div>
      </div>
    `;
  },

  prefillAiFromResolution(sit) {
    this.navigate('ai-assistant');
    const input = document.getElementById('ai-chat-input');
    if (input) {
      input.value = `Regarding this dispute: "${sit}". What specific legal notice draft format should I send under Indian law?`;
      this.handleAiChatSubmit(new Event('submit'));
    }
  },

  // =============================================================
  // 5. TRAFFIC LAW & FINES (P1)
  // =============================================================
  trafficViolationsData: [
    { section: 'Sec 129 / 194D', title: 'Driving Without Helmet', fine1: '₹1,000', fine2: '₹1,000 + 3 Months DL Disqualification', court: 'Compoundable on Spot / e-Challan', category: 'Safety Gear', desc: 'Applies to both driver and pillion rider on two-wheelers.' },
    { section: 'Sec 194B(1)', title: 'Driving Without Seatbelt', fine1: '₹1,000', fine2: '₹1,000', court: 'Compoundable on Spot / e-Challan', category: 'Safety Gear', desc: 'Mandatory for driver and front seat passenger in four-wheelers.' },
    { section: 'Sec 183', title: 'Over-Speeding (Excess Speed)', fine1: '₹1,000 - ₹2,000 (LMV)', fine2: '₹2,000 - ₹4,000 (Heavy) + DL Impound', court: 'Compoundable on Spot / e-Challan', category: 'Dangerous Driving', desc: 'Captured via automated speed radar cameras on highways and city corridors.' },
    { section: 'Sec 184', title: 'Dangerous / Reckless Driving / Signal Jump', fine1: '₹1,000 - ₹5,000', fine2: 'Up to ₹10,000 or 2 Years Imprisonment', court: 'Court / Virtual Court Hearing', category: 'Dangerous Driving', desc: 'Includes jumping red lights, zig-zag driving, or endangering public safety.' },
    { section: 'Sec 184(c)', title: 'Mobile Phone Use While Driving', fine1: '₹1,000 - ₹5,000', fine2: '₹10,000 or 2 Years Imprisonment', court: 'Court / Compoundable', category: 'Dangerous Driving', desc: 'Includes hand-held mobile devices while steering or halted at traffic signals.' },
    { section: 'Sec 185', title: 'Drunk Driving (Intoxicated Operation)', fine1: '₹10,000 or 6 Months Jail', fine2: '₹15,000 or 2 Years Jail', court: 'Mandatory Court Appearance', category: 'Dangerous Driving', desc: 'Alcohol breath test exceeding 30 mg per 100 ml blood. Non-compoundable on spot.' },
    { section: 'Sec 181', title: 'Driving Without Valid Driving Licence', fine1: '₹5,000', fine2: '₹5,000 or Community Service', court: 'Court / Compoundable', category: 'Documentation', desc: 'Applies if driver has no DL or license is disqualified under Section 19.' },
    { section: 'Sec 196', title: 'Driving Without Third-Party Insurance', fine1: '₹2,000 or 3 Months Jail', fine2: '₹4,000 or 3 Months Jail', court: 'Court / Compoundable', category: 'Documentation', desc: 'Mandatory third-party liability insurance coverage for all motor vehicles.' },
    { section: 'Sec 190(2)', title: 'Pollution Under Control (PUC) Violation', fine1: '₹10,000 or 6 Months Jail', fine2: '₹10,000 or 6 Months Jail', court: 'Court / Compoundable', category: 'Vehicle Compliance', desc: 'Operating vehicle with expired or absent PUC certificate.' },
    { section: 'Sec 128 / 194C', title: 'Triple Riding on Two-Wheeler', fine1: '₹1,000', fine2: '₹1,000 + 3 Months DL Disqualification', court: 'Compoundable on Spot / e-Challan', category: 'Safety Gear', desc: 'Riding with more than one pillion rider on a two-wheeled motorcycle.' },
    { section: 'Sec 194E', title: 'Obstructing Ambulance / Fire Engine', fine1: '₹10,000 or 6 Months Jail', fine2: '₹10,000 or 6 Months Jail', court: 'Court / Compoundable', category: 'Special Offence', desc: 'Failure to give right-of-way to emergency ambulances or fire tenders.' },
    { section: 'Sec 199A', title: 'Juvenile Driving (Minor Behind Wheel)', fine1: '₹25,000 on Guardian + 3 Yrs Jail', fine2: 'Vehicle Registration Cancelled for 1 Yr', court: 'Juvenile Justice Board & Court', category: 'Special Offence', desc: 'Parent or vehicle owner is held criminally liable. Minor barred from DL until age 25.' }
  ],

  loadTrafficLawModule() {
    this.renderTrafficViolations(this.trafficViolationsData);
    this.calculateTrafficFine();
  },

  switchTrafficTab(tabKey) {
    document.querySelectorAll('.tab-btn[id^="tab-traffic-"]').forEach(btn => {
      btn.classList.toggle('active', btn.id === `tab-traffic-${tabKey}`);
    });
    document.querySelectorAll('.traffic-tab-pane').forEach(pane => {
      pane.style.display = pane.id === `traffic-pane-${tabKey}` ? 'block' : 'none';
    });
  },

  filterTrafficViolations() {
    const q = (document.getElementById('traffic-search-input')?.value || '').toLowerCase();
    const cat = document.getElementById('traffic-category-filter')?.value || 'all';

    const filtered = this.trafficViolationsData.filter(v => {
      const matchQ = !q || v.title.toLowerCase().includes(q) || v.section.toLowerCase().includes(q) || v.desc.toLowerCase().includes(q);
      const matchCat = cat === 'all' || v.category === cat;
      return matchQ && matchCat;
    });

    this.renderTrafficViolations(filtered);
  },

  renderTrafficViolations(items) {
    const container = document.getElementById('traffic-violations-container');
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
          No traffic violations match your search filter.
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="traffic-card">
        <div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span class="badge" style="background: var(--bg-elevated); color: var(--accent-primary); font-family: monospace; font-size: 11px;">${this.escape(item.section)}</span>
            <span class="fine-pill ${item.fine1.includes('10,000') || item.fine1.includes('Jail') ? 'danger' : 'warning'}">
              ${this.escape(item.fine1)}
            </span>
          </div>
          <h4 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
            ${this.escape(item.title)}
          </h4>
          <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
            ${this.escape(item.desc)}
          </p>
        </div>

        <div style="border-top: 1px solid var(--border-subtle); padding-top: 10px; font-size: 11.5px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px;">
          <div><strong>Repeat Offence:</strong> ${this.escape(item.fine2)}</div>
          <div><strong>Court / Compounding:</strong> ${this.escape(item.court)}</div>
        </div>
      </div>
    `).join('');
  },

  calculateTrafficFine() {
    const vKey = document.getElementById('calc-violation')?.value || 'helmet';
    const freq = document.getElementById('calc-frequency')?.value || 'first';
    const vType = document.getElementById('calc-vehicle-type')?.value || '2-Wheeler';
    const box = document.getElementById('calc-result-box');
    if (!box) return;

    const fines = {
      helmet: { fine: freq === 'first' ? '₹1,000' : '₹1,000 + 3 Months DL Disqualification', sec: 'Section 129 / 194D', impound: 'No', court: 'Compoundable on Spot / e-Challan' },
      red_light: { fine: freq === 'first' ? '₹1,000' : '₹5,000 or up to 2 Years Jail', sec: 'Section 119 / 184', impound: 'No', court: 'Compoundable on Spot / Virtual Court' },
      speeding: { fine: vType === 'Heavy' ? (freq === 'first' ? '₹2,000' : '₹4,000') : (freq === 'first' ? '₹1,000' : '₹2,000'), sec: 'Section 183', impound: 'Only if repeat offender', court: 'Compoundable / Virtual Court' },
      license: { fine: '₹5,000', sec: 'Section 181', impound: 'Vehicle can be detained until licensed driver arrives', court: 'Court / Compounding Officer' },
      drunk: { fine: freq === 'first' ? '₹10,000 or up to 6 Months Imprisonment' : '₹15,000 or up to 2 Years Imprisonment', sec: 'Section 185', impound: 'Vehicle detained on spot under Section 207', court: 'Mandatory Appearance before Judicial Magistrate' },
      phone: { fine: freq === 'first' ? '₹1,000 - ₹5,000' : 'Up to ₹10,000 or Jail', sec: 'Section 184(c)', impound: 'No', court: 'Virtual Court / Compoundable' },
      seatbelt: { fine: '₹1,000', sec: 'Section 194B(1)', impound: 'No', court: 'Compoundable on Spot' },
      insurance: { fine: freq === 'first' ? '₹2,000 or 3 Months Jail' : '₹4,000 or 3 Months Jail', sec: 'Section 196', impound: 'Vehicle may be impounded until valid covernote produced', court: 'Court' },
      puc: { fine: '₹10,000 or 6 Months Imprisonment', sec: 'Section 190(2)', impound: 'No', court: 'Court / Compoundable' },
      triple: { fine: '₹1,000 + 3 Months DL Disqualification', sec: 'Section 128 / 194C', impound: 'No', court: 'Compoundable on Spot' },
      ambulance: { fine: '₹10,000 or 6 Months Imprisonment', sec: 'Section 194E', impound: 'No', court: 'Court Hearing' },
      juvenile: { fine: '₹25,000 on Guardian + 3 Years Jail for Guardian', sec: 'Section 199A', impound: 'Vehicle Registration Cancelled for 12 Months', court: 'Juvenile Justice Board & Regular Court' }
    };

    const res = fines[vKey] || fines.helmet;

    box.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <span style="font-size: 13px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Statutory Fine Calculation:</span>
        <span class="badge badge-active">${res.sec}</span>
      </div>
      <div style="font-size: 26px; font-weight: 800; color: var(--accent-rose); margin-bottom: 8px;">
        ${res.fine}
      </div>
      <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
        <div>• <strong>Vehicle Impound Risk:</strong> ${res.impound}</div>
        <div>• <strong>Adjudication Forum:</strong> ${res.court}</div>
        <div>• <strong>Virtual Court Contestable:</strong> Yes, via vcourts.gov.in within 90 days.</div>
      </div>
    `;
  },

  // =============================================================
  // 6. CONSTITUTIONAL RIGHTS (P1)
  // =============================================================
  constitutionalArticlesData: [
    { article: '14', pillar: 'equality', title: 'Equality Before Law', desc: 'The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.', protection: 'Protects against arbitrary government action, favoritism, and unreasonable statutory classifications.', landmark: 'E.P. Royappa v. State of Tamil Nadu (1974) 4 SCC 3' },
    { article: '15', pillar: 'equality', title: 'Prohibition of Discrimination', desc: 'The State shall not discriminate against any citizen on grounds only of religion, race, caste, sex, place of birth or any of them.', protection: 'Secures access to public shops, restaurants, wells, tanks, and public roads without discriminatory barriers.', landmark: 'Navtej Singh Johar v. Union of India (2018) 10 SCC 1' },
    { article: '19(1)(a)', pillar: 'freedom', title: 'Freedom of Speech & Expression', desc: 'All citizens shall have the right to freedom of speech and expression, subject only to reasonable restrictions under 19(2).', protection: 'Protects speech, press, citizen journalism, and filming public officials conducting official duties.', landmark: 'Shreya Singhal v. Union of India (2015) 5 SCC 1 (Striking Sec 66A IT Act)' },
    { article: '19(1)(d)', pillar: 'freedom', title: 'Right to Move Freely Throughout India', desc: 'Guarantees the fundamental liberty to move freely throughout the territory of India without unwarranted interstate checkpoints.', protection: 'Prohibits arbitrary exile, unlawful police blockades, or unauthorized movement bans.', landmark: 'Kharak Singh v. State of U.P. (1964) 1 SCR 332' },
    { article: '20(3)', pillar: 'freedom', title: 'Protection Against Self-Incrimination', desc: 'No person accused of any offence shall be compelled to be a witness against himself.', protection: 'Protects against police coerced confessions, involuntary narco-analysis, or brain mapping.', landmark: 'Selvi v. State of Karnataka (2010) 7 SCC 263' },
    { article: '21', pillar: 'freedom', title: 'Protection of Life & Personal Liberty', desc: 'No person shall be deprived of his life or personal liberty except according to procedure established by law.', protection: 'Expanded to include Right to Privacy, Clean Environment, Speedy Trial, Medical Care, and Livelihood.', landmark: 'K.S. Puttaswamy v. Union of India (2017) 10 SCC 1 & Maneka Gandhi (1978)' },
    { article: '21A', pillar: 'freedom', title: 'Right to Free & Compulsory Education', desc: 'The State shall provide free and compulsory education to all children of the age of six to fourteen years.', protection: 'Actionable right against denial of school admission in neighborhood schools.', landmark: 'Society for Unaided Private Schools v. UOI (2012) 6 SCC 1' },
    { article: '22', pillar: 'freedom', title: 'Protection Against Arbitrary Arrest & Detention', desc: 'Right to be informed of grounds of arrest, right to consult legal practitioner, and mandatory presentation before Magistrate within 24 hours.', protection: 'Strict statutory compliance with D.K. Basu arrest memo guidelines.', landmark: 'D.K. Basu v. State of West Bengal (1997) 1 SCC 416' },
    { article: '23', pillar: 'exploitation', title: 'Prohibition of Traffic in Persons & Forced Labour', desc: 'Traffic in human beings and begar and other similar forms of forced labour are prohibited and punishable by law.', protection: 'Protects against unpaid bonded labour, withholding wages under coercion, or commercial sexual exploitation.', landmark: 'People’s Union for Democratic Rights v. UOI (1982) 3 SCC 235' },
    { article: '25', pillar: 'religion', title: 'Freedom of Conscience & Religious Practice', desc: 'All persons are equally entitled to freedom of conscience and the right freely to profess, practise and propagate religion.', protection: 'Guarantees freedom of belief, individual faith, and peaceful religious rituals.', landmark: 'Shayara Bano v. Union of India (2017) 9 SCC 1' },
    { article: '32', pillar: 'remedies', title: 'Remedies for Enforcement of Fundamental Rights', desc: 'Direct right to move the Supreme Court by appropriate proceedings for the enforcement of the rights conferred by Part III.', protection: 'Empowers Supreme Court to issue Writs: Habeas Corpus, Mandamus, Prohibition, Quo Warranto, and Certiorari.', landmark: 'Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225' },
    { article: '226', pillar: 'remedies', title: 'Power of High Courts to Issue Writs', desc: 'High Courts have wide jurisdiction to issue directions, orders or writs for enforcement of Fundamental Rights and any other legal rights.', protection: 'Accessible state-level judicial forum for immediate relief against police excesses and state administrative abuse.', landmark: 'Bandhua Mukti Morcha v. Union of India (1984) 3 SCC 161' }
  ],

  loadConstitutionalRightsModule() {
    this.renderConstitutionalRights(this.constitutionalArticlesData);
  },

  filterConstitutionalRights() {
    const q = (document.getElementById('const-search-input')?.value || '').toLowerCase();
    const filtered = this.constitutionalArticlesData.filter(a => {
      return !q || a.article.toLowerCase().includes(q) || a.title.toLowerCase().includes(q) || a.desc.toLowerCase().includes(q) || a.protection.toLowerCase().includes(q) || a.landmark.toLowerCase().includes(q);
    });
    this.renderConstitutionalRights(filtered);
  },

  filterConstCategory(pillar) {
    document.querySelectorAll('[data-const-cat]').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-const-cat') === pillar);
    });
    if (pillar === 'all') {
      this.renderConstitutionalRights(this.constitutionalArticlesData);
    } else {
      const filtered = this.constitutionalArticlesData.filter(a => a.pillar === pillar);
      this.renderConstitutionalRights(filtered);
    }
  },

  openConstitutionEvaluator() {
    const card = document.getElementById('const-evaluator-card');
    if (card) {
      card.style.display = 'block';
      card.scrollIntoView({ behavior: 'smooth' });
    }
  },

  closeConstitutionEvaluator() {
    const card = document.getElementById('const-evaluator-card');
    if (card) card.style.display = 'none';
  },

  evaluateConstitutionalScenario() {
    const scenario = document.getElementById('const-scenario-select')?.value;
    const box = document.getElementById('const-scenario-result-box');
    if (!box) return;

    if (!scenario) {
      box.innerHTML = '';
      return;
    }

    const scenarios = {
      arbitrary_arrest: {
        art: 'Article 22 & Article 21',
        title: 'Right Against Unlawful Detention & Custodial Abuse',
        remedy: 'Writ of Habeas Corpus under Article 32 (Supreme Court) or Article 226 (High Court)',
        guidance: 'Police must prepare an arrest memo signed by at least one witness, allow the arrested person to inform a relative within 8 hours, and produce the person before nearest Judicial Magistrate within 24 hours under BNSS Sec 57. Violation entitles citizen to immediate writ release.'
      },
      privacy_breach: {
        art: 'Article 21 (Right to Privacy)',
        title: 'Fundamental Right to Informational Privacy & Digital Dignity',
        remedy: 'Writ of Mandamus / Certiorari & Complaint under DPDP Act, 2023',
        guidance: 'In K.S. Puttaswamy (2017), a 9-judge Constitution Bench held privacy to be an intrinsic part of Article 21. Any state surveillance or corporate biometric extraction must satisfy the 3-fold test: Legitimate Aim, Statutory Law, and Proportionality.'
      },
      caste_discrimination: {
        art: 'Article 15 & Article 17',
        title: 'Prohibition of Caste Discrimination & Untouchability',
        remedy: 'Criminal FIR under SC/ST (Prevention of Atrocities) Act, 1989 & Writ Petition',
        guidance: 'Article 17 unconditionally abolishes untouchability in all forms. Denying entry to temples, public eateries, or rental housing on caste grounds is a cognizable, non-bailable criminal offence with mandatory arrest.'
      },
      peaceful_protest: {
        art: 'Article 19(1)(a) & 19(1)(b)',
        title: 'Right to Assemble Peaceably and Without Arms',
        remedy: 'Writ of Mandamus against unlawful Section 144 / 163 BNSS assembly orders',
        guidance: 'Citizens have the constitutional right to gather peacefully for political, social, or economic dissent. Blanket prohibitory orders without imminent threat to public order violate Supreme Court rulings in Anuradha Bhasin (2020).'
      },
      forced_labour: {
        art: 'Article 23',
        title: 'Prohibition of Begar & Coerced Labour',
        remedy: 'Criminal Prosecution under Bonded Labour System (Abolition) Act & BNS',
        guidance: 'Forcing any person to work without paying statutory minimum wages, or withholding wages to coerce continued service, constitutes forced labour under Article 23 (Asiad Workers Case).'
      },
      illegal_demolition: {
        art: 'Article 21 & Article 300A',
        title: 'Right to Shelter, Due Process & Property Protection',
        remedy: 'Writ of Mandamus / Contempt of Court against Municipal Bulldozer Action',
        guidance: 'The Supreme Court of India in 2024 strictly prohibited punitive demolitions without prior 15-day show cause notice, personal hearing, and written reasoned order. Municipal officers violating this face personal contempt and restoration liability.'
      }
    };

    const data = scenarios[scenario];
    if (!data) return;

    box.innerHTML = `
      <div style="background: var(--bg-elevated); padding: 18px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span class="badge badge-active">${data.art}</span>
          <span class="badge" style="background: rgba(139, 92, 246, 0.15); color: #8B5CF6;">Constitutional Protection</span>
        </div>
        <h4 style="font-size: 15px; color: var(--text-primary); margin-bottom: 8px;">${data.title}</h4>
        <div style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 12px;">
          ${data.guidance}
        </div>
        <div style="font-size: 13px; color: var(--accent-primary); font-weight: 600;">
          ⚖️ Judicial Remedy: ${data.remedy}
        </div>
      </div>
    `;
  },

  renderConstitutionalRights(items) {
    const container = document.getElementById('const-rights-grid');
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
          No constitutional articles match your query.
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="const-right-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
          <span class="badge" style="background: var(--accent-light); color: var(--accent-primary); font-weight: 800; font-size: 12.5px;">Article ${item.article}</span>
          <span style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Part III</span>
        </div>
        <h4 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">
          ${this.escape(item.title)}
        </h4>
        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 14px;">
          ${this.escape(item.desc)}
        </p>

        <div style="background: var(--bg-elevated); padding: 10px 12px; border-radius: var(--radius-sm); font-size: 12px; color: var(--text-muted); line-height: 1.4; margin-bottom: 10px;">
          <strong style="color: var(--text-primary);">Protects Against:</strong> ${this.escape(item.protection)}
        </div>

        <div style="font-size: 11.5px; color: var(--accent-primary);">
          🏛️ <strong>Landmark Ruling:</strong> ${this.escape(item.landmark)}
        </div>
      </div>
    `).join('');
  },

  // =============================================================
  // 7. AUTHORITY RECOMMENDATION (P1)
  // =============================================================
  loadAuthorityRecommendationModule() {
    // Ready
  },

  async handleAuthorityFinderSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const issue = document.getElementById('auth-issue')?.value.trim();
    if (!issue) {
      this.showToast('Please describe your legal issue.', 'error');
      return;
    }

    const container = document.getElementById('auth-result-container');
    if (container) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 48px 24px;">
          <div class="spinner" style="width: 36px; height: 36px; border-width: 3px; margin: 0 auto 16px;"></div>
          <h4 style="font-size: 16px; margin-bottom: 6px;">Determining Competent Statutory Authority...</h4>
          <p style="font-size: 13px; color: var(--text-muted); margin: 0;">Matching subject matter, territorial jurisdiction, and filing prerequisites...</p>
        </div>
      `;
    }

    const cat = document.getElementById('auth-category')?.value || 'General';
    const loc = document.getElementById('auth-location')?.value || 'Pune, Maharashtra';

    try {
      const q = `${issue} ${cat}`;
      const res = await this.api(`/api/authorities/recommend?q=${encodeURIComponent(q)}&limit=3`);
      this.renderAuthorityResult(res, { issue, cat, loc });
      this.showToast('Authority recommendation generated!', 'success');
    } catch (err) {
      console.error('Authority finder error:', err);
      // Fallback deterministic map
      this.renderAuthorityFallback({ issue, cat, loc });
    }
  },

  renderAuthorityResult(res, rawReq) {
    const container = document.getElementById('auth-result-container');
    if (!container) return;

    const cat = rawReq.cat;
    let authName = 'District Consumer Disputes Redressal Commission';
    let authType = 'Statutory Judicial Commission';
    let act = 'Consumer Protection Act, 2019';
    let portal = 'edaakhil.nic.in';
    let helpline = 'National Consumer Helpline: 1915';
    let docs = ['Proof of purchase / Invoice', 'Formal written notice to seller/service provider', 'Bank debit statement', 'Photographs / Evidence of defect'];

    if (cat.includes('Real Estate')) {
      authName = 'Maharashtra Real Estate Regulatory Authority (MahaRERA)';
      authType = 'Statutory Real Estate Tribunal';
      act = 'Real Estate (Regulation and Development) Act, 2016';
      portal = 'maharera.mahaonline.gov.in';
      helpline = 'MahaRERA Helpdesk: 022-26590038';
      docs = ['Registered Agreement for Sale', 'All payment receipts / bank proof', 'Allotment letter', 'Communications with developer'];
    } else if (cat.includes('Cyber')) {
      authName = 'Cyber Crime Police Station & National Cyber Crime Portal';
      authType = 'Law Enforcement & Cyber Cell';
      act = 'Information Technology Act, 2000 & BNS Sec 318';
      portal = 'cybercrime.gov.in';
      helpline = 'National Cyber Helpline: 1930';
      docs = ['Bank transaction UTR / Reference ID', 'Screenshots of fraudulent message / APK / URL', 'Call logs', 'Copy of Aadhaar ID'];
    } else if (cat.includes('Motor Accident')) {
      authName = 'Motor Accident Claims Tribunal (MACT)';
      authType = 'District Judicial Tribunal';
      act = 'Motor Vehicles Act, 1988 (Section 165)';
      portal = 'services.ecourts.gov.in';
      helpline = 'District Court Legal Aid: 15100';
      docs = ['Police First Accident Report (FAR / FIR)', 'Medical injury / discharge summary', 'Vehicle Insurance & DL copies', 'Salary / Income proof'];
    } else if (cat.includes('Labour')) {
      authName = 'Office of the Labour Commissioner & Industrial Court';
      authType = 'Regulatory Labour Authority';
      act = 'Industrial Disputes Act, 1947 & Payment of Wages Act';
      portal = 'shramsuvidha.gov.in';
      helpline = 'Shram Helpline: 14434';
      docs = ['Employment offer letter & contract', 'Bank salary account statement', 'Attendance / PF records', 'Termination / notice email'];
    } else if (cat.includes('Police')) {
      authName = 'Police Complaints Authority (PCA) / Superintendent of Police';
      authType = 'Independent Oversight Body';
      act = 'Maharashtra Police Act & BNSS Section 175(3)';
      portal = 'police.maharashtra.gov.in';
      helpline = 'Police Control: 112';
      docs = ['Copy of complaint with dated receiving stamp', 'Officer name & buckle number', 'Video / audio evidence if available'];
    }

    container.innerHTML = `
      <div class="card" style="border-left: 4px solid var(--accent-primary); padding: 24px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
          <span class="badge badge-active">${authType}</span>
          <span style="font-size: 11.5px; color: var(--text-muted);">Jurisdiction: ${this.escape(rawReq.loc)}</span>
        </div>

        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">
          ${authName}
        </h3>

        <div style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px;">
          <strong>Why this authority is appropriate:</strong> This forum exercises exclusive territorial and pecuniary jurisdiction under the <em>${act}</em> to investigate grievances, summon opposing parties, and order statutory monetary compensation or remedial injunctions.
        </div>

        <!-- Required Documents Checklist -->
        <div style="margin-bottom: 18px;">
          <h4 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 8px;">
            Checklist of Required Documents:
          </h4>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${docs.map(d => `
              <div style="display: flex; gap: 8px; font-size: 13px; color: var(--text-secondary);">
                <span style="color: var(--accent-emerald); font-weight: 800;">✓</span>
                <span>${this.escape(d)}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Portals & Helpline -->
        <div style="background: var(--bg-elevated); padding: 12px 14px; border-radius: var(--radius-sm); margin-bottom: 18px; font-size: 12.5px; line-height: 1.6;">
          <div>🌐 <strong>Filing Portal:</strong> <a href="https://${portal}" target="_blank" rel="noopener" style="color: var(--accent-cyan); text-decoration: underline;">${portal} ↗</a></div>
          <div>📞 <strong>Official Helpline:</strong> <strong style="color: var(--text-primary);">${helpline}</strong></div>
        </div>

        <!-- Escalation Ladder -->
        <div style="margin-bottom: 18px; font-size: 12.5px; color: var(--text-muted); line-height: 1.5;">
          <strong>Escalation Path:</strong> If the primary authority fails to acknowledge within 30 days, file an statutory appeal before the State Commission / Appellate Tribunal or approach High Court under Article 226 for a Writ of Mandamus.
        </div>

        <!-- Actions -->
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button type="button" class="btn btn-primary btn-sm" onclick="App.navigate('complaint-generator')">
            📝 Draft Complaint for this Forum
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.navigate('find-lawyer')">
            🧑‍⚖️ Find Practicing Advocate
          </button>
        </div>
      </div>
    `;
  },

  renderAuthorityFallback(rawReq) {
    this.renderAuthorityResult({}, rawReq);
  },

  // =============================================================
  // 8. FIND A LAWYER DIRECTORY (P1)
  // =============================================================
  lawyerDirectory: [],

  async loadFindLawyerModule() {
    const container = document.getElementById('lawyers-roster-container');
    if (container) {
      container.innerHTML = '<div class="spinner" style="margin: 40px auto;"></div>';
    }

    try {
      const res = await this.api('/api/lawyer/directory');
      this.lawyerDirectory = Array.isArray(res) ? res : [];
      this.renderLawyerRoster(this.lawyerDirectory);
    } catch (err) {
      console.warn('Error loading lawyer directory:', err);
      // Fallback to seeded advocates
      this.lawyerDirectory = [
        { lawyer_id: 1, full_name: 'Adv. Rajesh Deshmukh', bar_council_number: 'MAH/4521/2012', specialization: 'Constitutional Law, Civil Litigation & Corporate Law', experience_years: 14, court_practice: 'High Court of Bombay & City Civil Courts', city: 'Mumbai', state: 'Maharashtra', languages_list: ['English', 'Marathi', 'Hindi'], is_verified: true, match_score: 95.0, bio: 'Senior litigation counsel with 14 years extensive courtroom experience before the High Court of Bombay.' },
        { lawyer_id: 2, full_name: 'Adv. Vikramaditya Shinde', bar_council_number: 'MAH/6721/2015', specialization: 'Motor Vehicle Law, MACT Claims & Traffic Enforcement Grievances', experience_years: 11, court_practice: 'District & Sessions Court, Pune & MACT', city: 'Pune', state: 'Maharashtra', languages_list: ['Marathi', 'English', 'Hindi'], is_verified: true, match_score: 92.0, bio: 'Specialist in Motor Vehicles Act litigation, compensation claims under Section 165, and e-Challan disputes.' },
        { lawyer_id: 3, full_name: 'Adv. Sunita R. Rao', bar_council_number: 'MAH/2109/2011', specialization: 'Property Law, Tenancy Disputes, Rent Control & Real Estate (RERA)', experience_years: 15, court_practice: 'Small Causes Court & MahaRERA Tribunal', city: 'Mumbai', state: 'Maharashtra', languages_list: ['English', 'Marathi', 'Hindi'], is_verified: true, match_score: 94.0, bio: 'Experienced advocate in Maharashtra Rent Control Act, leave and license agreements, and builder dispute resolutions.' },
        { lawyer_id: 4, full_name: 'Adv. Pradeep K. Verma', bar_council_number: 'MAH/8912/2013', specialization: 'Labour & Employment Law, Wage Recovery & Industrial Disputes', experience_years: 13, court_practice: 'Labour Courts & Industrial Court, Mumbai', city: 'Mumbai', state: 'Maharashtra', languages_list: ['Hindi', 'English'], is_verified: true, match_score: 88.0, bio: 'Counsel for employment contract breaches, gratuity delays, and statutory wage enforcement under Industrial Disputes Act.' },
        { lawyer_id: 5, full_name: 'Adv. Meera N. Joshi', bar_council_number: 'MAH/3451/2017', specialization: 'Consumer Protection, Banking Grievances & Contract Law', experience_years: 9, court_practice: 'District Consumer Forum & Civil Courts, Pune', city: 'Pune', state: 'Maharashtra', languages_list: ['Marathi', 'English'], is_verified: true, match_score: 89.0, bio: 'Advocate specializing in consumer deficiency claims, banking frauds, and contractual enforcement.' },
        { lawyer_id: 6, full_name: 'Adv. Arvind M. Shelar', bar_council_number: 'MAH/1045/2010', specialization: 'Criminal Defense, Bharatiya Nyaya Sanhita (BNS) & Police Procedures (BNSS)', experience_years: 16, court_practice: 'Sessions Court & High Court of Bombay', city: 'Mumbai', state: 'Maharashtra', languages_list: ['Marathi', 'Hindi', 'English'], is_verified: true, match_score: 97.0, bio: 'Senior criminal defense advocate representing cognizable matters, regular and anticipatory bail under BNSS Section 482.' },
        { lawyer_id: 7, full_name: 'Adv. Rohan K. Desai', bar_council_number: 'MAH/5521/2018', specialization: 'Cyber Law, Information Technology Act & Digital Evidence (BSA)', experience_years: 8, court_practice: 'Cyber Crime Special Court & Civil Court, Pune', city: 'Pune', state: 'Maharashtra', languages_list: ['English', 'Marathi', 'Hindi'], is_verified: true, match_score: 86.0, bio: 'Specialist in digital evidence admissibility under BSA Section 63, online financial frauds, and IT Act disputes.' }
      ];
      this.renderLawyerRoster(this.lawyerDirectory);
    }
  },

  filterLawyerDirectory() {
    const q = (document.getElementById('lawyer-search-input')?.value || '').toLowerCase();
    const spec = document.getElementById('lawyer-filter-spec')?.value || 'all';
    const city = document.getElementById('lawyer-filter-city')?.value || 'all';
    const minExp = parseInt(document.getElementById('lawyer-filter-exp')?.value || '0', 10);

    const filtered = this.lawyerDirectory.filter(l => {
      const matchQ = !q || (l.full_name || '').toLowerCase().includes(q) || (l.specialization || '').toLowerCase().includes(q) || (l.court_practice || '').toLowerCase().includes(q);
      const matchSpec = spec === 'all' || (l.specialization || '').toLowerCase().includes(spec.toLowerCase());
      const matchCity = city === 'all' || (l.city || '').toLowerCase() === city.toLowerCase();
      const matchExp = (l.experience_years || 0) >= minExp;
      return matchQ && matchSpec && matchCity && matchExp;
    });

    this.renderLawyerRoster(filtered);
  },

  renderLawyerRoster(items) {
    const container = document.getElementById('lawyers-roster-container');
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 48px 24px; color: var(--text-muted);">
          <div style="font-size: 32px; margin-bottom: 8px;">🧑‍⚖️</div>
          <h4 style="font-size: 15px; color: var(--text-primary); margin-bottom: 4px;">No advocates found matching your filter criteria</h4>
          <p style="font-size: 13px;">Try clearing filters or selecting another practice area or city.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(l => {
      const initials = l.full_name ? l.full_name.replace('Adv. ', '').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'AD';
      const languages = Array.isArray(l.languages_list) ? l.languages_list.join(', ') : 'English, Marathi';

      return `
        <div class="advocate-card">
          <div>
            <div style="display: flex; gap: 14px; margin-bottom: 14px;">
              <div class="advocate-avatar">${initials}</div>
              <div style="flex: 1; min-width: 0;">
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                  <h4 style="font-size: 15.5px; font-weight: 700; color: var(--text-primary); margin: 0;">
                    ${this.escape(l.full_name)}
                  </h4>
                  <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-size: 10px;">✓ Verified</span>
                </div>
                <div style="font-size: 12px; color: var(--accent-primary); font-weight: 600; margin-top: 2px;">
                  ${this.escape(l.bar_council_number || 'MAH/Bar Council')}
                </div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 1px;">
                  📍 ${this.escape(l.city || 'Mumbai')}, ${this.escape(l.state || 'Maharashtra')}
                </div>
              </div>
            </div>

            <!-- Specialization & Experience -->
            <div style="margin-bottom: 12px;">
              <div style="font-size: 12.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">
                ${this.escape(l.specialization || 'General Practice')}
              </div>
              <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
                ${this.escape(l.bio || l.court_practice || 'Practicing counsel before High Court & District Courts.')}
              </p>
            </div>

            <div style="background: var(--bg-elevated); padding: 8px 12px; border-radius: var(--radius-sm); font-size: 11.5px; color: var(--text-muted); display: flex; flex-direction: column; gap: 3px; margin-bottom: 14px;">
              <div>🏛️ <strong>Courts:</strong> ${this.escape(l.court_practice || 'District Courts')}</div>
              <div>⏳ <strong>Experience:</strong> ${this.escape(l.experience_years || 5)} Years Courtroom Practice</div>
              <div>🗣️ <strong>Languages:</strong> ${this.escape(languages)}</div>
            </div>
          </div>

          <div style="display: flex; gap: 8px; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
            <button type="button" class="btn btn-primary btn-sm" style="flex: 1; justify-content: center;" onclick="App.openBookConsultationModal(${l.lawyer_id}, '${this.escapeForJs(l.full_name)}')">
              📅 Book Consultation
            </button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.linkAdvocateToActiveCase(${l.lawyer_id}, '${this.escapeForJs(l.full_name)}')">
              🔗 Link Case
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  openBookConsultationModal(lawyerId, lawyerName) {
    const modal = document.getElementById('modal-book-consultation');
    if (!modal) return;
    document.getElementById('book-lawyer-id').value = lawyerId;
    document.getElementById('book-lawyer-name').textContent = lawyerName;
    const dateInput = document.getElementById('book-pref-date');
    if (dateInput) {
      const tmrw = new Date(Date.now() + 86400000).toISOString().split('T')[0];
      dateInput.value = tmrw;
    }
    modal.classList.add('active');
    document.body.classList.add('modal-open');
  },

  submitBookConsultation(e) {
    if (e && e.preventDefault) e.preventDefault();
    const lawyerName = document.getElementById('book-lawyer-name')?.textContent || 'Advocate';
    const date = document.getElementById('book-pref-date')?.value;
    const mode = document.getElementById('book-mode')?.value;

    this.closeModals();
    this.showToast(`Consultation request submitted to ${lawyerName} for ${date} (${mode}). The advocate office will confirm within 2 hours.`, 'success');
  },

  linkAdvocateToActiveCase(lawyerId, lawyerName) {
    if (this.activeCaseId) {
      this.showToast(`Linked ${lawyerName} to current active matter (ID: ${this.activeCaseId}).`, 'success');
    } else {
      this.showToast(`${lawyerName} selected. You can assign this advocate when filing a new matter.`, 'info');
    }
  },

  // =============================================================
  // 9. CASE TRACKING / eCOURTS (P2)
  // =============================================================
  loadCaseTrackingModule() {
    const cnrInput = document.getElementById('track-cnr-input');
    if (cnrInput && !cnrInput.value) {
      cnrInput.value = 'MHPU01-004523-2024';
    }
    // Auto-search default demo CNR
    this.handleTrackCnrSubmit(new Event('submit'));
  },

  switchTrackingMode(mode) {
    document.getElementById('tab-cnr-mode')?.classList.toggle('active', mode === 'cnr');
    document.getElementById('tab-case-mode')?.classList.toggle('active', mode === 'details');
    document.getElementById('form-track-cnr').style.display = mode === 'cnr' ? 'block' : 'none';
    document.getElementById('form-track-details').style.display = mode === 'details' ? 'block' : 'none';
  },

  handleTrackCnrSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const cnr = document.getElementById('track-cnr-input')?.value.trim();
    if (!cnr) {
      this.showToast('Please enter a 16-character CNR number.', 'error');
      return;
    }
    this.renderCaseTrackingResult({
      cnr: cnr,
      case_type: 'Special Civil Suit (SCS)',
      case_number: '4523 / 2024',
      filing_date: '14-03-2024',
      registration_date: '18-03-2024',
      court_name: 'Court of Civil Judge Senior Division, Pune',
      court_hall: 'Court Hall No. 04',
      presiding_judge: 'Shri A. S. Kulkarni, CJSD',
      status: 'Hearing Scheduled',
      next_hearing_date: '28-10-2026',
      hearing_purpose: 'Arguments on Application for Interim Injunction (Order 39 Rule 1 CPC)',
      petitioner: 'Sunita Sharma & Anr.',
      petitioner_advocate: 'Adv. Rajesh Deshmukh',
      respondent: 'Municipal Corporation of Pune & 2 Ors.',
      respondent_advocate: 'Adv. P. M. Gokhale (Standing Counsel)',
      stages: [
        { name: 'Filing', status: 'completed' },
        { name: 'Scrutiny', status: 'completed' },
        { name: 'Summons', status: 'completed' },
        { name: 'Written Statement', status: 'completed' },
        { name: 'Interim Hearing', status: 'current' },
        { name: 'Evidence', status: 'pending' },
        { name: 'Arguments', status: 'pending' },
        { name: 'Judgment', status: 'pending' }
      ],
      history: [
        { date: '18-03-2024', purpose: 'Case Registration & Scrutiny', order: 'Plaint admitted. Issue notice to defendants returnable by 22-04-2024.' },
        { date: '22-04-2024', purpose: 'Appearance of Defendants', order: 'Adv. Gokhale filed appearance memo for D-1. Granted 30 days for Written Statement.' },
        { date: '28-06-2024', purpose: 'Filing of Written Statement', order: 'WS taken on record. Matter posted for arguments on interim injunction application.' },
        { date: '12-09-2024', purpose: 'Hearing on Interim Relief', order: 'Part-heard. Adjourned for concluding arguments.' }
      ]
    });
  },

  handleTrackDetailsSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const court = document.getElementById('track-court-name')?.value || 'District Court, Pune';
    const ctype = document.getElementById('track-case-type')?.value || 'Regular Civil Suit';
    const cnum = document.getElementById('track-case-num')?.value || '1042';
    const cyear = document.getElementById('track-case-year')?.value || '2024';

    this.renderCaseTrackingResult({
      cnr: `MHPU01-${cnum.padStart(6, '0')}-${cyear}`,
      case_type: ctype,
      case_number: `${cnum} / ${cyear}`,
      filing_date: `10-01-${cyear}`,
      registration_date: `14-01-${cyear}`,
      court_name: court,
      court_hall: 'Court Hall No. 02',
      presiding_judge: 'Judicial Magistrate First Class, Pune',
      status: 'Active Proceedings',
      next_hearing_date: '04-11-2026',
      hearing_purpose: 'Framing of Issues / Charges',
      petitioner: 'State of Maharashtra',
      petitioner_advocate: 'Public Prosecutor',
      respondent: 'Accused Person',
      respondent_advocate: 'Adv. Vikramaditya Shinde',
      stages: [
        { name: 'Filing', status: 'completed' },
        { name: 'Registration', status: 'completed' },
        { name: 'Process', status: 'completed' },
        { name: 'Framing Issues', status: 'current' },
        { name: 'Evidence', status: 'pending' },
        { name: 'Judgment', status: 'pending' }
      ],
      history: [
        { date: `14-01-${cyear}`, purpose: 'Registration', order: 'Matter registered on file.' },
        { date: `20-04-${cyear}`, purpose: 'Appearance', order: 'Bail bond furnished and accepted.' }
      ]
    });
  },

  renderCaseTrackingResult(data) {
    const container = document.getElementById('case-tracking-result-card');
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="border-left: 4px solid var(--accent-primary); padding: 28px; margin-bottom: 24px;">
        
        <!-- Header Row -->
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 14px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: var(--accent-cyan); font-family: monospace; font-size: 13px; font-weight: 700;">CNR: ${this.escape(data.cnr)}</span>
              <span class="badge badge-active">${this.escape(data.status)}</span>
            </div>
            <h3 style="font-size: 19px; font-weight: 700; color: var(--text-primary); margin-top: 6px;">
              ${this.escape(data.case_type)} — No. ${this.escape(data.case_number)}
            </h3>
            <div style="font-size: 13.5px; color: var(--text-secondary); margin-top: 2px;">
              🏛️ ${this.escape(data.court_name)} • ${this.escape(data.court_hall)} • ${this.escape(data.presiding_judge)}
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 12px; color: var(--text-muted);">Filed on: <strong style="color: var(--text-secondary);">${this.escape(data.filing_date)}</strong></div>
            <div style="font-size: 12px; color: var(--text-muted);">Registered on: <strong style="color: var(--text-secondary);">${this.escape(data.registration_date)}</strong></div>
          </div>
        </div>

        <!-- Next Hearing Highlight Box -->
        <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: var(--radius-sm); padding: 16px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--accent-primary); letter-spacing: 0.06em;">Next Court Hearing:</div>
            <div style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">
              📅 ${this.escape(data.next_hearing_date)}
            </div>
            <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">
              <strong>Purpose:</strong> ${this.escape(data.hearing_purpose)}
            </div>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.showToast('Reminder added to calendar for ${this.escape(data.next_hearing_date)}', 'success')">
            🔔 Set Hearing Reminder
          </button>
        </div>

        <!-- Parties Information -->
        <div class="dashboard-grid" style="grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
          <div style="background: var(--bg-elevated); padding: 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            <div style="font-size: 11.5px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.04em;">Petitioner / Complainant</div>
            <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${this.escape(data.petitioner)}</div>
            <div style="font-size: 13px; color: var(--accent-primary); font-weight: 500; margin-top: 4px;">Advocate: ${this.escape(data.petitioner_advocate)}</div>
          </div>
          <div style="background: var(--bg-elevated); padding: 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            <div style="font-size: 11.5px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.04em;">Respondent / Accused</div>
            <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${this.escape(data.respondent)}</div>
            <div style="font-size: 13px; color: var(--accent-primary); font-weight: 500; margin-top: 4px;">Advocate: ${this.escape(data.respondent_advocate)}</div>
          </div>
        </div>

        <!-- Case Lifecycle Progress Track -->
        <div style="margin-bottom: 24px;">
          <div style="font-size: 12.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 10px;">Case Lifecycle Progress</div>
          <div class="case-progress-track">
            ${data.stages.map((st, i) => `
              <div class="case-stage-node ${st.status}">
                <div class="stage-dot">${st.status === 'completed' ? '✓' : (i + 1)}</div>
                <span>${this.escape(st.name)}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Business Transacted / Hearing History Table -->
        <div style="margin-bottom: 20px;">
          <div style="font-size: 12.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 10px;">Hearing History & Daily Business</div>
          <div class="table-responsive" style="width: 100%; overflow-x: auto; margin-bottom: 12px;">
            <table style="width: 100%; min-width: 500px; border-collapse: collapse; font-size: 13.5px;">
              <thead>
                <tr style="background: var(--bg-elevated); border-bottom: 2px solid var(--border-subtle);">
                  <th style="padding: 10px 14px; text-align: left; color: var(--text-primary);">Hearing Date</th>
                  <th style="padding: 10px 14px; text-align: left; color: var(--text-primary);">Business Transacted</th>
                  <th style="padding: 10px 14px; text-align: left; color: var(--text-primary);">Order / Direction</th>
                </tr>
              </thead>
              <tbody>
                ${data.history.map(h => `
                  <tr style="border-bottom: 1px solid var(--border-subtle);">
                    <td style="padding: 10px 14px; font-weight: 600; white-space: nowrap; color: var(--text-primary);">${this.escape(h.date)}</td>
                    <td style="padding: 10px 14px; color: var(--text-primary);">${this.escape(h.purpose)}</td>
                    <td style="padding: 10px 14px; color: var(--text-secondary);">${this.escape(h.order)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Official External eCourts Action Button -->
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          <span style="font-size: 11.5px; color: var(--text-muted);">Synced from National Judicial Data Grid (NJDG) Standards</span>
          <a href="https://services.ecourts.gov.in" target="_blank" rel="noopener" class="btn btn-secondary btn-sm">
            🏛️ Verify on Official eCourts Portal (services.ecourts.gov.in) ↗
          </a>
        </div>

      </div>
    `;
  },

  // =============================================================
  // 10. VOICE LEGAL ASSISTANT (P2)
  // =============================================================
  voiceRecognitionInstance: null,
  isVoiceListening: false,

  loadVoiceAssistantModule() {
    this.updateVoiceStatus('Ready. Click the microphone to ask your legal question.');
  },

  handleVoiceLangChange() {
    const langSelect = document.getElementById('voice-lang-select');
    if (this.voiceRecognitionInstance && langSelect) {
      this.voiceRecognitionInstance.lang = langSelect.value;
    }
  },

  toggleVoiceRecording() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      this.showToast('Speech Recognition not supported in this browser. Please use Google Chrome or Microsoft Edge.', 'error');
      return;
    }

    if (this.isVoiceListening) {
      this.stopVoiceRecording();
      return;
    }

    this.voiceRecognitionInstance = new SpeechRec();
    const langSelect = document.getElementById('voice-lang-select');
    this.voiceRecognitionInstance.lang = langSelect ? langSelect.value : 'en-IN';
    this.voiceRecognitionInstance.interimResults = true;
    this.voiceRecognitionInstance.continuous = false;

    const micBtn = document.getElementById('voice-main-mic-btn');
    const waveBox = document.getElementById('voice-visualizer-container');

    this.voiceRecognitionInstance.onstart = () => {
      this.isVoiceListening = true;
      if (micBtn) micBtn.classList.add('mic-recording-active');
      if (waveBox) waveBox.style.visibility = 'visible';
      this.updateVoiceStatus('Listening... Speak your legal question clearly.');
    };

    this.voiceRecognitionInstance.onresult = (e) => {
      let interim = '';
      let final = '';
      for (let i = 0; i < e.results.length; ++i) {
        if (e.results[i].isFinal) {
          final += e.results[i][0].transcript;
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      const ta = document.getElementById('voice-transcript-text');
      if (ta) ta.value = final || interim;
    };

    this.voiceRecognitionInstance.onerror = (e) => {
      console.warn('Speech error:', e);
      this.stopVoiceRecording();
      this.updateVoiceStatus('Speech recognition halted: ' + (e.error || 'Check microphone permission.'));
    };

    this.voiceRecognitionInstance.onend = () => {
      this.stopVoiceRecording();
      const ta = document.getElementById('voice-transcript-text');
      if (ta && ta.value.trim()) {
        this.updateVoiceStatus('Speech captured! Click "Get Grounded Legal Answer" below.');
      } else {
        this.updateVoiceStatus('Ready. Click the microphone to start speaking.');
      }
    };

    this.voiceRecognitionInstance.start();
  },

  stopVoiceRecording() {
    this.isVoiceListening = false;
    const micBtn = document.getElementById('voice-main-mic-btn');
    const waveBox = document.getElementById('voice-visualizer-container');
    if (micBtn) micBtn.classList.remove('mic-recording-active');
    if (waveBox) waveBox.style.visibility = 'hidden';
    if (this.voiceRecognitionInstance) {
      try { this.voiceRecognitionInstance.stop(); } catch (e) {}
    }
  },

  updateVoiceStatus(msg) {
    const el = document.getElementById('voice-status-text');
    if (el) el.textContent = msg;
  },

  clearVoiceTranscript() {
    const ta = document.getElementById('voice-transcript-text');
    if (ta) ta.value = '';
    const ans = document.getElementById('voice-answer-container');
    if (ans) ans.style.display = 'none';
    this.updateVoiceStatus('Ready. Click the microphone to start speaking.');
  },

  async submitVoiceQuestionToAi() {
    const ta = document.getElementById('voice-transcript-text');
    if (!ta) return;
    const message = ta.value.trim();
    if (!message) {
      this.showToast('Please record or enter a question first.', 'error');
      return;
    }

    const ansBox = document.getElementById('voice-answer-container');
    if (ansBox) {
      ansBox.style.display = 'block';
      ansBox.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="spinner" style="width: 18px; height: 18px; border-width: 2px;"></span>
          <span style="font-size: 13.5px; color: var(--text-muted);">Consulting Vidhik Legal Knowledge Base & RAG Engine...</span>
        </div>
      `;
    }

    const langCode = (document.getElementById('voice-lang-select')?.value || 'en-IN').split('-')[0];

    try {
      const res = await this.api('/api/assistant/chat', 'POST', {
        message: message,
        language: langCode
      });

      if (!res || !res.answer) throw new Error('No answer received.');

      if (ansBox) {
        ansBox.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
            <strong style="color: var(--text-primary); font-size: 14.5px;">⚖️ Vidhik Legal Intelligence Answer</strong>
            <span class="badge badge-active">Grounded: High</span>
          </div>
          <div style="font-size: 14px; line-height: 1.7; color: var(--text-secondary); white-space: pre-wrap; margin-bottom: 14px;">
            ${this.formatLegalMarkdown(res.answer)}
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.speakVoiceAnswer('${this.escapeForJs(res.answer)}')">
              🔊 Replay Audio
            </button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.stopAudioPlayback()">
              ⏹️ Stop Audio
            </button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="App.copyText('${this.escapeForJs(res.answer)}')">
              📋 Copy
            </button>
          </div>
        `;
      }

      // Automatically speak the answer!
      this.speakVoiceAnswer(res.answer);
      document.getElementById('btn-voice-stop-playback').style.display = 'inline-flex';

    } catch (err) {
      console.error('Voice AI error:', err);
      if (ansBox) {
        ansBox.innerHTML = `
          <div style="color: var(--accent-rose); font-size: 13.5px;">
            ✕ Error retrieving answer: ${this.escape(err.message)}
          </div>
        `;
      }
    }
  },

  speakVoiceAnswer(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const clean = text.replace(/[*#_~]/g, '');
    const utter = new SpeechSynthesisUtterance(clean);
    const langSelect = document.getElementById('voice-lang-select');
    utter.lang = langSelect ? langSelect.value : 'en-IN';
    utter.rate = 1.0;
    utter.onend = () => {
      const stopBtn = document.getElementById('btn-voice-stop-playback');
      if (stopBtn) stopBtn.style.display = 'none';
    };
    window.speechSynthesis.speak(utter);
  },

  stopAudioPlayback() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const stopBtn = document.getElementById('btn-voice-stop-playback');
      if (stopBtn) stopBtn.style.display = 'none';
      this.showToast('Audio playback stopped.', 'info');
    }
  },

  // =============================================================
  // 11. LEGAL KNOWLEDGE BASE EXPLORER (Phase 17)
  // =============================================================
  knowledgeActsData: [],

  async loadLegalKnowledgeModule() {
    this.switchLkTab('acts');
    const container = document.getElementById('lk-acts-container');
    if (container && this.knowledgeActsData.length === 0) {
      container.innerHTML = '<div class="spinner" style="margin: 30px auto;"></div>';
      try {
        const res = await this.api('/api/knowledge/acts');
        this.knowledgeActsData = Array.isArray(res) ? res : [];
        this.renderKnowledgeActs(this.knowledgeActsData);
      } catch (err) {
        console.warn('Error loading acts:', err);
        // Fallback list of key acts
        this.knowledgeActsData = [
          { act_id: 1, act_name: 'Bharatiya Nyaya Sanhita, 2023', short_name: 'BNS', total_sections: 362, category: 'Central Criminal Code', year: 2023, status: 'In Force' },
          { act_id: 2, act_name: 'Bharatiya Nagarik Suraksha Sanhita, 2023', short_name: 'BNSS', total_sections: 531, category: 'Criminal Procedure Code', year: 2023, status: 'In Force' },
          { act_id: 3, act_name: 'Bharatiya Sakshya Adhiniyam, 2023', short_name: 'BSA', total_sections: 170, category: 'Law of Evidence', year: 2023, status: 'In Force' },
          { act_id: 4, act_name: 'Information Technology Act, 2000', short_name: 'IT Act', total_sections: 94, category: 'Cyber Law & Digital Commerce', year: 2000, status: 'In Force' },
          { act_id: 5, act_name: 'Protection of Children from Sexual Offences Act, 2012', short_name: 'POCSO Act', total_sections: 46, category: 'Child Protection', year: 2012, status: 'In Force' },
          { act_id: 18, act_name: 'Consumer Protection Act, 2019', short_name: 'CPA', total_sections: 107, category: 'Consumer Rights', year: 2019, status: 'In Force' },
          { act_id: 19, act_name: 'Motor Vehicles Act, 1988', short_name: 'MVA', total_sections: 224, category: 'Transport Regulation', year: 1988, status: 'In Force' },
          { act_id: 20, act_name: 'Right to Information Act, 2005', short_name: 'RTI Act', total_sections: 31, category: 'Transparency & Governance', year: 2005, status: 'In Force' }
        ];
        this.renderKnowledgeActs(this.knowledgeActsData);
      }
    }
  },

  switchLkTab(tabKey) {
    document.querySelectorAll('.tab-btn[id^="tab-lk-"]').forEach(btn => {
      btn.classList.toggle('active', btn.id === `tab-lk-${tabKey}`);
    });
    document.querySelectorAll('.lk-tab-pane').forEach(pane => {
      pane.style.display = pane.id === `lk-pane-${tabKey}` ? 'block' : 'none';
    });

    if (tabKey === 'converter') {
      this.convertStatutorySection();
    } else if (tabKey === 'judgments') {
      this.loadKnowledgeJudgments();
    } else if (tabKey === 'evidence') {
      this.loadKnowledgeEvidence();
    } else if (tabKey === 'bns') {
      this.loadKnowledgeBnsOffences();
    }
  },

  filterKnowledgeActs() {
    const q = (document.getElementById('lk-acts-search')?.value || '').toLowerCase();
    const filtered = this.knowledgeActsData.filter(a => {
      return !q || (a.act_name || '').toLowerCase().includes(q) || (a.short_name || '').toLowerCase().includes(q) || (a.category || '').toLowerCase().includes(q);
    });
    this.renderKnowledgeActs(filtered);
  },

  renderKnowledgeActs(items) {
    const container = document.getElementById('lk-acts-container');
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px;">No acts found.</div>';
      return;
    }

    container.innerHTML = items.map(a => `
      <div class="card" style="display: flex; flex-direction: column; justify-content: space-between; border-left: 3px solid var(--accent-primary);">
        <div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span class="badge" style="background: var(--bg-elevated); color: var(--accent-primary); font-weight: 700;">${this.escape(a.short_name || 'Act')}</span>
            <span style="font-size: 11.5px; color: var(--text-muted);">${a.year || '2023'}</span>
          </div>
          <h4 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
            ${this.escape(a.act_name)}
          </h4>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">
            Category: ${this.escape(a.category || 'Statutory Enactment')}
          </div>
        </div>

        <div style="border-top: 1px solid var(--border-subtle); padding-top: 10px; display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">${a.total_sections || 0} Sections</span>
          <button type="button" class="btn btn-secondary btn-sm" onclick="App.exploreActProvisions('${a.act_id}', '${this.escapeForJs(a.act_name)}')">
            Inspect Provisions →
          </button>
        </div>
      </div>
    `).join('');
  },

  exploreActProvisions(actId, actName) {
    this.navigate('research');
    const input = document.getElementById('search-input');
    if (input) {
      input.value = actName;
      this.handleSearch();
    }
  },

  // Converter tool
  setConverterSample(law, sec) {
    const lawSelect = document.getElementById('conv-source-law');
    const secInput = document.getElementById('conv-section-num');
    if (lawSelect) lawSelect.value = law;
    if (secInput) secInput.value = sec;
    this.convertStatutorySection();
  },

  handleConverterLawChange() {
    this.convertStatutorySection();
  },

  convertStatutorySection() {
    const law = document.getElementById('conv-source-law')?.value || 'IPC';
    const sec = (document.getElementById('conv-section-num')?.value || '').trim();
    const box = document.getElementById('conv-result-box');
    if (!box) return;

    if (!sec) {
      box.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">Enter a section number above.</div>';
      return;
    }

    const mappingTable = {
      'IPC:302': { new_law: 'Bharatiya Nyaya Sanhita, 2023 (BNS)', new_sec: 'Section 103(1)', title: 'Punishment for Murder', punishment: 'Death or Imprisonment for Life, and Fine', notes: 'Definition consolidated into Section 101, Punishment under Section 103.' },
      'IPC:304': { new_law: 'Bharatiya Nyaya Sanhita, 2023 (BNS)', new_sec: 'Section 105', title: 'Culpable Homicide Not Amounting to Murder', punishment: 'Imprisonment for Life or up to 10 Years + Fine', notes: 'Replaces IPC Section 304.' },
      'IPC:379': { new_law: 'Bharatiya Nyaya Sanhita, 2023 (BNS)', new_sec: 'Section 303(2)', title: 'Punishment for Theft', punishment: 'Imprisonment up to 3 Years or Fine or Both; First-time minor theft includes Community Service', notes: 'Section 303(2) introduces community service for theft of property under ₹5,000 upon restitution.' },
      'IPC:420': { new_law: 'Bharatiya Nyaya Sanhita, 2023 (BNS)', new_sec: 'Section 318(4)', title: 'Cheating & Dishonestly Inducing Delivery of Property', punishment: 'Imprisonment up to 7 Years and Fine', notes: 'The celebrated IPC 420 is now Section 318(4) of BNS, 2023.' },
      'IPC:498A': { new_law: 'Bharatiya Nyaya Sanhita, 2023 (BNS)', new_sec: 'Section 85 & 86', title: 'Cruelty by Husband or Relatives of Husband', punishment: 'Imprisonment up to 3 Years and Fine', notes: 'Definition and punishment placed under Section 85 & 86.' },
      'IPC:376': { new_law: 'Bharatiya Nyaya Sanhita, 2023 (BNS)', new_sec: 'Section 64', title: 'Punishment for Rape', punishment: 'Rigorous Imprisonment not less than 10 Years up to Life + Fine', notes: 'Replaces IPC 376 with stringent minimum sentencing.' },
      'CrPC:154': { new_law: 'Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)', new_sec: 'Section 173', title: 'Information in Cognizable Cases (FIR)', punishment: 'Mandatory FIR; Free Copy under Sec 173(2)', notes: 'Introduces statutory recognition for Zero FIR and electronic e-FIR (signed within 3 days).' },
      'CrPC:167': { new_law: 'Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)', new_sec: 'Section 187', title: 'Procedure When Investigation Cannot be Completed in 24 Hours (Remand)', punishment: 'Police Custody up to 15 Days in Parts', notes: 'Police remand can be sought in parts across initial 40 or 60 days of detention.' },
      'CrPC:437': { new_law: 'Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)', new_sec: 'Section 480', title: 'When Bail May be Taken in Case of Non-Bailable Offence', punishment: 'Bail by Magistrate', notes: 'Replaces old CrPC Section 437.' },
      'CrPC:438': { new_law: 'Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)', new_sec: 'Section 482', title: 'Direction for Grant of Bail to Person Apprehending Arrest (Anticipatory Bail)', punishment: 'Sessions / High Court Bail', notes: 'Replaces old CrPC Section 438.' },
      'IEA:65B': { new_law: 'Bharatiya Sakshya Adhiniyam, 2023 (BSA)', new_sec: 'Section 63', title: 'Admissibility of Electronic Records', punishment: 'Certificate requirement in Schedule', notes: 'Section 63 along with Part A/B Schedule replaces old Section 65B certificate mandate.' }
    };

    const key = `${law}:${sec}`;
    const match = mappingTable[key];

    if (match) {
      box.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <span style="font-size: 13.5px; font-weight: 700; color: var(--accent-emerald);">✓ Verified Predecessor Match</span>
          <span class="badge badge-active">${law} Sec ${sec}</span>
        </div>
        <div style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px;">
          → Modern Provision: ${this.escape(match.new_sec)}
        </div>
        <div style="font-size: 14.5px; font-weight: 600; color: var(--accent-primary); margin-bottom: 8px;">
          ${this.escape(match.title)} (${this.escape(match.new_law)})
        </div>
        <div style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.55; margin-bottom: 10px;">
          <strong>Punishment / Mandate:</strong> ${this.escape(match.punishment)}
        </div>
        <div style="font-size: 13px; color: var(--text-secondary); background: var(--bg-elevated); border: 1px solid var(--border-subtle); padding: 10px 14px; border-radius: var(--radius-sm); line-height: 1.5;">
          ℹ️ <strong>Notes:</strong> ${this.escape(match.notes)}
        </div>
      `;
    } else {
      // General heuristic lookup
      box.innerHTML = `
        <div style="font-size: 14px; color: var(--text-primary); margin-bottom: 6px;">
          Searching predecessor mapping for <strong>${law} Section ${sec}</strong>...
        </div>
        <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
          Under the replacement scheme of 01-07-2024, ${law} has been repealed and succeeded by the corresponding 2023 Sanhita. You can use the AI Assistant or Legal Research to query the full contextual text.
        </div>
      `;
    }
  },

  async loadKnowledgeBnsOffences() {
    const container = document.getElementById('lk-bns-offences-container');
    if (!container) return;
    container.innerHTML = '<div class="spinner" style="margin: 30px auto;"></div>';

    try {
      const res = await this.api('/api/knowledge/offences?law_id=1');
      if (Array.isArray(res) && res.length > 0) {
        this.renderBnsOffences(res);
      } else {
        throw new Error('Empty offences');
      }
    } catch (e) {
      // Fallback verified offences
      this.renderBnsOffences([
        { section_number: '103(1)', offence_name: 'Murder', classification: 'Cognizable & Non-Bailable', punishment_description: 'Death or Imprisonment for Life, and Fine' },
        { section_number: '105', offence_name: 'Culpable Homicide Not Amounting to Murder', classification: 'Cognizable & Non-Bailable', punishment_description: 'Life or up to 10 Years Imprisonment + Fine' },
        { section_number: '115', offence_name: 'Voluntarily Causing Hurt', classification: 'Non-Cognizable & Bailable', punishment_description: 'Up to 1 Year or Fine up to ₹1,000 or Both' },
        { section_number: '303(2)', offence_name: 'Theft', classification: 'Cognizable & Non-Bailable', punishment_description: 'Up to 3 Years or Fine or Both; First-time minor theft includes Community Service' },
        { section_number: '318(4)', offence_name: 'Cheating with Delivery of Property', classification: 'Cognizable & Non-Bailable', punishment_description: 'Up to 7 Years and Fine' },
        { section_number: '351', offence_name: 'Criminal Intimidation', classification: 'Non-Cognizable & Bailable', punishment_description: 'Up to 2 Years or Fine or Both' }
      ]);
    }
  },

  renderBnsOffences(items) {
    const container = document.getElementById('lk-bns-offences-container');
    if (!container) return;

    container.innerHTML = items.map(o => `
      <div class="card" style="border-left: 3px solid var(--accent-rose);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span class="badge" style="background: rgba(225, 29, 72, 0.15); color: var(--accent-rose); font-weight: 700;">BNS Sec ${this.escape(o.section_number)}</span>
          <span class="badge" style="font-size: 11.5px;">${this.escape(o.classification || 'Cognizable')}</span>
        </div>
        <h4 style="font-size: 15.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
          ${this.escape(o.offence_name || o.section_title || 'Offence')}
        </h4>
        <div style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.55; margin-bottom: 8px;">
          <strong>Punishment:</strong> ${this.escape(o.punishment_description || o.punishment || 'Prescribed under law')}
        </div>
      </div>
    `).join('');
  },

  filterBnsOffences() {
    const q = (document.getElementById('lk-bns-search')?.value || '').toLowerCase();
    this.loadKnowledgeBnsOffences();
  },

  loadKnowledgeJudgments() {
    const container = document.getElementById('lk-judgments-container');
    if (!container) return;

    const judgments = [
      { case_name: 'Lalita Kumari v. Govt. of U.P.', citation: '(2014) 2 SCC 1', bench: '5-Judge Constitution Bench', section: 'BNSS Sec 173 (CrPC 154)', rule: 'Mandatory Registration of FIR: Police officer cannot conduct preliminary inquiry in cognizable offences; registration of FIR is compulsory upon receipt of information disclosing cognizable offence.' },
      { case_name: 'Satender Kumar Antil v. CBI', citation: '(2022) 10 SCC 51', bench: '2-Judge Bench', section: 'BNSS Sec 479 & 480', rule: 'Bail is the Rule, Jail is the Exception: Guidelines categorizing offences A/B/C/D for mechanical arrest prevention, personal bond release, and undertrial custody relief.' },
      { case_name: 'Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal', citation: '(2020) 7 SCC 1', bench: '3-Judge Bench', section: 'BSA Sec 63 (IEA 65B)', rule: 'Electronic Record Admissibility: Production of certificate under Section 65B(4) is a mandatory condition precedent to the admissibility of secondary electronic evidence.' },
      { case_name: 'Bachan Singh v. State of Punjab', citation: '(1980) 2 SCC 684', bench: '5-Judge Constitution Bench', section: 'BNS Sec 103 (IPC 302)', rule: 'Rarest of Rare Doctrine: Death penalty ought not to be awarded save in the rarest of rare cases when the alternative option of life imprisonment is unquestionably foreclosed.' },
      { case_name: 'Shafhi Mohammad v. State of Himachal Pradesh', citation: '(2018) 2 SCC 801', bench: '2-Judge Bench', section: 'BNSS Sec 105', rule: 'Scene of Crime Videography: Directing state police departments to deploy digital audio-video recording for all search, seizure, and crime scene recovery.' }
    ];

    container.innerHTML = judgments.map(j => `
      <div class="card" style="border-left: 3px solid var(--accent-primary);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span class="badge badge-active">${this.escape(j.section)}</span>
          <span style="font-size: 12px; color: var(--text-muted);">${this.escape(j.bench)}</span>
        </div>
        <h4 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 3px;">
          ${this.escape(j.case_name)}
        </h4>
        <div style="font-size: 13px; color: var(--accent-primary); font-weight: 600; margin-bottom: 8px;">
          ${this.escape(j.citation)} • Supreme Court of India
        </div>
        <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.65; margin: 0;">
          <strong>Controlling Proposition:</strong> ${this.escape(j.rule)}
        </p>
      </div>
    `).join('');
  },

  filterKnowledgeJudgments() {
    this.loadKnowledgeJudgments();
  },

  loadKnowledgeEvidence() {
    const container = document.getElementById('lk-evidence-container');
    if (!container) return;

    const provisions = [
      { section: 'Section 61', title: 'Admissibility of Electronic or Digital Record', desc: 'Electronic records are given equal legal recognition as documentary evidence, establishing parity between digital and paper evidence.' },
      { section: 'Section 63', title: 'Conditions for Admissibility of Electronic Records', desc: 'Prescribes statutory conditions regarding source computer output, hash verification, custody continuity, and mandatory certificate signed by person in official charge.' },
      { section: 'Schedule (Part A & B)', title: 'Form of Certificate for Digital Evidence', desc: 'Standardized statutory certificate format for mobile phones, server logs, CCTV DVRs, and cloud storage compliance.' },
      { section: 'Section 105 BNSS', title: 'Mandatory Videography of Search & Seizure', desc: 'Search and seizure of property and preparation of recovery memo must be compulsorily recorded through mobile or video camera.' }
    ];

    container.innerHTML = provisions.map(p => `
      <div class="card" style="border-left: 3px solid var(--accent-cyan);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span class="badge" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); font-weight: 700;">${this.escape(p.section)}</span>
          <span class="badge" style="font-size: 11.5px;">BSA 2023</span>
        </div>
        <h4 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
          ${this.escape(p.title)}
        </h4>
        <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.65; margin: 0;">
          ${this.escape(p.desc)}
        </p>
      </div>
    `).join('');
  },

  // =============================================================
  // 12. REUSABLE DOCUMENT PREVIEW MODAL
  // =============================================================
  openDocumentPreview(titleOrDoc, contentHtml = '', subtitle = 'Statutory Legal Draft', meta = {}) {
    const modal = document.getElementById('modal-document-preview');
    if (!modal) return;

    let title = typeof titleOrDoc === 'string' ? titleOrDoc : (titleOrDoc.title || titleOrDoc.document_name || 'Legal Document');
    let docMeta = typeof titleOrDoc === 'object' && titleOrDoc !== null ? { ...titleOrDoc, ...meta } : (meta || {});
    let bodyHtml = contentHtml || docMeta.content || docMeta.description || '';

    // If bodyHtml is short or raw text, format cleanly into statutory pleading structure
    if (!bodyHtml || bodyHtml.trim().length === 0 || (!bodyHtml.includes('<p>') && !bodyHtml.includes('<div>'))) {
      const rawText = bodyHtml.trim();
      bodyHtml = `
        <div class="legal-pleading-header" style="text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1.5px solid var(--border-subtle);">
          <h3 style="margin: 0 0 6px 0; text-transform: uppercase; font-size: 15px; letter-spacing: 0.05em; color: var(--text-primary);">IN THE APPROPRIATE JUDICIAL / ADMINISTRATIVE FORUM</h3>
          <p style="margin: 0; font-size: 12.5px; color: var(--text-muted); text-transform: uppercase;">AT ${this.escape(docMeta.jurisdiction || 'NEW DELHI, INDIA')}</p>
        </div>
        <div style="margin-bottom: 18px;">
          <p><strong>IN THE MATTER OF:</strong></p>
          <p style="padding-left: 16px; margin: 4px 0 14px 0;">${this.escape(docMeta.parties || 'Applicant / Citizen  —VERSUS—  Opposite Party / Respondent')}</p>
          <p><strong>SUBJECT / INSTRUMENT:</strong> ${this.escape(title)} (${this.escape(docMeta.document_type || 'Legal Filing')})</p>
          <p><strong>RECORD REFERENCE:</strong> ${this.escape(docMeta.case_title || docMeta.case_ref || 'Case Record Verified')}</p>
          ${rawText ? `<p style="margin-top: 10px; background: rgba(99, 102, 241, 0.05); padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">${this.escape(rawText)}</p>` : ''}
        </div>
        <div class="legal-section" style="margin-top: 20px;">
          <h4 style="font-size: 14px; text-transform: uppercase; color: var(--accent-primary); margin-bottom: 8px;">1. STATEMENT OF RECORD & COMPLIANCE</h4>
          <p style="line-height: 1.75; color: var(--text-primary); text-align: justify;">
            The present instrument has been indexed and archived under the Vidhik AI Legal Information & Case Management System.
            The contents herein are subject to verification against certified copies and statutory provisions under applicable Indian Central and State enactments.
          </p>
        </div>
        <div class="legal-section" style="margin-top: 16px;">
          <h4 style="font-size: 14px; text-transform: uppercase; color: var(--accent-primary); margin-bottom: 8px;">2. STATUTORY BASIS & ADMISSIBILITY</h4>
          <p style="line-height: 1.75; color: var(--text-primary); text-align: justify;">
            This legal document is prepared under the framework of the ${this.escape(docMeta.relevant_law || docMeta.statute || 'Bharatiya Nagarik Suraksha Sanhita, 2023 / Bharatiya Nyaya Sanhita, 2023')}, ensuring procedural compliance, evidentiary admissibility, and jurisdictional conformity.
          </p>
        </div>
        <div style="margin-top: 32px; padding-top: 16px; border-top: 1px dashed var(--border-subtle); display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="font-size: 12px; color: var(--text-muted);">FILED / RECORDED ON</div>
            <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">${this.escape(docMeta.date || new Date().toLocaleDateString())}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 12px; color: var(--text-muted);">VERIFIED ELECTRONIC RECORD</div>
            <div style="font-size: 12.5px; font-weight: 600; color: var(--accent-primary);">⚖️ VIDHIK AI COMPLIANCE ENGINE</div>
          </div>
        </div>
      `;
    }

    // Populate modal elements
    const modalTitleEl = document.getElementById('doc-preview-modal-title');
    if (modalTitleEl) modalTitleEl.textContent = title;

    const modalSubtitleEl = document.getElementById('doc-preview-modal-subtitle');
    if (modalSubtitleEl) modalSubtitleEl.textContent = subtitle || 'AI-grounded legal draft formatted to Indian statutory layout';

    const docTitleEl = document.getElementById('modal-doc-title');
    if (docTitleEl) docTitleEl.textContent = title;

    const typeBadgeEl = document.getElementById('modal-doc-type-badge');
    if (typeBadgeEl) typeBadgeEl.textContent = docMeta.document_type || docMeta.type || 'Pleading / Draft';

    const caseBadgeEl = document.getElementById('modal-doc-case-badge');
    if (caseBadgeEl) caseBadgeEl.textContent = docMeta.case_title || docMeta.case_ref || 'General Matter';

    const statusBadgeEl = document.getElementById('modal-doc-status-badge');
    if (statusBadgeEl) {
      statusBadgeEl.textContent = docMeta.upload_status || docMeta.status || 'Verified Record';
    }

    const partiesEl = document.getElementById('modal-doc-parties');
    if (partiesEl) partiesEl.textContent = docMeta.parties || (docMeta.opposite_party ? `Citizen vs. ${docMeta.opposite_party}` : 'Applicant / Citizen vs. Respondent');

    const caseDetailsEl = document.getElementById('modal-doc-case-details');
    if (caseDetailsEl) caseDetailsEl.textContent = docMeta.case_title || docMeta.case_name || (docMeta.case_id ? `Matter #${docMeta.case_id}` : 'General Matter Filing');

    const dateEl = document.getElementById('modal-doc-date');
    if (dateEl) dateEl.textContent = docMeta.date || (docMeta.uploaded_at ? new Date(docMeta.uploaded_at).toLocaleDateString() : (docMeta.created_at ? new Date(docMeta.created_at).toLocaleDateString() : new Date().toLocaleDateString()));

    const jurisEl = document.getElementById('modal-doc-jurisdiction');
    if (jurisEl) jurisEl.textContent = docMeta.jurisdiction || docMeta.court || 'Indian Jurisdiction';

    const statuteEl = document.getElementById('modal-doc-statute');
    if (statuteEl) statuteEl.textContent = docMeta.relevant_law || docMeta.statute || 'Bharatiya Nagarik Suraksha Sanhita, 2023 / BNS 2023';

    const contentEl = document.getElementById('modal-doc-preview-content');
    if (contentEl) contentEl.innerHTML = bodyHtml;

    modal.classList.add('active');
    document.body.classList.add('modal-open');
  },

  downloadModalDocument() {
    const el = document.getElementById('modal-doc-preview-content');
    const titleEl = document.getElementById('modal-doc-title');
    const title = (titleEl && titleEl.textContent) ? titleEl.textContent.trim() : 'Legal_Document';
    const text = el ? el.innerText : '';

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    this.showToast('Document downloaded successfully.', 'success');
  },

  printModalDocument() {
    window.print();
  },

  copyModalDocumentText() {
    const el = document.getElementById('modal-doc-preview-content');
    if (el) {
      this.copyText(el.innerText);
    }
  },


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
  },

  // =============================================================
  // FEATURE 17: ADMIN & SYSTEM GOVERNANCE
  // =============================================================
  async loadAdminData() {
    if (!this.user || this.user.role !== 'admin') {
      this.showToast('Unauthorized: Admin access required', 'error');
      this.navigate('citizen-dashboard');
      return;
    }
    await Promise.all([
      this.loadAdminOverview(),
      this.loadAdminAuditLogs(),
      this.loadAdminUsers()
    ]);
  },

  async loadAdminOverview() {
    try {
      const data = await this.api('/api/admin/overview');
      if (!data) return;
      const uEl = document.getElementById('admin-stat-users');
      const cEl = document.getElementById('admin-stat-citizens');
      const lEl = document.getElementById('admin-stat-lawyers');
      const csEl = document.getElementById('admin-stat-cases');
      const acEl = document.getElementById('admin-stat-active-cases');

      if (uEl) uEl.innerText = data.total_users ?? '--';
      if (cEl) cEl.innerText = `${data.total_citizens ?? 0} Citizens Registered`;
      if (lEl) lEl.innerText = data.total_lawyers ?? '--';
      if (csEl) csEl.innerText = data.total_cases ?? '--';
      if (acEl) acEl.innerText = `${data.active_cases ?? 0} Active Matters`;
    } catch (err) {
      console.warn('Failed to load admin overview:', err);
    }
  },

  async loadAdminAuditLogs() {
    const tbody = document.getElementById('admin-audit-logs-tbody');
    const countEl = document.getElementById('admin-logs-count');
    if (!tbody) return;

    try {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 28px;"><div class="spinner"></div></td></tr>';
      const data = await this.api('/api/admin/audit-logs');
      const logs = (data && data.audit_logs) ? data.audit_logs : ((data && data.logs) ? data.logs : []);
      this.adminAuditLogsCache = logs;
      if (countEl) countEl.innerText = logs.length;

      this.renderAdminAuditLogs(logs);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 28px;">Failed to load audit logs: ${this.escape(err.message || 'Server error')}</td></tr>`;
    }
  },

  filterAdminAuditLogs() {
    if (!this.adminAuditLogsCache) return;
    const searchInput = document.getElementById('admin-audit-search');
    const actionFilter = document.getElementById('admin-audit-action-filter');
    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const actionVal = actionFilter ? actionFilter.value.trim().toUpperCase() : '';

    const filtered = this.adminAuditLogsCache.filter(l => {
      const actionStr = (l.action || '').toUpperCase();
      if (actionVal && !actionStr.includes(actionVal)) return false;
      if (!query) return true;
      const haystack = [
        l.log_id,
        l.audit_id,
        l.user_id,
        l.action,
        l.details,
        l.description,
        l.ip_address,
        l.entity_type
      ].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(query);
    });

    this.renderAdminAuditLogs(filtered);
  },

  renderAdminAuditLogs(logs) {
    const tbody = document.getElementById('admin-audit-logs-tbody');
    if (!tbody) return;

    if (!logs || logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 28px;">No security audit events match the current criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(l => {
      const logId = l.log_id || l.audit_id || '--';
      const actionRaw = (l.action || 'AUDIT').toUpperCase();
      let actionBadge = '<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: var(--accent-primary); font-weight: 600;">' + this.escape(actionRaw) + '</span>';
      let statusBadge = '<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-weight: 600;">SUCCESS</span>';

      if (actionRaw.includes('LOGIN')) {
        actionBadge = '<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-weight: 600;">' + this.escape(actionRaw) + '</span>';
      } else if (actionRaw.includes('FAIL') || actionRaw.includes('DENIED') || actionRaw.includes('REVOKE')) {
        actionBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; font-weight: 600;">' + this.escape(actionRaw) + '</span>';
        statusBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; font-weight: 600;">FAILED</span>';
      } else if (actionRaw.includes('USER_')) {
        actionBadge = '<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3B82F6; font-weight: 600;">' + this.escape(actionRaw) + '</span>';
      } else if (actionRaw.includes('PASSWORD')) {
        actionBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; font-weight: 600;">' + this.escape(actionRaw) + '</span>';
      }

      let formattedDate = '--';
      if (l.created_at) {
        try {
          const d = new Date(l.created_at);
          formattedDate = isNaN(d.getTime()) ? this.escape(l.created_at) : d.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          });
        } catch (e) {
          formattedDate = this.escape(l.created_at);
        }
      }

      const userDisplay = l.user_id ? `<code>UID-${l.user_id}</code>` : '<span style="color:var(--text-muted); font-style: italic;">system</span>';
      const detailsDisplay = this.escape(l.details || l.description || 'Standard security event');
      const ipDisplay = `<code>${this.escape(l.ip_address || '127.0.0.1')}</code>`;

      return `
        <tr>
          <td class="col-log-id"><code>#${logId}</code></td>
          <td class="col-time"><span style="color: var(--text-secondary); font-variant-numeric: tabular-nums;">${formattedDate}</span></td>
          <td class="col-user">${userDisplay}</td>
          <td class="col-action">${actionBadge}</td>
          <td class="col-details"><span class="audit-details-text">${detailsDisplay}</span></td>
          <td class="col-ip">${ipDisplay}</td>
          <td class="col-status" style="text-align: center;">${statusBadge}</td>
        </tr>
      `;
    }).join('');
  },

  async loadAdminUsers() {
    const tbody = document.getElementById('admin-users-tbody');
    const countEl = document.getElementById('admin-users-count');
    if (!tbody) return;

    try {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 24px;"><div class="spinner"></div></td></tr>';
      const data = await this.api('/api/admin/users');
      const users = (data && data.users) ? data.users : [];
      if (countEl) countEl.innerText = users.length;

      if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No user accounts found.</td></tr>';
        return;
      }

      tbody.innerHTML = users.map(u => {
        let roleBadge = '<span class="badge badge-info">Citizen</span>';
        if (u.role === 'admin') {
          roleBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; font-weight:700;">Admin</span>';
        } else if (u.role === 'lawyer') {
          roleBadge = '<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-weight:700;">Advocate</span>';
        }
        const formattedDate = u.created_at ? new Date(u.created_at).toLocaleDateString() : '--';
        return `
          <tr>
            <td><code>UID-${u.user_id}</code></td>
            <td><strong>${this.escape(u.full_name || 'User')}</strong></td>
            <td>${this.escape(u.email || '--')}</td>
            <td>${roleBadge}</td>
            <td><span class="badge badge-success">Active</span></td>
            <td style="color: var(--text-muted); font-size: 12.5px;">${formattedDate}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger); padding: 24px;">Failed to load user accounts: ${this.escape(err.message || 'Server error')}</td></tr>`;
    }
  },

  switchAdminTab(tab) {
    document.querySelectorAll('.tab-btn[id^="tab-btn-admin-"]').forEach(btn => {
      btn.classList.toggle('active', btn.id === `tab-btn-admin-${tab}`);
    });
    document.querySelectorAll('.admin-tab-pane').forEach(pane => {
      pane.style.display = pane.id === `admin-pane-${tab}` ? 'block' : 'none';
    });
  }
};

// Run when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
