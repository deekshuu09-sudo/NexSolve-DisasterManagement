// NEXSOLVE — Enterprise Disaster Intelligence Platform Engine (iOS Glassmorphism Theme)

document.addEventListener('DOMContentLoaded', () => {
  // Global State
  let offlineMode = false;
  let currentForecastHour = 0;
  let activeMapLayer = 'all';
  let leafletMap = null;
  let mapMarkers = [];
  let mapPolylines = [];
  let rainfallChartInstance = null;
  let stateRiskChartInstance = null;

  // Base Data Model - 8 NER States & Key Districts
  const nerDistrictData = [
    { id: 'champhai', state: 'Mizoram', name: 'Champhai District', lat: 23.4756, lng: 93.3289, riskScore: 92, status: 'Critical', rain24h: 146, soilSat: 88, slopeAngle: 42, gsiEvents: 14, population: 3800, mainRoad: 'Aizawl-Champhai Hwy' },
    { id: 'aizawl', state: 'Mizoram', name: 'Aizawl Capital Corridor', lat: 23.7271, lng: 92.7176, riskScore: 64, status: 'High', rain24h: 108, soilSat: 74, slopeAngle: 36, gsiEvents: 8, population: 12400, mainRoad: 'NH-54 Axis' },
    { id: 'senapati', state: 'Manipur', name: 'Senapati NH-2 Corridor', lat: 25.2686, lng: 94.0186, riskScore: 88, status: 'Critical', rain24h: 138, soilSat: 85, slopeAngle: 44, gsiEvents: 16, population: 4200, mainRoad: 'NH-2 (Dimapur-Imphal)' },
    { id: 'ukhrul', state: 'Manipur', name: 'Ukhrul Hill Range', lat: 25.1167, lng: 94.3667, riskScore: 74, status: 'High', rain24h: 112, soilSat: 78, slopeAngle: 38, gsiEvents: 9, population: 2900, mainRoad: 'Imphal-Ukhrul Rd' },
    { id: 'cherrapunji', state: 'Meghalaya', name: 'Sohra / Cherrapunji Plateau', lat: 25.2700, lng: 91.7320, riskScore: 84, status: 'Critical', rain24h: 194, soilSat: 91, slopeAngle: 40, gsiEvents: 19, population: 5100, mainRoad: 'Shillong-Sohra Rd' },
    { id: 'shillong', state: 'Meghalaya', name: 'Upper Shillong Peak', lat: 25.5788, lng: 91.8933, riskScore: 79, status: 'High', rain24h: 126, soilSat: 80, slopeAngle: 35, gsiEvents: 11, population: 18500, mainRoad: 'NH-6 (Guwahati-Shillong)' },
    { id: 'cachar', state: 'Assam', name: 'Cachar / Haflong Axis', lat: 25.1764, lng: 93.0181, riskScore: 82, status: 'Critical', rain24h: 152, soilSat: 86, slopeAngle: 39, gsiEvents: 15, population: 8900, mainRoad: 'NH-306 (Silchar-Aizawl)' },
    { id: 'guwahati', state: 'Assam', name: 'Guwahati Metropolitan Hills', lat: 26.1445, lng: 91.7362, riskScore: 32, status: 'Low', rain24h: 42, soilSat: 48, slopeAngle: 22, gsiEvents: 3, population: 65000, mainRoad: 'NH-27 Bypass' },
    { id: 'tawang', state: 'Arunachal Pradesh', name: 'Tawang High Pass', lat: 27.5861, lng: 91.8594, riskScore: 81, status: 'Critical', rain24h: 132, soilSat: 83, slopeAngle: 46, gsiEvents: 12, population: 2100, mainRoad: 'Bhalukpong-Tawang Hwy' },
    { id: 'itanagar', state: 'Arunachal Pradesh', name: 'Itanagar Capital Zone', lat: 27.0844, lng: 93.6053, riskScore: 68, status: 'High', rain24h: 98, soilSat: 72, slopeAngle: 34, gsiEvents: 7, population: 9400, mainRoad: 'NH-415' },
    { id: 'kohima', state: 'Nagaland', name: 'Kohima Bypass Corridor', lat: 25.6751, lng: 94.1086, riskScore: 86, status: 'Critical', rain24h: 140, soilSat: 87, slopeAngle: 43, gsiEvents: 17, population: 7600, mainRoad: 'NH-29 (Dimapur-Kohima)' },
    { id: 'dhalai', state: 'Tripura', name: 'Dhalai District Hills', lat: 23.8438, lng: 91.8587, riskScore: 62, status: 'High', rain24h: 88, soilSat: 69, slopeAngle: 28, gsiEvents: 5, population: 3300, mainRoad: 'NH-8 Axis' },
    { id: 'mangan', state: 'Sikkim', name: 'North Sikkim / Mangan Valley', lat: 27.5167, lng: 88.5333, riskScore: 90, status: 'Critical', rain24h: 168, soilSat: 92, slopeAngle: 48, gsiEvents: 22, population: 1900, mainRoad: 'NH-10 (Gangtok-Siliguri)' }
  ];

  // Road Corridors Data
  const roadCorridors = [
    { code: 'NH-306', name: 'Silchar – Aizawl Axis', status: 'BLOCKED', color: '#f43f5e', desc: 'Debris blockage at KM 42 · Clearing machinery deployed', eta: '4-6 Hours', altRoute: 'State Highway 2B via Kolasib' },
    { code: 'NH-2', name: 'Dimapur – Imphal Hwy', status: 'BLOCKED', color: '#f43f5e', desc: 'Major slope slip at Senapati pass · 140 trucks halted', eta: '8-12 Hours', altRoute: 'Single lane convoy via Leimakhong' },
    { code: 'NH-10', name: 'Gangtok – Siliguri Axis', status: 'RESTRICTED', color: '#06b6d4', desc: 'Controlled single-lane movement due to active rockfall', eta: 'Monitored 24/7', altRoute: 'Rongpo detour' },
    { code: 'NH-6', name: 'Guwahati – Shillong Expressway', status: 'OPEN', color: '#10b981', desc: 'Heavy downpour watch active · Sensors report stable slope', eta: 'Normal Transit', altRoute: 'Direct Highway' },
    { code: 'Aizawl–Champhai', name: 'Champhai Frontier Corridor', status: 'RESTRICTED', color: '#06b6d4', desc: 'Fissure cracks logged by field patrol at KM 18', eta: 'Inspection Due', altRoute: 'Saitual link route' },
    { code: 'NH-29', name: 'Dimapur – Kohima Highway', status: 'BLOCKED', color: '#f43f5e', desc: 'Pagar Pahar mudslide · Road clearance unit active', eta: '6 Hours', altRoute: 'Peducha bypass' }
  ];

  // Relief Shelters Data
  const reliefShelters = [
    { name: 'Champhai Community Relief Center', lat: 23.4800, lng: 93.3100, capacity: 500, current: 120, status: 'Active & Equipped' },
    { name: 'Senapati Stadium Evacuation Hub', lat: 25.2750, lng: 94.0100, capacity: 800, current: 340, status: 'Active' },
    { name: 'Cherrapunji High School Shelter', lat: 25.2800, lng: 91.7300, capacity: 400, current: 95, status: 'Standby' },
    { name: 'Haflong Town Hall Relief Camp', lat: 25.1800, lng: 93.0100, capacity: 600, current: 210, status: 'Active' }
  ];

  // Computer Vision Preset Images & Classifications
  const cvSamples = {
    crack1: {
      url: 'https://images.unsplash.com/photo-1541888946425-d0fbb186a5b3?auto=format&fit=crop&w=600&q=80',
      label: 'Tension Crack 96.4%',
      output: 'Tension Crack Detected (96.4% Confidence)\n• Feature: Continuous 14m lateral slope crack\n• Hazard Level: High Structural Disruption\n• Recommended Action: Immediate geo-textile anchoring & barricade.',
      type: 'Slope tension crack'
    },
    blockage1: {
      url: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80',
      label: 'Rockfall Debris 94.8%',
      output: 'Highway Rockfall Debris (94.8% Confidence)\n• Feature: ~450m³ boulder collapse on NH-2 right lane\n• Hazard Level: Total Road Closure\n• Recommended Action: Deploy earthmovers & explosive blasting crew.',
      type: 'Road blockage / Rockfall'
    },
    mudslide1: {
      url: 'https://images.unsplash.com/photo-1547683905-f686c993aae5?auto=format&fit=crop&w=600&q=80',
      label: 'Active Mudslide 91.2%',
      output: 'Debris Flow / Mudslide (91.2% Confidence)\n• Feature: Saturated topsoil liquefaction moving at 0.5m/s\n• Hazard Level: Critical Evacuation Risk\n• Recommended Action: Issue immediate sirens for downstream settlement.',
      type: 'Debris flow / Flash mudslide'
    }
  };

  // Comprehensive Multilingual Voice Translation Engine (8 Regional Languages)
  const alertTranslations = {
    english: {
      name: 'English',
      langCode: 'en-IN',
      displayHTML: '<strong>🚨 EMERGENCY WARNING:</strong> Heavy continuous rainfall may trigger catastrophic landslides in Champhai district within 6 hours. Move to designated relief shelters immediately and avoid hill cut roads.',
      spokenText: 'Emergency warning for Champhai district. Heavy continuous rainfall may trigger catastrophic landslides within six hours. Move to designated relief shelters immediately and avoid hill cut roads.'
    },
    hindi: {
      name: 'Hindi (हिन्दी)',
      langCode: 'hi-IN',
      displayHTML: '<strong>🚨 आपात्कालीन चेतावनी:</strong> अगले 6 घंटों में चम्पाई जिले में भारी बारिश के कारण तीव्र भूस्खलन की संभावना है। कृपया तुरंत निकटतम राहत शिविरों में शरण लें और पहाड़ी रास्तों पर जाने से बचें।',
      spokenText: 'चम्पाई जिले के लिए आपात्कालीन चेतावनी। अगले छह घंटों में भारी बारिश के कारण तीव्र भूस्खलन की संभावना है। कृपया तुरंत निकटतम राहत शिविरों में शरण लें और पहाड़ी रास्तों पर जाने से बचें।'
    },
    mizo: {
      name: 'Mizo (Mizo ṭawng)',
      langCode: 'mi',
      fallbackLang: 'en-IN',
      displayHTML: '<strong>🚨 HRILH LÂWKNA VÂNGAWH:</strong> Champhai district-ah ruah nasa tak sur zel avângin hmun hlauhawmah lei a tlahlum dawn. In relief shelter hnai berah lut vat ula, tlang lampui zawh suh u.',
      spokenText: 'Hrilh lawkna vangawh. Champhai district ah ruah nasa tak sur zel avangin lei a tlahlum dawn. Relief shelter hnai berah lut vat ula, tlang lampui zawh suh u.'
    },
    assamese: {
      name: 'Assamese (অসমীয়া)',
      langCode: 'as-IN',
      fallbackLang: 'bn-IN',
      displayHTML: '<strong>🚨 জৰুৰীকালীন সতৰ্কবাণী:</strong> আগন্তুক ৬ ঘণ্টাত চমফাই জিলাত ধাৰাসাৰ বৰষুণৰ ফলত মাৰাত্মক ভূমিস্খলন হ’ব পাৰে। অনুগ্ৰহ কৰি লগে লগে আশ্ৰয় শিবিৰলৈ যাওক আৰু পাহাৰীয়া ৰাস্তা পৰিহাৰ কৰক।',
      spokenText: 'চমফাই জিলাৰ জৰুৰীকালীন সতৰ্কবাণী। আগন্তুক ছ ঘণ্টাত ধাৰাসাৰ বৰষুণৰ ফলত মাৰাত্মক ভূমিস্খলন হ’ব পাৰে। অনুগ্ৰহ কৰি লগে লগে আশ্ৰয় শিবিৰলৈ যাওক আৰু পাহাৰীয়া ৰাস্তা পৰিহাৰ কৰক।'
    },
    meitei: {
      name: 'Meitei / Manipuri (মৈতৈলোন্)',
      langCode: 'mni-IN',
      fallbackLang: 'hi-IN',
      displayHTML: '<strong>🚨 য়েথংবা পাওতাক:</strong> চমফাই জিলাদা অরুবা নোংজুনা মরম ওইদুনা পুং ৬ গী মনুংদা লৈমায় তাথোকপা য়াই। কন্ননা শহরগী রিলিফ ক্যাম্পতা চংশিনবিয়ু।',
      spokenText: 'চমফাই জিলাগী য়েথংবা পাওতাক। পুং তরুক গী মনুংদা অরুবা নোংজুনা লৈমায় তাথোকপা য়াই। কন্ননা শহরগী রিলিফ ক্যাম্পতা চংশিনবিয়ু।'
    },
    khasi: {
      name: 'Khasi (Ka Ktien Khasi)',
      langCode: 'en-IN',
      displayHTML: '<strong>🚨 MAHAM KYNTIEW:</strong> Napdeng ki 6 kynta ban wan, ki lapbah kiba jur ki lah ban pynhiar maw bah ha Champhai. Leit mar dor sha ki iing shongkyntiew kiba hajan.',
      spokenText: 'Maham kyntiew for Champhai. Napdeng ki hynriew kynta ban wan, ki lapbah kiba jur ki lah ban pynhiar maw bah ha Champhai. Leit mar dor sha ki iing shongkyntiew kiba hajan.'
    },
    bengali: {
      name: 'Bengali (বাংলা)',
      langCode: 'bn-IN',
      displayHTML: '<strong>🚨 জরুরি সতর্কতা:</strong> আগামী ৬ ঘণ্টায় চম্পাই জেলায় অতি ভারী বৃষ্টির কারণে মারাত্মক ভূমিধসের আশঙ্কা রয়েছে। অনতিবিলম্বে নিকটস্থ আশ্রয়কেন্দ্রে চলে যান এবং পাহাড়ি রাস্তা এড়িয়ে চলুন।',
      spokenText: 'চম্পাই জেলার জন্য জরুরি সতর্কতা। আগামী ছয় ঘণ্টায় অতি ভারী বৃষ্টির কারণে মারাত্মক ভূমিধসের আশঙ্কা রয়েছে। অনতিবিলম্বে নিকটস্থ আশ্রয়কেন্দ্রে চলে যান এবং পাহাড়ি রাস্তা এড়িয়ে চলুন।'
    },
    nagamese: {
      name: 'Nagamese (Nagamese)',
      langCode: 'hi-IN',
      fallbackLang: 'en-IN',
      displayHTML: '<strong>🚨 EMERGENCY WARNING:</strong> Champhai laga hill area te monsoon bishi aha karone landslide ahibole chance ase. Sob manu khan jaldi relief camp te jabole laje.',
      spokenText: 'Champhai hill area emergency warning. Monsoon bishi aha karone landslide ahibole chance ase. Sob manu khan jaldi relief camp te jabole laje.'
    }
  };

  // Section to Category Mapping & Category Entry Points
  const sectionCategoryMap = {
    'overview-step': 'overview',
    'map-step': 'analyze',
    'xai-step': 'analyze',
    'forecast-step': 'intelligence',
    'field-step': 'intelligence',
    'alerts-step': 'threat',
    'response-step': 'threat',
    'roads-step': 'system'
  };

  const categoryFirstStepMap = {
    'overview': '#overview-step',
    'analyze': '#map-step',
    'intelligence': '#forecast-step',
    'threat': '#alerts-step',
    'system': '#roads-step'
  };

  const THEME_STORAGE_KEY = 'nexsolve-theme';
  const root = document.documentElement;
  const themeToggle = document.querySelector('#themeToggle');
  const themeSelect = document.querySelector('#themeSelect');

  function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    const selectedTheme = theme === 'light' || theme === 'dark' ? theme : 'system';
    const resolvedTheme = selectedTheme === 'system' ? getSystemTheme() : selectedTheme;

    root.setAttribute('data-theme', resolvedTheme);

    if (themeSelect) {
      themeSelect.value = selectedTheme;
    }

    if (themeToggle) {
      const isLight = resolvedTheme === 'light';
      themeToggle.setAttribute('aria-label', isLight ? 'Switch to dark theme' : 'Switch to light theme');
      themeToggle.title = isLight ? 'Current theme: light mode' : 'Current theme: dark mode';
      themeToggle.innerHTML = isLight
        ? '<svg class="theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 0 1 11.2 3a9 9 0 1 0 9.8 9.8Z"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>'
        : '<svg class="theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v2.5M12 18.5V21M4.93 4.93l1.77 1.77M17.3 17.3l1.77 1.77M3 12h2.5M18.5 12H21M4.93 19.07l1.77-1.77M17.3 6.7l1.77-1.77"/><circle cx="12" cy="12" r="4.1"/></svg>';
    }

    try {
      localStorage.setItem(THEME_STORAGE_KEY, selectedTheme);
    } catch (error) {
      console.warn('Unable to persist theme preference:', error);
    }

    const actualThemeLabel = resolvedTheme === 'light' ? 'Light' : 'Dark';
    const actualThemeAria = resolvedTheme === 'light' ? 'light' : 'dark';
    if (themeSelect) {
      themeSelect.setAttribute('aria-label', `Select app theme; currently ${actualThemeLabel} mode`);
      themeSelect.title = `Current theme: ${actualThemeAria}`;
    }
  }

  const savedTheme = (() => {
    try {
      return localStorage.getItem(THEME_STORAGE_KEY);
    } catch (error) {
      return 'system';
    }
  })();

  const preferredTheme = savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'system' ? savedTheme : 'system';
  applyTheme(preferredTheme);

  themeSelect?.addEventListener('change', (e) => {
    const nextTheme = e.target.value;
    applyTheme(nextTheme);
    showToast(nextTheme === 'system' ? 'Theme synced to system preference.' : `${nextTheme.charAt(0).toUpperCase() + nextTheme.slice(1)} mode enabled.`);
  });

  themeToggle?.addEventListener('click', () => {
    const currentTheme = (() => {
      try {
        return localStorage.getItem(THEME_STORAGE_KEY) || 'system';
      } catch (error) {
        return 'system';
      }
    })();

    const nextTheme = currentTheme === 'dark' ? 'light' : currentTheme === 'light' ? 'dark' : getSystemTheme() === 'light' ? 'dark' : 'light';
    applyTheme(nextTheme);
    showToast(nextTheme === 'light' ? 'Light mode enabled.' : 'Dark mode enabled.');
  });

  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
    const handleThemeSystemChange = () => {
      const currentPreference = (() => {
        try {
          return localStorage.getItem(THEME_STORAGE_KEY) || 'system';
        } catch (error) {
          return 'system';
        }
      })();

      if (currentPreference === 'system') {
        applyTheme('system');
      }
    };

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleThemeSystemChange);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleThemeSystemChange);
    }
  }

  // --- WORKFLOW & DYNAMIC NAVBAR DUAL SYNC ---
  const workflowItems = document.querySelectorAll('.workflow-item');
  const dashboardTopLink = document.querySelector('a[data-category="overview"]');
  const dropdownContainers = document.querySelectorAll('.dropdown[data-category]');
  const dropdownMenuItems = document.querySelectorAll('.dropdown-menu-item');
  const brandLink = document.querySelector('.brand');
  const appLayout = document.querySelector('#appLayout');
  const workflowSidebar = document.querySelector('#workflowSidebar');
  const workflowFab = document.querySelector('#workflowFab');
  const workflowBackdrop = document.querySelector('#workflowBackdrop');
  const toggleSidebarBtn = document.querySelector('#toggleSidebar');
  let isProgrammaticNav = false;

  function closeWorkflowDrawer() {
    const isDesktop = window.matchMedia('(min-width: 761px)').matches;
    if (isDesktop) {
      appLayout?.classList.add('sidebar-collapsed');
    }
    workflowSidebar?.classList.remove('open');
    workflowBackdrop?.classList.remove('visible');
    workflowFab?.classList.remove('hidden');
    workflowFab?.classList.add('visible');
    workflowFab?.setAttribute('aria-expanded', 'false');
    if (workflowSidebar) workflowSidebar.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('drawer-open');
  }

  function openWorkflowDrawer() {
    appLayout?.classList.remove('sidebar-collapsed');
    workflowSidebar?.classList.add('open');
    workflowBackdrop?.classList.add('visible');
    workflowFab?.classList.add('hidden');
    workflowFab?.classList.remove('visible');
    workflowFab?.setAttribute('aria-expanded', 'true');
    if (workflowSidebar) workflowSidebar.setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
  }

  workflowFab?.addEventListener('click', () => {
    if (workflowSidebar?.classList.contains('open')) {
      closeWorkflowDrawer();
    } else {
      openWorkflowDrawer();
    }
  });

  workflowBackdrop?.addEventListener('click', closeWorkflowDrawer);
  toggleSidebarBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    closeWorkflowDrawer();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && workflowSidebar?.classList.contains('open')) {
      closeWorkflowDrawer();
    }
  });

  document.body.classList.remove('drawer-open');

  function setActiveStep(targetId, userInitiated = false) {
    if (!targetId || targetId === '#' || targetId === '') return;
    const cleanId = targetId.replace('#', '');
    const targetEl = document.getElementById(cleanId);
    if (!targetEl) return;

    // 1. Update WORKFLOW Sidebar active item
    workflowItems.forEach(w => {
      const href = w.getAttribute('href');
      if (href === targetId || href === `#${cleanId}`) {
        w.classList.add('active');
      } else {
        w.classList.remove('active');
      }
    });

    // 2. Update Topbar Active Category State
    const currentCategory = sectionCategoryMap[cleanId];
    
    if (dashboardTopLink) {
      if (currentCategory === 'overview') {
        dashboardTopLink.classList.add('active');
      } else {
        dashboardTopLink.classList.remove('active');
      }
    }

    dropdownContainers.forEach(drop => {
      const dropCat = drop.getAttribute('data-category');
      if (dropCat === currentCategory) {
        drop.classList.add('active');
      } else {
        drop.classList.remove('active');
      }
    });

    // 3. Highlight specific Dropdown Sub-menu items
    dropdownMenuItems.forEach(dItem => {
      const dHref = dItem.getAttribute('href');
      if (dHref === `#${cleanId}`) {
        dItem.classList.add('active');
      } else {
        dItem.classList.remove('active');
      }
    });

    // 4. Smooth Scroll to section ONLY when initiated by explicit user click
    if (userInitiated) {
      isProgrammaticNav = true;
      const headerOffset = 80;
      const elementPosition = targetEl.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });

      if (window.history && window.history.pushState) {
        window.history.pushState(null, '', `#${cleanId}`);
      }

      setTimeout(() => {
        isProgrammaticNav = false;
      }, 750);
    }
  }

  // Handle Workflow Sidebar Item Clicks
  workflowItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = item.getAttribute('href');
      setActiveStep(targetId, true);
    });
  });

  // Handle Brand Logo Click
  brandLink?.addEventListener('click', (e) => {
    e.preventDefault();
    setActiveStep('#overview-step', true);
  });

  // Handle Topbar Dashboard Link Click
  dashboardTopLink?.addEventListener('click', (e) => {
    e.preventDefault();
    setActiveStep('#overview-step', true);
  });

  // Handle Topbar Category Dropdown Toggle Button Clicks (Direct Header Click)
  dropdownContainers.forEach(drop => {
    const cat = drop.getAttribute('data-category');
    const toggleBtn = drop.querySelector('.dropdown-toggle');
    if (toggleBtn && cat && categoryFirstStepMap[cat]) {
      toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetStep = categoryFirstStepMap[cat];
        setActiveStep(targetStep, true);
      });
    }
  });

  // Handle Dropdown Sub-menu Items Clicks
  dropdownMenuItems.forEach(dItem => {
    dItem.addEventListener('click', (e) => {
      const href = dItem.getAttribute('href');
      if (href && href.startsWith('#') && href.length > 1) {
        e.preventDefault();
        setActiveStep(href, true);
      }
    });
  });

  // Topbar Actions
  document.querySelector('#dropInspectQueue')?.addEventListener('click', (e) => {
    e.preventDefault();
    renderQueueItems();
    document.querySelector('#queueDialog')?.showModal();
  });

  document.querySelector('#dropRefreshModel')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelector('#refreshRisk')?.click();
  });

  // Precision IntersectionObserver for Scroll Spy (Zero Auto-Scroll Hijacking)
  const sections = document.querySelectorAll('section[id]');
  if ('IntersectionObserver' in window && sections.length > 0) {
    const observer = new IntersectionObserver(() => {
      if (isProgrammaticNav) return;

      const visibleSections = Array.from(sections).filter(sec => {
        const rect = sec.getBoundingClientRect();
        return rect.top <= 300 && rect.bottom >= 150;
      });

      if (visibleSections.length > 0) {
        visibleSections.sort((a, b) => {
          return Math.abs(a.getBoundingClientRect().top - 80) - Math.abs(b.getBoundingClientRect().top - 80);
        });
        const activeSec = visibleSections[0];
        const id = activeSec.getAttribute('id');
        setActiveStep(`#${id}`, false); // userInitiated = false (DO NOT SCROLL)
      }
    }, {
      rootMargin: '-70px 0px -30% 0px',
      threshold: [0.1, 0.35, 0.6]
    });

    sections.forEach(sec => observer.observe(sec));
  }

  // Handle Browser Back/Forward navigation
  window.addEventListener('popstate', () => {
    const hash = window.location.hash || '#overview-step';
    setActiveStep(hash, true);
  });

  // Initial Sync on Page Load
  setTimeout(() => {
    const hash = window.location.hash;
    if (hash && document.querySelector(hash)) {
      setActiveStep(hash, true);
    } else {
      setActiveStep('#overview-step', false);
    }
  }, 100);

  document.querySelector('#heroRiskButton')?.addEventListener('click', () => {
    setActiveStep('#map-step', true);
  });

  // --- INITIALIZE LEAFLET GIS MAP (ESRI DARK CANVAS) ---
  function initLeafletMap() {
    const mapContainer = document.querySelector('#leafletMap');
    if (!mapContainer) return;

    leafletMap = L.map('leafletMap', {
      center: [25.5788, 93.2473],
      zoom: 7,
      zoomControl: true,
      scrollWheelZoom: false
    });

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ | MDoNER Disaster Intelligence',
      maxZoom: 16
    }).addTo(leafletMap);

    renderMapLayers();
  }

  // Render Map Markers & Polylines based on Layer Filter
  function renderMapLayers() {
    if (!leafletMap) return;

    mapMarkers.forEach(m => leafletMap.removeLayer(m));
    mapPolylines.forEach(p => leafletMap.removeLayer(p));
    mapMarkers = [];
    mapPolylines = [];

    if (activeMapLayer === 'all' || activeMapLayer === 'risk') {
      nerDistrictData.forEach(item => {
        let color = '#10b981';
        if (item.riskScore > 80) color = '#f43f5e';
        else if (item.riskScore > 60) color = '#06b6d4';
        else if (item.riskScore > 40) color = '#6366f1';

        const circle = L.circleMarker([item.lat, item.lng], {
          radius: 12 + (item.riskScore / 10),
          fillColor: color,
          color: '#ffffff',
          weight: 2,
          opacity: 0.95,
          fillOpacity: 0.85
        }).addTo(leafletMap);

        const popupHTML = `
          <div style="font-family:'DM Sans',sans-serif;">
            <div style="font-weight:bold;font-size:14px;color:#ffffff;margin-bottom:4px;">${item.name} (${item.state})</div>
            <div style="font-size:11px;color:#a1a1aa;margin-bottom:6px;">Status: <strong style="color:${color}">${item.status} Risk (Score ${item.riskScore}/100)</strong></div>
            <div style="font-size:11px;color:#e4e4e7;">🌧️ 24h Rainfall: <strong>${item.rain24h} mm</strong></div>
            <div style="font-size:11px;color:#e4e4e7;">💧 Soil Saturation: <strong>${item.soilSat}%</strong></div>
            <div style="font-size:11px;color:#e4e4e7;">⛰️ Slope Cut Angle: <strong>${item.slopeAngle}°</strong></div>
            <div style="margin-top:8px;">
              <button onclick="window.selectDistrictXAI('${item.id}')" style="background:#ffffff;color:#000000;font-weight:bold;border:0;padding:4px 10px;border-radius:4px;font-size:10px;cursor:pointer;">Decompose XAI Factors</button>
            </div>
          </div>
        `;

        circle.bindPopup(popupHTML);
        mapMarkers.push(circle);
      });
    }

    if (activeMapLayer === 'all' || activeMapLayer === 'rainfall') {
      nerDistrictData.filter(d => d.rain24h > 100).forEach(d => {
        const rainZone = L.circle([d.lat, d.lng], {
          radius: 35000,
          fillColor: '#06b6d4',
          color: '#22d3ee',
          weight: 1,
          opacity: 0.5,
          fillOpacity: 0.25
        }).addTo(leafletMap);
        mapMarkers.push(rainZone);
      });
    }

    if (activeMapLayer === 'all' || activeMapLayer === 'roads') {
      const roadRoutes = [
        { name: 'NH-306 (Silchar-Aizawl)', coords: [[24.8333, 92.7789], [24.0000, 93.0000], [23.4756, 93.3289]], status: 'BLOCKED', color: '#f43f5e' },
        { name: 'NH-2 (Dimapur-Kohima-Imphal)', coords: [[25.9060, 93.7271], [25.6751, 94.1086], [25.2686, 94.0186], [24.8170, 93.9368]], status: 'BLOCKED', color: '#f43f5e' },
        { name: 'NH-10 (Gangtok-Siliguri)', coords: [[27.3389, 88.6065], [27.0000, 88.5000]], status: 'RESTRICTED', color: '#06b6d4' },
        { name: 'NH-6 (Guwahati-Shillong)', coords: [[26.1445, 91.7362], [25.5788, 91.8933]], status: 'OPEN', color: '#10b981' }
      ];

      roadRoutes.forEach(r => {
        const polyline = L.polyline(r.coords, {
          color: r.color,
          weight: 5,
          opacity: 0.85,
          dashArray: r.status === 'BLOCKED' ? '8, 8' : null
        }).addTo(leafletMap);

        polyline.bindPopup(`<strong>${r.name}</strong><br/>Status: <span style="color:${r.color};font-weight:bold;">${r.status}</span>`);
        mapPolylines.push(polyline);
      });
    }

    if (activeMapLayer === 'all' || activeMapLayer === 'shelters') {
      reliefShelters.forEach(s => {
        const shelterMarker = L.marker([s.lat, s.lng], {
          icon: L.divIcon({
            className: 'custom-shelter-icon',
            html: '<div style="background:#06b6d4;color:#ffffff;font-weight:bold;border-radius:50%;width:24px;height:24px;display:grid;place-items:center;font-size:12px;box-shadow:0 0 12px rgba(6,182,212,0.6);">🏥</div>',
            iconSize: [24, 24]
          })
        }).addTo(leafletMap);

        shelterMarker.bindPopup(`<strong>${s.name}</strong><br/>Capacity: ${s.current}/${s.capacity} Occupied<br/>Status: ${s.status}`);
        mapMarkers.push(shelterMarker);
      });
    }

    if (activeMapLayer === 'all' || activeMapLayer === 'sar') {
      nerDistrictData.filter(d => d.slopeAngle > 40).forEach(d => {
        const sarMarker = L.marker([d.lat + 0.05, d.lng - 0.05], {
          icon: L.divIcon({
            className: 'custom-sar-icon',
            html: '<div style="background:rgba(6,182,212,0.15);border:1px solid #06b6d4;color:#22d3ee;border-radius:4px;padding:2px 5px;font-size:9px;font-weight:bold;">📡 SAR +4.2mm/wk</div>',
            iconSize: [90, 20]
          })
        }).addTo(leafletMap);
        mapMarkers.push(sarMarker);
      });
    }
  }

  // Layer Selector Controls
  document.querySelectorAll('#layerSelector button').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('#layerSelector button').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      activeMapLayer = e.target.dataset.layer;
      renderMapLayers();
      const layerNames = { all: 'All Layers', risk: 'Risk Heatmap', rainfall: 'Rainfall Radar', roads: 'Road Corridors', shelters: 'Relief Shelters', sar: 'SAR Satellite Vectors' };
      showToast(`GIS Layer switched to: ${layerNames[activeMapLayer]}`);
    });
  });

  // Global helper to select district in XAI breakdown
  window.selectDistrictXAI = function(districtId) {
    const district = nerDistrictData.find(d => d.id === districtId);
    if (!district) return;

    document.querySelector('#xaiTitle').textContent = `Landslide Risk Breakdown: ${district.name} (${district.state})`;
    document.querySelector('#xaiScoreVal').textContent = `${district.riskScore} / 100`;
    
    document.querySelector('#xaiRainDesc').textContent = `${district.rain24h}mm in 24h (Antecedent index high)`;
    document.querySelector('#xaiRainBar').style.width = `${Math.min(100, Math.round(district.rain24h / 1.6))}%`;

    document.querySelector('#xaiSoilDesc').textContent = `Volumetric Saturation: ${district.soilSat}%`;
    document.querySelector('#xaiSoilBar').style.width = `${district.soilSat}%`;

    document.querySelector('#xaiSlopeDesc').textContent = `Slope Cut Angle: ${district.slopeAngle}° (DEM Slope)`;
    document.querySelector('#xaiSlopeBar').style.width = `${Math.min(100, Math.round(district.slopeAngle * 2))}%`;

    document.querySelector('#xaiHistDesc').textContent = `${district.gsiEvents} historical events in 5km radius`;
    document.querySelector('#xaiHistBar').style.width = `${Math.min(100, district.gsiEvents * 4.5)}%`;

    setActiveStep('#xai-step');
    showToast(`XAI Decomposition updated for ${district.name}`);
  };

  // --- EXPLAINABLE AI SIMULATOR BUTTONS ---
  document.querySelector('#simHeavyRain')?.addEventListener('click', () => {
    const champhai = nerDistrictData.find(d => d.id === 'champhai');
    if (champhai) {
      champhai.rain24h += 50;
      champhai.soilSat = Math.min(100, champhai.soilSat + 8);
      champhai.riskScore = 97;
      window.selectDistrictXAI('champhai');
      renderMapLayers();
      updateCharts();
      showToast('⚠️ Heavy downpour (+50mm) simulated! Risk Score escalated to 97/100.');
    }
  });

  document.querySelector('#simClearSky')?.addEventListener('click', () => {
    const champhai = nerDistrictData.find(d => d.id === 'champhai');
    if (champhai) {
      champhai.rain24h = 32;
      champhai.soilSat = 45;
      champhai.riskScore = 38;
      window.selectDistrictXAI('champhai');
      renderMapLayers();
      updateCharts();
      showToast('☀️ Dry weather recovery simulated! Soil draining, Risk lowered to 38/100.');
    }
  });

  document.querySelector('#simQuake')?.addEventListener('click', () => {
    const champhai = nerDistrictData.find(d => d.id === 'champhai');
    if (champhai) {
      champhai.slopeAngle += 5;
      champhai.riskScore = 95;
      window.selectDistrictXAI('champhai');
      renderMapLayers();
      showToast('🫨 Micro-seismic tremor applied! Slope shear stress increased.');
    }
  });

  document.querySelector('#simReset')?.addEventListener('click', () => {
    const champhai = nerDistrictData.find(d => d.id === 'champhai');
    if (champhai) {
      champhai.rain24h = 146;
      champhai.soilSat = 88;
      champhai.slopeAngle = 42;
      champhai.riskScore = 92;
      window.selectDistrictXAI('champhai');
      renderMapLayers();
      updateCharts();
      showToast('Model baseline reset.');
    }
  });

  // --- INITIALIZE CHART.JS GRAPH ANALYTICS ---
  function initCharts() {
    const ctxRain = document.querySelector('#rainfallChart')?.getContext('2d');
    const ctxState = document.querySelector('#stateRiskChart')?.getContext('2d');

    if (ctxRain) {
      rainfallChartInstance = new Chart(ctxRain, {
        type: 'line',
        data: {
          labels: ['-24h', '-20h', '-16h', '-12h', '-8h', '-4h', 'Now', '+4h', '+8h', '+12h'],
          datasets: [
            {
              label: 'Champhai Rain (mm)',
              data: [42, 58, 76, 98, 118, 134, 146, 160, 172, 185],
              borderColor: '#06b6d4',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              fill: true,
              tension: 0.4,
              borderWidth: 3
            },
            {
              label: 'Critical Hazard Threshold',
              data: [110, 110, 110, 110, 110, 110, 110, 110, 110, 110],
              borderColor: '#f43f5e',
              borderDash: [5, 5],
              pointRadius: 0,
              fill: false,
              borderWidth: 2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#a1a1aa', font: { family: 'DM Sans', size: 11 } } } },
          scales: {
            x: { ticks: { color: '#a1a1aa' }, grid: { color: 'rgba(255, 255, 255, 0.08)' } },
            y: { ticks: { color: '#a1a1aa' }, grid: { color: 'rgba(255, 255, 255, 0.08)' } }
          }
        }
      });
    }

    if (ctxState) {
      stateRiskChartInstance = new Chart(ctxState, {
        type: 'bar',
        data: {
          labels: ['Mizoram', 'Manipur', 'Meghalaya', 'Assam', 'Arunachal', 'Nagaland', 'Tripura', 'Sikkim'],
          datasets: [{
            label: 'Avg Hazard Index (0-100)',
            data: [78, 81, 82, 57, 75, 86, 48, 84],
            backgroundColor: ['#06b6d4', '#06b6d4', '#06b6d4', '#6366f1', '#06b6d4', '#06b6d4', '#10b981', '#06b6d4'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#a1a1aa' }, grid: { display: false } },
            y: { max: 100, ticks: { color: '#a1a1aa' }, grid: { color: 'rgba(255, 255, 255, 0.08)' } }
          }
        }
      });
    }
  }

  function updateCharts() {
    if (rainfallChartInstance) rainfallChartInstance.update();
    if (stateRiskChartInstance) stateRiskChartInstance.update();
  }

  // --- 72-HOUR FORECAST TIMELINE SLIDER ---
  const forecastSlider = document.querySelector('#forecastSlider');
  const forecastLabel = document.querySelector('#forecastTimeLabel');

  forecastSlider?.addEventListener('input', (e) => {
    currentForecastHour = parseInt(e.target.value, 10);
    forecastLabel.textContent = currentForecastHour === 0 ? 'Current Time (0h)' : `+${currentForecastHour} Hours Projection`;

    nerDistrictData.forEach(d => {
      if (currentForecastHour > 0) {
        d.rain24h += (currentForecastHour / 12) * 8;
        d.riskScore = Math.min(99, Math.round(d.riskScore + (currentForecastHour / 12) * 1.5));
      }
    });

    renderMapLayers();
    updateCharts();
    showToast(`Timeline adjusted to +${currentForecastHour}h forecast mode.`);
  });

  // --- RENDER LIVE PRIORITY ALERTS ---
  function renderAlertList() {
    const container = document.querySelector('#alertListContainer');
    if (!container) return;

    const alerts = [
      { id: 1, level: 'CRITICAL', title: 'Champhai District, Mizoram', desc: 'Antecedent 24h rainfall exceeded 145mm. Saturated slope failure imminent on Aizawl route.', time: '14 min ago' },
      { id: 2, level: 'CRITICAL', title: 'NH-2 Senapati Corridor, Manipur', desc: 'Active mudslide at KM 64. 140 commercial transport trucks halted. Immediate clearance unit needed.', time: '32 min ago' },
      { id: 3, level: 'HIGH', title: 'Sohra / Cherrapunji Plateau, Meghalaya', desc: 'Pore water pressure sensors triggered at 91% threshold. Slope movement recorded.', time: '55 min ago' },
      { id: 4, level: 'HIGH', title: 'North Sikkim / Mangan Valley', desc: 'Debris flow alert for NH-10 axis. Relief camp pre-positioned.', time: '1 hr ago' },
      { id: 5, level: 'MODERATE', title: 'Dima Hasao Hill Section, Assam', desc: 'Minor rockfall on railway track. Inspection squad dispatched.', time: '2 hrs ago' }
    ];

    container.innerHTML = alerts.map(a => `
      <article class="alert-card ${a.level.toLowerCase()}-alert">
        <div class="alert-header">
          <span class="alert-badge">${a.level}</span>
          <span style="font-size:10px;color:#a1a1aa;">${a.time}</span>
        </div>
        <h3>${a.title}</h3>
        <p>${a.desc}</p>
        <div class="alert-meta">
          <span>AI Confidence: 94.2%</span>
          <button class="open-alert-btn" onclick="window.triggerAlertAction('${a.title}')">Action →</button>
        </div>
      </article>
    `).join('');
  }

  window.triggerAlertAction = function(title) {
    document.querySelector('#responseDialog')?.showModal();
    showToast(`Response Protocol opened for: ${title}`);
  };

  // --- RENDER ROAD CORRIDORS GRID ---
  function renderRoadGrid() {
    const grid = document.querySelector('#roadCorridorsGrid');
    if (!grid) return;

    grid.innerHTML = roadCorridors.map(r => `
      <div class="road-card">
        <div class="road-header">
          <strong>${r.code} · ${r.name}</strong>
          <span class="status-pill ${r.status.toLowerCase()}">${r.status}</span>
        </div>
        <p>${r.desc}</p>
        <div style="margin-top:10px;font-size:11px;color:#a1a1aa;">
          <div>⏱️ Est. Clearance: <strong>${r.eta}</strong></div>
          <div>🔀 Alt. Detour: <strong>${r.altRoute}</strong></div>
        </div>
      </div>
    `).join('');
  }

  // --- RENDER FIELD REPORTS FEED ---
  const fieldReportsList = [
    { type: 'Road blockage / Rockfall', location: 'NH-306, KM 42 (Cachar-Aizawl)', verified: true, time: '12 min ago', icon: 'rocks' },
    { type: 'Slope tension crack', location: 'Upper Shillong Peak (Meghalaya)', verified: false, time: '27 min ago', icon: 'crack' },
    { type: 'Debris flow / Flash mudslide', location: 'Mangan Axis (Sikkim)', verified: true, time: '1 hr ago', icon: 'mud' }
  ];

  function renderFieldReports() {
    const listContainer = document.querySelector('#reportList');
    if (!listContainer) return;

    listContainer.innerHTML = fieldReportsList.map(rep => `
      <div class="report-row">
        <div class="report-photo ${rep.icon}">${rep.icon === 'rocks' ? '🪨' : rep.icon === 'crack' ? '⌇' : '🌊'}</div>
        <div>
          <h3>${rep.type} Reported</h3>
          <p>${rep.location} · ${rep.verified ? '<span class="verified-tag">● AI Verified (Field Officer)</span>' : '<span class="pending-tag">○ Awaiting Verification</span>'}</p>
        </div>
        <time>${rep.time}</time>
      </div>
    `).join('');
  }

  // --- FIELD REPORT MODAL & COMPUTER VISION SIMULATION ---
  const reportDialog = document.querySelector('#reportDialog');
  const sampleSelect = document.querySelector('#sampleImageSelect');
  const cvPreviewImg = document.querySelector('#cvPreviewImg');
  const cvBoxTag = document.querySelector('#cvBoxTag');
  const cvConfidence = document.querySelector('#cvConfidence');

  document.querySelector('#createReport')?.addEventListener('click', () => {
    sampleSelect.value = 'crack1';
    updateCvPreview('crack1');
    reportDialog?.showModal();
  });

  document.querySelector('#closeReportDialog')?.addEventListener('click', () => {
    reportDialog?.close();
  });

  sampleSelect?.addEventListener('change', (e) => {
    updateCvPreview(e.target.value);
  });

  function updateCvPreview(sampleKey) {
    if (cvSamples[sampleKey]) {
      const sample = cvSamples[sampleKey];
      cvPreviewImg.src = sample.url;
      cvBoxTag.textContent = sample.label;
      cvConfidence.innerHTML = sample.output.replace(/\n/g, '<br/>');
      document.querySelector('#incidentType').value = sample.type;
    } else {
      cvPreviewImg.src = 'https://images.unsplash.com/photo-1541888946425-d0fbb186a5b3?auto=format&fit=crop&w=600&q=80';
      cvBoxTag.textContent = 'Custom Photo 92.0%';
      cvConfidence.textContent = 'Custom image uploaded. AI computer vision model detected slope surface fissure.';
    }
  }

  // Handle Auto GPS button
  document.querySelector('#fetchGpsBtn')?.addEventListener('click', () => {
    const lat = (23.47 + Math.random() * 0.05).toFixed(4);
    const lng = (93.32 + Math.random() * 0.05).toFixed(4);
    document.querySelector('#incidentLocation').value = `Champhai Corridor (${lat}°N, ${lng}°E)`;
    showToast('📍 GPS location coordinates captured successfully.');
  });

  // Submit Field Report
  document.querySelector('#fieldReportForm')?.addEventListener('submit', (e) => {
    const type = document.querySelector('#incidentType').value;
    const location = document.querySelector('#incidentLocation').value;

    const newRep = {
      type: type,
      location: location,
      verified: true,
      time: 'Just now',
      icon: type.includes('blockage') ? 'rocks' : type.includes('crack') ? 'crack' : 'mud'
    };

    fieldReportsList.unshift(newRep);
    renderFieldReports();

    const queue = JSON.parse(localStorage.getItem('nexsolve-report-queue') || '[]');
    queue.push({ ...newRep, createdAt: new Date().toISOString() });
    localStorage.setItem('nexsolve-report-queue', JSON.stringify(queue));
    updateQueueCount();

    reportDialog?.close();
    showToast(offlineMode ? 'Report saved to PWA offline queue. Will sync when online.' : 'Field report submitted & AI verified!');
  });

  // --- MULTILINGUAL VOICE MEMO & SPEECH SYNTHESIS ENGINE ---
  const responseDialog = document.querySelector('#responseDialog');
  const alertLanguageSelect = document.querySelector('#alertLanguage');
  const alertPreviewText = document.querySelector('#alertPreview');
  const speakTTSBtn = document.querySelector('#speakTTSBtn');
  const ttsStatus = document.querySelector('#ttsStatus');

  function updateAlertPreviewText(langKey) {
    const translation = alertTranslations[langKey] || alertTranslations['english'];
    if (alertPreviewText) {
      alertPreviewText.innerHTML = translation.displayHTML;
    }
  }

  document.querySelector('#dispatchButton')?.addEventListener('click', () => {
    const selectedLang = alertLanguageSelect ? alertLanguageSelect.value : 'english';
    updateAlertPreviewText(selectedLang);
    responseDialog?.showModal();
  });

  document.querySelector('#closeResponseDialog')?.addEventListener('click', () => {
    responseDialog?.close();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  });

  alertLanguageSelect?.addEventListener('change', (e) => {
    const lang = e.target.value;
    updateAlertPreviewText(lang);
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    ttsStatus.textContent = `Ready to speak in ${alertTranslations[lang]?.name || lang}`;
  });

  // Web Audio Siren Beep Beacon Generator
  function playAlertChime() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note chime
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.2);
    } catch(e) {
      // AudioContext fallback ignored
    }
  }

  // Precision Speech Synthesis Handler
  speakTTSBtn?.addEventListener('click', () => {
    if (!('speechSynthesis' in window)) {
      showToast('Web Speech API Text-to-Speech not supported by browser.');
      return;
    }

    window.speechSynthesis.cancel(); // Stop active speech
    playAlertChime();

    const langKey = alertLanguageSelect ? alertLanguageSelect.value : 'english';
    const translation = alertTranslations[langKey] || alertTranslations['english'];

    const spokenText = translation.spokenText;
    const utterance = new SpeechSynthesisUtterance(spokenText);

    // Pre-fetch browser voice engines
    const voices = window.speechSynthesis.getVoices();
    let targetVoice = voices.find(v => v.lang === translation.langCode || v.lang.startsWith(translation.langCode.split('-')[0]));
    
    if (!targetVoice && translation.fallbackLang) {
      targetVoice = voices.find(v => v.lang === translation.fallbackLang || v.lang.startsWith(translation.fallbackLang.split('-')[0]));
    }

    if (targetVoice) {
      utterance.voice = targetVoice;
      utterance.lang = targetVoice.lang;
    } else {
      utterance.lang = translation.langCode || 'en-IN';
    }

    utterance.rate = 0.92;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      ttsStatus.textContent = `🔊 Playing voice broadcast in ${translation.name}...`;
      speakTTSBtn.style.background = '#f43f5e';
      speakTTSBtn.style.color = '#ffffff';
    };

    utterance.onend = () => {
      ttsStatus.textContent = `Voice broadcast in ${translation.name} completed.`;
      speakTTSBtn.style.background = '#ffffff';
      speakTTSBtn.style.color = '#000000';
    };

    utterance.onerror = (err) => {
      console.warn('SpeechSynthesis error:', err);
      ttsStatus.textContent = 'Voice playback finished.';
      speakTTSBtn.style.background = '#ffffff';
      speakTTSBtn.style.color = '#000000';
    };

    window.speechSynthesis.speak(utterance);
  });

  // Pre-load voices on browser load
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.getVoices();
    };
  }

  document.querySelector('#responseForm')?.addEventListener('submit', () => {
    responseDialog?.close();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    showToast('🚀 Multilingual Warning broadcasted to Champhai district SMS & Siren network!');
  });

  // --- PWA OFFLINE QUEUE MANAGER ---
  const offlineToggle = document.querySelector('#offlineToggle');
  const inspectQueueBtn = document.querySelector('#inspectQueueBtn');
  const queueDialog = document.querySelector('#queueDialog');

  function updateQueueCount() {
    const queue = JSON.parse(localStorage.getItem('nexsolve-report-queue') || '[]');
    const countEl = document.querySelector('#queueCount');
    if (countEl) countEl.textContent = `${queue.length} reports`;
  }

  offlineToggle?.addEventListener('click', () => {
    offlineMode = !offlineMode;
    const netStatus = document.querySelector('#networkStatus');
    const pulse = document.querySelector('#networkPulse');

    if (offlineMode) {
      if (netStatus) netStatus.textContent = 'OFFLINE MODE';
      offlineToggle.textContent = 'Restore System';
      pulse?.classList.add('offline-mode');
      showToast('Simulated Offline Mode enabled. Field reports stored locally in queue.');
    } else {
      if (netStatus) netStatus.textContent = 'SYSTEM READY';
      offlineToggle.textContent = 'Simulate Offline';
      pulse?.classList.remove('offline-mode');
      showToast('System connection restored. Processing offline queue...');
      syncOfflineQueue();
    }
  });

  inspectQueueBtn?.addEventListener('click', () => {
    renderQueueItems();
    queueDialog?.showModal();
  });

  document.querySelector('#closeQueueDialog')?.addEventListener('click', () => {
    queueDialog?.close();
  });

  function renderQueueItems() {
    const queueList = document.querySelector('#queueItemList');
    if (!queueList) return;

    const queue = JSON.parse(localStorage.getItem('nexsolve-report-queue') || '[]');
    if (queue.length === 0) {
      queueList.innerHTML = '<div style="padding:20px;text-align:center;color:#a1a1aa;">No pending offline reports in queue.</div>';
      return;
    }

    queueList.innerHTML = queue.map((q, idx) => `
      <div style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;">
        <div>
          <strong style="color:#ffffff;">#${idx + 1} · ${q.type}</strong>
          <div style="font-size:11px;color:#a1a1aa;">${q.location}</div>
        </div>
        <span style="font-size:10px;background:rgba(6,182,212,0.15);color:#06b6d4;padding:2px 6px;border-radius:4px;font-weight:bold;">Queued</span>
      </div>
    `).join('');
  }

  document.querySelector('#clearQueueBtn')?.addEventListener('click', () => {
    localStorage.removeItem('nexsolve-report-queue');
    updateQueueCount();
    renderQueueItems();
    showToast('Offline queue cleared.');
  });

  document.querySelector('#syncQueueNowBtn')?.addEventListener('click', () => {
    syncOfflineQueue();
    queueDialog?.close();
  });

  function syncOfflineQueue() {
    const queue = JSON.parse(localStorage.getItem('nexsolve-report-queue') || '[]');
    if (queue.length === 0) {
      showToast('No pending reports to sync.');
      return;
    }

    localStorage.removeItem('nexsolve-report-queue');
    updateQueueCount();
    showToast(`⚡ Synchronized ${queue.length} offline reports with central disaster server!`);
  }

  // Region Selector Change Handler
  document.querySelector('#regionSelect')?.addEventListener('change', (e) => {
    const selectedState = e.target.value;
    if (selectedState === 'ner') {
      leafletMap?.setView([25.5788, 93.2473], 7);
    } else {
      const match = nerDistrictData.find(d => d.state.toLowerCase().includes(selectedState));
      if (match && leafletMap) {
        leafletMap.setView([match.lat, match.lng], 9);
      }
    }
    showToast(`Monitoring focus changed to: ${e.target.options[e.target.selectedIndex].text}`);
  });

  // Refresh AI Risk Trigger
  document.querySelector('#refreshRisk')?.addEventListener('click', () => {
    const nowStr = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    document.querySelector('#mapNote').textContent = `Esri Dark Gray Engine · Refreshed ${nowStr}`;
    showToast('AI Risk Engine recalculated using fresh IMD radar and sensor inputs.');
  });

  // Toast Notification Helper
  function showToast(msg) {
    const toast = document.querySelector('#toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3500);
  }

  // --- INITIALIZE ALL COMPONENTS ---
  initLeafletMap();
  initCharts();
  renderAlertList();
  renderRoadGrid();
  renderFieldReports();
  updateQueueCount();
});
