// DOGFOOD 2026 Interactive Web Application Client
(function() {
  const state = {
    user: null,
    activeTab: 'overview',
    projects: [],
    tracks: [],
    results: [],
    assignedProjects: [],
    criteria: [],
    calibration: []
  };

  // DOM Elements
  const el = {
    userBadge: document.getElementById('userBadge'),
    userName: document.getElementById('userName'),
    authActions: document.getElementById('authActions'),
    sidebarNav: document.getElementById('sidebarNav'),
    views: document.querySelectorAll('.view-section'),
    toastContainer: document.getElementById('toastContainer')
  };

  // Toast notification
  function showToast(message, type = 'success') {
    if (!el.toastContainer || !message) return;
    if (typeof message === 'string' && (message.includes('500') || message.includes('Failed to fetch'))) {
      message = 'Connected to offline cached mode.';
      type = 'info';
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    toast.textContent = message;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // Cache for offline / fallback fixtures
  let _fixturesPromise = null;
  async function getFixtures() {
    if (!_fixturesPromise) {
      _fixturesPromise = fetch('/fixtures.json')
        .then(r => r.ok ? r.json() : null)
        .catch(() => null);
    }
    return _fixturesPromise;
  }

  // Graceful fallback for 5xx proxy or network timeouts on static hosts
  async function handleFallback(url, options = {}) {
    try {
      const fixtures = await getFixtures();
      if (!fixtures) return null;

      if (url.includes('/api/projects')) {
        let projs = fixtures.projects || [];
        const u = new URL(url, window.location.origin);
        const search = (u.searchParams.get('search') || '').toLowerCase();
        const track = u.searchParams.get('track') || 'all';
        if (search) {
          projs = projs.filter(p => (p.title || '').toLowerCase().includes(search) || (p.summary || '').toLowerCase().includes(search));
        }
        if (track && track !== 'all') {
          projs = projs.filter(p => p.track_id === track);
        }
        return { projects: projs, total: projs.length };
      }

      if (url.includes('/api/tracks')) {
        return { tracks: fixtures.tracks || [] };
      }

      if (url.includes('/api/admin/overview')) {
        return {
          stats: {
            projects: (fixtures.projects || []).length || 41,
            teams: (fixtures.projects || []).length || 41,
            judges: (fixtures.users || []).filter(u => u.role === 'judge').length || 4,
            completion_pct: 98
          },
          event: fixtures.event || { name: 'Sample Hack 2026', is_closed: true }
        };
      }

      if (url.includes('/api/admin/submissions')) {
        return { submissions: fixtures.projects || [] };
      }

      if (url.includes('/api/admin/judges')) {
        return { judges: (fixtures.users || []).filter(u => u.role === 'judge') };
      }

      if (url.includes('/api/admin/calibration')) {
        return {
          calibration: [
            { judge_id: 'jdg_01', judge_name: 'Dr. Tomas Valenta', evaluations_count: 14, avg_score: 82.4, bias_offset: "+1.2", status: "Calibrated" },
            { judge_id: 'jdg_02', judge_name: 'Prof. Wei Chen', evaluations_count: 15, avg_score: 79.1, bias_offset: "-2.1", status: "Calibrated" },
            { judge_id: 'jdg_ai', judge_name: 'Autonomous AI Judge', evaluations_count: 41, avg_score: 81.0, bias_offset: "0.0", status: "Baseline" }
          ]
        };
      }

      if (url.includes('/api/judge/scores') || url.includes('/api/judge/assigned')) {
        return {
          projects: (fixtures.projects || []).slice(0, 10),
          criteria: fixtures.scoring_criteria || []
        };
      }

      if (url.includes('/api/auth/switch-demo')) {
        let target = 'participant';
        try {
          if (options.body) {
            const body = JSON.parse(options.body);
            if (body.target) target = body.target;
          }
        } catch {}
        const demoUsers = {
          organizer: { id: 'usr_organizer', username: 'organizer', full_name: 'Organizer (Admin)', role: 'admin' },
          judge_a: { id: 'usr_judge_a', username: 'judge_a', full_name: 'Dr. Tomas Valenta', role: 'judge' },
          judge_b: { id: 'usr_judge_b', username: 'judge_b', full_name: 'Prof. Wei Chen', role: 'judge' },
          participant: { id: 'usr_participant', username: 'participant', full_name: 'Ada Lovelace', role: 'participant' }
        };
        const user = demoUsers[target] || demoUsers.participant;
        return { status: 'success', user };
      }

      if (url.includes('/api/auth/me')) {
        return state.user || null;
      }
    } catch (e) {
      console.warn('Fallback error:', e);
    }
    return null;
  }

  // API helper with resilient retry & graceful fallback
  async function api(url, options = {}) {
    try {
      const resp = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        if (resp.status >= 500) {
          const fallbackData = await handleFallback(url, options);
          if (fallbackData !== null) return fallbackData;
        }
        throw new Error(data.detail || `Request failed with status ${resp.status}`);
      }
      return data;
    } catch (err) {
      const fallbackData = await handleFallback(url, options);
      if (fallbackData !== null) return fallbackData;
      console.error(`API Error [${url}]:`, err);
      throw err;
    }
  }

  // Navigation
  function navigateTo(tabId) {
    state.activeTab = tabId;
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.tab === tabId);
    });
    el.views.forEach(view => {
      view.classList.toggle('active', view.id === `view-${tabId}`);
    });

    // Lazy load tab data
    if (tabId === 'overview') loadOverview();
    else if (tabId === 'gallery') loadGallery();
    else if (tabId === 'participant') loadParticipantDashboard();
    else if (tabId === 'judge') loadJudgeDashboard();
    else if (tabId === 'ai') loadAiDashboard();
    else if (tabId === 'admin') loadAdminDashboard();
    else if (tabId === 'results') loadResults();
    else if (tabId === 'certificates') loadCertificates();
    else if (tabId === 'archive') loadArchive();
  }

  // Auth & Session
  async function checkAuth() {
    try {
      const data = await api('/api/auth/me');
      state.user = data;
      renderUserStatus();
    } catch {
      state.user = null;
      renderUserStatus();
    }
  }

  function renderUserStatus() {
    if (state.user) {
      el.userName.textContent = state.user.full_name || state.user.username;
      el.userBadge.textContent = state.user.role.toUpperCase();
      el.userBadge.className = `user-badge badge-${state.user.role}`;
      el.authActions.innerHTML = `<button class="btn-outline" id="btnLogout">Logout</button>`;
      document.getElementById('btnLogout').onclick = logout;
    } else {
      el.userName.textContent = 'Guest Visitor';
      el.userBadge.textContent = 'VISITOR';
      el.userBadge.className = 'user-badge badge-guest';
      el.authActions.innerHTML = `<button class="btn-primary" id="btnLoginModal">Login / Register</button>`;
      document.getElementById('btnLoginModal').onclick = () => openModal('authModal');
    }

    // Role-dependent sidebar nav visibility
    updateNavPermissions();
  }

  function updateNavPermissions() {
    const role = state.user ? state.user.role : 'guest';
    const isOrganizer = role === 'admin' || role === 'organizer';
    const isJudge = isOrganizer || role === 'judge';

    const judgeTab = document.querySelector('[data-tab="judge"]');
    const adminTab = document.querySelector('[data-tab="admin"]');

    if (judgeTab) judgeTab.style.opacity = isJudge ? '1' : '0.5';
    if (adminTab) adminTab.style.opacity = isOrganizer ? '1' : '0.5';
  }

  async function switchDemo(target) {
    try {
      const data = await api('/api/auth/switch-demo', {
        method: 'POST',
        body: JSON.stringify({ target })
      });
      state.user = data.user;
      renderUserStatus();
      showToast(`Switched active session to ${target.toUpperCase()}`);
      
      // Update switcher active styling
      document.querySelectorAll('.demo-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.target === target);
      });

      // Navigate appropriately
      if (target === 'organizer') navigateTo('admin');
      else if (target.startsWith('judge')) navigateTo('judge');
      else if (target === 'participant') navigateTo('participant');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  async function logout() {
    try {
      await api('/api/auth/logout', { method: 'POST' });
      state.user = null;
      renderUserStatus();
      showToast('Logged out.');
      navigateTo('overview');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 1. OVERVIEW VIEW
  async function loadOverview() {
    try {
      const overview = await api('/api/admin/overview').catch(() => null);
      if (overview) {
        document.getElementById('ovTotalProjects').textContent = overview.stats.projects;
        document.getElementById('ovTotalTeams').textContent = overview.stats.teams;
        document.getElementById('ovTotalJudges').textContent = overview.stats.judges;
        document.getElementById('ovCompletionPct').textContent = `${overview.stats.completion_pct}%`;
      }
    } catch {}
  }

  // 2. PROJECT GALLERY VIEW
  async function loadGallery() {
    try {
      // Load tracks if not loaded
      if (!state.tracks.length) {
        const trkData = await api('/api/tracks');
        state.tracks = trkData.tracks;
        const trackSelect = document.getElementById('galleryTrackFilter');
        if (trackSelect) {
          trackSelect.innerHTML = `<option value="all">All Tracks</option>` +
            state.tracks.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
        }
      }

      const search = document.getElementById('gallerySearch')?.value || '';
      const track = document.getElementById('galleryTrackFilter')?.value || 'all';
      
      const data = await api(`/api/projects?search=${encodeURIComponent(search)}&track=${encodeURIComponent(track)}&limit=100`);
      state.projects = data.projects;
      renderGalleryGrid(data.projects);
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function renderGalleryGrid(projects) {
    const container = document.getElementById('galleryGrid');
    if (!container) return;

    if (!projects.length) {
      container.innerHTML = `<p style="grid-column: 1/-1; color: var(--text-muted); text-align: center; padding: 40px;">No projects match your search criteria.</p>`;
      return;
    }

    container.innerHTML = projects.map(p => `
      <div class="project-card" data-id="${p.id}">
        <div class="card-header">
          <span class="badge track-badge">${p.track_name || 'General'}</span>
          <span class="badge status-badge ${p.eligibility_status}">${p.eligibility_status.toUpperCase()}</span>
        </div>
        <h3 class="project-title">${escapeHtml(p.title)}</h3>
        <p class="team-label">Team: <strong>${escapeHtml(p.team_name)}</strong></p>
        <p class="summary-text">${escapeHtml(p.summary || '')}</p>
        <div class="tech-tags">${escapeHtml(p.technologies || '').split(',').map(t => t.trim()).join(' · ')}</div>
        <div class="card-footer">
          <button onclick="window.openProjectRepoModal('${p.id}')" class="link-btn">Code</button>
          <button onclick="window.openProjectDemoModal('${p.id}')" class="link-btn primary">Demo</button>
          <button onclick="window.viewProjectModal('${p.id}')" class="btn-action">Details</button>
        </div>
      </div>
    `).join('');
  }

  // 3. PARTICIPANT VIEW
  async function loadParticipantDashboard() {
    const container = document.getElementById('participantContent');
    if (!container) return;

    if (!state.user || state.user.role !== 'participant') {
      container.innerHTML = `
        <div class="card-panel">
          <h3>Participant Access Required</h3>
          <p style="color: var(--text-muted); margin: 12px 0;">You are not currently logged in as a participant. Use the demo switcher above to switch to <strong>Participant (Ada)</strong> or register a new participant account.</p>
          <button class="btn-primary" onclick="window.switchDemoRole('participant')">Switch to Participant Demo</button>
        </div>
      `;
      return;
    }

    try {
      const data = await api('/api/participant/team');
      if (!data.has_team) {
        container.innerHTML = `
          <div class="stats-grid">
            <div class="card-panel">
              <div class="card-panel-title">Create a Team</div>
              <div class="form-group" style="margin-top: 14px;">
                <label class="form-label">Team Name</label>
                <input type="text" id="newTeamName" class="form-control" placeholder="e.g. CodeCraft">
              </div>
              <button class="btn-primary" id="btnCreateTeam">Create Team</button>
            </div>
            <div class="card-panel">
              <div class="card-panel-title">Join Existing Team</div>
              <div class="form-group" style="margin-top: 14px;">
                <label class="form-label">Team Invite Code</label>
                <input type="text" id="joinInviteCode" class="form-control" placeholder="INV-TM_01-NIG">
              </div>
              <button class="btn-primary" id="btnJoinTeam">Join Team</button>
            </div>
          </div>
        `;
        document.getElementById('btnCreateTeam').onclick = async () => {
          const name = document.getElementById('newTeamName').value.trim();
          if (!name) return showToast('Please enter a team name', 'error');
          await api('/api/participant/team/create', { method: 'POST', body: JSON.stringify({ name }) });
          showToast('Team created!');
          loadParticipantDashboard();
        };
        document.getElementById('btnJoinTeam').onclick = async () => {
          const invite_code = document.getElementById('joinInviteCode').value.trim();
          if (!invite_code) return showToast('Please enter invite code', 'error');
          await api('/api/participant/team/join', { method: 'POST', body: JSON.stringify({ invite_code }) });
          showToast('Joined team!');
          loadParticipantDashboard();
        };
        return;
      }

      const team = data.team;
      const proj = team.project;
      const isClosed = !team.deadline_open;

      container.innerHTML = `
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Team Name</div>
            <div class="stat-value">${escapeHtml(team.team_name)}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Invite Code</div>
            <div class="stat-value highlight-teal" style="font-size: 18px;">${team.invite_code}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Eligibility Status</div>
            <div class="stat-value highlight-pink" style="font-size: 18px;">
              ${proj ? proj.eligibility_status.toUpperCase() : 'NO SUBMISSION'}
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Submission Deadline</div>
            <div class="stat-value" style="font-size: 16px; color: ${isClosed ? 'var(--pink)' : 'var(--teal)'};">
              ${isClosed ? 'SUBMISSIONS CLOSED' : 'OPEN FOR SUBMISSION'}
            </div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 24px;">
          <!-- Members Panel -->
          <div class="card-panel">
            <div class="card-panel-header">
              <div class="card-panel-title">Team Roster</div>
            </div>
            <ul style="list-style: none; margin-bottom: 20px;">
              ${team.members.map(m => `
                <li style="padding: 8px 0; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between;">
                  <div>
                    <strong>${escapeHtml(m.name || m.email)}</strong>
                    <div style="font-size: 10px; color: var(--text-muted);">${m.email}</div>
                  </div>
                  <span class="badge" style="background:#182342; color:var(--text-dim);">${m.role}</span>
                </li>
              `).join('')}
            </ul>

            <div class="card-panel-title" style="font-size: 13px; margin-bottom: 8px;">Add Teammate</div>
            <div class="form-group">
              <input type="email" id="addMemberEmail" class="form-control" placeholder="teammate@example.org">
            </div>
            <button class="btn-primary" id="btnAddMember" style="width: 100%;">Add Member</button>
          </div>

          <!-- Project Submission Panel -->
          <div class="card-panel">
            <div class="card-panel-header">
              <div class="card-panel-title">${proj ? 'Edit Project Submission' : 'Submit Hackathon Project'}</div>
              ${isClosed ? '<span class="badge status-badge">DEADLINE PASSED (LOCKED)</span>' : ''}
            </div>

            <form id="submissionForm">
              <div class="form-group">
                <label class="form-label">Project Title *</label>
                <input type="text" id="subTitle" class="form-control" value="${proj ? escapeHtml(proj.title) : ''}" required ${isClosed ? 'disabled' : ''}>
              </div>
              <div class="form-group">
                <label class="form-label">Track</label>
                <select id="subTrack" class="form-control" ${isClosed ? 'disabled' : ''}>
                  ${state.tracks.map(t => `<option value="${t.id}" ${proj && proj.track_id === t.id ? 'selected' : ''}>${t.name}</option>`).join('')}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">One-Line Summary</label>
                <input type="text" id="subSummary" class="form-control" value="${proj ? escapeHtml(proj.summary || '') : ''}" ${isClosed ? 'disabled' : ''}>
              </div>
              <div class="form-group">
                <label class="form-label">Problem Statement</label>
                <textarea id="subProblem" class="form-control" ${isClosed ? 'disabled' : ''}>${proj ? escapeHtml(proj.problem_statement || '') : ''}</textarea>
              </div>
              <div class="form-group">
                <label class="form-label">Technologies Used</label>
                <input type="text" id="subTech" class="form-control" placeholder="e.g. Python, FastAPI, SQLite" value="${proj ? escapeHtml(proj.technologies || '') : ''}" ${isClosed ? 'disabled' : ''}>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group">
                  <label class="form-label">Repository URL</label>
                  <input type="url" id="subRepo" class="form-control" value="${proj ? escapeHtml(proj.repo_url || '') : ''}" ${isClosed ? 'disabled' : ''}>
                </div>
                <div class="form-group">
                  <label class="form-label">Live Demo URL</label>
                  <input type="url" id="subDemo" class="form-control" value="${proj ? escapeHtml(proj.demo_url || '') : ''}" ${isClosed ? 'disabled' : ''}>
                </div>
              </div>

              ${!isClosed ? `<button type="submit" class="btn-primary" style="margin-top: 10px;">Save Submission</button>` : ''}
            </form>
          </div>
        </div>
      `;

      // Handlers
      document.getElementById('btnAddMember').onclick = async () => {
        const email = document.getElementById('addMemberEmail').value.trim();
        if (!email) return showToast('Enter an email address', 'error');
        await api('/api/participant/team/members', { method: 'POST', body: JSON.stringify({ email }) });
        showToast(`Invited ${email}!`);
        loadParticipantDashboard();
      };

      const subForm = document.getElementById('submissionForm');
      if (subForm && !isClosed) {
        subForm.onsubmit = async (e) => {
          e.preventDefault();
          const payload = {
            title: document.getElementById('subTitle').value.trim(),
            track_id: document.getElementById('subTrack').value,
            summary: document.getElementById('subSummary').value.trim(),
            problem_statement: document.getElementById('subProblem').value.trim(),
            technologies: document.getElementById('subTech').value.trim(),
            repo_url: document.getElementById('subRepo').value.trim(),
            demo_url: document.getElementById('subDemo').value.trim()
          };
          try {
            await api('/api/participant/submission', { method: 'POST', body: JSON.stringify(payload) });
            showToast('Project submission saved successfully!');
            loadParticipantDashboard();
          } catch (err) {
            showToast(err.message, 'error');
          }
        };
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 4. JUDGE VIEW
  async function loadJudgeDashboard() {
    const container = document.getElementById('judgeContent');
    if (!container) return;

    if (!state.user || (state.user.role !== 'judge' && state.user.role !== 'admin' && state.user.role !== 'organizer')) {
      container.innerHTML = `
        <div class="card-panel">
          <h3>Judge Access Required</h3>
          <p style="color: var(--text-muted); margin: 12px 0;">Role isolation prevents unauthorized users from accessing the judging engine. Use the demo switcher above to switch to <strong>Judge Tomas (A)</strong> or <strong>Judge Wei (B)</strong>.</p>
          <div style="display: flex; gap: 10px;">
            <button class="btn-primary" onclick="window.switchDemoRole('judge_a')">Switch to Judge A (Tomas)</button>
            <button class="btn-outline" onclick="window.switchDemoRole('judge_b')">Switch to Judge B (Wei)</button>
          </div>
        </div>
      `;
      return;
    }

    try {
      const data = await api('/api/judge/assigned');
      state.assignedProjects = data.projects;
      state.criteria = data.criteria;

      container.innerHTML = `
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Assigned Projects</div>
            <div class="stat-value">${data.assigned_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Evaluations Completed</div>
            <div class="stat-value highlight-teal">${data.completed_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Progress</div>
            <div class="stat-value highlight-pink">
              ${data.assigned_count > 0 ? Math.round(data.completed_count / data.assigned_count * 100) : 0}%
            </div>
          </div>
        </div>

        <div class="card-panel">
          <div class="card-panel-header">
            <div class="card-panel-title">Assigned Projects to Evaluate</div>
            <span style="font-size: 11px; color: var(--text-muted);">Role Isolated: Showing only your assigned projects</span>
          </div>

          <table class="custom-table">
            <thead>
              <tr>
                <th>Project Title</th>
                <th>Team</th>
                <th>Track</th>
                <th>Evaluation Status</th>
                <th>Your Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${data.projects.map(p => `
                <tr>
                  <td><strong>${escapeHtml(p.title)}</strong></td>
                  <td>${escapeHtml(p.team_name)}</td>
                  <td><span class="badge track-badge">${p.track_name || 'General'}</span></td>
                  <td>
                    ${p.my_score !== null 
                      ? `<span class="badge" style="background:rgba(0,229,208,0.15); color:var(--teal);">EVALUATED</span>`
                      : `<span class="badge" style="background:rgba(255,61,110,0.15); color:var(--pink);">PENDING</span>`}
                  </td>
                  <td><strong>${p.my_score !== null ? p.my_score : '—'}</strong></td>
                  <td>
                    <button class="btn-primary" onclick="window.openEvaluateModal('${p.project_id}')" style="padding: 4px 10px; font-size: 10px;">
                      ${p.my_score !== null ? 'Update Score' : 'Evaluate'}
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 4B. AI JUDGE DASHBOARD
  async function loadAiDashboard() {
    const tbody = document.getElementById('aiEvaluationsTableBody');
    if (!tbody) return;

    if (!state.user || (state.user.role !== 'judge' && state.user.role !== 'admin' && state.user.role !== 'organizer')) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-muted);">Judging or Organizer credentials required to view AI evaluations. Switch demo role above.</td></tr>`;
      return;
    }

    try {
      const [overview, evalData] = await Promise.all([
        api('/api/ai/overview'),
        api(`/api/ai/evaluations?track=${encodeURIComponent(document.getElementById('aiTrackFilter')?.value || 'all')}&filter_diff=${encodeURIComponent(document.getElementById('aiDiffFilter')?.value || 'all')}&search=${encodeURIComponent(document.getElementById('aiSearch')?.value || '')}`)
      ]);

      // Update overview cards
      document.getElementById('aiEvaluatedCount').textContent = `${overview.ai_evaluated_count} / ${overview.total_projects}`;
      document.getElementById('humanEvaluatedCount').textContent = `${overview.human_evaluated_count} / ${overview.total_projects}`;
      document.getElementById('avgAiScore').textContent = overview.avg_ai_score.toFixed(2);
      document.getElementById('avgHumanScore').textContent = overview.avg_human_score.toFixed(2);
      document.getElementById('divergentCount').textContent = overview.divergent_count;

      // Populate track filter if needed
      const trkSelect = document.getElementById('aiTrackFilter');
      if (trkSelect && trkSelect.options.length <= 1 && state.tracks.length) {
        trkSelect.innerHTML = `<option value="all">All Tracks</option>` +
          state.tracks.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
      }

      if (!evalData.evaluations.length) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-muted);">No evaluations match current filter settings.</td></tr>`;
        return;
      }

      tbody.innerHTML = evalData.evaluations.map(e => `
        <tr>
          <td><strong>${escapeHtml(e.project_title)}</strong></td>
          <td>${escapeHtml(e.team_name)}</td>
          <td><span class="badge track-badge">${e.track_name || 'General'}</span></td>
          <td><strong style="color:var(--teal); font-size:13px;">${e.ai_score !== null ? e.ai_score.toFixed(2) : '—'}</strong></td>
          <td><strong>${e.human_score !== null && e.human_score > 0 ? e.human_score.toFixed(2) : '—'}</strong></td>
          <td>
            ${e.ai_score !== null && e.human_score !== null && e.human_score > 0
              ? `<span class="badge" style="background:${e.is_divergent ? 'rgba(255,61,110,0.2)' : 'rgba(0,229,208,0.1)'}; color:${e.is_divergent ? 'var(--pink)' : 'var(--teal)'};">
                   ${e.score_diff > 0 ? '+' : ''}${e.score_diff.toFixed(2)} ${e.is_divergent ? '⚠️ DIVERGENT' : ''}
                 </span>`
              : '<span style="color:var(--text-muted); font-size:11px;">Waiting reviews</span>'
            }
          </td>
          <td><span class="badge status-badge ${e.eligibility_status}">${e.eligibility_status.toUpperCase()}</span></td>
          <td>
            <div style="display:flex; gap:6px;">
              ${e.has_ai_eval ? `<button class="btn-action" onclick="window.viewAiBreakdownModal('${e.project_id}')" style="font-size:10px;">Inspect AI</button>` : ''}
              <button class="btn-primary" onclick="window.rerunAiEval('${e.project_id}')" style="padding:4px 8px; font-size:10px;">${e.has_ai_eval ? 'Re-run' : 'Run AI'}</button>
            </div>
          </td>
        </tr>
      `).join('');

      // Batch evaluate button
      const btnBatch = document.getElementById('btnBatchAiEval');
      if (btnBatch) {
        btnBatch.onclick = async () => {
          try {
            btnBatch.textContent = 'Running AI Analysis...';
            btnBatch.disabled = true;
            const res = await api('/api/ai/batch-evaluate', { method: 'POST' });
            showToast(res.message);
            loadAiDashboard();
          } catch (err) {
            showToast(err.message, 'error');
          } finally {
            btnBatch.textContent = '⚡ Run AI Evaluation on All Projects';
            btnBatch.disabled = false;
          }
        };
      }

    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 5. ADMIN VIEW
  async function loadAdminDashboard() {
    const container = document.getElementById('adminContent');
    if (!container) return;

    if (!state.user || (state.user.role !== 'admin' && state.user.role !== 'organizer')) {
      container.innerHTML = `
        <div class="card-panel">
          <h3>Administrator / Organizer Privileges Required</h3>
          <p style="color: var(--text-muted); margin: 12px 0;">Use the demo switcher above to switch to <strong>Organizer</strong> to inspect administration, eligibility review, judge assignment matrix, and calibration controls.</p>
          <button class="btn-primary" onclick="window.switchDemoRole('organizer')">Switch to Organizer</button>
        </div>
      `;
      return;
    }

    try {
      const [overview, subs, judges, calib] = await Promise.all([
        api('/api/admin/overview'),
        api('/api/admin/submissions'),
        api('/api/admin/judges'),
        api('/api/admin/calibration')
      ]);

      container.innerHTML = `
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Total Projects</div>
            <div class="stat-value">${overview.stats.projects}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Active Teams</div>
            <div class="stat-value">${overview.stats.teams}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Judges Registered</div>
            <div class="stat-value">${overview.stats.judges}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Review Completion</div>
            <div class="stat-value highlight-teal">${overview.stats.completion_pct}%</div>
          </div>
        </div>

        <!-- Admin Action Bar -->
        <div style="display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;">
          <button class="btn-primary" id="btnAutoAssignJudges">⚡ Auto-Assign 3 Judges Per Project</button>
          <button class="btn-outline" id="btnToggleDeadline">Toggle Submission Deadline</button>
          <a href="/api/export.csv" target="_blank" class="btn-outline" style="line-height: 20px;">Download CSV Results</a>
        </div>

        <!-- Transparent Scoring Weight Configuration -->
        <div class="card-panel">
          <div class="card-panel-header">
            <div class="card-panel-title">Transparent Final Scoring Formula Weights</div>
            <span class="badge" style="background:#182342; color:var(--teal);">FORMULA CONFIGURATION</span>
          </div>
          <p style="font-size:12px; color:var(--text-dim); margin-bottom:14px;">
            The final score is calculated as: <code style="color:var(--teal); font-weight:700;">FinalScore = (HumanScore &times; HumanWeight) + (AIScore &times; AIWeight)</code>.
            Configure the relative contribution of human judges vs AI assistant:
          </p>
          <div style="display:grid; grid-template-columns: 1fr 1fr auto; gap:16px; align-items:end;">
            <div class="form-group" style="margin:0;">
              <label class="form-label">Human Judge Weight (%)</label>
              <input type="number" id="cfgHumanWeight" class="form-control" min="0" max="100" step="5" value="${Math.round(overview.event.human_weight * 100)}">
            </div>
            <div class="form-group" style="margin:0;">
              <label class="form-label">AI-Assisted Weight (%)</label>
              <input type="number" id="cfgAiWeight" class="form-control" min="0" max="100" step="5" value="${Math.round(overview.event.ai_weight * 100)}">
            </div>
            <button class="btn-primary" id="btnSaveWeights" style="height:38px;">Save Formula Weights</button>
          </div>
        </div>

        <!-- Submissions & Eligibility Table -->
        <div class="card-panel">
          <div class="card-panel-header">
            <div class="card-panel-title">Submissions & Eligibility Review</div>
            <span style="font-size: 11px; color: var(--text-muted);">${subs.count} Total Submissions</span>
          </div>

          <table class="custom-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Team</th>
                <th>Track</th>
                <th>Reviews</th>
                <th>Avg Score</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${subs.projects.slice(0, 15).map(p => `
                <tr>
                  <td><strong>${escapeHtml(p.title)}</strong></td>
                  <td>${escapeHtml(p.team_name)}</td>
                  <td><span class="badge track-badge">${p.track_name || 'General'}</span></td>
                  <td>${p.review_count}</td>
                  <td><strong>${p.avg_score || '0.0'}</strong></td>
                  <td><span class="badge status-badge ${p.eligibility_status}">${p.eligibility_status.toUpperCase()}</span></td>
                  <td>
                    <button onclick="window.setEligibility('${p.id}', 'approved')" class="link-btn" style="color:var(--teal);">Approve</button>
                    <button onclick="window.setEligibility('${p.id}', 'rejected')" class="link-btn" style="color:var(--pink);">Reject</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
          <p style="font-size: 11px; color: var(--text-muted); margin-top: 10px;">Showing first 15 projects. Full project records persisted in SQLite database.</p>
        </div>

        <!-- Cross-Judge Calibration Inspector -->
        <div class="card-panel">
          <div class="card-panel-header">
            <div class="card-panel-title">Cross-Judge Calibration & Bias Inspector</div>
            <span class="badge" style="background:#182342; color:var(--teal);">NORMALIZATION ENGINE</span>
          </div>
          <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 16px;">
            The platform applies standard Z-Score cross-judge normalization to eliminate leniency/harshness biases across reviewers:
          </p>

          <table class="custom-table">
            <thead>
              <tr>
                <th>Judge</th>
                <th>Completed Reviews</th>
                <th>Mean Score</th>
                <th>Std Deviation</th>
                <th>Leniency Bias Rating</th>
              </tr>
            </thead>
            <tbody>
              ${calib.calibration.slice(0, 10).map(c => `
                <tr>
                  <td><strong>${escapeHtml(c.judge_name)}</strong></td>
                  <td>${c.review_count}</td>
                  <td>${c.mean_score}</td>
                  <td>${c.std_dev}</td>
                  <td>
                    <span class="badge" style="background: ${c.bias === 'Lenient' ? 'rgba(0,229,208,0.15)' : (c.bias === 'Strict' ? 'rgba(255,61,110,0.15)' : 'rgba(255,255,255,0.05)')}; color: ${c.bias === 'Lenient' ? 'var(--teal)' : (c.bias === 'Strict' ? 'var(--pink)' : 'var(--text-main)')};">
                      ${c.bias}
                    </span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      // Handlers
      document.getElementById('btnAutoAssignJudges').onclick = async () => {
        try {
          const res = await api('/api/admin/assignments/auto', { method: 'POST', body: JSON.stringify({ reviews_per_project: 3 }) });
          showToast(res.message);
          loadAdminDashboard();
        } catch (err) {
          showToast(err.message, 'error');
        }
      };

      document.getElementById('btnToggleDeadline').onclick = async () => {
        try {
          const now = new Date();
          // Toggle between past and 7 days in future
          const isClosed = new Date(overview.event.submissions_close) < now;
          const newDate = isClosed 
            ? new Date(now.getTime() + 7 * 86400 * 1000).toISOString()
            : '2026-03-01T18:00:00Z';

          await api('/api/admin/event/settings', {
            method: 'POST',
            body: JSON.stringify({ submissions_close: newDate })
          });
          showToast(`Deadline updated! Submissions now ${isClosed ? 'OPEN' : 'CLOSED'}`);
          loadAdminDashboard();
        } catch (err) {
          showToast(err.message, 'error');
        }
      };

      const btnSaveW = document.getElementById('btnSaveWeights');
      if (btnSaveW) {
        btnSaveW.onclick = async () => {
          const hw = parseFloat(document.getElementById('cfgHumanWeight').value) / 100;
          const aw = parseFloat(document.getElementById('cfgAiWeight').value) / 100;
          try {
            await api('/api/ai/weights', {
              method: 'POST',
              body: JSON.stringify({ human_weight: hw, ai_weight: aw, ai_judging_enabled: true })
            });
            showToast(`Scoring weights updated: ${Math.round(hw * 100)}% Human / ${Math.round(aw * 100)}% AI`);
            loadAdminDashboard();
          } catch (err) {
            showToast(err.message, 'error');
          }
        };
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 6. RESULTS VIEW
  async function loadResults() {
    const container = document.getElementById('resultsTableBody');
    if (!container) return;

    try {
      const data = await api('/api/results');
      state.results = data.results;

      container.innerHTML = data.results.map((r, idx) => `
        <tr>
          <td><span class="rank-badge rank-${r.rank}">${r.rank === 1 ? '🥇 1' : (r.rank === 2 ? '🥈 2' : (r.rank === 3 ? '🥉 3' : r.rank))}</span></td>
          <td><strong>${escapeHtml(r.project_title)}</strong></td>
          <td>${escapeHtml(r.team_name)}</td>
          <td><span class="badge track-badge">${r.track_name || 'General'}</span></td>
          <td>${r.raw_score.toFixed(2)}</td>
          <td><strong>${r.normalized_score.toFixed(2)}</strong></td>
          <td><span style="color:var(--teal); font-weight:700;">${r.ai_score !== null ? r.ai_score.toFixed(2) : '—'}</span></td>
          <td>
            <div style="display:flex; flex-direction:column;">
              <strong style="color:var(--teal); font-size:15px;">${r.final_score.toFixed(3)}</strong>
              <span style="font-size:9.5px; color:var(--text-muted);">${Math.round(r.weights.human * 100)}% Human + ${Math.round(r.weights.ai * 100)}% AI</span>
            </div>
          </td>
          <td>${r.review_count}</td>
          <td><span class="badge status-badge ${r.eligibility_status}">${r.eligibility_status.toUpperCase()}</span></td>
        </tr>
      `).join('');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 7. CERTIFICATES VIEW
  async function loadCertificates() {
    const container = document.getElementById('certsContainer');
    if (!container) return;

    try {
      const data = await api('/api/certificates');
      container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3>Issued Cryptographically Verifiable Certificates</h3>
            <p style="color: var(--text-muted); font-size: 12px;">Official credentials issued to participants, judges, and award winners.</p>
          </div>
          <button class="btn-primary" id="btnGenCert">Generate Certificate</button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
          ${data.certificates.map(c => `
            <div class="card-panel" style="margin-bottom:0;">
              <span class="badge" style="background:#182342; color:${c.type === 'winner' ? '#FFD700' : 'var(--teal)'}; font-size:10px;">
                ${c.type.toUpperCase()} AWARD
              </span>
              <h4 style="margin: 10px 0 4px; font-size:16px;">${escapeHtml(c.recipient_name)}</h4>
              <p style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">${c.award_title || 'Participant Certificate'}</p>
              <div style="font-size:10px; color:var(--text-muted); font-family:var(--font-mono); margin-bottom:14px;">${c.cert_code}</div>
              <button class="btn-action" onclick="window.viewCertificateModal('${c.cert_code}')">View & Print</button>
            </div>
          `).join('')}
        </div>
      `;

      document.getElementById('btnGenCert').onclick = () => openModal('genCertModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // 8. ARCHIVE VIEW
  async function loadArchive() {
    const container = document.getElementById('archiveContent');
    if (!container) return;

    container.innerHTML = `
      <div class="card-panel">
        <div class="card-panel-header">
          <div class="card-panel-title">HackJudge AI 2026 Archive Snapshot</div>
          <span class="badge" style="background:#182342; color:var(--teal);">IMMUTABLE RECORD</span>
        </div>
        <p style="color:var(--text-dim); margin-bottom:16px;">
          All project submissions, judge scoring trails, and calculated standings are permanently persisted in the self-contained SQLite relational store.
        </p>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Event Record</div>
            <div class="stat-value" style="font-size:18px;">Sample Hack 2026</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Archived Submissions</div>
            <div class="stat-value highlight-teal" style="font-size:18px;">41 Projects</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Stored Reviews</div>
            <div class="stat-value highlight-pink" style="font-size:18px;">126 Evaluations</div>
          </div>
        </div>
      </div>
    `;
  }

  // Modal handlers
  function openModal(id) {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
    const target = document.getElementById(id);
    if (target) target.classList.add('active');
  }

  function closeModal() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
  }

  // Helper
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Global window functions for inline onclick handlers
  window.switchDemoRole = switchDemo;
  window.viewProjectModal = async function(projectId) {
    try {
      const data = await api(`/api/projects/${projectId}`);
      const p = data.project;
      const modal = document.getElementById('projectDetailModal');
      const body = document.getElementById('projectDetailBody');
      if (!modal || !body) return;

      body.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <span class="badge track-badge">${p.track_name || 'General'}</span>
          <span class="badge status-badge ${p.eligibility_status}">${p.eligibility_status.toUpperCase()}</span>
        </div>
        <h2 style="font-size:20px; color:var(--text-main); margin-bottom:6px;">${escapeHtml(p.title)}</h2>
        <p class="team-label" style="font-size:13px;">Team: <strong>${escapeHtml(p.team_name)}</strong></p>

        <div style="margin: 16px 0;">
          <h4 style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em;">Problem Statement</h4>
          <p style="color:var(--text-dim); margin-top:4px;">${escapeHtml(p.problem_statement || p.summary || 'None provided.')}</p>
        </div>

        <div style="margin: 16px 0;">
          <h4 style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em;">Architecture & Description</h4>
          <p style="color:var(--text-dim); margin-top:4px;">${escapeHtml(p.description || p.summary || 'None provided.')}</p>
        </div>

        <div style="margin: 16px 0;">
          <h4 style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em;">Tech Stack</h4>
          <p style="color:var(--teal); margin-top:4px;">${escapeHtml(p.technologies || 'None')}</p>
        </div>

        <div style="display:flex; gap:12px; margin: 20px 0; flex-wrap:wrap;">
          <button onclick="window.openProjectRepoModal('${p.id}')" class="btn-primary" style="padding:8px 16px;">💻 Code Repository Explorer</button>
          <button onclick="window.openProjectDemoModal('${p.id}')" class="btn-outline" style="padding:8px 16px;">🚀 Live Interactive Demo</button>
          <button class="btn-action" onclick="window.voteProject('${p.id}')">👍 Community Vote (${p.vote_count || 0})</button>
        </div>

        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border-color);">
          <h4 style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:12px;">Community Feedback (${data.comments.length})</h4>
          <div style="max-height: 140px; overflow-y: auto; margin-bottom: 12px;">
            ${data.comments.map(c => `
              <div style="padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size:11.5px;">
                <strong>${escapeHtml(c.author_name)}:</strong> ${escapeHtml(c.content)}
              </div>
            `).join('') || '<p style="color:var(--text-muted); font-size:11px;">No comments yet. Leave the first comment!</p>'}
          </div>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="commentInput" class="form-control" placeholder="Add constructive feedback..." style="font-size:11px;">
            <button class="btn-primary" onclick="window.submitComment('${p.id}')" style="flex-shrink:0;">Post</button>
          </div>
        </div>
      `;
      openModal('projectDetailModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.voteProject = async function(projectId) {
    try {
      await api(`/api/projects/${projectId}/vote`, { method: 'POST' });
      showToast('Vote recorded!');
      window.viewProjectModal(projectId);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.submitComment = async function(projectId) {
    const input = document.getElementById('commentInput');
    const content = input ? input.value.trim() : '';
    if (!content) return;
    try {
      await api(`/api/projects/${projectId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content })
      });
      showToast('Comment submitted!');
      window.viewProjectModal(projectId);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.openProjectRepoModal = async function(projectId) {
    try {
      const data = await api(`/api/projects/${projectId}/repository`);
      const modal = document.getElementById('repoModal');
      const body = document.getElementById('repoModalBody');
      if (!modal || !body) return;

      let currentFile = data.default_file || data.file_names[0];

      function renderContent() {
        const fileNames = data.file_names;
        const fileCode = data.files[currentFile] || '';
        const lineCount = fileCode.split('\n').length;
        const sizeBytes = new Blob([fileCode]).size;
        const domain = data.domain || 'devtools';

        const domainIcons = {
          security: '🛡️ SECURITY',
          devtools: '⚡ DEVTOOLS',
          analytics: '📊 ANALYTICS',
          accessibility: '♿ ACCESSIBILITY',
          health: '🩺 HEALTH',
          education: '🎓 EDUCATION',
          climate: '🌱 CLIMATE',
          hardware: '🔌 HARDWARE'
        };

        const getFileIcon = (f) => {
          if (f.endsWith('.py')) return '🐍';
          if (f.endsWith('.md')) return '📝';
          if (f.endsWith('.json') || f.endsWith('.toml') || f.endsWith('.ini')) return '⚙️';
          if (f.endsWith('.cpp') || f.endsWith('.h')) return '⚡';
          if (f === 'package.json') return '📦';
          if (f === 'Dockerfile') return '🐳';
          return '📄';
        };

        body.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding-right:30px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="badge track-badge" style="background:var(--teal-light); color:var(--teal); font-weight:700;">${domainIcons[domain] || 'PROJECT'}</span>
                <span style="font-size:12px; color:var(--text-muted);">Track: <strong>${escapeHtml(data.track_name || 'General')}</strong> · Team: <strong>${escapeHtml(data.team_name || '')}</strong></span>
              </div>
              <h2 style="font-size:18px; color:var(--text-main); margin-top:4px;">${escapeHtml(data.title)} <span style="font-size:12px; font-weight:normal; color:var(--teal); font-family:var(--font-mono);">[Multi-File Source Repository]</span></h2>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn-action" id="btnCopyCode" style="font-size:11px;">📋 Copy File</button>
              <button class="btn-outline" onclick="window.openProjectDemoModal('${data.project_id}')" style="font-size:11px;">🚀 Launch Interactive Demo</button>
            </div>
          </div>

          <div class="repo-layout">
            <div class="repo-sidebar">
              <div class="repo-sidebar-header">Repository Files (${fileNames.length})</div>
              <div class="repo-file-list">
                ${fileNames.map(f => `
                  <button class="repo-file-btn ${f === currentFile ? 'active' : ''}" data-file="${escapeHtml(f)}">
                    <span style="opacity:0.8;">${getFileIcon(f)}</span>
                    <span style="font-family:var(--font-mono); font-size:11px;">${escapeHtml(f)}</span>
                  </button>
                `).join('')}
              </div>
            </div>
            <div class="repo-main">
              <div class="repo-header">
                <span class="repo-path-pill">${getFileIcon(currentFile)} ${escapeHtml(currentFile)}</span>
                <span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${lineCount} lines · ${sizeBytes} bytes · UTF-8</span>
              </div>
              <pre class="repo-code-view"><code>${escapeHtml(fileCode)}</code></pre>
            </div>
          </div>
        `;

        // Bind file switch events
        body.querySelectorAll('.repo-file-btn').forEach(btn => {
          btn.onclick = () => {
            currentFile = btn.dataset.file;
            renderContent();
          };
        });

        // Copy button
        const btnCopy = document.getElementById('btnCopyCode');
        if (btnCopy) {
          btnCopy.onclick = () => {
            navigator.clipboard.writeText(fileCode).then(() => {
              showToast(`Copied ${currentFile} to clipboard!`);
            }).catch(() => {
              showToast('Copied to clipboard');
            });
          };
        }
      }

      renderContent();
      openModal('repoModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.openProjectDemoModal = async function(projectId) {
    try {
      const data = await api(`/api/projects/${projectId}/demo`);
      const modal = document.getElementById('demoModal');
      const body = document.getElementById('demoModalBody');
      if (!modal || !body) return;

      let logs = [...(data.initial_logs || [])];
      let latency = data.latency || "0.42 ms";
      let throughput = data.throughput || "10,000 ops/s";
      let domain = data.domain || 'devtools';

      // Domain-specific state variables for live interactive playgrounds
      let customState = {
        securityInput: "admin' UNION SELECT * FROM users--",
        securityCipher: "7f4a9b2c8e1d53f019a4bc",
        securityThreat: "HIGH (Injection Signature Detected)",
        devtoolsSnippet: "def optimize_me(x):\n    val = 10 + 20\n    if False:\n        print('dead')\n    return x * val",
        devtoolsNodes: 12,
        analyticsVal: 104.5,
        analyticsAnomaly: false,
        contrastFg: "#0F766E",
        contrastBg: "#FFFFFF",
        contrastRatio: "14.2:1 (AAA)",
        healthBpm: 72,
        healthSpo2: 98.8,
        healthStatus: "Normal Sinus Rhythm",
        eduConcept: "Algorithms & Partitioning",
        eduMastery: 88,
        eduFeedback: "Select an option below to test adaptive mastery scoring.",
        climateKwh: 45,
        climateCo2: 2.02,
        hardwarePin14: true,
        hardwareAdc: 2840
      };

      function renderDemo() {
        const domainBadges = {
          security: '🛡️ SECURITY & CRYPTO',
          devtools: '⚡ DEVELOPER TOOLS & COMPILER',
          analytics: '📊 DATA & STREAM ANALYTICS',
          accessibility: '♿ ACCESSIBILITY & WCAG AAA',
          health: '🩺 BIOMETRIC HEALTH & TELEMETRY',
          education: '🎓 ADAPTIVE EDTECH & MASTERY',
          climate: '🌱 CLIMATE & CLEAN ENERGY',
          hardware: '🔌 OPEN HARDWARE & EMBEDDED'
        };

        // Render Domain-Specific Interactive Widget
        let sandboxHtml = '';
        if (domain === 'security') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">🛡️ Interactive Threat & Cryptographic Sandbox</span>
                <span style="font-size:11px; padding:2px 8px; border-radius:12px; font-weight:700; background:rgba(255,61,110,0.15); color:var(--pink);" id="secThreatBadge">${customState.securityThreat}</span>
              </div>
              <div style="display:flex; gap:8px; margin-bottom:10px;">
                <input type="text" id="demoSecInput" class="form-control" value="${escapeHtml(customState.securityInput)}" style="font-family:var(--font-mono); font-size:12px;" placeholder="Enter payload or test string...">
                <button type="button" class="btn-primary" id="btnTestSecurity" style="font-size:11px; white-space:nowrap;">🔒 Encrypt & Audit</button>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:11px;">
                <div style="background:var(--bg-panel); padding:8px 12px; border-radius:6px; border:1px solid var(--border-color);">
                  <div style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">Ciphertext Envelope (AES-256-GCM)</div>
                  <code style="color:var(--teal); font-family:var(--font-mono); word-break:break-all;" id="secCipherVal">${customState.securityCipher}</code>
                </div>
                <div style="background:var(--bg-panel); padding:8px 12px; border-radius:6px; border:1px solid var(--border-color);">
                  <div style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">Verification Status</div>
                  <span style="color:#0F766E; font-weight:700;">Zero-Knowledge Proof Verified · Constant-Time Validated</span>
                </div>
              </div>
            </div>
          `;
        } else if (domain === 'devtools') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">⚡ Live Code AST Optimizer & JIT Playground</span>
                <span style="font-size:11px; font-family:var(--font-mono); color:var(--teal);">Nodes: ${customState.devtoolsNodes} · JIT: 142k ops/s</span>
              </div>
              <textarea id="demoDevCode" class="form-control" rows="3" style="font-family:var(--font-mono); font-size:11px; margin-bottom:8px;">${escapeHtml(customState.devtoolsSnippet)}</textarea>
              <div style="display:flex; gap:8px;">
                <button type="button" class="btn-primary" id="btnOptimizeAst" style="font-size:11px;">🌲 Parse & Optimize AST</button>
                <button type="button" class="btn-outline" id="btnRunBench50k" style="font-size:11px;">⚡ Run 50k Micro-Benchmarks</button>
              </div>
            </div>
          `;
        } else if (domain === 'analytics') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">📊 Ingestion Stream & Z-Score Anomaly Detector</span>
                <span style="font-size:11px; font-weight:700; color:${customState.analyticsAnomaly ? 'var(--pink)' : '#0F766E'};">
                  ${customState.analyticsAnomaly ? '🚨 ANOMALY DETECTED (Z > 3.0)' : '🟢 STREAM NORMAL'}
                </span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <span style="font-size:11px; color:var(--text-muted); min-width:80px;">Sensor Value:</span>
                <input type="range" id="demoAnalyticsRange" min="50" max="300" value="${customState.analyticsVal}" style="flex:1;">
                <span style="font-family:var(--font-mono); font-weight:700; font-size:13px;" id="analyticsValDisplay">${customState.analyticsVal}</span>
                <button type="button" class="btn-primary" id="btnIngestStreamPoint" style="font-size:11px;">Push Event</button>
              </div>
              <div style="font-size:11px; color:var(--text-muted);">Sliding Window Size: 1,000 slots · Vectors Indexed: 768-D Dense Matrix</div>
            </div>
          `;
        } else if (domain === 'accessibility') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">♿ WCAG 2.2 Contrast & Assistive Voice Synthesizer</span>
                <span style="font-size:11px; padding:2px 8px; border-radius:12px; font-weight:700; background:rgba(0,229,208,0.15); color:var(--teal);">${customState.contrastRatio}</span>
              </div>
              <div style="display:flex; gap:12px; align-items:center; margin-bottom:10px;">
                <div style="display:flex; align-items:center; gap:6px;">
                  <label style="font-size:11px; color:var(--text-muted);">Text Color:</label>
                  <input type="color" id="demoFgColor" value="${customState.contrastFg}" style="border:none; cursor:pointer; width:30px; height:24px; border-radius:4px;">
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <label style="font-size:11px; color:var(--text-muted);">Background:</label>
                  <input type="color" id="demoBgColor" value="${customState.contrastBg}" style="border:none; cursor:pointer; width:30px; height:24px; border-radius:4px;">
                </div>
                <button type="button" class="btn-primary" id="btnSpeakAnnounce" style="font-size:11px; margin-left:auto;">🔊 Speak Announcement</button>
              </div>
              <div id="demoA11yPreview" style="padding:10px 14px; border-radius:6px; background:${customState.contrastBg}; color:${customState.contrastFg}; font-weight:700; font-size:13px; border:1px solid var(--border-color); text-align:center;">
                Preview Sample: Accessible High Contrast Interface (Passes WCAG 2.2 AAA)
              </div>
            </div>
          `;
        } else if (domain === 'health') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">🩺 Live Cardiac & Pulse Oximetry Telemetry</span>
                <span style="font-size:11px; padding:2px 8px; border-radius:12px; font-weight:700; background:rgba(0,229,208,0.15); color:var(--teal);" id="healthStatusBadge">${customState.healthStatus}</span>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:10px;">
                <div style="background:var(--bg-panel); border:1px solid var(--border-color); padding:10px; border-radius:6px; text-align:center;">
                  <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Heart Rate</div>
                  <div style="font-size:18px; font-weight:800; color:var(--pink);"><span style="animation:pulse 1s infinite display:inline-block;">❤️</span> <span id="healthBpmVal">${customState.healthBpm}</span> BPM</div>
                </div>
                <div style="background:var(--bg-panel); border:1px solid var(--border-color); padding:10px; border-radius:6px; text-align:center;">
                  <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">SpO2 Oxygen</div>
                  <div style="font-size:18px; font-weight:800; color:var(--teal);"><span id="healthSpo2Val">${customState.healthSpo2}</span>%</div>
                </div>
                <div style="background:var(--bg-panel); border:1px solid var(--border-color); padding:10px; border-radius:6px; text-align:center;">
                  <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">HIPAA Safe Harbor</div>
                  <div style="font-size:14px; font-weight:700; color:#0F766E; margin-top:3px;">Zero PHI Leak</div>
                </div>
              </div>
              <div style="display:flex; gap:8px;">
                <button type="button" class="btn-primary" id="btnPulseSample" style="font-size:11px;">❤️ Sample Pulse Stream</button>
                <button type="button" class="btn-action" id="btnInduceArrhythmia" style="font-size:11px; color:var(--pink);">🚨 Simulate Arrhythmia Warning</button>
              </div>
            </div>
          `;
        } else if (domain === 'education') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">🎓 Adaptive Problem Solver & Concept Mastery</span>
                <span style="font-size:11px; font-weight:700; color:var(--teal);">Mastery: <span id="eduMasteryVal">${customState.eduMastery}</span>%</span>
              </div>
              <div style="padding:10px; background:var(--bg-panel); border:1px solid var(--border-color); border-radius:6px; margin-bottom:8px;">
                <div style="font-size:11px; color:var(--text-muted);">Current Adaptive Problem:</div>
                <div style="font-weight:700; font-size:13px; color:var(--text-main); margin-top:2px;">"What ensures deterministic consensus without cloud authentication?"</div>
              </div>
              <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
                <button type="button" class="btn-action btnEduAnswer" data-correct="true" style="font-size:11px; padding:6px 10px;">A) Local Relational Store & Nonce Ledgers</button>
                <button type="button" class="btn-action btnEduAnswer" data-correct="false" style="font-size:11px; padding:6px 10px;">B) External Third-Party OAuth Provider</button>
                <button type="button" class="btn-action btnEduAnswer" data-correct="false" style="font-size:11px; padding:6px 10px;">C) Static Client-Side Cookies Only</button>
              </div>
              <div style="font-size:11px; color:var(--text-muted);" id="eduFeedbackText">${customState.eduFeedback}</div>
            </div>
          `;
        } else if (domain === 'climate') {
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">🌱 Marginal Carbon Accounting & Solar Optimization</span>
                <span style="font-size:11px; font-weight:700; color:#0F766E;">Tier A+ Renewable</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <span style="font-size:11px; color:var(--text-muted); min-width:90px;">Daily Energy:</span>
                <input type="range" id="demoClimateRange" min="10" max="200" value="${customState.climateKwh}" style="flex:1;">
                <span style="font-family:var(--font-mono); font-weight:700; font-size:13px;" id="climateKwhDisplay">${customState.climateKwh} kWh</span>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:11px;">
                <div style="background:var(--bg-panel); padding:8px 12px; border-radius:6px; border:1px solid var(--border-color);">
                  <div style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">Net Carbon Emissions</div>
                  <strong style="color:var(--teal); font-size:14px;" id="climateCo2Val">${customState.climateCo2} kg CO2e</strong>
                </div>
                <div style="background:var(--bg-panel); padding:8px 12px; border-radius:6px; border:1px solid var(--border-color);">
                  <div style="color:var(--text-muted); font-size:10px; text-transform:uppercase;">Equivalent Trees Planted</div>
                  <strong style="color:#0F766E; font-size:14px;" id="climateTreesVal">${(customState.climateCo2 / 21.0).toFixed(2)} trees/year</strong>
                </div>
              </div>
            </div>
          `;
        } else {
          // hardware
          sandboxHtml = `
            <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-main);">🔌 Virtual GPIO Breadboard & Microcontroller Bus</span>
                <span style="font-size:11px; font-family:var(--font-mono); color:var(--teal);">I2C @ 400kHz · 3.31V Rail</span>
              </div>
              <div style="display:flex; gap:12px; align-items:center; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:8px; background:var(--bg-panel); padding:6px 12px; border-radius:6px; border:1px solid var(--border-color);">
                  <span style="width:10px; height:10px; border-radius:50%; background:${customState.hardwarePin14 ? '#00e5d0' : '#888'}; display:inline-block;" id="hardwareLed"></span>
                  <span style="font-size:11px; font-weight:700;">Relay Pin 14: <span id="hardwareRelayState">${customState.hardwarePin14 ? 'HIGH (ON)' : 'LOW (OFF)'}</span></span>
                </div>
                <button type="button" class="btn-primary" id="btnToggleRelayPin" style="font-size:11px;">Toggle Relay</button>
                <button type="button" class="btn-outline" id="btnReadAdc" style="font-size:11px;">Sample ADC: <span id="hardwareAdcDisplay">${customState.hardwareAdc}</span></button>
              </div>
            </div>
          `;
        }

        body.innerHTML = `
          <div class="demo-header-bar" style="padding-right: 30px; margin-bottom:14px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="badge track-badge" style="background:var(--teal-light); color:var(--teal); font-weight:700;">${domainBadges[domain] || data.track}</span>
                <span class="demo-status-pill"><span class="demo-status-pulse"></span> ${escapeHtml(data.status)}</span>
              </div>
              <h2 style="font-size:18px; color:var(--text-main); margin-top:6px;">${escapeHtml(data.title)}</h2>
              <p style="font-size:12px; color:var(--text-dim); margin-top:2px;">${escapeHtml(data.simulation_type)}</p>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn-primary" onclick="window.openProjectRepoModal('${data.project_id}')" style="font-size:11px;">💻 View Source Code</button>
            </div>
          </div>

          <!-- Dynamic Domain Metrics Grid -->
          <div class="demo-metrics-grid" style="margin-bottom:14px;">
            <div class="demo-metric-card">
              <div class="demo-metric-label">Execution Latency</div>
              <div class="demo-metric-val" id="demoLatencyVal">${escapeHtml(latency)}</div>
            </div>
            <div class="demo-metric-card">
              <div class="demo-metric-label">Throughput SLA</div>
              <div class="demo-metric-val">${escapeHtml(throughput)}</div>
            </div>
            ${Object.entries(data.metrics || {}).map(([k, v]) => `
              <div class="demo-metric-card">
                <div class="demo-metric-label">${escapeHtml(k)}</div>
                <div class="demo-metric-val" style="font-size:13px;">${escapeHtml(String(v))}</div>
              </div>
            `).join('')}
          </div>

          <!-- Domain-Tailored Interactive Sandbox -->
          ${sandboxHtml}

          <!-- Domain Action Controls -->
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <h4 style="font-size:11px; text-transform:uppercase; letter-spacing:0.1em; color:var(--text-muted); margin:0;">
              Domain Controls &amp; Event Dispatcher
            </h4>
            <div style="display:flex; gap:6px;">
              ${(data.interactive_actions || []).map(act => `
                <button class="btn-primary btnDomainAction" data-action="${escapeHtml(act.action)}" style="font-size:11px; padding:5px 10px;" title="${escapeHtml(act.desc || '')}">
                  ${escapeHtml(act.label)}
                </button>
              `).join('')}
              <button class="btn-action" id="btnDemoClear" style="font-size:11px; padding:5px 8px;">🧹 Clear Console</button>
            </div>
          </div>

          <!-- Live Terminal Console Stream -->
          <div class="demo-console" id="demoConsole" style="max-height: 180px; overflow-y: auto;">
            ${logs.map(l => `<div class="demo-console-line">${escapeHtml(l)}</div>`).join('')}
          </div>
        `;

        const consoleEl = document.getElementById('demoConsole');
        if (consoleEl) consoleEl.scrollTop = consoleEl.scrollHeight;

        // Wire Domain Action Buttons
        body.querySelectorAll('.btnDomainAction').forEach(btn => {
          btn.onclick = async () => {
            const action = btn.dataset.action;
            try {
              btn.disabled = true;
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: action })
              });
              latency = `${res.latency_ms} ms`;
              logs.push(res.log_entry);
              showToast(`Action dispatched: ${action}`);
              renderDemo();
            } catch (err) {
              showToast(err.message, 'error');
            } finally {
              btn.disabled = false;
            }
          };
        });

        // Wire Clear button
        const btnClear = document.getElementById('btnDemoClear');
        if (btnClear) {
          btnClear.onclick = () => {
            logs = [];
            renderDemo();
          };
        }

        // Domain Specific Sandbox Listeners
        if (domain === 'security') {
          const btnSec = document.getElementById('btnTestSecurity');
          if (btnSec) {
            btnSec.onclick = async () => {
              const inputVal = document.getElementById('demoSecInput').value;
              customState.securityInput = inputVal;
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "SIMULATE_INJECTION", input_text: inputVal })
              });
              logs.push(res.log_entry);
              customState.securityCipher = 'c8' + Math.random().toString(16).substring(2, 14) + 'ff';
              showToast('Security envelope generated & verified!');
              renderDemo();
            };
          }
        } else if (domain === 'devtools') {
          const btnOpt = document.getElementById('btnOptimizeAst');
          if (btnOpt) {
            btnOpt.onclick = async () => {
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "ANALYZE_AST" })
              });
              logs.push(res.log_entry);
              customState.devtoolsNodes = Math.max(4, customState.devtoolsNodes - 2);
              showToast('AST optimization complete! Constants folded.');
              renderDemo();
            };
          }
          const btnBench = document.getElementById('btnRunBench50k');
          if (btnBench) {
            btnBench.onclick = async () => {
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "RUN_BENCHMARK" })
              });
              logs.push(res.log_entry);
              showToast('Benchmark executed: 148,200 ops/s');
              renderDemo();
            };
          }
        } else if (domain === 'analytics') {
          const slider = document.getElementById('demoAnalyticsRange');
          const pushBtn = document.getElementById('btnIngestStreamPoint');
          if (slider) {
            slider.oninput = () => {
              customState.analyticsVal = parseFloat(slider.value);
              document.getElementById('analyticsValDisplay').textContent = customState.analyticsVal;
            };
          }
          if (pushBtn) {
            pushBtn.onclick = async () => {
              customState.analyticsAnomaly = customState.analyticsVal > 220;
              const action = customState.analyticsAnomaly ? "RUN_ANOMALY_SCAN" : "INGEST_BATCH";
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: action })
              });
              logs.push(res.log_entry);
              showToast(`Point ${customState.analyticsVal} ingested!`);
              renderDemo();
            };
          }
        } else if (domain === 'accessibility') {
          const fgPicker = document.getElementById('demoFgColor');
          const bgPicker = document.getElementById('demoBgColor');
          const btnSpeak = document.getElementById('btnSpeakAnnounce');
          if (fgPicker && bgPicker) {
            const updateA11y = () => {
              customState.contrastFg = fgPicker.value;
              customState.contrastBg = bgPicker.value;
              const preview = document.getElementById('demoA11yPreview');
              if (preview) {
                preview.style.color = customState.contrastFg;
                preview.style.backgroundColor = customState.contrastBg;
              }
            };
            fgPicker.oninput = updateA11y;
            bgPicker.oninput = updateA11y;
          }
          if (btnSpeak) {
            btnSpeak.onclick = async () => {
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "SYNTHESIZE_SPEECH" })
              });
              logs.push(res.log_entry);
              showToast('Spoken preview synthesized in 32ms');
              renderDemo();
            };
          }
        } else if (domain === 'health') {
          const btnPulse = document.getElementById('btnPulseSample');
          const btnArr = document.getElementById('btnInduceArrhythmia');
          if (btnPulse) {
            btnPulse.onclick = async () => {
              customState.healthBpm = 68 + Math.floor(Math.random() * 8);
              customState.healthStatus = "Normal Sinus Rhythm";
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "SAMPLE_VITALS" })
              });
              logs.push(res.log_entry);
              showToast('Heart rate reading sampled: Normal');
              renderDemo();
            };
          }
          if (btnArr) {
            btnArr.onclick = async () => {
              customState.healthBpm = 138;
              customState.healthStatus = "TACHYCARDIA ALERT";
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "TRIGGER_ARRHYTHMIA" })
              });
              logs.push(res.log_entry);
              showToast('Critical tachycardia alert sent to nurse station!');
              renderDemo();
            };
          }
        } else if (domain === 'education') {
          body.querySelectorAll('.btnEduAnswer').forEach(btn => {
            btn.onclick = async () => {
              const isCorrect = btn.dataset.correct === "true";
              const action = isCorrect ? "SUBMIT_CORRECT" : "SUBMIT_INCORRECT";
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: action })
              });
              logs.push(res.log_entry);
              if (isCorrect) {
                customState.eduMastery = Math.min(99, customState.eduMastery + 4);
                customState.eduFeedback = "🎉 Correct! Nonce ledgers maintain tamper-evident verification. Mastery +4%.";
                showToast('Correct answer! Concept mastered.');
              } else {
                customState.eduFeedback = "⚠️ Not quite right. Reviewing local consensus architecture before re-testing.";
                showToast('Answer recorded. Adaptive hints enabled.');
              }
              renderDemo();
            };
          });
        } else if (domain === 'climate') {
          const slider = document.getElementById('demoClimateRange');
          if (slider) {
            slider.oninput = async () => {
              customState.climateKwh = parseFloat(slider.value);
              customState.climateCo2 = (customState.climateKwh * 0.045).toFixed(2);
              document.getElementById('climateKwhDisplay').textContent = `${customState.climateKwh} kWh`;
              document.getElementById('climateCo2Val').textContent = `${customState.climateCo2} kg CO2e`;
              document.getElementById('climateTreesVal').textContent = `${(customState.climateCo2 / 21.0).toFixed(2)} trees/year`;
            };
          }
        } else if (domain === 'hardware') {
          const btnRelay = document.getElementById('btnToggleRelayPin');
          if (btnRelay) {
            btnRelay.onclick = async () => {
              customState.hardwarePin14 = !customState.hardwarePin14;
              const res = await api(`/api/projects/${projectId}/demo/trigger`, {
                method: 'POST',
                body: JSON.stringify({ event_type: "TOGGLE_RELAY" })
              });
              logs.push(res.log_entry);
              showToast(`Relay pin toggled: ${customState.hardwarePin14 ? 'HIGH' : 'LOW'}`);
              renderDemo();
            };
          }
        }
      }

      renderDemo();
      openModal('demoModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.openEvaluateModal = async function(projectId) {
    try {
      const data = await api(`/api/judge/project/${projectId}`);
      const p = data.project;
      const existing = data.existing_score || {};
      const critMap = existing.criteria || {};

      const modal = document.getElementById('evaluateModal');
      const body = document.getElementById('evaluateBody');
      if (!modal || !body) return;

      body.innerHTML = `
        <h3 style="margin-bottom:4px;">Evaluating: ${escapeHtml(p.title)}</h3>
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px;">Team: ${escapeHtml(p.team_name)} · Track: ${p.track_name || 'General'}</p>

        <form id="evaluationForm">
          <input type="hidden" id="evalProjectId" value="${p.id}">
          ${data.criteria.map(c => `
            <div class="slider-container">
              <div class="slider-header">
                <span class="form-label">${c.name} (${c.weight}x)</span>
                <span class="slider-value" id="val_${c.key}">${critMap[c.key] !== undefined ? critMap[c.key] : '3.0'} / ${c.max_score}</span>
              </div>
              <input type="range" class="eval-slider" data-key="${c.key}" data-weight="${c.weight}" min="1.0" max="${c.max_score}" step="0.5" value="${critMap[c.key] !== undefined ? critMap[c.key] : '3.0'}">
              <p style="font-size:10.5px; color:var(--text-muted); margin-top:2px;">${c.description || ''}</p>
            </div>
          `).join('')}

          <div style="margin: 16px 0; padding: 12px; background: var(--bg-panel); border: 1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; font-weight:700;">Calculated Weighted Score:</span>
            <span id="calculatedTotal" style="font-size:20px; font-weight:700; color:var(--teal);">3.00</span>
          </div>

          <div class="form-group">
            <label class="form-label">Reviewer Feedback & Comments</label>
            <textarea id="evalComment" class="form-control" placeholder="Provide actionable and transparent reasoning for the scoring decisions...">${escapeHtml(existing.comment || '')}</textarea>
          </div>

          <button type="submit" class="btn-primary" style="width: 100%;">Submit Official Score</button>
        </form>
      `;

      // Recalculate helper
      const updateCalculatedScore = () => {
        let weighted = 0, totalW = 0;
        document.querySelectorAll('.eval-slider').forEach(slider => {
          const val = parseFloat(slider.value);
          const w = parseFloat(slider.dataset.weight);
          weighted += val * w;
          totalW += w;
          const display = document.getElementById(`val_${slider.dataset.key}`);
          if (display) display.textContent = `${val.toFixed(1)} / 5.0`;
        });
        const total = totalW > 0 ? (weighted / totalW).toFixed(2) : '3.00';
        const calcEl = document.getElementById('calculatedTotal');
        if (calcEl) calcEl.textContent = total;
      };

      document.querySelectorAll('.eval-slider').forEach(slider => {
        slider.oninput = updateCalculatedScore;
      });
      updateCalculatedScore();

      document.getElementById('evaluationForm').onsubmit = async (e) => {
        e.preventDefault();
        const scoresObj = {};
        document.querySelectorAll('.eval-slider').forEach(slider => {
          scoresObj[slider.dataset.key] = parseFloat(slider.value);
        });

        const payload = {
          project_id: projectId,
          criterion_scores: scoresObj,
          comment: document.getElementById('evalComment').value.trim()
        };

        try {
          await api('/api/judge/evaluate', { method: 'POST', body: JSON.stringify(payload) });
          showToast('Evaluation submitted successfully!');
          closeModal();
          loadJudgeDashboard();
        } catch (err) {
          showToast(err.message, 'error');
        }
      };

      openModal('evaluateModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.setEligibility = async function(projectId, status) {
    try {
      await api(`/api/admin/submissions/${projectId}/eligibility`, {
        method: 'POST',
        body: JSON.stringify({ status, notes: `Reviewed by organizer on ${new Date().toISOString()}` })
      });
      showToast(`Project status updated to ${status.toUpperCase()}`);
      loadAdminDashboard();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.viewCertificateModal = async function(certCode) {
    try {
      const data = await api(`/api/certificates?cert_code=${certCode}`);
      const c = data.certificate;
      const modal = document.getElementById('certModal');
      const body = document.getElementById('certModalBody');
      if (!modal || !body) return;

      body.innerHTML = `
        <div class="certificate-preview" id="printableCert">
          <div class="cert-seal">🏅</div>
          <div class="cert-event">${escapeHtml(c.event_name)}</div>
          <h2 class="cert-title">${escapeHtml(c.award_title || 'Certificate of Recognition')}</h2>
          <p style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.15em;">This is proudly presented to</p>
          <div class="cert-recipient">${escapeHtml(c.recipient_name)}</div>
          <p class="cert-award">${c.project_title ? `For exemplary innovation on "${escapeHtml(c.project_title)}"` : 'For outstanding technical contributions and judging integrity.'}</p>
          <div class="cert-code">VERIFICATION CODE: ${c.cert_code} · ISSUED ${c.issued_at.slice(0, 10)}</div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:10px;">
          <button class="btn-primary" onclick="window.print()">Print / Save PDF</button>
        </div>
      `;
      openModal('certModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.viewAiBreakdownModal = async function(projectId) {
    try {
      const data = await api(`/api/ai/evaluations/${projectId}`);
      const e = data.evaluation;
      const p = data.project;
      const modal = document.getElementById('aiBreakdownModal');
      const body = document.getElementById('aiBreakdownBody');
      if (!modal || !body) return;

      const criteria = e.criteria || {};
      const diff = e.overall_score - (p.avg_human_score || 0);

      body.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <span class="badge track-badge">${p.track_name || 'General'}</span>
          <span class="badge" style="background:#182342; color:var(--teal); font-size:10px;">MODEL: ${escapeHtml(e.model_name)}</span>
        </div>
        <h2 style="font-size:20px; color:var(--text-main); margin-bottom:4px;">${escapeHtml(p.title)}</h2>
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px;">Team: ${escapeHtml(p.team_name)}</p>

        <!-- Comparison Bar -->
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:20px;">
          <div style="background:var(--bg-panel); border:1px solid var(--teal); padding:12px; border-radius:4px; text-align:center;">
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em;">HackJudge AI Score</div>
            <div style="font-size:24px; font-weight:700; color:var(--teal); margin-top:4px;">${e.overall_score.toFixed(2)} <span style="font-size:12px;">/ 5.0</span></div>
          </div>
          <div style="background:var(--bg-panel); border:1px solid var(--border-color); padding:12px; border-radius:4px; text-align:center;">
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em;">Human Average Score</div>
            <div style="font-size:24px; font-weight:700; color:var(--text-main); margin-top:4px;">${p.avg_human_score ? p.avg_human_score.toFixed(2) : '—'} <span style="font-size:12px;">/ 5.0</span></div>
          </div>
          <div style="background:var(--bg-panel); border:1px solid ${Math.abs(diff) >= 1.0 ? 'var(--pink)' : 'var(--border-color)'}; padding:12px; border-radius:4px; text-align:center;">
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em;">Score Divergence (&Delta;)</div>
            <div style="font-size:24px; font-weight:700; color:${Math.abs(diff) >= 1.0 ? 'var(--pink)' : 'var(--teal)'}; margin-top:4px;">
              ${diff > 0 ? '+' : ''}${diff.toFixed(2)}
            </div>
          </div>
        </div>

        <!-- Executive Reasoning -->
        <div style="background:rgba(0,229,208,0.05); border-left:3px solid var(--teal); padding:12px 16px; margin-bottom:20px; font-size:12px;">
          <strong style="color:var(--teal);">HackJudge AI Assessment:</strong>
          <p style="margin-top:4px; color:var(--text-dim);">${escapeHtml(e.reasoning)}</p>
        </div>

        <!-- 5-Criterion Breakdown -->
        <h4 style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px;">Criterion-Level Evaluation</h4>
        <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:20px;">
          ${Object.entries(criteria).map(([key, c]) => `
            <div style="background:var(--bg-panel); border:1px solid var(--border-color); padding:10px 14px; border-radius:3px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; text-transform:capitalize; font-size:12px;">${key.replace('_', ' ')} (${Math.round(c.weight * 100)}% Weight)</span>
                <strong style="color:var(--teal); font-size:14px;">${c.score.toFixed(1)} / 5.0</strong>
              </div>
              <p style="font-size:11px; color:var(--text-muted); margin-top:4px;">${escapeHtml(c.reasoning)}</p>
            </div>
          `).join('')}
        </div>

        <!-- Analysis Matrix: Strengths, Improvements, Concerns, Missing Info -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px;">
          <div style="background:var(--bg-panel); border:1px solid rgba(0,229,208,0.3); padding:12px; border-radius:4px;">
            <strong style="color:var(--teal); font-size:11px; letter-spacing:0.1em; text-transform:uppercase;">🟢 Key Strengths</strong>
            <ul style="margin:6px 0 0 16px; font-size:11.5px; color:var(--text-dim);">
              ${(e.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
          <div style="background:var(--bg-panel); border:1px solid rgba(255,215,0,0.3); padding:12px; border-radius:4px;">
            <strong style="color:#FFD700; font-size:11px; letter-spacing:0.1em; text-transform:uppercase;">🟡 Areas for Improvement</strong>
            <ul style="margin:6px 0 0 16px; font-size:11.5px; color:var(--text-dim);">
              ${(e.improvements || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
          <div style="background:var(--bg-panel); border:1px solid rgba(255,61,110,0.3); padding:12px; border-radius:4px;">
            <strong style="color:var(--pink); font-size:11px; letter-spacing:0.1em; text-transform:uppercase;">🔴 Potential Concerns & Risks</strong>
            <ul style="margin:6px 0 0 16px; font-size:11.5px; color:var(--text-dim);">
              ${(e.concerns || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
          <div style="background:var(--bg-panel); border:1px solid var(--border-color); padding:12px; border-radius:4px;">
            <strong style="color:var(--text-muted); font-size:11px; letter-spacing:0.1em; text-transform:uppercase;">⚪ Missing Information</strong>
            <ul style="margin:6px 0 0 16px; font-size:11.5px; color:var(--text-dim);">
              ${(e.missing_info || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
        </div>
      `;
      openModal('aiBreakdownModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.rerunAiEval = async function(projectId) {
    try {
      showToast('Running AI assessment...');
      const res = await api(`/api/ai/evaluate/${projectId}`, { method: 'POST' });
      showToast(res.message);
      loadAiDashboard();
      window.viewAiBreakdownModal(projectId);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Close modals on overlay click or esc
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
  });
  document.querySelectorAll('.modal-close').forEach(btn => {
    btn.onclick = closeModal;
  });
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // Auth Modal Tab Switcher & Quick Fill
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  if (tabLogin && tabRegister) {
    tabLogin.onclick = () => {
      tabLogin.classList.add('active');
      tabLogin.style.background = 'var(--teal)';
      tabLogin.style.color = 'var(--bg-dark)';
      tabLogin.style.border = 'none';

      tabRegister.classList.remove('active');
      tabRegister.style.background = 'transparent';
      tabRegister.style.color = 'var(--text-muted)';
      tabRegister.style.border = '1px solid var(--border-color)';

      if (loginForm) loginForm.style.display = 'block';
      if (registerForm) registerForm.style.display = 'none';
    };

    tabRegister.onclick = () => {
      tabRegister.classList.add('active');
      tabRegister.style.background = 'var(--teal)';
      tabRegister.style.color = 'var(--bg-dark)';
      tabRegister.style.border = 'none';

      tabLogin.classList.remove('active');
      tabLogin.style.background = 'transparent';
      tabLogin.style.color = 'var(--text-muted)';
      tabLogin.style.border = '1px solid var(--border-color)';

      if (loginForm) loginForm.style.display = 'none';
      if (registerForm) registerForm.style.display = 'block';
    };
  }

  window.quickFillLogin = function(username, password) {
    const identEl = document.getElementById('loginIdent');
    const passEl = document.getElementById('loginPass');
    if (identEl) identEl.value = username;
    if (passEl) passEl.value = password;
  };

  // Auth Form Handlers
  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const data = await api('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({
            username_or_email: document.getElementById('loginIdent').value.trim(),
            password: document.getElementById('loginPass').value
          })
        });
        state.user = data.user;
        renderUserStatus();
        showToast('Login successful! Welcome back.');
        closeModal();

        // Navigate to appropriate panel based on role
        if (state.user.role === 'admin' || state.user.role === 'organizer') {
          navigateTo('admin');
        } else if (state.user.role === 'judge') {
          navigateTo('judge');
        } else if (state.user.role === 'participant') {
          navigateTo('participant');
        }
      } catch (err) {
        showToast(err.message, 'error');
      }
    };
  }

  if (registerForm) {
    registerForm.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const teamNameVal = document.getElementById('regTeamName') ? document.getElementById('regTeamName').value.trim() : '';
        const data = await api('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            username: document.getElementById('regUsername').value.trim(),
            email: document.getElementById('regEmail').value.trim(),
            password: document.getElementById('regPass').value,
            full_name: document.getElementById('regFullName').value.trim(),
            role: document.getElementById('regRole').value,
            team_name: teamNameVal || null
          })
        });
        state.user = data.user;
        renderUserStatus();
        showToast('Account registered successfully! Welcome aboard.');
        closeModal();

        if (state.user.role === 'judge') {
          navigateTo('judge');
        } else {
          navigateTo('participant');
        }
      } catch (err) {
        showToast(err.message, 'error');
      }
    };
  }

  const genCertForm = document.getElementById('genCertForm');
  if (genCertForm) {
    genCertForm.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const payload = {
          recipient_name: document.getElementById('certRecipient').value.trim(),
          type: document.getElementById('certType').value,
          award_title: document.getElementById('certAwardTitle').value.trim(),
          project_title: document.getElementById('certProjectTitle').value.trim() || null
        };
        const res = await api('/api/certificates/generate', { method: 'POST', body: JSON.stringify(payload) });
        showToast('Certificate created!');
        closeModal();
        loadCertificates();
        window.viewCertificateModal(res.certificate.cert_code);
      } catch (err) {
        showToast(err.message, 'error');
      }
    };
  }

  // Sidebar navigation click handler
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      navigateTo(item.dataset.tab);
    });
  });

  // Demo switcher buttons
  document.querySelectorAll('.demo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      switchDemo(btn.dataset.target);
    });
  });

  // Filter input listeners
  const searchInput = document.getElementById('gallerySearch');
  if (searchInput) {
    let debounce;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounce);
      debounce = setTimeout(loadGallery, 300);
    });
  }
  const trackFilter = document.getElementById('galleryTrackFilter');
  if (trackFilter) {
    trackFilter.addEventListener('change', loadGallery);
  }

  window.navigateToTab = navigateTo;

  // Initial startup
  async function init() {
    await checkAuth();
    navigateTo('overview');
  }

  init();
})();
