// Travel Scout Multi-City Collaborative Client
let currentTripId = null;
let currentUser = null;
let currentTripData = null;
let leafletMap = null;
let mapMarkersGroup = null;
let mapRouteGroup = null;

// Explore & Discover State
let exploreSearchQuery = "";
let exploreCategory = "all";
let exploreCity = "all";
let exploreNeighborhood = "all";
let exploreSchedule = "all";
let exploreFreeOnly = false;
let exploreDebounceTimer = null;

// Global Sign In Modal Controls
window.openLogin = function() {
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.style.display = "flex";
    const nameInput = document.getElementById("customLoginName");
    if (nameInput) setTimeout(() => nameInput.focus(), 100);
  }
};

window.closeLogin = function() {
  const modal = document.getElementById("loginModal");
  if (modal) modal.style.display = "none";
};

document.addEventListener("DOMContentLoaded", async () => {
  // Check for Google OAuth callback parameters in URL
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("google_auth") === "success") {
    const uid = urlParams.get("user_id");
    if (uid) {
      localStorage.setItem("travel_scout_user_id", uid);
    }
    window.history.replaceState({}, document.title, window.location.pathname);
  } else if (urlParams.get("error")) {
    const errCode = urlParams.get("error");
    if (errCode === "google_oauth_not_configured") {
      setTimeout(() => {
        alert("🔑 Google OAuth 2.0 is enabled in the code!\n\nTo connect to your live Google accounts, please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your Render Environment Variables.\n\nIn the meantime, you can sign in using any team profile or enter your Gmail address!");
        if (window.openLogin) window.openLogin();
      }, 300);
    } else {
      alert("Google Sign-In note: " + decodeURIComponent(errCode));
    }
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // Register PWA Service Worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js")
      .then(reg => {
        console.log("Travel Scout Service Worker active:", reg.scope);
        reg.update().catch(() => {});
      })
      .catch(err => console.log("Service Worker registration skipped:", err));
  }

  initTabs();
  initModals();
  initAddItemModal();
  initExpenseTracker();
  initBookingModal();
  initCalendarExport();
  initExploreFilters();
  await loadCurrentUser();
  await loadInitialTrip();
  initScout();
});

// 1. Navigation Tabs
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.dataset.tab;
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      const section = document.getElementById(`tab-${target}`);
      if (section) section.classList.add("active");

      if (window.isBulkSelectMode) {
        exitBulkSelectMode();
      }

      if (target === "scout") {
        syncScoutCityWithItinerary();
      }

      if (target === "expenses") {
        loadTripExpenses();
      }

      if (target === "map") {
        setTimeout(() => {
          if (leafletMap) {
            leafletMap.invalidateSize();
            fitMapBounds();
          } else {
            initMap();
          }
        }, 150);
      }
    });
  });
}

// 2. Auth & User Switcher
async function loadCurrentUser() {
  try {
    const sessionToken = localStorage.getItem("travel_scout_session");
    const localUserId = localStorage.getItem("travel_scout_user_id");
    const headers = {};
    if (sessionToken) {
      headers["x-travel-scout-session"] = sessionToken;
    } else if (localUserId) {
      headers["x-travel-scout-user-id"] = localUserId;
    }

    const res = await fetch("/auth/me", { headers, credentials: "include" });
    const data = await res.json();
    currentUser = data.current_user;

    const avatarEl = document.getElementById("currentUserAvatar");
    const nameEl = document.getElementById("currentUserName");
    const roleEl = document.getElementById("currentUserRole");
    const emailEl = document.getElementById("currentUserEmail");
    const logoffBtn = document.getElementById("logoffBtn");
    const headerSignInBtn = document.getElementById("headerSignInBtn");
    const bannerSignInBtn = document.getElementById("bannerSignInBtn");
    const loggedOutBanner = document.getElementById("loggedOutBanner");

    if (currentUser) {
      if (avatarEl) {
        if (currentUser.avatar_url) {
          avatarEl.innerHTML = `<img src="${escapeHtml(currentUser.avatar_url)}" alt="${escapeHtml(currentUser.name)}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;" />`;
          avatarEl.style.background = "transparent";
        } else {
          avatarEl.style.background = currentUser.avatar_color || "#38bdf8";
          avatarEl.textContent = currentUser.name.slice(0, 2).toUpperCase();
        }
      }
      if (nameEl) nameEl.textContent = currentUser.name;
      if (roleEl) roleEl.textContent = "Active";
      if (emailEl) emailEl.textContent = currentUser.email;
      if (logoffBtn) {
        logoffBtn.style.display = "inline-flex";
        logoffBtn.title = `Log off from ${currentUser.email}`;
      }
      if (headerSignInBtn) headerSignInBtn.style.display = "none";
      if (loggedOutBanner) loggedOutBanner.style.display = "none";
    } else {
      if (avatarEl) {
        avatarEl.style.background = "#64748b";
        avatarEl.textContent = "?";
      }
      if (nameEl) nameEl.textContent = "Not Logged In";
      if (roleEl) roleEl.textContent = "Guest";
      if (emailEl) emailEl.textContent = "Please sign in";
      if (logoffBtn) logoffBtn.style.display = "none";
      if (headerSignInBtn) headerSignInBtn.style.display = "inline-flex";
      if (loggedOutBanner) loggedOutBanner.style.display = "flex";
    }

    // Logoff button handler
    if (logoffBtn) {
      logoffBtn.onclick = async () => {
        await logoff();
      };
    }

    // Sign in modal handlers
    const loginModal = document.getElementById("loginModal");
    const closeLoginModalBtn = document.getElementById("closeLoginModalBtn");

    function openLogin() {
      if (loginModal) loginModal.style.display = "flex";
    }
    function closeLogin() {
      if (loginModal) loginModal.style.display = "none";
    }
    window.openLogin = openLogin;
    window.closeLogin = closeLogin;

    if (headerSignInBtn) headerSignInBtn.onclick = openLogin;
    if (bannerSignInBtn) bannerSignInBtn.onclick = openLogin;
    if (closeLoginModalBtn) closeLoginModalBtn.onclick = closeLogin;

    // Dynamically populate and attach Quick Pick list
    const quickPickContainer = document.getElementById("loginQuickPickList");
    const availUsers = data.available_users || [];
    if (quickPickContainer) {
      if (availUsers.length > 0) {
        quickPickContainer.innerHTML = availUsers.map(u => `
          <button type="button" class="btn btn-secondary quick-login-btn" data-email="${escapeHtml(u.email)}" data-name="${escapeHtml(u.name)}" style="justify-content:flex-start; padding:0.6rem 0.9rem; width:100%; text-align:left; border-color:rgba(255,255,255,0.08);">
            <span class="user-avatar-badge" style="background:${u.avatar_url ? 'transparent' : (u.avatar_color || '#38bdf8')}; width:28px; height:28px; font-size:0.75rem; margin-right:0.75rem; flex-shrink:0;">
              ${u.avatar_url ? `<img src="${escapeHtml(u.avatar_url)}" alt="${escapeHtml(u.name)}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;" />` : escapeHtml(u.name.slice(0, 2).toUpperCase())}
            </span>
            <div style="display:flex; flex-direction:column; flex:1;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color:var(--text-main); font-size:0.86rem;">${escapeHtml(u.name)}</strong>
                <span style="font-size:0.7rem; color:#38bdf8; font-weight:600;">Sign In &rarr;</span>
              </div>
              <span style="font-size:0.75rem; color:#94a3b8; font-family:var(--font-mono, monospace);">✉️ ${escapeHtml(u.email)}</span>
            </div>
          </button>
        `).join("");

        quickPickContainer.querySelectorAll(".quick-login-btn").forEach(btn => {
          btn.onclick = async () => {
            const email = btn.dataset.email;
            const name = btn.dataset.name;
            if (email && name) {
              await loginAs(email, name);
            }
          };
        });
      } else {
        quickPickContainer.innerHTML = `<p style="font-size:0.78rem; color:var(--text-muted); font-style:italic; margin:0.4rem 0;">No saved traveler profiles. Sign in with Google above or enter an address below.</p>`;
      }
    }

    // Custom login form
    const customLoginForm = document.getElementById("customLoginForm");
    if (customLoginForm) {
      customLoginForm.onsubmit = async (e) => {
        e.preventDefault();
        const name = document.getElementById("customLoginName")?.value.trim();
        const email = document.getElementById("customLoginEmail")?.value.trim();
        if (name && email) {
          await loginAs(email, name);
        }
      };
    }

    // Switcher dropdown: Only action options, NO cached users listed
    const switcher = document.getElementById("userSwitcherSelect");
    if (switcher) {
      const activeLabel = currentUser ? `👤 ${currentUser.name}` : "Account Menu...";
      switcher.innerHTML = `
        <option value="" disabled selected>${escapeHtml(activeLabel)}</option>
        <option value="switch">🔑 Switch / Sign In Account</option>
        <option value="manage">👥 Manage & Delete Users</option>
        ${currentUser ? `<option value="logout">🚪 Log Off</option>` : ''}
      `;
      switcher.onchange = async (e) => {
        const val = e.target.value;
        if (val === "switch") {
          openLogin();
        } else if (val === "manage") {
          openManageUsersModal();
        } else if (val === "logout") {
          await logoff();
        }
        switcher.selectedIndex = 0;
      };
    }

    // Manage Users modal buttons
    const openManageUsersBtn = document.getElementById("openManageUsersBtn");
    const manageUsersFromLoginBtn = document.getElementById("manageUsersFromLoginBtn");
    const closeManageUsersModalBtn = document.getElementById("closeManageUsersModalBtn");
    const closeManageUsersModalBtn2 = document.getElementById("closeManageUsersModalBtn2");
    const cleanupDemoBtn = document.getElementById("cleanupDemoBtn");

    if (openManageUsersBtn) openManageUsersBtn.onclick = openManageUsersModal;
    if (manageUsersFromLoginBtn) {
      manageUsersFromLoginBtn.onclick = () => {
        closeLogin();
        openManageUsersModal();
      };
    }
    if (closeManageUsersModalBtn) closeManageUsersModalBtn.onclick = closeManageUsersModal;
    if (closeManageUsersModalBtn2) closeManageUsersModalBtn2.onclick = closeManageUsersModal;
    if (cleanupDemoBtn) cleanupDemoBtn.onclick = purgeDemoAccounts;

  } catch (err) {
    console.error("Auth check error:", err);
  }
}

// User Management Modal Handlers
function getAuthHeaders(extra = {}) {
  const sessionToken = localStorage.getItem("travel_scout_session");
  const localUserId = localStorage.getItem("travel_scout_user_id");
  const headers = { ...extra };
  if (sessionToken) {
    headers["x-travel-scout-session"] = sessionToken;
  } else if (localUserId) {
    headers["x-travel-scout-user-id"] = localUserId;
  }
  return headers;
}

async function openManageUsersModal() {
  const modal = document.getElementById("manageUsersModal");
  if (!modal) return;
  modal.style.display = "flex";
  await loadManageUsers();
}

function closeManageUsersModal() {
  const modal = document.getElementById("manageUsersModal");
  if (modal) modal.style.display = "none";
}

async function loadManageUsers() {
  const listEl = document.getElementById("manageUsersList");
  const countEl = document.getElementById("manageUsersCount");
  if (!listEl) return;

  try {
    const res = await fetch("/api/users", {
      headers: getAuthHeaders(),
      credentials: "include"
    });
    const users = await res.json();
    if (countEl) countEl.textContent = users.length;

    if (!users || users.length === 0) {
      listEl.innerHTML = `<p style="font-size:0.85rem; color:var(--text-muted); font-style:italic; padding:0.5rem 0;">No registered users found in database.</p>`;
      return;
    }

    listEl.innerHTML = users.map(u => {
      const isCurrent = (currentUser && currentUser.id === u.id);
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; background:#0f172a; border:1px solid ${isCurrent ? '#38bdf8' : 'rgba(255,255,255,0.08)'}; border-radius:6px; padding:0.6rem 0.85rem; gap:0.75rem;">
          <div style="display:flex; align-items:center; gap:0.75rem; min-width:0;">
            <div class="user-avatar-badge" style="background:${u.avatar_url ? 'transparent' : (u.avatar_color || '#38bdf8')}; width:32px; height:32px; font-size:0.8rem; flex-shrink:0;">
              ${u.avatar_url ? `<img src="${escapeHtml(u.avatar_url)}" alt="${escapeHtml(u.name)}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;" />` : escapeHtml(u.name.slice(0, 2).toUpperCase())}
            </div>
            <div style="min-width:0;">
              <div style="display:flex; align-items:center; gap:0.4rem; flex-wrap:wrap;">
                <strong style="color:var(--text-main); font-size:0.86rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(u.name)}</strong>
                ${isCurrent ? `<span style="background:#38bdf8; color:#0f172a; font-size:0.65rem; font-weight:700; padding:0.1rem 0.35rem; border-radius:3px;">YOU</span>` : ''}
                ${u.is_demo ? `<span style="background:#f97316; color:#ffffff; font-size:0.65rem; font-weight:700; padding:0.1rem 0.35rem; border-radius:3px;">DEMO</span>` : ''}
              </div>
              <div style="font-size:0.75rem; color:#94a3b8; font-family:var(--font-mono, monospace); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ✉️ ${escapeHtml(u.email)} &bull; ${u.trips_count} trip(s)
              </div>
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-delete-user" data-id="${u.id}" data-name="${escapeHtml(u.name)}" data-email="${escapeHtml(u.email)}" style="background:#ef4444; color:#fff; padding:0.35rem 0.65rem; font-size:0.75rem; border:none; border-radius:4px; cursor:pointer; flex-shrink:0;">
            🗑️ Delete
          </button>
        </div>
      `;
    }).join("");

    listEl.querySelectorAll(".btn-delete-user").forEach(btn => {
      btn.onclick = async () => {
        const uid = btn.dataset.id;
        const uname = btn.dataset.name;
        const uemail = btn.dataset.email;
        if (confirm(`Are you sure you want to permanently delete user "${uname}" (${uemail})?\n\nThis will also delete any itineraries and data owned by this account.`)) {
          await deleteUserAccount(uid);
        }
      };
    });

  } catch (err) {
    console.error("Failed to load users:", err);
    listEl.innerHTML = `<p style="font-size:0.82rem; color:#ef4444;">Failed to load registered users.</p>`;
  }
}

async function deleteUserAccount(userId) {
  try {
    const res = await fetch(`/api/users/${userId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "Failed to delete user");
      return;
    }
    alert(data.message || "User deleted successfully!");
    if (data.was_logged_in) {
      localStorage.removeItem("travel_scout_session");
      localStorage.removeItem("travel_scout_user_id");
      window.location.reload();
    } else {
      await loadManageUsers();
      await loadCurrentUser();
    }
  } catch (err) {
    alert("Error deleting user: " + err.message);
  }
}

async function purgeDemoAccounts() {
  if (!confirm("Are you sure you want to permanently delete the pre-seeded demo accounts (Larry Munroe and Sarah Chen) and their demo itineraries?\n\nThis will give you a completely clean instance for your own team.")) {
    return;
  }
  try {
    const res = await fetch("/api/users/cleanup-demo", {
      method: "POST",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "Failed to purge demo accounts");
      return;
    }
    alert(`Demo accounts purged successfully! (${data.count} demo users removed)`);
    if (data.was_logged_in) {
      localStorage.removeItem("travel_scout_session");
      localStorage.removeItem("travel_scout_user_id");
      window.location.reload();
    } else {
      await loadManageUsers();
      await loadCurrentUser();
    }
  } catch (err) {
    alert("Error purging demo accounts: " + err.message);
  }
}

window.loginAs = async function(email, name) {
  try {
    const res = await fetch("/auth/dev-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, name })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert("Login failed: " + (err.detail || JSON.stringify(err)));
      return;
    }
    const data = await res.json();
    if (data.session_token) {
      localStorage.setItem("travel_scout_session", data.session_token);
    }
    if (data.user && data.user.id) {
      localStorage.setItem("travel_scout_user_id", data.user.id);
    }
    // Evict any cached HTML from CacheStorage to prevent showing guest view
    if ('caches' in window) {
      try {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
      } catch (e) {}
    }
    window.location.href = "/";
  } catch (err) {
    alert("Login failed: " + err.message);
  }
};

window.logoff = async function() {
  try {
    localStorage.removeItem("travel_scout_session");
    localStorage.removeItem("travel_scout_user_id");
    // Evict any cached HTML from CacheStorage to prevent showing logged in view
    if ('caches' in window) {
      try {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
      } catch (e) {}
    }
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    window.location.href = "/";
  } catch (err) {
    console.error("Logout error:", err);
    localStorage.removeItem("travel_scout_session");
    localStorage.removeItem("travel_scout_user_id");
    window.location.href = "/";
  }
};

// Aliases for backward compatibility
const loginAs = window.loginAs;
const logoff = window.logoff;

// 3. Load Trip Details & Switcher
async function loadTripsDropdown() {
  const switcher = document.getElementById("tripSwitcherSelect");
  if (!switcher) return;
  try {
    const res = await fetch("/api/trips", {
      headers: getAuthHeaders(),
      credentials: "include"
    });
    const trips = await res.json();
    switcher.innerHTML = trips.map(t => `<option value="${t.id}">${escapeHtml(t.title)} (${t.cities_count} cities)</option>`).join("");
    if (currentTripId) switcher.value = currentTripId;
    switcher.onchange = async (e) => {
      currentTripId = e.target.value;
      await refreshTrip();
    };
  } catch (err) {
    console.error("Failed to load trips dropdown:", err);
  }
}

async function loadInitialTrip() {
  try {
    const res = await fetch("/api/trips", { headers: getAuthHeaders(), credentials: "include" });
    const trips = await res.json();
    if (trips.length > 0) {
      if (!currentTripId || !trips.find(t => t.id === currentTripId)) {
        currentTripId = trips[0].id;
      }
      await loadTripsDropdown();
      await refreshTrip();
    } else {
      currentTripId = null;
      currentTripData = null;
      const switcher = document.getElementById("tripSwitcherSelect");
      if (switcher) switcher.innerHTML = `<option value="">No Itineraries</option>`;
      const sub = document.getElementById("tripSubtitle");
      if (sub) {
        sub.textContent = !currentUser
          ? "You are currently logged out. Sign in with your Gmail account to access itineraries."
          : "No private itineraries found. Click '➕ New Trip' to start your first journey!";
      }
      const citiesList = document.getElementById("citiesList");
      if (citiesList) {
        if (!currentUser) {
          citiesList.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:3.5rem 1.5rem; background:rgba(255,255,255,0.02); border:1px dashed var(--border); border-radius:8px;">
              <h3 style="color:#fca5a5; font-size:1.1rem; margin-bottom:0.4rem;">🔒 Signed Out</h3>
              <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:1.2rem;">Please sign in with your Gmail account to view, customize, or collaborate on multi-city itineraries.</p>
              <button class="btn btn-primary" onclick="window.openLogin ? window.openLogin() : document.getElementById('loginModal').style.display='flex'">🔑 Sign In with Gmail</button>
            </div>
          `;
        } else {
          citiesList.innerHTML = `<p style="color:var(--text-muted); text-align:center; padding:3rem;">You have no active trips. Click "➕ New Trip" in the header to create your first journey or ask a companion to share theirs with you!</p>`;
        }
      }
      const todoGrid = document.getElementById("todoGrid");
      if (todoGrid) todoGrid.innerHTML = `<p style="grid-column:1/-1; color:var(--text-muted); text-align:center; padding:2rem;">${!currentUser ? 'Please sign in with Gmail to view the To-Do list.' : 'No items yet. Create a trip to start planning.'}</p>`;
      const daysContainer = document.getElementById("daysContainer");
      if (daysContainer) daysContainer.innerHTML = "";

      const exploreCardsGrid = document.getElementById("exploreCardsGrid");
      if (exploreCardsGrid) {
        exploreCardsGrid.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; padding: 3.5rem 1.5rem; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-md); border: 1px dashed var(--border);">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🎒</div>
            <h3 style="color: var(--text-main); margin-bottom: 0.4rem;">No Active Itinerary</h3>
            <p style="font-size: 0.88rem; margin-bottom: 1.2rem;">You do not have any trips saved right now. Click "➕ New Trip" in the header to start a new adventure!</p>
            <button class="btn btn-primary" onclick="document.getElementById('createTripModal').style.display='flex'">➕ Start a New Trip</button>
          </div>
        `;
      }
      const exploreCount = document.getElementById("exploreItemCount");
      if (exploreCount) exploreCount.textContent = "0";
      const collabsBar = document.getElementById("collaboratorsBar");
      if (collabsBar) collabsBar.innerHTML = "";
    }
  } catch (err) {
    console.error("Failed to load initial trip:", err);
  }
}

async function refreshTrip() {
  if (!currentTripId) return;
  try {
    const localUserId = localStorage.getItem("travel_scout_user_id");
    const headers = {};
    if (localUserId) headers["x-travel-scout-user-id"] = localUserId;

    const res = await fetch(`/api/trips/${currentTripId}`, { headers, credentials: "include" });
    currentTripData = await res.json();

    if (currentTripData.trip) {
      const sub = document.getElementById("tripSubtitle");
      if (sub) {
        const citiesList = currentTripData.cities || [];
        const citiesTrail = citiesList.length > 0
          ? citiesList.map(c => escapeHtml(c.city_name)).join(" &rarr; ")
          : "";
        const desc = currentTripData.trip.description ? escapeHtml(currentTripData.trip.description) : "";
        let titleHtml = `<strong>${escapeHtml(currentTripData.trip.title)}</strong>`;
        if (citiesTrail) {
          titleHtml += ` &bull; ${citiesTrail}`;
        } else if (desc) {
          titleHtml += ` &bull; ${desc}`;
        }
        sub.innerHTML = titleHtml;
      }
    }

    const switcher = document.getElementById("tripSwitcherSelect");
    if (switcher && switcher.value !== currentTripId) {
      switcher.value = currentTripId;
    }

    renderCollaborators();
    renderCitiesTab();
    renderItineraryTab();
    populateCityDropdowns();
    renderExploreTab(true);
    if (leafletMap) renderMapLocations();

    const activeTab = document.querySelector(".nav-tab.active");
    if (activeTab && activeTab.dataset.tab === "expenses") {
      loadTripExpenses();
    }
  } catch (err) {
    console.error("Failed to refresh trip:", err);
  }
}

// 4. Render Collaborators Avatar Stack & Manage Modal
function renderCollaborators() {
  const bar = document.getElementById("collaboratorsBar");
  if (!bar || !currentTripData) return;

  bar.innerHTML = currentTripData.collaborators.map(c => `
    <div class="collab-avatar" style="background:${c.avatar_color || '#38bdf8'}; cursor:pointer;" title="${escapeHtml(c.name)} (${escapeHtml(c.email)}) - ${c.role} (Click to manage)" onclick="openCollaboratorsModal()">
      ${c.name.slice(0, 2).toUpperCase()}
    </div>
  `).join("");

  renderModalCollaborators();
}

function renderModalCollaborators() {
  const list = document.getElementById("modalCollaboratorsList");
  if (!list || !currentTripData) return;

  if (currentTripData.collaborators.length === 0) {
    list.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted);">No contributors on this trip yet.</p>`;
    return;
  }

  list.innerHTML = currentTripData.collaborators.map(c => `
    <div class="collab-row-item">
      <div class="collab-row-info">
        <span class="user-avatar-badge" style="background:${c.avatar_color || '#38bdf8'}; width:28px; height:28px; font-size:0.75rem;">
          ${c.name.slice(0, 2).toUpperCase()}
        </span>
        <div style="display:flex; flex-direction:column;">
          <div style="display:flex; align-items:center; gap:0.4rem;">
            <strong style="color:var(--text-main); font-size:0.86rem;">${escapeHtml(c.name)}</strong>
            <span class="user-role">${c.role}</span>
          </div>
          <span style="font-size:0.74rem; color:#94a3b8; font-family:var(--font-mono, monospace);">✉️ ${escapeHtml(c.email)}</span>
        </div>
      </div>
      <div>
        ${c.is_owner ? `
          <span style="font-size:0.75rem; color:#fbbf24; font-weight:700; padding:0.2rem 0.5rem; background:rgba(251,191,36,0.1); border-radius:4px; border:1px solid rgba(251,191,36,0.25);">👑 Trip Owner</span>
        ` : `
          <button type="button" class="btn-remove-collab" onclick="removeCollaborator('${c.user_id || c.id}', '${escapeHtml(c.name)}')">
            🗑️ Remove
          </button>
        `}
      </div>
    </div>
  `).join("");
}

window.openCollaboratorsModal = function() {
  const modal = document.getElementById("inviteModal");
  if (modal) {
    renderModalCollaborators();
    modal.style.display = "flex";
  }
};

window.removeCollaborator = async function(userId, name) {
  if (!confirm(`Are you sure you want to remove ${name} from this trip? They will no longer have access.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/trips/${currentTripId}/collaborators/${userId}`, {
      method: "DELETE"
    });
    if (res.ok) {
      alert(`Removed ${name} from contributors.`);
      await refreshTrip();
    } else {
      const data = await res.json();
      alert("Failed to remove contributor: " + (data.detail || res.statusText));
    }
  } catch (err) {
    alert("Error removing contributor: " + err.message);
  }
};

// 5. Render Cities & Stays Manager Tab
function renderCitiesTab() {
  const container = document.getElementById("citiesList");
  if (!container || !currentTripData) return;

  if (currentTripData.cities.length === 0) {
    container.innerHTML = `<p style="color:var(--text-muted); text-align:center; padding:3rem;">No destination cities added yet. Click "Add Destination City" above to start your journey!</p>`;
    return;
  }

  container.innerHTML = currentTripData.cities.map(city => {
    const cityNow = (currentTripData.weather && currentTripData.weather._current) ? currentTripData.weather._current[city.city_name] : null;
    return `
    <div class="city-card">
      <div class="city-card-header">
        <div class="city-card-title-group">
          <div class="city-order-badge">${city.order_index}</div>
          <div>
            <div class="city-name">${escapeHtml(city.city_name)}, <span style="color:var(--text-muted); font-size:1rem; font-weight:400;">${escapeHtml(city.country)}</span></div>
            <div class="city-dates">📅 ${city.start_date} &rarr; ${city.end_date}</div>
            ${cityNow ? `
              <div style="display:inline-flex; align-items:center; gap:0.35rem; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.15); border-radius:999px; padding:0.18rem 0.55rem; font-size:0.75rem; margin-top:0.35rem;" title="Current live weather in ${escapeHtml(city.city_name)}">
                <span>${cityNow.icon}</span>
                <span style="font-weight:700; color:#38bdf8;">${Math.round(cityNow.temp_f)}&deg;F</span>
                <span style="color:var(--text-muted); font-size:0.72rem;">${escapeHtml(cityNow.condition)} (Live Now)</span>
              </div>
            ` : ''}
          </div>
        </div>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
          <button class="btn btn-primary btn-sm" onclick="jumpToScoutCity('${escapeHtml(city.city_name)}')">
            🌐 Scout City 🚀
          </button>
          <button class="btn btn-secondary btn-sm" onclick="openAddStayModal('${city.id}', '${escapeHtml(city.city_name)}')">
            🏨 Add Hotel by Date
          </button>
          <button class="btn-danger-sm" onclick="deleteCity('${city.id}', '${escapeHtml(city.city_name)}')">
            🗑️ Delete City
          </button>
        </div>
      </div>

      <div style="font-size:0.85rem; font-weight:700; color:#38bdf8; margin-top:0.5rem;">
        Accommodations & Stays in ${escapeHtml(city.city_name)}:
      </div>
      <div class="stays-subgrid">
        ${city.stays.map(stay => {
          const isHomeOrFriend = /friend|house|home|airbnb|apartment|apt|staying with|condo/i.test(stay.name);
          const stayIcon = isHomeOrFriend ? '🏡' : '🏨';
          const stayLabel = isHomeOrFriend ? 'Stay' : 'Hotel';
          const mapsDest = (stay.lat && stay.lon && stay.lat !== 0)
            ? `${stay.lat},${stay.lon}`
            : encodeURIComponent(isHomeOrFriend ? stay.address : (stay.name + ', ' + stay.address));
          return `
          <div class="stay-box">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem;">
              <div class="stay-box-title">
                <a href="https://www.google.com/maps/dir/?api=1&destination=${mapsDest}" target="_blank" rel="noopener noreferrer" class="card-title-link" title="Get directions to lodging in Google Maps">
                  ${stayIcon} ${escapeHtml(stay.name)} <span class="card-link-icon">↗</span>
                </a>
              </div>
              <div style="display:flex; gap:0.35rem; align-items:center;">
                <button type="button" class="btn btn-secondary btn-sm" onclick='openEditStayModal("${stay.id}", ${JSON.stringify(stay.name).replace(/'/g, "&apos;")}, ${JSON.stringify(stay.address).replace(/'/g, "&apos;")}, "${stay.start_date}", "${stay.end_date}", ${JSON.stringify(stay.notes || "").replace(/'/g, "&apos;")})' style="font-size:0.7rem; padding:0.18rem 0.45rem;" title="Edit lodging name, street address, or dates">
                  ✏️ Edit
                </button>
                ${city.stays.length > 1 ? `
                  <button onclick="deleteStay('${stay.id}')" style="background:none; border:none; color:#f43f5e; cursor:pointer; font-size:0.85rem; padding:0 0.2rem;" title="Delete this stay">&times;</button>
                ` : ''}
              </div>
            </div>
            <div class="stay-box-dates">Check-in: <strong>${stay.start_date}</strong> &bull; Check-out: <strong>${stay.end_date}</strong></div>
            <div class="stay-box-address" style="color:#e2e8f0; font-size:0.8rem; margin:0.25rem 0;">📍 <strong>${escapeHtml(stay.address)}</strong></div>
            ${stay.notes ? `<div style="font-size:0.75rem; color:#94a3b8; margin-top:0.2rem;"><em>${escapeHtml(stay.notes)}</em></div>` : ''}
            <div style="margin-top:0.55rem; display:flex; gap:0.4rem; flex-wrap:wrap;">
              <a href="https://www.google.com/maps/dir/?api=1&destination=${mapsDest}" target="_blank" rel="noopener noreferrer" class="item-link-pill maps" style="font-size:0.7rem; padding:0.2rem 0.55rem; background:#0284c7; color:#ffffff; font-weight:600;" title="Open directions to lodging in Google Maps with destination pre-populated">
                🧭 Directions to ${stayLabel} ↗
              </a>
              <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(stay.address || (stay.name + ' ' + city.city_name))}" target="_blank" rel="noopener noreferrer" class="item-link-pill neutral" style="font-size:0.7rem; padding:0.2rem 0.55rem;" title="View location pin in Google Maps">
                📍 View on Map ↗
              </a>
            </div>
          </div>
        `;
        }).join("")}
      </div>
    </div>
  `;
  }).join("");
}

// 6. Render Collaborative Itinerary Tab
function renderItineraryTab() {
  const todoGrid = document.getElementById("todoGrid");
  const daysContainer = document.getElementById("daysContainer");
  const todoBadge = document.getElementById("todoCountBadge");
  const cityFilter = document.getElementById("itineraryCityFilter")?.value || "all";

  if (!todoGrid || !daysContainer || !currentTripData) return;

  const itin = currentTripData.itinerary;
  const availDates = currentTripData.available_dates;

  // Filter To-Do items
  let filteredTodo = itin.todo;
  if (cityFilter !== "all") {
    filteredTodo = filteredTodo.filter(it => it.city_id === cityFilter);
  }

  if (todoBadge) todoBadge.textContent = `${filteredTodo.length} Items`;

  if (filteredTodo.length === 0) {
    todoGrid.innerHTML = `<p style="grid-column:1/-1; color:var(--text-muted); font-size:0.85rem; text-align:center; padding:1.5rem 0;">No unscheduled items in this city. <button type="button" class="btn btn-secondary btn-sm" style="margin-left:0.5rem; font-size:0.75rem; padding:0.2rem 0.5rem;" onclick="openAddItemModal('todo')">➕ Add Wishlist Card</button> or scout new places below!</p>`;
  } else {
    todoGrid.innerHTML = filteredTodo.map(it => renderCard(it, availDates)).join("");
  }

  // Filter Days
  daysContainer.innerHTML = itin.days.map(day => {
    let dayItems = day.items;
    if (cityFilter !== "all") {
      dayItems = dayItems.filter(it => it.city_id === cityFilter);
    }

    if (cityFilter !== "all" && dayItems.length === 0) return "";

    const dayCity = (dayItems.length > 0 && dayItems[0].city_name && dayItems[0].city_name !== "Universal") ? dayItems[0].city_name : null;
    const dayStay = day.stay || getLodgingForDate(day.date);
    const weather = (currentTripData.weather && currentTripData.weather[day.date]) ? currentTripData.weather[day.date] : null;
    const cityNow = (dayCity && currentTripData.weather && currentTripData.weather._current) ? currentTripData.weather._current[dayCity] : null;

    return `
      <div class="day-block">
        <div class="day-header" style="flex-wrap:wrap; gap:0.5rem; align-items:center;">
          <div class="day-title">📅 Date: <strong>${day.date}</strong> ${dayCity ? `&bull; <span style="color:#38bdf8; font-weight:600;">🏙️ ${escapeHtml(dayCity)}</span>` : ''}</div>
          ${dayStay ? `
            <span class="badge" title="Active Lodging: ${escapeHtml(dayStay.name)} (${escapeHtml(dayStay.address || '')})" style="background:rgba(2,132,199,0.18); border:1px solid rgba(56,189,248,0.35); color:#bae6fd; font-size:0.75rem; display:inline-flex; align-items:center; gap:0.35rem; padding:0.2rem 0.55rem; border-radius:999px;">
              <span>🏨 Base: <strong>${escapeHtml(dayStay.name)}</strong></span>
              <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dayStay.name + ', ' + (dayStay.address || ''))}" target="_blank" rel="noopener noreferrer" style="color:#38bdf8; text-decoration:none; font-weight:700; margin-left:0.2rem;" title="Directions to lodging in Google Maps">🧭 Hotel ↗</a>
            </span>
          ` : ''}
          <span class="badge" style="background:rgba(56,189,248,0.15); color:#38bdf8;">${dayItems.length} Stops</span>
          ${weather ? `
            <span class="badge" title="${escapeHtml(weather.advisory)}" style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.15); color:var(--text-main); font-size:0.75rem; display:inline-flex; align-items:center; gap:0.35rem; padding:0.2rem 0.55rem; border-radius:999px;">
              <span>${weather.icon}</span>
              <span style="font-weight:600;">${Math.round(weather.temp_max_f)}&deg;F / ${Math.round(weather.temp_min_f)}&deg;F</span>
              <span style="color:#94a3b8; font-size:0.7rem;">${escapeHtml(weather.condition)}</span>
              ${weather.precipitation_probability_max > 20 ? `<span style="color:#38bdf8; font-size:0.7rem;">💧 ${weather.precipitation_probability_max}%</span>` : ''}
            </span>
          ` : (cityNow ? `
            <span class="badge" title="Live current weather in ${escapeHtml(dayCity)}. Day-specific forecasts appear 14 days prior to departure." style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.15); color:var(--text-main); font-size:0.75rem; display:inline-flex; align-items:center; gap:0.35rem; padding:0.2rem 0.55rem; border-radius:999px;">
              <span>${cityNow.icon}</span>
              <span style="font-weight:600;">${Math.round(cityNow.temp_f)}&deg;F</span>
              <span style="color:#94a3b8; font-size:0.7rem;">${escapeHtml(cityNow.condition)} (Live Now)</span>
            </span>
          ` : '')}
          <div style="display:flex; gap:0.4rem; align-items:center; margin-left:auto;">
            <button type="button" class="btn btn-primary btn-sm" style="padding:0.2rem 0.55rem; font-size:0.75rem;" onclick="openAddItemModal('${day.date}', '${escapeHtml(dayCity || '')}')" title="Add a custom stop or card to this date">
              ➕ Add Stop
            </button>
            ${dayCity ? `
              <button type="button" class="btn btn-secondary btn-sm" style="padding:0.2rem 0.55rem; font-size:0.75rem;" onclick="jumpToScoutCity('${escapeHtml(dayCity)}')">
                🌐 Scout ${escapeHtml(dayCity)} 🚀
              </button>
            ` : ''}
          </div>
        </div>
        ${weather && weather.is_rainy ? `
          <div style="background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); color:#bae6fd; border-radius:6px; padding:0.45rem 0.75rem; font-size:0.8rem; margin:0.4rem 0 0.6rem 0; display:flex; align-items:center; gap:0.5rem;">
            <span>☔</span>
            <span><strong>Rain Forecast:</strong> ${escapeHtml(weather.advisory)}</span>
          </div>
        ` : ''}
        ${dayItems.length === 0 ? `
          <div style="color:var(--text-muted); font-size:0.85rem; padding:1.2rem 0; text-align:center; background:rgba(255,255,255,0.02); border-radius:8px; border:1px dashed var(--border);">
            No stops scheduled for this day yet.
            <button type="button" class="btn btn-secondary btn-sm" style="margin-left:0.5rem; font-size:0.75rem; padding:0.22rem 0.55rem;" onclick="openAddItemModal('${day.date}', '${escapeHtml(dayCity || '')}')">
              ➕ Add Stop to this Day
            </button>
          </div>
        ` : `
          <div class="cards-grid">
            ${dayItems.map(it => renderCard(it, availDates)).join("")}
          </div>
        `}
      </div>
    `;
  }).join("");

  attachCardEventListeners();
  if (window.isBulkSelectMode) {
    updateBulkActionBarUI();
  }
}

function buildCardTransitBox(transit) {
  if (!transit || (!transit.miles && !transit.transit_line && !transit.walk_time)) {
    return '';
  }

  const isWalkable = Boolean(transit.is_walkable);
  const stayName = escapeHtml(transit.stay_name || 'Hotel');
  const transitLine = escapeHtml(transit.transit_line || 'Local Transit');
  const busRoutes = transit.bus_routes ? escapeHtml(transit.bus_routes) : '';
  const transitDetails = transit.transit_details ? escapeHtml(transit.transit_details) : '';
  const fareTip = transit.fare_tip ? escapeHtml(transit.fare_tip) : '';
  const walkTime = escapeHtml(transit.walk_time || '');
  const walkLabel = escapeHtml(transit.walk_label || (isWalkable ? 'Walkable' : 'Transit Advised'));
  const miles = transit.miles ? `${transit.miles} mi` : '';
  const rideshare = transit.rideshare_estimate ? escapeHtml(transit.rideshare_estimate) : '';

  const transitUrl = transit.transit_url ? escapeHtml(transit.transit_url) : '';
  const walkingUrl = transit.walking_url ? escapeHtml(transit.walking_url) : '';

  return `
    <div class="card-transit-box">
      <!-- Top Header Row: Recommended Mode & Stay Reference -->
      <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.35rem;">
        <div style="font-weight:700; font-size:0.82rem; color:#38bdf8; display:flex; align-items:center; gap:0.35rem;">
          <span>${escapeHtml(transit.best_mode || 'Transit / Walk')}</span>
        </div>
        <div style="font-size:0.72rem; color:var(--text-muted);">
          📍 From <strong>${stayName}</strong>
        </div>
      </div>

      <!-- Bus & Public Transit Row -->
      ${transit.transit_line ? `
        <div style="font-size:0.78rem; color:#bae6fd; margin-bottom:0.35rem; line-height:1.4; display:flex; align-items:flex-start; gap:0.4rem;">
          <span style="font-size:0.95rem; line-height:1; flex-shrink:0;">🚌</span>
          <div style="flex:1;">
            <div>
              <strong style="color:#ffffff;">${transitLine}</strong>
              ${transit.transit_time ? `<span style="color:#38bdf8; font-weight:600; margin-left:0.3rem;">(~${escapeHtml(transit.transit_time)})</span>` : ''}
            </div>
            ${busRoutes ? `<div style="font-size:0.72rem; color:#93c5fd; margin-top:0.1rem;"><strong>Bus Lines:</strong> ${busRoutes}</div>` : ''}
            ${transitDetails ? `<div style="font-size:0.72rem; color:#cbd5e1; margin-top:0.15rem;">${transitDetails}</div>` : ''}
            ${fareTip ? `<div style="font-size:0.70rem; color:#6ee7b7; margin-top:0.15rem;">💳 ${fareTip}</div>` : ''}
          </div>
        </div>
      ` : ''}

      <!-- Walking & Rideshare Bottom Row -->
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#cbd5e1; border-top:1px dashed rgba(255,255,255,0.08); padding-top:0.35rem; margin-top:0.35rem; flex-wrap:wrap; gap:0.4rem;">
        <div style="display:flex; align-items:center; gap:0.4rem;">
          <span>🚶 <strong>${miles}</strong> (${walkTime})</span>
          <span style="color:${isWalkable ? '#4ade80' : '#f59e0b'}; font-size:0.70rem; font-weight:600; padding:0.1rem 0.35rem; background:${isWalkable ? 'rgba(34,197,94,0.12)' : 'rgba(245,158,11,0.12)'}; border-radius:4px;">
            ${walkLabel}
          </span>
        </div>
        ${rideshare ? `
          <div style="font-size:0.70rem; color:var(--text-muted);" title="Estimated rideshare duration and fare">
            🚕 ${rideshare}
          </div>
        ` : ''}
      </div>

      <!-- Action Navigation Buttons (Google Maps Live Transit & Walking) -->
      <div style="margin-top:0.45rem; display:flex; gap:0.4rem; flex-wrap:wrap;">
        ${transitUrl ? `
          <a href="${transitUrl}" target="_blank" rel="noopener noreferrer" class="transit-action-btn bus" style="font-size:0.72rem; padding:0.25rem 0.6rem; border-radius:6px; font-weight:600; display:inline-flex; align-items:center; gap:0.3rem;" title="Open real-time Bus &amp; Transit Directions in Google Maps">
            🚌 Bus &amp; Transit Directions ↗
          </a>
        ` : ''}
        ${walkingUrl ? `
          <a href="${walkingUrl}" target="_blank" rel="noopener noreferrer" class="transit-action-btn walk" style="font-size:0.72rem; padding:0.25rem 0.6rem; border-radius:6px; font-weight:600; display:inline-flex; align-items:center; gap:0.3rem;" title="Open Walking Route in Google Maps">
            🚶 Walking Route ↗
          </a>
        ` : ''}
      </div>
    </div>
  `;
}

function getLodgingForDate(targetDate, cityId = null) {
  if (!currentTripData || !Array.isArray(currentTripData.cities)) return null;

  // 1. If date is a specific calendar date, search all stays across all trip cities
  if (targetDate && targetDate !== "todo") {
    for (const city of currentTripData.cities) {
      if (Array.isArray(city.stays)) {
        for (const s of city.stays) {
          if (s.start_date && s.end_date && s.start_date <= targetDate && targetDate <= s.end_date) {
            return s;
          }
        }
      }
    }
    // Check if city date boundaries cover it
    for (const city of currentTripData.cities) {
      if (city.start_date && city.end_date && city.start_date <= targetDate && targetDate <= city.end_date) {
        if (Array.isArray(city.stays) && city.stays.length > 0) {
          return city.stays[0];
        }
      }
    }
  }

  // 2. Preferred city match
  if (cityId) {
    const matchedCity = currentTripData.cities.find(c => String(c.id) === String(cityId));
    if (matchedCity && Array.isArray(matchedCity.stays) && matchedCity.stays.length > 0) {
      return matchedCity.stays[0];
    }
  }

  // 3. Fallback to first stay of first city
  const firstCity = currentTripData.cities[0];
  if (firstCity && Array.isArray(firstCity.stays) && firstCity.stays.length > 0) {
    return firstCity.stays[0];
  }

  return null;
}

function getDirectionsUrlFromLodging(item, targetDate = null) {
  const transit = item.transit;
  if (transit && (transit.walking_url || transit.transit_url || transit.driving_url)) {
    return transit.is_walkable ? (transit.walking_url || transit.transit_url) : (transit.transit_url || transit.walking_url);
  }

  const effectiveDate = targetDate || item.assigned_date;
  const stay = getLodgingForDate(effectiveDate, item.city_id || item.city_segment_id);

  let orig = "";
  if (stay) {
    if (stay.lat != null && stay.lon != null && stay.lat !== 0) {
      orig = `${stay.lat},${stay.lon}`;
    } else if (stay.address) {
      const origName = (stay.name && !stay.address.includes(stay.name)) ? `${stay.name}, ` : "";
      orig = encodeURIComponent(origName + stay.address);
    } else if (stay.name) {
      orig = encodeURIComponent(stay.name);
    }
  }

  let dest = "";
  if (item.lat != null && item.lon != null && item.lat !== 0) {
    dest = `${item.lat},${item.lon}`;
  } else {
    dest = encodeURIComponent((item.title || '') + ' ' + (item.address || item.city_name || ''));
  }

  const base = "https://www.google.com/maps/dir/?api=1";
  const origParam = orig ? `&origin=${orig}` : '';
  return `${base}${origParam}&destination=${dest}&travelmode=transit`;
}

function renderCard(item, availableDates) {
  const author = item.added_by || { name: "Traveler", avatar_color: "#38bdf8" };
  const transit = item.transit || {};
  const categories = (currentTripData && currentTripData.categories) || {};
  const catConfig = categories[item.category] || {
    icon: "✨",
    label: item.category ? (item.category.charAt(0).toUpperCase() + item.category.slice(1)) : "General"
  };

  const bookingStatus = item.booking_status || "unbooked";
  const bookingRef = item.booking_ref || "";
  const statusBadge = {
    unbooked: { icon: "⚪", label: "Unbooked", bg: "rgba(148,163,184,0.12)", color: "#94a3b8" },
    pending: { icon: "🟡", label: "Pending", bg: "rgba(251,191,36,0.15)", color: "#fbbf24" },
    confirmed: { icon: "🟢", label: "Confirmed", bg: "rgba(34,197,94,0.15)", color: "#22c55e" },
    completed: { icon: "🟣", label: "Completed", bg: "rgba(168,85,247,0.15)", color: "#c084fc" }
  }[bookingStatus] || { icon: "⚪", label: "Unbooked", bg: "rgba(148,163,184,0.12)", color: "#94a3b8" };

  let gcalUrl = "";
  if (item.assigned_date && item.assigned_date !== "todo") {
    const cleanDate = item.assigned_date.replace(/-/g, "");
    const gcalStart = `${cleanDate}T100000Z`;
    const gcalEnd = `${cleanDate}T120000Z`;
    const gcalDetails = encodeURIComponent((item.highlight || "") + (item.url ? `\n\nLink: ${item.url}` : ""));
    const gcalLoc = encodeURIComponent(item.address || item.city_name || "");
    gcalUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(item.title)}&dates=${gcalStart}/${gcalEnd}&details=${gcalDetails}&location=${gcalLoc}`;
  }

  const hasDirectUrl = Boolean(item.url && item.url.trim() !== "");
  const safeDirectUrl = hasDirectUrl ? sanitizeUrl(item.url) : "";
  const targetUrl = safeDirectUrl
    ? safeDirectUrl
    : `https://www.google.com/search?q=${encodeURIComponent(item.title + ' ' + (item.city_name || ''))}`;

  let mapsUrl = "";
  if (item.lat && item.lon) {
    mapsUrl = `https://www.google.com/maps/search/?api=1&query=${item.lat},${item.lon}`;
  } else {
    mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.title + ' ' + (item.address || item.city_name || ''))}`;
  }

  const matchedStay = getLodgingForDate(item.assigned_date, item.city_id);
  const stayName = item.transit?.stay_name || matchedStay?.name || "Hotel";
  const directionsUrl = getDirectionsUrlFromLodging(item);

  const sourceLabel = item.source_platform ? escapeHtml(item.source_platform) : "Website";
  const isSelected = Boolean(window.isBulkSelectMode && window.selectedBulkItemIds && window.selectedBulkItemIds.has(item.id));

  return `
    <div class="itin-card ${isSelected ? 'bulk-card-selected' : ''}" data-item-id="${item.id}" onclick="handleCardBulkClick(event, '${item.id}')">
      <div class="card-bulk-checkbox-wrapper" onclick="event.stopPropagation()">
        <input type="checkbox" class="card-bulk-checkbox" id="bulk-cb-${item.id}" data-bulk-id="${item.id}" ${isSelected ? 'checked' : ''} onchange="toggleCardSelection('${item.id}', this.checked)">
      </div>
      <div class="card-top-row">
        <div>
          <div class="card-title">
            <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" class="card-title-link" title="Open ${escapeHtml(item.title)} link">
              ${escapeHtml(item.title)}
              <span class="card-link-icon">↗</span>
            </a>
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">
            <span>📍 ${escapeHtml(item.neighborhood || item.city_name || 'City')}</span> &bull; 
            <span style="color:#fbbf24; font-weight:600;">${escapeHtml(item.cost || 'Free')}</span>
          </div>
        </div>
        <div style="display:flex; gap:0.4rem; align-items:center; flex-wrap:wrap; justify-content:flex-end;">
          <button type="button" class="btn-booking-status" onclick='openBookingModal("${item.id}", ${JSON.stringify(item.title).replace(/'/g, "&apos;")}, "${bookingStatus}", ${JSON.stringify(bookingRef).replace(/'/g, "&apos;")})' style="background:${statusBadge.bg}; color:${statusBadge.color}; border:1px solid ${statusBadge.color}40; border-radius:999px; padding:0.18rem 0.5rem; font-size:0.72rem; cursor:pointer; display:inline-flex; align-items:center; gap:0.3rem; font-weight:600;" title="Click to update reservation / booking status">
            <span>${statusBadge.icon} ${statusBadge.label}</span>
            ${bookingRef ? `<span style="opacity:0.85; font-size:0.68rem; margin-left:0.2rem;">#${escapeHtml(bookingRef)}</span>` : ''}
          </button>
          <span class="badge" style="background:rgba(56,189,248,0.12); color:#38bdf8; font-size:0.72rem; padding:0.18rem 0.45rem;">${catConfig.icon} ${escapeHtml(catConfig.label)}</span>
          <span class="card-city-badge">${escapeHtml(item.city_name || 'General')}</span>
        </div>
      </div>

      <!-- Date-Matched Hotel Transit & Bus Box -->
      ${buildCardTransitBox(transit)}


      ${item.highlight ? `
        <div style="font-size:0.82rem; color:#cbd5e1; line-height:1.4;">
          ${escapeHtml(item.highlight)}
        </div>
      ` : ''}

      <!-- Item Direct Links Row -->
      <div class="card-links-row">
        ${safeDirectUrl ? `
          <a href="${escapeHtml(safeDirectUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill primary" title="Visit official source or guide">
            🌐 ${sourceLabel} ↗
          </a>
        ` : `
          <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill neutral" title="Search web for info">
            🔍 Web Info ↗
          </a>
        `}
        <a href="${escapeHtml(directionsUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill maps" title="Open Google Maps directions from ${escapeHtml(stayName)} to ${escapeHtml(item.title)} with origin and destination pre-populated">
          🧭 Directions from Hotel ↗
        </a>
        <a href="${escapeHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill neutral" title="Open venue location pin in Google Maps">
          📍 Map Pin ↗
        </a>
        ${gcalUrl ? `
          <a href="${escapeHtml(gcalUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill calendar" title="Add event to Google Calendar" style="background:rgba(59,130,246,0.12); color:#60a5fa; border:1px solid rgba(59,130,246,0.25);">
            📅 + Google Cal ↗
          </a>
        ` : ''}
      </div>

      <!-- Personal Note Section -->
      <div class="card-note-box" id="note-box-${item.id}">
        ${item.personal_note ? `
          <div class="note-content-display">
            <div class="note-meta-line">
              <span class="note-author">📝 Note by <strong>${escapeHtml(item.note_author?.name || 'Traveler')}</strong> <span style="font-size:0.7rem; color:#94a3b8;">(${escapeHtml(item.note_author?.email || '')})</span>:</span>
              <span class="note-date">${escapeHtml(item.note_date || '')}</span>
            </div>
            <div class="note-text">&ldquo;${escapeHtml(item.personal_note)}&rdquo;</div>
            <div style="margin-top:0.35rem; display:flex; gap:0.6rem; align-items:center;">
              <button type="button" class="btn-note-edit" onclick='editCardNote("${item.id}", ${JSON.stringify(item.personal_note).replace(/'/g, "&apos;")})'>✏️ Edit Note</button>
              <button type="button" class="btn-note-delete" onclick="deleteCardNote('${item.id}')">🗑️ Remove</button>
            </div>
          </div>
        ` : `
          <button type="button" class="btn-add-note" onclick="openAddNotePrompt('${item.id}')">
            📝 + Add Personal Note
          </button>
        `}
      </div>

      <div class="card-footer-actions">
        <!-- Author Avatar Tag -->
        <div class="card-author-tag" title="Added by ${escapeHtml(author.name)}">
          <span class="author-dot" style="background:${author.avatar_color || '#38bdf8'};">
            ${author.name.slice(0, 2).toUpperCase()}
          </span>
          <span>${escapeHtml(author.name.split(" ")[0])}</span>
        </div>

        <div style="display:flex; align-items:center; gap:0.4rem;">
          <select class="card-date-select" data-item-id="${item.id}">
            <option value="todo" ${item.assigned_date === 'todo' || !item.assigned_date ? 'selected' : ''}>📋 Bucket List</option>
            ${availableDates.map(d => `
              <option value="${d}" ${item.assigned_date === d ? 'selected' : ''}>📅 ${d}</option>
            `).join("")}
          </select>

          <button onclick="deleteItem('${item.id}')" style="background:none; border:none; color:#f43f5e; cursor:pointer; font-size:1rem; padding:0 0.3rem;" title="Delete item">&times;</button>
        </div>
      </div>
    </div>
  `;
}

function attachCardEventListeners() {
  document.querySelectorAll(".card-date-select").forEach(sel => {
    sel.addEventListener("change", async (e) => {
      const itemId = e.target.dataset.itemId;
      const newDate = e.target.value;
      try {
        await fetch(`/api/trips/${currentTripId}/items/${itemId}`, {
          method: "PUT",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({ assigned_date: newDate })
        });
        await refreshTrip();
      } catch (err) {
        alert("Failed to assign date: " + err.message);
      }
    });
  });
}

window.openAddNotePrompt = async function(itemId) {
  const note = prompt("Enter personal note for this stop (e.g. reservation timing, photo spot, dress code):");
  if (note !== null && note.trim() !== "") {
    await saveCardNote(itemId, note.trim());
  }
};

window.editCardNote = async function(itemId, currentNote) {
  const note = prompt("Edit your personal note for this stop:", currentNote);
  if (note !== null) {
    await saveCardNote(itemId, note.trim());
  }
};

window.deleteCardNote = async function(itemId) {
  if (confirm("Are you sure you want to remove this personal note?")) {
    await saveCardNote(itemId, "");
  }
};

async function saveCardNote(itemId, noteText) {
  try {
    const res = await fetch(`/api/trips/${currentTripId}/items/${itemId}/note`, {
      method: "PUT",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      credentials: "include",
      body: JSON.stringify({ personal_note: noteText })
    });
    if (res.ok) {
      await refreshTrip();
    } else {
      const err = await res.json();
      alert("Failed to save note: " + (err.detail || res.statusText));
    }
  } catch (e) {
    alert("Error saving note: " + e.message);
  }
}

// 7. City Actions (Add & Delete)
async function deleteCity(cityId, cityName) {
  if (!confirm(`Are you sure you want to remove ${cityName} and all its stays from your journey?`)) return;

  try {
    const res = await fetch(`/api/trips/${currentTripId}/cities/${cityId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (res.ok) {
      await refreshTrip();
    } else {
      const err = await res.json().catch(() => ({}));
      alert("Failed to delete city: " + (err.detail || res.statusText));
    }
  } catch (err) {
    alert("Error deleting city: " + err.message);
  }
}

async function deleteStay(stayId) {
  if (!confirm("Remove this hotel stay location?")) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}/stays/${stayId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (res.ok) {
      await refreshTrip();
    } else {
      const err = await res.json().catch(() => ({}));
      alert("Failed to delete stay: " + (err.detail || res.statusText));
    }
  } catch (err) {
    alert("Error deleting stay: " + err.message);
  }
}

async function deleteItem(itemId) {
  if (!confirm("Delete this stop from the itinerary?")) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}/items/${itemId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (res.ok) {
      await refreshTrip();
    } else {
      const err = await res.json().catch(() => ({}));
      alert("Failed to delete item: " + (err.detail || res.statusText));
    }
  } catch (err) {
    alert("Error deleting item: " + err.message);
  }
}
window.deleteItem = deleteItem;

// ==================== BULK CARD SELECTION & DELETION ====================

window.isBulkSelectMode = false;
window.selectedBulkItemIds = new Set();
window.bulkSelectScope = "itinerary"; // 'itinerary' | 'explore'

function toggleBulkSelectMode(scope) {
  if (window.isBulkSelectMode) {
    if (scope && scope !== window.bulkSelectScope) {
      window.bulkSelectScope = scope;
      window.selectedBulkItemIds.clear();
      updateAllCardsBulkState();
      updateBulkActionBarUI();
      return;
    }
    exitBulkSelectMode();
  } else {
    enterBulkSelectMode(scope || "itinerary");
  }
}
window.toggleBulkSelectMode = toggleBulkSelectMode;

function enterBulkSelectMode(scope) {
  window.isBulkSelectMode = true;
  window.bulkSelectScope = scope || "itinerary";
  if (!window.selectedBulkItemIds) {
    window.selectedBulkItemIds = new Set();
  } else {
    window.selectedBulkItemIds.clear();
  }

  document.body.classList.add("bulk-select-active");

  const bar = document.getElementById("bulkActionBar");
  if (bar) bar.style.display = "block";

  updateBulkButtonsText(true);
  updateAllCardsBulkState();
  updateBulkActionBarUI();
}
window.enterBulkSelectMode = enterBulkSelectMode;

function exitBulkSelectMode() {
  window.isBulkSelectMode = false;
  if (window.selectedBulkItemIds) {
    window.selectedBulkItemIds.clear();
  }

  document.body.classList.remove("bulk-select-active");

  const bar = document.getElementById("bulkActionBar");
  if (bar) bar.style.display = "none";

  updateBulkButtonsText(false);
  updateAllCardsBulkState();
}
window.exitBulkSelectMode = exitBulkSelectMode;

function updateBulkButtonsText(isActive) {
  const exploreBtn = document.getElementById("exploreBulkSelectBtn");
  const itinBtn = document.getElementById("itineraryBulkSelectBtn");
  const todoBtn = document.getElementById("todoBulkSelectBtn");

  if (isActive) {
    if (exploreBtn) exploreBtn.innerHTML = "✕ Cancel Select";
    if (itinBtn) itinBtn.innerHTML = "✕ Cancel Select";
    if (todoBtn) todoBtn.innerHTML = "✕ Cancel Select";
  } else {
    if (exploreBtn) exploreBtn.innerHTML = "☑️ Bulk Select";
    if (itinBtn) itinBtn.innerHTML = "☑️ Bulk Select";
    if (todoBtn) todoBtn.innerHTML = "☑️ Bulk Select";
  }
}

function getVisibleBulkCardIds() {
  const ids = [];
  let containers = [];
  if (window.bulkSelectScope === "explore") {
    const grid = document.getElementById("exploreCardsGrid");
    if (grid) containers.push(grid);
  } else {
    const days = document.getElementById("daysContainer");
    const todo = document.getElementById("todoGrid");
    if (days) containers.push(days);
    if (todo) containers.push(todo);
  }

  containers.forEach(container => {
    const cards = container.querySelectorAll("[data-item-id]");
    cards.forEach(card => {
      if (card.offsetParent !== null) {
        const id = card.getAttribute("data-item-id");
        if (id && !ids.includes(id)) {
          ids.push(id);
        }
      }
    });
  });
  return ids;
}

function handleCardBulkClick(event, itemId) {
  if (!window.isBulkSelectMode) return;
  // Ignore clicks on interactive controls
  if (event.target.closest('a, button, select, input, textarea, .btn-booking-status, .badge-clickable, .btn-add-note, .btn-note-edit, .btn-note-delete')) {
    return;
  }
  event.preventDefault();
  const isNowSelected = !window.selectedBulkItemIds.has(itemId);
  toggleCardSelection(itemId, isNowSelected);
}
window.handleCardBulkClick = handleCardBulkClick;

function toggleCardSelection(itemId, forceState) {
  if (!window.selectedBulkItemIds) {
    window.selectedBulkItemIds = new Set();
  }

  const shouldSelect = typeof forceState === "boolean" 
    ? forceState 
    : !window.selectedBulkItemIds.has(itemId);

  if (shouldSelect) {
    window.selectedBulkItemIds.add(itemId);
  } else {
    window.selectedBulkItemIds.delete(itemId);
  }

  document.querySelectorAll(`[data-item-id="${itemId}"]`).forEach(card => {
    if (shouldSelect) {
      card.classList.add("bulk-card-selected");
    } else {
      card.classList.remove("bulk-card-selected");
    }
  });

  document.querySelectorAll(`input.card-bulk-checkbox[data-bulk-id="${itemId}"]`).forEach(cb => {
    cb.checked = shouldSelect;
  });

  updateBulkActionBarUI();
}
window.toggleCardSelection = toggleCardSelection;

function updateAllCardsBulkState() {
  const allCards = document.querySelectorAll("[data-item-id]");
  allCards.forEach(card => {
    const id = card.getAttribute("data-item-id");
    const isSelected = Boolean(window.isBulkSelectMode && window.selectedBulkItemIds && window.selectedBulkItemIds.has(id));
    if (isSelected) {
      card.classList.add("bulk-card-selected");
    } else {
      card.classList.remove("bulk-card-selected");
    }

    const cb = card.querySelector(`input.card-bulk-checkbox[data-bulk-id="${id}"]`);
    if (cb) {
      cb.checked = isSelected;
    }
  });
}

function updateBulkActionBarUI() {
  const bar = document.getElementById("bulkActionBar");
  if (!bar) return;

  const count = window.selectedBulkItemIds ? window.selectedBulkItemIds.size : 0;
  const visibleIds = getVisibleBulkCardIds();
  const totalVisible = visibleIds.length;

  const countEl = document.getElementById("bulkSelectCount");
  const totalVisibleEl = document.getElementById("bulkSelectTotalVisible");
  const deleteBtnCountEl = document.getElementById("bulkDeleteBtnCount");
  const deleteBtn = document.getElementById("bulkDeleteConfirmBtn");

  if (countEl) countEl.textContent = count;
  if (totalVisibleEl) totalVisibleEl.textContent = totalVisible;
  if (deleteBtnCountEl) deleteBtnCountEl.textContent = count;

  if (deleteBtn) {
    if (count > 0) {
      deleteBtn.disabled = false;
      deleteBtn.style.opacity = "1";
      deleteBtn.style.cursor = "pointer";
    } else {
      deleteBtn.disabled = true;
      deleteBtn.style.opacity = "0.5";
      deleteBtn.style.cursor = "not-allowed";
    }
  }
}

function bulkSelectAllVisible() {
  if (!window.selectedBulkItemIds) {
    window.selectedBulkItemIds = new Set();
  }
  const visibleIds = getVisibleBulkCardIds();
  visibleIds.forEach(id => {
    window.selectedBulkItemIds.add(id);
  });
  updateAllCardsBulkState();
  updateBulkActionBarUI();
}
window.bulkSelectAllVisible = bulkSelectAllVisible;

function bulkDeselectAll() {
  if (window.selectedBulkItemIds) {
    window.selectedBulkItemIds.clear();
  }
  updateAllCardsBulkState();
  updateBulkActionBarUI();
}
window.bulkDeselectAll = bulkDeselectAll;

async function confirmBulkDelete() {
  if (!window.selectedBulkItemIds || window.selectedBulkItemIds.size === 0) {
    alert("Please select at least one card to delete.");
    return;
  }

  const count = window.selectedBulkItemIds.size;
  const msg = count === 1
    ? "Are you sure you want to permanently delete this card from the itinerary?"
    : `Are you sure you want to permanently delete all ${count} selected cards from the itinerary? This action cannot be undone.`;

  if (!confirm(msg)) {
    return;
  }

  const deleteBtn = document.getElementById("bulkDeleteConfirmBtn");
  const originalText = deleteBtn ? deleteBtn.innerHTML : "";
  if (deleteBtn) {
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = `⏳ Deleting (${count})...`;
  }

  try {
    const itemIds = Array.from(window.selectedBulkItemIds);
    const res = await fetch(`/api/trips/${currentTripId}/items/bulk-delete`, {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json"
      },
      credentials: "include",
      body: JSON.stringify({ item_ids: itemIds })
    });

    if (res.ok) {
      exitBulkSelectMode();
      await refreshTrip();
    } else {
      const err = await res.json().catch(() => ({}));
      alert("Failed to delete selected cards: " + (err.detail || res.statusText));
      if (deleteBtn) {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
      }
    }
  } catch (err) {
    alert("Error executing bulk delete: " + err.message);
    if (deleteBtn) {
      deleteBtn.disabled = false;
      deleteBtn.innerHTML = originalText;
    }
  }
}
window.confirmBulkDelete = confirmBulkDelete;


// ==================== EXPLORE & DISCOVER IMPLEMENTATION ====================

function initExploreFilters() {
  const searchInput = document.getElementById("exploreSearchInput");
  const clearBtn = document.getElementById("clearExploreSearchBtn");
  const citySelect = document.getElementById("exploreCitySelect");
  const neighborhoodSelect = document.getElementById("exploreNeighborhoodSelect");
  const scheduleSelect = document.getElementById("exploreScheduleSelect");
  const freeToggle = document.getElementById("exploreFreeOnlyToggle");
  const resetBtn = document.getElementById("clearAllExploreFiltersBtn");

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      exploreSearchQuery = e.target.value.trim();
      if (clearBtn) clearBtn.style.display = exploreSearchQuery ? "block" : "none";
      clearTimeout(exploreDebounceTimer);
      exploreDebounceTimer = setTimeout(() => {
        renderExploreTab(false);
      }, 200);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      exploreSearchQuery = "";
      clearBtn.style.display = "none";
      renderExploreTab(false);
    });
  }

  if (citySelect) {
    citySelect.addEventListener("change", (e) => {
      exploreCity = e.target.value;
      renderExploreTab(false);
    });
  }

  if (neighborhoodSelect) {
    neighborhoodSelect.addEventListener("change", (e) => {
      exploreNeighborhood = e.target.value;
      renderExploreTab(false);
    });
  }

  if (scheduleSelect) {
    scheduleSelect.addEventListener("change", (e) => {
      exploreSchedule = e.target.value;
      renderExploreTab(false);
    });
  }

  if (freeToggle) {
    freeToggle.addEventListener("change", (e) => {
      exploreFreeOnly = e.target.checked;
      renderExploreTab(false);
    });
  }

  // Category Pills delegation
  const categoryPillsContainer = document.getElementById("exploreCategoryPills");
  if (categoryPillsContainer) {
    categoryPillsContainer.addEventListener("click", (e) => {
      const pill = e.target.closest(".cat-pill");
      if (!pill) return;
      categoryPillsContainer.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      exploreCategory = pill.dataset.cat || "all";
      renderExploreTab(false);
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      resetExploreFilters();
    });
  }
}

function resetExploreFilters() {
  exploreSearchQuery = "";
  exploreCategory = "all";
  exploreCity = "all";
  exploreNeighborhood = "all";
  exploreSchedule = "all";
  exploreFreeOnly = false;

  const searchInput = document.getElementById("exploreSearchInput");
  const clearBtn = document.getElementById("clearExploreSearchBtn");
  const citySelect = document.getElementById("exploreCitySelect");
  const neighborhoodSelect = document.getElementById("exploreNeighborhoodSelect");
  const scheduleSelect = document.getElementById("exploreScheduleSelect");
  const freeToggle = document.getElementById("exploreFreeOnlyToggle");
  const pills = document.querySelectorAll("#exploreCategoryPills .cat-pill");

  if (searchInput) searchInput.value = "";
  if (clearBtn) clearBtn.style.display = "none";
  if (citySelect) citySelect.value = "all";
  if (neighborhoodSelect) neighborhoodSelect.value = "all";
  if (scheduleSelect) scheduleSelect.value = "all";
  if (freeToggle) freeToggle.checked = false;

  pills.forEach(p => {
    if (p.dataset.cat === "all") p.classList.add("active");
    else p.classList.remove("active");
  });

  renderExploreTab(false);
}
window.resetExploreFilters = resetExploreFilters;

function renderExploreTab(populateDropdowns = true) {
  const grid = document.getElementById("exploreCardsGrid");
  const countEl = document.getElementById("exploreItemCount");
  const filterNote = document.getElementById("exploreActiveFilterNote");
  const resetBtn = document.getElementById("clearAllExploreFiltersBtn");
  const citySelect = document.getElementById("exploreCitySelect");
  const neighborhoodSelect = document.getElementById("exploreNeighborhoodSelect");

  if (!grid || !currentTripData) return;

  const allItems = currentTripData.all_items || [];
  const cities = currentTripData.cities || [];
  const availDates = currentTripData.available_dates || [];

  // Populate city & neighborhood dropdowns if requested
  if (populateDropdowns) {
    if (citySelect) {
      let cityOptions = `<option value="all" ${exploreCity === "all" ? "selected" : ""}>🏙️ All Cities</option>`;
      cities.forEach(c => {
        cityOptions += `<option value="${c.id}" ${exploreCity === c.id ? "selected" : ""}>🏙️ ${escapeHtml(c.city_name)}</option>`;
      });
      citySelect.innerHTML = cityOptions;
    }

    if (neighborhoodSelect) {
      const distinctNeighborhoods = Array.from(new Set(
        allItems.map(it => it.neighborhood).filter(n => n && n.trim().length > 0)
      )).sort();
      let nOptions = `<option value="all" ${exploreNeighborhood === "all" ? "selected" : ""}>📍 All Neighborhoods</option>`;
      distinctNeighborhoods.forEach(n => {
        nOptions += `<option value="${escapeHtml(n)}" ${exploreNeighborhood.toLowerCase() === n.toLowerCase() ? "selected" : ""}>📍 ${escapeHtml(n)}</option>`;
      });
      neighborhoodSelect.innerHTML = nOptions;
    }
  }

  // Filter items
  let filtered = allItems.filter(item => {
    // 1. Category
    if (exploreCategory !== "all") {
      if ((item.category || "").toLowerCase() !== exploreCategory.toLowerCase()) {
        return false;
      }
    }

    // 2. City
    if (exploreCity !== "all") {
      const matchId = item.city_segment_id === exploreCity;
      const matchName = (item.city_name || "").toLowerCase() === exploreCity.toLowerCase();
      if (!matchId && !matchName) return false;
    }

    // 3. Neighborhood
    if (exploreNeighborhood !== "all") {
      if ((item.neighborhood || "").toLowerCase() !== exploreNeighborhood.toLowerCase()) {
        return false;
      }
    }

    // 4. Schedule
    if (exploreSchedule === "todo") {
      if (item.assigned_date && item.assigned_date !== "todo") return false;
    } else if (exploreSchedule === "scheduled") {
      if (!item.assigned_date || item.assigned_date === "todo") return false;
    }

    // 5. Free only
    if (exploreFreeOnly) {
      const isFree = item.is_free || (item.cost && item.cost.toLowerCase().includes("free"));
      if (!isFree) return false;
    }

    // 6. Search Query
    if (exploreSearchQuery) {
      const q = exploreSearchQuery.toLowerCase();
      const text = [
        item.title || "",
        item.description || "",
        item.neighborhood || "",
        item.city_name || "",
        item.highlight || "",
        item.cost || "",
        item.source_platform || "",
        item.category || ""
      ].join(" ").toLowerCase();
      if (!text.includes(q)) return false;
    }

    return true;
  });

  if (countEl) countEl.textContent = filtered.length;

  // Active filter indicator
  const hasActiveFilters = Boolean(
    exploreCategory !== "all" ||
    exploreCity !== "all" ||
    exploreNeighborhood !== "all" ||
    exploreSchedule !== "all" ||
    exploreFreeOnly ||
    exploreSearchQuery
  );

  if (resetBtn) resetBtn.style.display = hasActiveFilters ? "inline-block" : "none";
  if (filterNote) {
    if (hasActiveFilters) {
      const activeDesc = [];
      if (exploreCategory !== "all") activeDesc.push(`Category: ${exploreCategory}`);
      if (exploreCity !== "all") {
        const foundCity = cities.find(c => c.id === exploreCity);
        activeDesc.push(`City: ${foundCity ? foundCity.city_name : exploreCity}`);
      }
      if (exploreNeighborhood !== "all") activeDesc.push(`Neighborhood: ${exploreNeighborhood}`);
      if (exploreSchedule === "todo") activeDesc.push("Bucket List Only");
      if (exploreSchedule === "scheduled") activeDesc.push("Scheduled Only");
      if (exploreFreeOnly) activeDesc.push("Free Only");
      if (exploreSearchQuery) activeDesc.push(`"${exploreSearchQuery}"`);

      filterNote.textContent = `(Filters: ${activeDesc.join(", ")})`;
      filterNote.style.display = "inline";
    } else {
      filterNote.style.display = "none";
    }
  }

  // Render cards or empty state
  if (filtered.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3.5rem 1.5rem; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-md); border: 1px dashed var(--border);">
        <div style="font-size: 2.2rem; margin-bottom: 0.6rem;">🔍</div>
        <h3 style="color: var(--text-main); font-size: 1.15rem; margin-bottom: 0.4rem;">No matching discoveries found</h3>
        <p style="font-size: 0.88rem; max-width: 480px; margin: 0 auto 1.2rem auto;">
          Try adjusting or clearing your filters, or scout live events & attractions in the <strong>🌐 City Event Scout</strong> tab.
        </p>
        <button class="btn btn-secondary" onclick="resetExploreFilters()">✕ Clear All Filters</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(item => renderExploreCard(item, availDates)).join("");
  attachExploreCardEvents();
  if (window.isBulkSelectMode) {
    updateBulkActionBarUI();
  }
}

function renderExploreCard(item, availableDates) {
  const author = item.added_by || { name: "Traveler", avatar_color: "#38bdf8" };
  const transit = item.transit || {};
  const categories = (currentTripData && currentTripData.categories) || {};
  const catConfig = categories[item.category] || {
    icon: "✨",
    label: item.category ? (item.category.charAt(0).toUpperCase() + item.category.slice(1)) : "General"
  };

  const hasDirectUrl = Boolean(item.url && item.url.trim() !== "");
  const safeDirectUrl = hasDirectUrl ? sanitizeUrl(item.url) : "";
  const targetUrl = safeDirectUrl
    ? safeDirectUrl
    : `https://www.google.com/search?q=${encodeURIComponent(item.title + ' ' + (item.city_name || ''))}`;

  let mapsUrl = "";
  if (item.lat && item.lon) {
    mapsUrl = `https://www.google.com/maps/search/?api=1&query=${item.lat},${item.lon}`;
  } else {
    mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.title + ' ' + (item.address || item.city_name || ''))}`;
  }

  const matchedStay = getLodgingForDate(item.assigned_date, item.city_id || item.city_segment_id);
  const stayName = item.transit?.stay_name || matchedStay?.name || "Hotel";
  const directionsUrl = getDirectionsUrlFromLodging(item);

  const isFree = Boolean(item.is_free || (item.cost && item.cost.toLowerCase().includes("free")));
  const costBadge = isFree
    ? `<span class="badge badge-curated badge-clickable" data-filter-type="free" title="Click to filter Free Only">🎟️ FREE</span>`
    : `<span class="badge badge-cost" title="Cost: ${escapeHtml(item.cost || 'Paid')}">💰 ${escapeHtml(item.cost || 'Paid')}</span>`;

  const isScheduled = Boolean(item.assigned_date && item.assigned_date !== "todo");
  const scheduleBadge = isScheduled
    ? `<span class="badge badge-scheduled badge-clickable" data-filter-type="schedule" data-filter-value="scheduled" title="Click to filter Scheduled items">📅 Day: ${escapeHtml(item.assigned_date)}</span>`
    : `<span class="badge badge-todo badge-clickable" data-filter-type="schedule" data-filter-value="todo" title="Click to filter Bucket List items">📋 In Bucket List</span>`;

  const catBadge = `<span class="badge badge-clickable" data-filter-type="cat" data-filter-value="${escapeHtml(item.category || '')}" style="background:rgba(56,189,248,0.12); color:#38bdf8; border:1px solid rgba(56,189,248,0.28);" title="Click to filter by ${escapeHtml(catConfig.label)}">${catConfig.icon} ${escapeHtml(catConfig.label)}</span>`;

  const cityBadge = item.city_name
    ? `<span class="badge badge-city badge-clickable" data-filter-type="city" data-filter-value="${escapeHtml(item.city_segment_id || item.city_name)}" title="Click to filter by ${escapeHtml(item.city_name)}">🏙️ ${escapeHtml(item.city_name)}</span>`
    : '';

  const neighborhoodBadge = item.neighborhood
    ? `<span class="badge badge-clickable" data-filter-type="neighborhood" data-filter-value="${escapeHtml(item.neighborhood)}" style="background:rgba(168,85,247,0.12); color:#c084fc; border:1px solid rgba(168,85,247,0.28);" title="Click to filter by neighborhood ${escapeHtml(item.neighborhood)}">📍 ${escapeHtml(item.neighborhood)}</span>`
    : '';

  let sourceIcon = "🌐";
  if (/eventbrite/i.test(item.source_platform)) sourceIcon = "🎟️";
  else if (/songkick/i.test(item.source_platform)) sourceIcon = "🎸";
  else if (/dice/i.test(item.source_platform)) sourceIcon = "🎲";
  else if (/ticketmaster/i.test(item.source_platform)) sourceIcon = "🎫";
  else if (/venue/i.test(item.source_platform)) sourceIcon = "🏛️";
  else if (/yelp/i.test(item.source_platform)) sourceIcon = "⭐";
  else if (/eater/i.test(item.source_platform)) sourceIcon = "🍴";
  else if (/michelin/i.test(item.source_platform)) sourceIcon = "⭐";
  else if (/brewery|beer/i.test(item.source_platform)) sourceIcon = "🍺";
  else if (/cocktail|speakeasy/i.test(item.source_platform)) sourceIcon = "🍸";
  else if (/magazine/i.test(item.source_platform)) sourceIcon = "📰";
  else if (/reddit/i.test(item.source_platform)) sourceIcon = "💬";
  else if (/tiktok/i.test(item.source_platform)) sourceIcon = "🎬";

  const sourceBadge = item.source_platform
    ? `<span class="badge badge-web" title="Scout Source">${sourceIcon} ${escapeHtml(item.source_platform)}</span>`
    : `<span class="badge badge-curated" title="Curated Essential">🏛️ Curated</span>`;

  let transitBadge = '';
  if (transit && transit.miles) {
    if (transit.is_walkable) {
      transitBadge = `<span class="badge badge-transit" style="background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid rgba(34,197,94,0.3);" title="Walk from ${escapeHtml(transit.stay_name || 'Stay')}: ${escapeHtml(transit.walk_time || '')}">🚶 ${transit.miles} mi (${escapeHtml(transit.walk_time || '')})</span>`;
    } else {
      transitBadge = `<span class="badge badge-transit" style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3);" title="Transit from ${escapeHtml(transit.stay_name || 'Stay')}: ${escapeHtml(transit.transit_line || 'Transit')}">🚌 ${escapeHtml(transit.transit_time || '')} (~${transit.miles} mi)</span>`;
    }
  }

  const sourceLabel = item.source_platform ? escapeHtml(item.source_platform) : "Website";
  const isSelected = Boolean(window.isBulkSelectMode && window.selectedBulkItemIds && window.selectedBulkItemIds.has(item.id));

  return `
    <div class="card ${isSelected ? 'bulk-card-selected' : ''}" id="explore-card-${item.id}" data-item-id="${item.id}" onclick="handleCardBulkClick(event, '${item.id}')">
      <div class="card-bulk-checkbox-wrapper" onclick="event.stopPropagation()">
        <input type="checkbox" class="card-bulk-checkbox" id="bulk-cb-${item.id}" data-bulk-id="${item.id}" ${isSelected ? 'checked' : ''} onchange="toggleCardSelection('${item.id}', this.checked)">
      </div>
      <div>
        <!-- Card Top & Clickable Filter Badges -->
        <div class="card-top">
          <div class="card-badges">
            ${catBadge}
            ${cityBadge}
            ${neighborhoodBadge}
            ${costBadge}
            ${scheduleBadge}
            ${transitBadge}
            ${sourceBadge}
          </div>
        </div>

        <h3 class="card-title" style="margin-top:0.6rem; font-size:1.05rem; line-height:1.35;">
          <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--text-main); text-decoration:none;" onmouseover="this.style.color='#38bdf8'" onmouseout="this.style.color='var(--text-main)'">
            ${escapeHtml(item.title)} ↗
          </a>
        </h3>

        <div class="card-meta" style="font-size:0.8rem; color:var(--text-muted); margin:0.35rem 0 0.65rem 0;">
          <span>📍 ${escapeHtml(item.neighborhood || item.city_name || 'Location')}</span>
          ${item.time_info ? ` &bull; <span style="color:var(--text-dim);">${escapeHtml(item.time_info)}</span>` : ''}
        </div>

        <!-- Hotel Transit & Bus Information Box -->
        ${buildCardTransitBox(transit)}


        ${item.description ? `
          <p class="card-desc" style="font-size:0.84rem; color:#cbd5e1; line-height:1.45; margin-bottom:0.65rem;">
            ${escapeHtml(item.description)}
          </p>
        ` : ''}

        ${item.highlight ? `
          <div style="background:rgba(251,191,36,0.08); border-left:3px solid #fbbf24; padding:0.4rem 0.65rem; border-radius:0 6px 6px 0; font-size:0.79rem; color:#fef08a; margin-bottom:0.75rem;">
            <strong>Key Highlight:</strong> ${escapeHtml(item.highlight)}
          </div>
        ` : ''}

        <!-- Personal Note Section -->
        <div class="card-note-box" id="explore-note-box-${item.id}" style="margin-top:0.4rem;">
          ${item.personal_note ? `
            <div class="note-content-display">
              <div class="note-meta-line">
                <span class="note-author">📝 Note by <strong>${escapeHtml(item.note_author?.name || 'Traveler')}</strong> <span style="font-size:0.7rem; color:#94a3b8;">(${escapeHtml(item.note_author?.email || '')})</span>:</span>
                <span class="note-date">${escapeHtml(item.note_date || '')}</span>
              </div>
              <div class="note-text">&ldquo;${escapeHtml(item.personal_note)}&rdquo;</div>
              <div style="margin-top:0.35rem; display:flex; gap:0.6rem; align-items:center;">
                <button type="button" class="btn-note-edit" onclick='editCardNote("${item.id}", ${JSON.stringify(item.personal_note).replace(/'/g, "&apos;")})'>✏️ Edit Note</button>
                <button type="button" class="btn-note-delete" onclick="deleteCardNote('${item.id}')">🗑️ Remove</button>
              </div>
            </div>
          ` : `
            <button type="button" class="btn-add-note" onclick="openAddNotePrompt('${item.id}')">
              📝 + Add Personal Note
            </button>
          `}
        </div>
      </div>

      <!-- Card Footer -->
      <div class="card-footer" style="margin-top:1rem; padding-top:0.75rem; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.6rem;">
        <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
          <a href="${escapeHtml(directionsUrl)}" target="_blank" rel="noopener noreferrer" style="color:#38bdf8; font-size:0.8rem; text-decoration:none; font-weight:600;" title="Open Google Maps directions from ${escapeHtml(stayName)} to ${escapeHtml(item.title)} with origin and destination pre-populated">
            🧭 Directions from Hotel ↗
          </a>
          <a href="${escapeHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer" style="color:#94a3b8; font-size:0.8rem; text-decoration:none;" title="Open venue location pin in Google Maps">
            📍 Map Pin
          </a>
          ${safeDirectUrl ? `
            <a href="${escapeHtml(safeDirectUrl)}" target="_blank" rel="noopener noreferrer" style="color:#a78bfa; font-size:0.8rem; text-decoration:none; font-weight:500;">
              🌐 ${sourceLabel} &rarr;
            </a>
          ` : `
            <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" style="color:#94a3b8; font-size:0.8rem; text-decoration:none;">
              🔍 Info &rarr;
            </a>
          `}
        </div>

        <div style="display:flex; align-items:center; gap:0.5rem;">
          <div class="card-author-tag" title="Added by ${escapeHtml(author.name)}" style="display:flex; align-items:center; gap:0.3rem; font-size:0.74rem; color:var(--text-muted);">
            <span class="author-dot" style="background:${author.avatar_color || '#38bdf8'}; width:18px; height:18px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; color:#fff; font-size:0.65rem; font-weight:700;">
              ${author.name.slice(0, 2).toUpperCase()}
            </span>
            <span>${escapeHtml(author.name.split(" ")[0])}</span>
          </div>

          <select class="card-date-select" data-item-id="${item.id}" style="background:var(--bg-main); border:1px solid var(--border); color:var(--text-main); padding:0.25rem 0.5rem; border-radius:var(--radius-sm); font-size:0.78rem;">
            <option value="todo" ${item.assigned_date === 'todo' || !item.assigned_date ? 'selected' : ''}>📋 Bucket List</option>
            ${availableDates.map(d => `
              <option value="${d}" ${item.assigned_date === d ? 'selected' : ''}>📅 ${d}</option>
            `).join("")}
          </select>

          <button onclick="deleteItem('${item.id}')" style="background:none; border:none; color:#f43f5e; cursor:pointer; font-size:1.1rem; padding:0 0.25rem; line-height:1;" title="Delete discovery">&times;</button>
        </div>
      </div>
    </div>
  `;
}

function attachExploreCardEvents() {
  const grid = document.getElementById("exploreCardsGrid");
  if (!grid) return;

  // 1. Clickable Tag Badges delegation
  grid.querySelectorAll(".badge-clickable").forEach(badge => {
    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      const filterType = badge.dataset.filterType;
      const filterVal = badge.dataset.filterValue;

      if (filterType === "cat") {
        exploreCategory = filterVal;
        const pills = document.querySelectorAll("#exploreCategoryPills .cat-pill");
        pills.forEach(p => {
          if (p.dataset.cat === filterVal) p.classList.add("active");
          else p.classList.remove("active");
        });
      } else if (filterType === "city") {
        exploreCity = filterVal;
        const citySelect = document.getElementById("exploreCitySelect");
        if (citySelect) citySelect.value = filterVal;
      } else if (filterType === "neighborhood") {
        exploreNeighborhood = filterVal;
        const neighborhoodSelect = document.getElementById("exploreNeighborhoodSelect");
        if (neighborhoodSelect) neighborhoodSelect.value = filterVal;
      } else if (filterType === "free") {
        exploreFreeOnly = true;
        const freeToggle = document.getElementById("exploreFreeOnlyToggle");
        if (freeToggle) freeToggle.checked = true;
      } else if (filterType === "schedule") {
        exploreSchedule = filterVal;
        const scheduleSelect = document.getElementById("exploreScheduleSelect");
        if (scheduleSelect) scheduleSelect.value = filterVal;
      }

      renderExploreTab(false);
    });
  });

  // 2. Card date dropdown change handler
  grid.querySelectorAll(".card-date-select").forEach(sel => {
    sel.addEventListener("change", async (e) => {
      const itemId = e.target.dataset.itemId;
      const newDate = e.target.value;
      try {
        await fetch(`/api/trips/${currentTripId}/items/${itemId}`, {
          method: "PUT",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({ assigned_date: newDate })
        });
        await refreshTrip();
      } catch (err) {
        alert("Failed to assign date: " + err.message);
      }
    });
  });
}

// 8. Modals Management
function initModals() {
  const addCityModal = document.getElementById("addCityModal");
  const openAddCityBtn = document.getElementById("openAddCityBtn");
  const closeAddCityBtn = document.getElementById("closeAddCityBtn");
  const cancelAddCityBtn = document.getElementById("cancelAddCityBtn");
  const addCityForm = document.getElementById("addCityForm");

  if (openAddCityBtn) {
    openAddCityBtn.addEventListener("click", () => {
      if (!currentUser) {
        alert("🔒 Please sign in with your Google or Gmail account before adding destination cities.");
        if (window.openLogin) window.openLogin();
        return;
      }
      addCityModal.style.display = "flex";
    });
  }
  if (closeAddCityBtn) closeAddCityBtn.addEventListener("click", () => addCityModal.style.display = "none");
  if (cancelAddCityBtn) cancelAddCityBtn.addEventListener("click", () => addCityModal.style.display = "none");

  if (addCityForm) {
    addCityForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!currentUser) {
        alert("🔒 Please sign in with your Google or Gmail account before adding destination cities.");
        if (window.openLogin) window.openLogin();
        return;
      }

      const cityName = document.getElementById("newCityName").value.trim();
      const country = document.getElementById("newCityCountry").value.trim() || "";
      const startDate = document.getElementById("newCityStart").value;
      const endDate = document.getElementById("newCityEnd").value;
      const hotelName = document.getElementById("newCityHotel").value.trim();
      const hotelAddress = document.getElementById("newCityAddress").value.trim();

      if (!cityName || !startDate || !endDate) {
        alert("Please specify the city name, arrival date, and departure date.");
        return;
      }

      const payload = {
        city_name: cityName,
        country: country,
        start_date: startDate,
        end_date: endDate,
        hotel_name: hotelName || `${cityName} Central Hotel`,
        hotel_address: hotelAddress || (country ? `${cityName}, ${country}` : cityName),
      };

      try {
        const targetTripId = currentTripId || "null";
        const res = await fetch(`/api/trips/${targetTripId}/cities`, {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          addCityModal.style.display = "none";
          addCityForm.reset();
          if (data.trip_id && (!currentTripId || currentTripId !== data.trip_id)) {
            currentTripId = data.trip_id;
            await loadTripsDropdown();
          }
          await refreshTrip();
        } else {
          alert("Failed to add city: " + (data.detail || res.statusText || "Please check your inputs and try again."));
        }
      } catch (err) {
        alert("Error adding city: " + err.message);
      }
    });
  }

  // Stay Modal
  const addStayModal = document.getElementById("addStayModal");
  const closeAddStayBtn = document.getElementById("closeAddStayBtn");
  const cancelAddStayBtn = document.getElementById("cancelAddStayBtn");
  const addStayForm = document.getElementById("addStayForm");

  if (closeAddStayBtn) closeAddStayBtn.addEventListener("click", () => addStayModal.style.display = "none");
  if (cancelAddStayBtn) cancelAddStayBtn.addEventListener("click", () => addStayModal.style.display = "none");

  if (addStayForm) {
    addStayForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const cityId = document.getElementById("stayCityId").value;
      const payload = {
        name: document.getElementById("stayNameInput").value.trim(),
        address: document.getElementById("stayAddressInput").value.trim(),
        start_date: document.getElementById("stayStartInput").value,
        end_date: document.getElementById("stayEndInput").value,
        notes: document.getElementById("stayNotesInput").value.trim(),
      };

      try {
        const res = await fetch(`/api/trips/${currentTripId}/cities/${cityId}/stays`, {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          addStayModal.style.display = "none";
          addStayForm.reset();
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to add stay: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error adding stay: " + err.message);
      }
    });
  }

  // Edit Stay Modal
  const editStayModal = document.getElementById("editStayModal");
  const closeEditStayBtn = document.getElementById("closeEditStayBtn");
  const cancelEditStayBtn = document.getElementById("cancelEditStayBtn");
  const editStayForm = document.getElementById("editStayForm");

  if (closeEditStayBtn) closeEditStayBtn.addEventListener("click", () => editStayModal.style.display = "none");
  if (cancelEditStayBtn) cancelEditStayBtn.addEventListener("click", () => editStayModal.style.display = "none");

  if (editStayForm) {
    editStayForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const stayId = document.getElementById("editStayId").value;
      const payload = {
        name: document.getElementById("editStayNameInput").value.trim(),
        address: document.getElementById("editStayAddressInput").value.trim(),
        start_date: document.getElementById("editStayStartInput").value,
        end_date: document.getElementById("editStayEndInput").value,
        notes: document.getElementById("editStayNotesInput").value.trim()
      };

      try {
        const res = await fetch(`/api/trips/${currentTripId}/stays/${stayId}`, {
          method: "PUT",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          editStayModal.style.display = "none";
          editStayForm.reset();
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to update hotel details: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error updating hotel: " + err.message);
      }
    });
  }

  // Invite Modal
  const inviteModal = document.getElementById("inviteModal");
  const openInviteBtn = document.getElementById("openInviteBtn");
  const closeInviteBtn = document.getElementById("closeInviteModalBtn");
  const cancelInviteBtn = document.getElementById("cancelInviteBtn");
  const inviteForm = document.getElementById("inviteForm");

  if (openInviteBtn) openInviteBtn.addEventListener("click", () => inviteModal.style.display = "flex");
  if (closeInviteBtn) closeInviteBtn.addEventListener("click", () => inviteModal.style.display = "none");
  if (cancelInviteBtn) cancelInviteBtn.addEventListener("click", () => inviteModal.style.display = "none");

  if (inviteForm) {
    inviteForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        email: document.getElementById("inviteEmail").value.trim(),
        name: document.getElementById("inviteName").value.trim(),
        role: document.getElementById("inviteRole").value,
      };
      try {
        const res = await fetch(`/api/trips/${currentTripId}/collaborators`, {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          inviteModal.style.display = "none";
          inviteForm.reset();
          alert(`Invitation sent to ${payload.email}! They can now view and edit this itinerary.`);
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to invite collaborator: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error inviting collaborator: " + err.message);
      }
    });
  }

  // Edit Trip Modal
  const editTripModal = document.getElementById("editTripModal");
  const openEditTripBtn = document.getElementById("openEditTripBtn");
  const closeEditTripBtn = document.getElementById("closeEditTripBtn");
  const cancelEditTripBtn = document.getElementById("cancelEditTripBtn");
  const editTripForm = document.getElementById("editTripForm");

  if (openEditTripBtn) {
    openEditTripBtn.addEventListener("click", () => {
      if (currentTripData && currentTripData.trip) {
        document.getElementById("editTripTitleInput").value = currentTripData.trip.title || "";
        document.getElementById("editTripDescInput").value = currentTripData.trip.description || "";
      }
      editTripModal.style.display = "flex";
    });
  }
  if (closeEditTripBtn) closeEditTripBtn.addEventListener("click", () => editTripModal.style.display = "none");
  if (cancelEditTripBtn) cancelEditTripBtn.addEventListener("click", () => editTripModal.style.display = "none");

  if (editTripForm) {
    editTripForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = document.getElementById("editTripTitleInput").value.trim();
      const description = document.getElementById("editTripDescInput").value.trim();
      try {
        const res = await fetch(`/api/trips/${currentTripId}`, {
          method: "PUT",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({ title, description })
        });
        if (res.ok) {
          editTripModal.style.display = "none";
          await loadTripsDropdown();
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to update trip details: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error updating trip: " + err.message);
      }
    });
  }

  const deleteTripBtn = document.getElementById("deleteTripBtn");
  if (deleteTripBtn) {
    deleteTripBtn.addEventListener("click", async () => {
      if (!currentTripId || !currentTripData || !currentTripData.trip) return;
      const tripTitle = currentTripData.trip.title || "this itinerary";
      if (!confirm(`⚠️ Are you sure you want to permanently delete "${tripTitle}"?\n\nThis will remove all cities, accommodations, notes, and scheduled stops in this trip. This action cannot be undone.`)) {
        return;
      }
      try {
        const res = await fetch(`/api/trips/${currentTripId}`, {
          method: "DELETE",
          headers: getAuthHeaders(),
          credentials: "include"
        });
        if (res.ok) {
          const data = await res.json();
          editTripModal.style.display = "none";
          alert(`"${tripTitle}" has been permanently deleted.`);
          currentTripId = data.next_trip_id || null;
          window.location.reload();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to delete trip: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error deleting trip: " + err.message);
      }
    });
  }

  const headerDeleteTripBtn = document.getElementById("headerDeleteTripBtn");
  if (headerDeleteTripBtn) {
    headerDeleteTripBtn.addEventListener("click", () => {
      if (deleteTripBtn) {
        deleteTripBtn.click();
      }
    });
  }

  // Create Trip Modal
  const createTripModal = document.getElementById("createTripModal");
  const openCreateTripBtn = document.getElementById("openCreateTripBtn");
  const closeCreateTripBtn = document.getElementById("closeCreateTripBtn");
  const cancelCreateTripBtn = document.getElementById("cancelCreateTripBtn");
  const createTripForm = document.getElementById("createTripForm");

  if (openCreateTripBtn) openCreateTripBtn.addEventListener("click", () => createTripModal.style.display = "flex");
  if (closeCreateTripBtn) closeCreateTripBtn.addEventListener("click", () => createTripModal.style.display = "none");
  if (cancelCreateTripBtn) cancelCreateTripBtn.addEventListener("click", () => createTripModal.style.display = "none");

  if (createTripForm) {
    createTripForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = document.getElementById("newTripTitle").value.trim();
      const first_city_name = document.getElementById("newTripCity").value.trim();
      const start_date = document.getElementById("newTripStart").value;
      const end_date = document.getElementById("newTripEnd").value;
      let hotel_name = document.getElementById("newTripHotel")?.value.trim() || "";
      const hotel_address = document.getElementById("newTripHotelAddress")?.value.trim() || "";

      // If user provided an address but no lodging name, default to friendly label
      if (!hotel_name) {
        if (hotel_address) {
          hotel_name = "Friend's Home / Lodging";
        } else {
          hotel_name = `${first_city_name} Lodging`;
        }
      }
      const effective_address = hotel_address || hotel_name;

      try {
        const res = await fetch("/api/trips", {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({
            title,
            first_city_name,
            start_date,
            end_date,
            hotel_name,
            hotel_address: effective_address,
            address: effective_address
          })
        });
        if (res.ok) {
          const data = await res.json();
          createTripModal.style.display = "none";
          createTripForm.reset();
          currentTripId = data.trip_id;
          await loadTripsDropdown();
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to create new trip: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error creating trip: " + err.message);
      }
    });
  }

  // Help Guide Modal
  const helpModal = document.getElementById("helpModal");
  const openHelpBtn = document.getElementById("openHelpBtn");
  const closeHelpModalBtn = document.getElementById("closeHelpModalBtn");
  const closeHelpModalBtn2 = document.getElementById("closeHelpModalBtn2");

  if (openHelpBtn) openHelpBtn.addEventListener("click", () => helpModal.style.display = "flex");
  if (closeHelpModalBtn) closeHelpModalBtn.addEventListener("click", () => helpModal.style.display = "none");
  if (closeHelpModalBtn2) closeHelpModalBtn2.addEventListener("click", () => helpModal.style.display = "none");

  // Print & Export Modal
  const printModal = document.getElementById("printModal");
  const openPrintModalBtn = document.getElementById("openPrintModalBtn");
  const openPrintHeaderBtn = document.getElementById("openPrintHeaderBtn");
  const closePrintModalBtn = document.getElementById("closePrintModalBtn");
  const closePrintModalBtn2 = document.getElementById("closePrintModalBtn2");

  const printDateModeSelect = document.getElementById("printDateModeSelect");
  const printSingleDateGroup = document.getElementById("printSingleDateGroup");
  const printSingleDateSelect = document.getElementById("printSingleDateSelect");
  const printRangeDateGroup = document.getElementById("printRangeDateGroup");
  const printRangeStart = document.getElementById("printRangeStart");
  const printRangeEnd = document.getElementById("printRangeEnd");
  const printIncludeTodoCheck = document.getElementById("printIncludeTodoCheck");
  const printFormattedTextarea = document.getElementById("printFormattedTextarea");

  function openPrintModal() {
    if (!currentTripData) return;
    const avail = currentTripData.available_dates || [];
    if (printSingleDateSelect) {
      printSingleDateSelect.innerHTML = avail.map(d => `<option value="${d}">📅 ${d}</option>`).join("");
    }
    if (avail.length > 0) {
      if (printRangeStart) printRangeStart.value = avail[0];
      if (printRangeEnd) printRangeEnd.value = avail[avail.length - 1];
    }
    updatePrintPreview();
    if (printModal) printModal.style.display = "flex";
  }

  if (openPrintModalBtn) openPrintModalBtn.addEventListener("click", openPrintModal);
  if (openPrintHeaderBtn) openPrintHeaderBtn.addEventListener("click", openPrintModal);
  if (closePrintModalBtn) closePrintModalBtn.addEventListener("click", () => printModal.style.display = "none");
  if (closePrintModalBtn2) closePrintModalBtn2.addEventListener("click", () => printModal.style.display = "none");

  if (printDateModeSelect) {
    printDateModeSelect.addEventListener("change", () => {
      const val = printDateModeSelect.value;
      if (val === "single") {
        if (printSingleDateGroup) printSingleDateGroup.style.display = "block";
        if (printRangeDateGroup) printRangeDateGroup.style.display = "none";
      } else if (val === "range") {
        if (printSingleDateGroup) printSingleDateGroup.style.display = "none";
        if (printRangeDateGroup) printRangeDateGroup.style.display = "grid";
      } else {
        if (printSingleDateGroup) printSingleDateGroup.style.display = "none";
        if (printRangeDateGroup) printRangeDateGroup.style.display = "none";
      }
      updatePrintPreview();
    });
  }

  [printSingleDateSelect, printRangeStart, printRangeEnd, printIncludeTodoCheck].forEach(el => {
    if (el) el.addEventListener("change", updatePrintPreview);
  });

  function getPrintQueryParams(autoprint = false) {
    const mode = printDateModeSelect ? printDateModeSelect.value : "all";
    const includeTodo = printIncludeTodoCheck ? printIncludeTodoCheck.checked : true;
    const params = new URLSearchParams();
    if (mode === "single" && printSingleDateSelect) {
      params.set("date", printSingleDateSelect.value);
    } else if (mode === "range" && printRangeStart && printRangeEnd) {
      params.set("start_date", printRangeStart.value);
      params.set("end_date", printRangeEnd.value);
    } else {
      params.set("date", "all");
    }
    params.set("include_todo", includeTodo ? "1" : "0");
    if (autoprint) params.set("autoprint", "1");
    return params.toString();
  }

  // Action: Print / PDF
  const triggerPrintPdfBtn = document.getElementById("triggerPrintPdfBtn");
  if (triggerPrintPdfBtn) {
    triggerPrintPdfBtn.addEventListener("click", () => {
      if (!currentTripId) return;
      const url = `/api/trips/${currentTripId}/print?${getPrintQueryParams(true)}`;
      window.open(url, "_blank");
    });
  }

  // Action: Open in new tab
  const triggerOpenPrintTabBtn = document.getElementById("triggerOpenPrintTabBtn");
  if (triggerOpenPrintTabBtn) {
    triggerOpenPrintTabBtn.addEventListener("click", () => {
      if (!currentTripId) return;
      const url = `/api/trips/${currentTripId}/print?${getPrintQueryParams(false)}`;
      window.open(url, "_blank");
    });
  }

  // Action: Email Share
  const triggerEmailShareBtn = document.getElementById("triggerEmailShareBtn");
  if (triggerEmailShareBtn) {
    triggerEmailShareBtn.addEventListener("click", () => {
      const emailContent = generateFormattedItineraryText("email");
      const subject = `Travel Scout Itinerary: ${currentTripData.trip.title}`;
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(emailContent)}`;
    });
  }

  // Action: SMS Share
  const triggerSmsShareBtn = document.getElementById("triggerSmsShareBtn");
  if (triggerSmsShareBtn) {
    triggerSmsShareBtn.addEventListener("click", () => {
      const smsContent = generateFormattedItineraryText("sms");
      window.location.href = `sms:?body=${encodeURIComponent(smsContent)}`;
    });
  }

  // Clipboard copies
  const copyEmailTextBtn = document.getElementById("copyEmailTextBtn");
  if (copyEmailTextBtn) {
    copyEmailTextBtn.addEventListener("click", async () => {
      const text = generateFormattedItineraryText("email");
      await navigator.clipboard.writeText(text);
      copyEmailTextBtn.textContent = "✓ Copied Email Text!";
      setTimeout(() => copyEmailTextBtn.textContent = "📋 Copy Email Text", 2000);
    });
  }

  const copySmsTextBtn = document.getElementById("copySmsTextBtn");
  if (copySmsTextBtn) {
    copySmsTextBtn.addEventListener("click", async () => {
      const text = generateFormattedItineraryText("sms");
      await navigator.clipboard.writeText(text);
      copySmsTextBtn.textContent = "✓ Copied SMS Text!";
      setTimeout(() => copySmsTextBtn.textContent = "📋 Copy SMS Text", 2000);
    });
  }

  function updatePrintPreview() {
    if (!printFormattedTextarea) return;
    printFormattedTextarea.value = generateFormattedItineraryText("email");
  }
}

function generateFormattedItineraryText(mode = "email") {
  if (!currentTripData || !currentTripData.trip) return "";

  const trip = currentTripData.trip;
  const cities = currentTripData.cities || [];
  const exportMode = document.getElementById("printDateModeSelect")?.value || "all";
  const singleDate = document.getElementById("printSingleDateSelect")?.value;
  const rangeStart = document.getElementById("printRangeStart")?.value;
  const rangeEnd = document.getElementById("printRangeEnd")?.value;
  const includeTodo = document.getElementById("printIncludeTodoCheck")?.checked ?? true;

  // Filter days
  let filteredDays = currentTripData.itinerary?.days || [];
  if (exportMode === "single" && singleDate) {
    filteredDays = filteredDays.filter(d => d.date === singleDate);
  } else if (exportMode === "range" && rangeStart && rangeEnd) {
    filteredDays = filteredDays.filter(d => d.date >= rangeStart && d.date <= rangeEnd);
  }

  let lines = [];

  if (mode === "sms") {
    lines.push(`🌍 ${trip.title.toUpperCase()}`);
    if (exportMode === "single") lines.push(`📅 Date: ${singleDate}`);
    else lines.push(`📅 Dates: ${currentTripData.available_dates?.[0] || ''} to ${currentTripData.available_dates?.slice(-1)[0] || ''}`);
    lines.push("");

    filteredDays.forEach(day => {
      lines.push(`▶ DAY: ${day.date} (${day.items.length} stops)`);
      day.items.forEach((it, idx) => {
        const tr = it.transit ? ` [${it.transit.miles || ''}mi • ${it.transit.walk_time || ''}]` : '';
        lines.push(`${idx + 1}. ${it.title}${tr} - ${it.cost || 'Free'}`);
        if (it.highlight) lines.push(`   "${it.highlight}"`);
        if (it.transit?.transit_line) lines.push(`   🚌 Transit: ${it.transit.transit_line} (${it.transit.transit_time || ''})`);
        else if (it.transit?.best_mode) lines.push(`   Transit: ${it.transit.best_mode}`);
        if (it.personal_note) lines.push(`   📝 Note: "${it.personal_note}"`);
      });
      lines.push("");
    });

    if (includeTodo && currentTripData.itinerary?.todo?.length > 0) {
      lines.push(`📋 TO-DO WISHLIST:`);
      currentTripData.itinerary.todo.slice(0, 5).forEach((it, i) => {
        lines.push(`• ${it.title} (${it.city_name || ''})`);
        if (it.personal_note) lines.push(`   📝 Note: "${it.personal_note}"`);
      });
    }

    const origin = (typeof window !== "undefined" && window.location?.origin) ? window.location.origin : "http://127.0.0.1:8000";
    lines.push(`\nShared via Travel Scout: ${origin}`);
    return lines.join("\n");
  }

  // Full Rich Email format
  lines.push(`=======================================================`);
  lines.push(`🌍 TRAVEL SCOUT ITINERARY: ${trip.title.toUpperCase()}`);
  if (trip.description) lines.push(`📝 Purpose: ${trip.description}`);
  lines.push(`📅 Dates: ${currentTripData.available_dates?.[0] || ''} to ${currentTripData.available_dates?.slice(-1)[0] || ''}`);
  lines.push(`🏙️ Cities: ${cities.map(c => c.city_name).join(" -> ")}`);
  lines.push(`👥 Team: ${currentTripData.collaborators?.map(c => c.name).join(", ") || 'Travelers'}`);
  lines.push(`=======================================================\n`);

  // Accommodations
  lines.push(`🏨 ACCOMMODATIONS REFERENCE:`);
  cities.forEach(c => {
    c.stays.forEach(s => {
      lines.push(`• ${s.name} (${c.city_name})`);
      lines.push(`  Address: ${s.address}`);
      lines.push(`  Check-in: ${s.start_date} | Check-out: ${s.end_date}`);
      if (s.notes) lines.push(`  Notes: ${s.notes}`);
    });
  });
  lines.push("");

  // Days
  filteredDays.forEach((day, dIdx) => {
    lines.push(`-------------------------------------------------------`);
    lines.push(`📅 DAY ${dIdx + 1}: ${day.date}`);
    lines.push(`-------------------------------------------------------`);

    if (day.items.length === 0) {
      lines.push(`(No stops scheduled for this day yet)\n`);
      return;
    }

    day.items.forEach((it, iIdx) => {
      lines.push(`\n[Stop ${iIdx + 1}] ${it.title.toUpperCase()}`);
      lines.push(`• Category: ${it.category} | Cost: ${it.cost || 'Free'} | Neighborhood: ${it.neighborhood || it.city_name}`);
      lines.push(`• Address: ${it.address || 'City Center'}`);

      if (it.transit) {
        lines.push(`• Distance: ${it.transit.miles || '?'} mi from ${it.transit.stay_name || 'hotel'} (${it.transit.walk_time || ''} • ${it.transit.walk_label || 'Walk'})`);
        if (it.transit.transit_line) lines.push(`• Public Transit: 🚌 ${it.transit.transit_line} (~${it.transit.transit_time || ''})`);
        if (it.transit.bus_routes) lines.push(`• Bus Routes: ${it.transit.bus_routes}`);
        if (it.transit.transit_details) lines.push(`• Transit Route: ${it.transit.transit_details}`);
        if (it.transit.fare_tip) lines.push(`• Fare Tip: ${it.transit.fare_tip}`);
        if (it.transit.transit_url) lines.push(`• Live Transit Directions: ${it.transit.transit_url}`);
      }

      if (it.highlight) lines.push(`• Highlight: "${it.highlight}"`);
      if (it.description) lines.push(`• Overview: ${it.description}`);
      if (it.time_info) lines.push(`• Hours: ${it.time_info}`);
      if (it.url) lines.push(`• Web: ${it.url}`);
      lines.push(`• Maps: https://www.google.com/maps/search/?api=1&query=${it.lat},${it.lon}`);
      lines.push(`• Added by: ${it.added_by?.name || 'Traveler'}`);
      if (it.personal_note) {
        lines.push(`• 📝 Personal Note: "${it.personal_note}" (added by ${it.note_author?.name || 'Traveler'} on ${it.note_date || ''})`);
      }
    });
    lines.push("");
  });

  // To-Do Wishlist
  if (includeTodo && currentTripData.itinerary?.todo?.length > 0) {
    lines.push(`=======================================================`);
    lines.push(`📋 UNSCHEDULED BUCKET LIST & WISHLIST:`);
    lines.push(`=======================================================`);
    currentTripData.itinerary.todo.forEach((it, idx) => {
      lines.push(`\n${idx + 1}. ${it.title} (${it.city_name || ''}) - ${it.cost || 'Free'}`);
      if (it.address) lines.push(`   Address: ${it.address}`);
      if (it.highlight) lines.push(`   "${it.highlight}"`);
      if (it.personal_note) lines.push(`   📝 Personal Note: "${it.personal_note}" (added by ${it.note_author?.name || 'Traveler'} on ${it.note_date || ''})`);
      if (it.url) lines.push(`   Link: ${it.url}`);
    });
    lines.push("");
  }

  const origin = (typeof window !== "undefined" && window.location?.origin) ? window.location.origin : "http://127.0.0.1:8000";
  lines.push(`\nGenerated with Travel Scout (${origin})`);
  return lines.join("\n");
}

function openAddStayModal(cityId, cityName) {
  document.getElementById("stayCityId").value = cityId;
  const modal = document.getElementById("addStayModal");
  modal.querySelector("h3").textContent = `🏨 Add Hotel / Stay in ${cityName}`;
  modal.style.display = "flex";
}

function openEditStayModal(stayId, name, address, startDate, endDate, notes) {
  document.getElementById("editStayId").value = stayId;
  document.getElementById("editStayNameInput").value = name || "";
  document.getElementById("editStayAddressInput").value = address || "";
  document.getElementById("editStayStartInput").value = startDate || "";
  document.getElementById("editStayEndInput").value = endDate || "";
  document.getElementById("editStayNotesInput").value = notes || "";
  const modal = document.getElementById("editStayModal");
  if (modal) modal.style.display = "flex";
}
window.openEditStayModal = openEditStayModal;

// Helper to get all cities present across the itinerary and destination segments
function getTripItineraryCities() {
  if (!currentTripData) return [];
  const cityMap = new Map();

  // 1. From Destination Cities (city_segments)
  (currentTripData.cities || []).forEach(c => {
    if (c.city_name && c.city_name.trim()) {
      const norm = c.city_name.trim();
      if (!cityMap.has(norm.toLowerCase())) {
        cityMap.set(norm.toLowerCase(), {
          id: c.id,
          city_name: norm,
          country: c.country || ""
        });
      }
    }
  });

  // 2. From all itinerary items (so Scout cities always align with any city on the itinerary)
  (currentTripData.all_items || []).forEach(it => {
    if (it.city_name && it.city_name !== "Universal" && it.city_name.trim()) {
      const norm = it.city_name.trim();
      if (!cityMap.has(norm.toLowerCase())) {
        cityMap.set(norm.toLowerCase(), {
          id: it.city_segment_id || it.city_id || norm,
          city_name: norm,
          country: ""
        });
      }
    }
  });

  return Array.from(cityMap.values());
}

function syncScoutCityWithItinerary() {
  const itinSelect = document.getElementById("itineraryCityFilter");
  const scoutSelect = document.getElementById("scoutTargetCity");
  if (!itinSelect || !scoutSelect || !currentTripData) return;

  const cities = getTripItineraryCities();
  if (itinSelect.value && itinSelect.value !== "all") {
    const matched = cities.find(c => c.id === itinSelect.value);
    if (matched) {
      scoutSelect.value = matched.city_name;
      renderScoutSuggestions();
    }
  }
}

window.jumpToScoutCity = function(cityName) {
  if (!cityName) return;
  const scoutSelect = document.getElementById("scoutTargetCity");
  if (scoutSelect) {
    const options = Array.from(scoutSelect.options).map(o => o.value);
    if (!options.includes(cityName)) {
      const opt = document.createElement("option");
      opt.value = cityName;
      opt.textContent = `🏙️ ${cityName}`;
      scoutSelect.appendChild(opt);
    }
    scoutSelect.value = cityName;
    renderScoutSuggestions();
  }
  const scoutTab = document.querySelector('.nav-tab[data-tab="scout"]');
  if (scoutTab) scoutTab.click();
};

// 9. Dropdown helpers
function populateCityDropdowns() {
  const itinSelect = document.getElementById("itineraryCityFilter");
  const scoutSelect = document.getElementById("scoutTargetCity");
  const mapCitySelect = document.getElementById("mapCityJump");

  if (!currentTripData) return;

  const cities = getTripItineraryCities();

  if (itinSelect) {
    const prev = itinSelect.value;
    itinSelect.innerHTML = `<option value="all">🌐 All Cities (Unified Timeline)</option>` +
      cities.map(c => `<option value="${c.id}">${escapeHtml(c.city_name)}</option>`).join("");
    itinSelect.value = prev || "all";
    itinSelect.onchange = () => {
      renderItineraryTab();
      syncScoutCityWithItinerary();
    };
  }

  if (scoutSelect) {
    const prev = scoutSelect.value;
    scoutSelect.innerHTML = cities.map(c => `<option value="${escapeHtml(c.city_name)}">🏙️ ${escapeHtml(c.city_name)}</option>`).join("");
    if (prev && cities.some(c => c.city_name.toLowerCase() === prev.toLowerCase())) {
      scoutSelect.value = prev;
    } else if (itinSelect && itinSelect.value !== "all") {
      const focusedCity = cities.find(c => c.id === itinSelect.value);
      if (focusedCity) scoutSelect.value = focusedCity.city_name;
    }
    scoutSelect.onchange = () => renderScoutSuggestions();
  }

  if (mapCitySelect) {
    mapCitySelect.innerHTML = `<option value="all">🌍 Whole Journey Overview</option>` +
      cities.map(c => `<option value="${c.id}">${escapeHtml(c.city_name)}</option>`).join("");
  }

  populateLocalAgentCities();
  renderScoutSuggestions();
}


function renderScoutSuggestions() {
  const container = document.getElementById("scoutSuggestions");
  const citySelect = document.getElementById("scoutTargetCity");
  const queryInput = document.getElementById("scoutQueryInput");
  if (!container) return;

  const cities = getTripItineraryCities();
  if (cities.length === 0) {
    container.innerHTML = `<span style="font-size:0.8rem; color:var(--text-muted);">Add destination cities to your journey to see tailored live scout suggestions.</span>`;
    return;
  }

  const selectedCity = citySelect ? (citySelect.value || cities[0].city_name) : cities[0].city_name;
  if (queryInput) {
    queryInput.placeholder = `Search live concerts, venues, hidden gems, or dining in ${selectedCity}...`;
  }

  let chipsHtml = `<span style="font-size:0.8rem; color:var(--text-muted);">Quick Scout:</span>`;
  cities.forEach(c => {
    const name = escapeHtml(c.city_name);
    chipsHtml += `
      <button type="button" class="scout-chip" data-city="${name}" data-q="craft breweries beer tasting rooms taprooms" data-ch="breweries">🍺 ${name} Breweries & Taprooms</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="craft cocktail bars and secret speakeasies" data-ch="cocktails">🍸 ${name} Speakeasies & Cocktails</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="Michelin star restaurants and fine dining" data-ch="michelin">⭐ ${name} Michelin Dining</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="Eater 38 essential restaurants heatmap" data-ch="eater">🍴 ${name} Eater Heatmap</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="best restaurants and bars Yelp top rated" data-ch="yelp">⭐ ${name} Yelp Best Rated</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="city magazine best of dining nightlife guide" data-ch="magazines">📰 ${name} City Magazine Guide</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="live music concerts gig guide" data-ch="music">🎵 ${name} Live Music</button>
      <button type="button" class="scout-chip" data-city="${name}" data-q="Reddit hidden gems secret viewpoints" data-ch="reddit">💎 ${name} Gems</button>
    `;
  });

  container.innerHTML = chipsHtml;

  container.querySelectorAll(".scout-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const city = chip.dataset.city;
      const q = chip.dataset.q;
      const ch = chip.dataset.ch;
      const btn = document.getElementById("runScoutBtn");
      const chSelect = document.getElementById("scoutChannelSelect");
      if (city && citySelect) citySelect.value = city;
      if (q && queryInput) queryInput.value = q;
      if (ch && chSelect) chSelect.value = ch;
      if (btn) btn.click();
    });
  });
}

// 10. City-Scoped Live Web Scout & Daily Scanner
function initScout() {
  const btn = document.getElementById("runScoutBtn");
  const queryInput = document.getElementById("scoutQueryInput");
  const citySelect = document.getElementById("scoutTargetCity");
  const chSelect = document.getElementById("scoutChannelSelect");
  const catSelect = document.getElementById("scoutCategorySelect");
  const loading = document.getElementById("scoutLoading");
  const grid = document.getElementById("scoutResultsGrid");
  const dailyBtn = document.getElementById("runMultiDailyScanBtn");

  if (btn) {
    btn.addEventListener("click", async () => {
      const q = queryInput.value.trim();
      const city = citySelect.value;
      if (!q) return;

      loading.style.display = "block";
      grid.innerHTML = "";

      try {
        const res = await fetch("/api/search", {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({
            city_name: city,
            query: q,
            channel: chSelect.value || "all",
            category: catSelect.value || null
          })
        });
        const data = await res.json();
        loading.style.display = "none";

        if (data.results.length === 0) {
          grid.innerHTML = `<p style="grid-column:1/-1; text-align:center; color:var(--text-muted); padding:2rem;">No live web results returned for '${escapeHtml(q)}'. Try other keywords.</p>`;
        } else {
          window._lastSearchResults = data.results;
          grid.innerHTML = data.results.map((r, idx) => {
            const hasUrl = Boolean(r.url && r.url.trim() !== "");
            const safeUrl = hasUrl ? sanitizeUrl(r.url) : "";
            const targetUrl = safeUrl ? safeUrl : `https://www.google.com/search?q=${encodeURIComponent(r.title + ' ' + city)}`;
            const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(r.title + ' ' + (r.address || city))}`;
                let pIcon = "🌐";
                if (/eventbrite/i.test(r.source_platform)) pIcon = "🎟️";
                else if (/songkick/i.test(r.source_platform)) pIcon = "🎸";
                else if (/dice/i.test(r.source_platform)) pIcon = "🎲";
                else if (/ticketmaster/i.test(r.source_platform)) pIcon = "🎫";
                else if (/venue/i.test(r.source_platform)) pIcon = "🏛️";
                else if (/yelp/i.test(r.source_platform)) pIcon = "⭐";
                else if (/eater/i.test(r.source_platform)) pIcon = "🍴";
                else if (/michelin/i.test(r.source_platform)) pIcon = "⭐";
                else if (/brewery|beer/i.test(r.source_platform)) pIcon = "🍺";
                else if (/cocktail|speakeasy/i.test(r.source_platform)) pIcon = "🍸";
                else if (/magazine/i.test(r.source_platform)) pIcon = "📰";
                else if (/reddit/i.test(r.source_platform)) pIcon = "💬";
                else if (/tiktok/i.test(r.source_platform)) pIcon = "🎬";

                return `
              <div class="itin-card">
                <div class="card-top-row">
                  <div class="card-title">
                    <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" class="card-title-link" title="Open ${escapeHtml(r.title)}">
                      ${escapeHtml(r.title)}
                      <span class="card-link-icon">↗</span>
                    </a>
                  </div>
                  <span class="card-city-badge">${escapeHtml(city)}</span>
                </div>
                <div style="font-size:0.8rem; color:#38bdf8;">Platform: <strong>${pIcon} ${escapeHtml(r.source_platform)}</strong></div>
                <p style="font-size:0.82rem; color:var(--text-muted);">${escapeHtml(r.highlight)}</p>
                <div class="card-links-row">
                  <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill primary" title="View on source platform">
                    ${pIcon} ${escapeHtml(r.source_platform || 'Web Source')} ↗
                  </a>
                  <a href="${escapeHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer" class="item-link-pill maps" title="Open in Google Maps">
                    📍 Maps ↗
                  </a>
                </div>
                <div class="card-footer-actions">
                  <button class="btn btn-primary btn-sm" onclick="addSearchResultToWishlist(${idx})">
                    ➕ Add to To-Do List
                  </button>
                </div>
              </div>
            `;
          }).join("");
        }
      } catch (err) {
        loading.style.display = "none";
        grid.innerHTML = `<p style="color:#f43f5e; text-align:center;">Error: ${err.message}</p>`;
      }
    });
  }

  // Daily Scan
  if (dailyBtn) {
    dailyBtn.addEventListener("click", async () => {
      dailyBtn.disabled = true;
      dailyBtn.textContent = "⏳ Scanning all trip destination cities...";
      try {
        const res = await fetch(`/api/trips/${currentTripId}/scan/daily`, {
          method: "POST",
          headers: getAuthHeaders(),
          credentials: "include"
        });
        const data = await res.json();
        dailyBtn.disabled = false;
        dailyBtn.textContent = "⚡ Run Daily Autonomous Scan (All Trip Cities)";
        alert(`✓ Daily Scan Complete! Scanned ${data.cities_scanned} cities. Discovered ${data.newly_discovered} fresh cultural items added to your wishlist!`);
        await refreshTrip();
      } catch (err) {
        dailyBtn.disabled = false;
        dailyBtn.textContent = "⚡ Run Daily Autonomous Scan (All Trip Cities)";
        alert("Scan error: " + err.message);
      }
    });
  }

  initLocalAgentModal();
}

// ==================== LOCAL CITY CULTURAL SCOUT AGENT ====================

function initLocalAgentModal() {
  const modal = document.getElementById("localAgentModal");
  const openTab1Btn = document.getElementById("exploreLaunchAgentBtn");
  const openTab4Btn = document.getElementById("openLocalAgentModalBtn");
  const closeBtn1 = document.getElementById("closeLocalAgentModalBtn");
  const closeBtn2 = document.getElementById("closeLocalAgentModalBtn2");
  const citySelect = document.getElementById("localAgentCitySelect");
  const pubsList = document.getElementById("localAgentPubsList");
  const statusBox = document.getElementById("localAgentStatus");
  const statusText = document.getElementById("localAgentStatusText");
  const resultsBox = document.getElementById("localAgentResultsBox");
  const resultsTitle = document.getElementById("localAgentResultsTitle");
  const resultsDetail = document.getElementById("localAgentResultsDetail");
  const executeBtn = document.getElementById("runLocalAgentExecuteBtn");
  const selectAllBtn = document.getElementById("agentSelectAllBtn");
  const deselectAllBtn = document.getElementById("agentDeselectAllBtn");

  if (!modal) return;

  const openModal = async () => {
    if (!currentUser) {
      alert("🔒 Please sign in with your account before launching the cultural scout agent.");
      if (window.openLogin) window.openLogin();
      return;
    }
    modal.style.display = "flex";
    if (statusBox) statusBox.style.display = "none";
    if (resultsBox) resultsBox.style.display = "none";
    if (executeBtn) {
      executeBtn.disabled = false;
      executeBtn.textContent = "🚀 Run Local Cultural Agent";
    }

    populateLocalAgentCities();

    if (citySelect) {
      await updateLocalAgentPublications(citySelect.value);
    }
  };

  if (openTab1Btn) openTab1Btn.addEventListener("click", openModal);
  if (openTab4Btn) openTab4Btn.addEventListener("click", openModal);
  if (closeBtn1) closeBtn1.addEventListener("click", () => modal.style.display = "none");
  if (closeBtn2) closeBtn2.addEventListener("click", () => modal.style.display = "none");

  if (citySelect) {
    citySelect.addEventListener("change", async () => {
      await updateLocalAgentPublications(citySelect.value);
    });
  }

  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", (e) => {
      e.preventDefault();
      document.querySelectorAll('input[name="agent_event_type"]').forEach(cb => cb.checked = true);
    });
  }

  if (deselectAllBtn) {
    deselectAllBtn.addEventListener("click", (e) => {
      e.preventDefault();
      document.querySelectorAll('input[name="agent_event_type"]').forEach(cb => cb.checked = false);
    });
  }

  if (executeBtn) {
    executeBtn.addEventListener("click", async () => {
      const selectedTypes = Array.from(document.querySelectorAll('input[name="agent_event_type"]:checked')).map(cb => cb.value);
      if (selectedTypes.length === 0) {
        alert("Please select at least one cultural event type to scout.");
        return;
      }

      const cityId = citySelect ? citySelect.value : "all";
      const cityName = citySelect && citySelect.selectedOptions.length > 0 ? citySelect.selectedOptions[0].text : "destination cities";

      executeBtn.disabled = true;
      executeBtn.textContent = "⏳ Agent Scouting in Progress...";
      if (statusBox) {
        statusBox.style.display = "block";
        statusText.textContent = `Agent is scanning local publications and event feeds for ${cityName}...`;
      }
      if (resultsBox) resultsBox.style.display = "none";

      try {
        const res = await fetch(`/api/trips/${currentTripId}/scout/local-agent`, {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({
            city_id: cityId === "all" ? null : cityId,
            event_types: selectedTypes,
            max_per_type: 3
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Failed to complete local agent scout");
        }

        const data = await res.json();
        if (statusBox) statusBox.style.display = "none";

        if (resultsBox) {
          resultsBox.style.display = "block";
          resultsTitle.textContent = `✨ Discovered ${data.total_newly_discovered} New Cultural Events!`;
          resultsDetail.innerHTML = `Scanned <strong>${data.total_cities_scanned}</strong> destination cities across local newspapers, alt-weeklies, and event platforms. All discoveries are now live in your <strong>Explore & Discover</strong> wishlist!`;
        }

        executeBtn.disabled = false;
        executeBtn.textContent = "✓ Ingested! Run Again";

        // Refresh trip data to update items and UI counters
        await refreshTrip();

        // Switch to Explore & Discover tab
        const exploreTab = document.querySelector('.nav-tab[data-tab="explore"]');
        if (exploreTab) {
          setTimeout(() => {
            exploreTab.click();
          }, 800);
        }
      } catch (err) {
        if (statusBox) statusBox.style.display = "none";
        executeBtn.disabled = false;
        executeBtn.textContent = "🚀 Run Local Cultural Agent";
        alert("Local Cultural Agent Notice: " + err.message);
      }
    });
  }
}

function populateLocalAgentCities() {
  const citySelect = document.getElementById("localAgentCitySelect");
  if (!citySelect || !currentTripData) return;

  const cities = getTripItineraryCities();
  const prev = citySelect.value;

  citySelect.innerHTML = `<option value="all">🏙️ All Destination Cities on Trip Itinerary (${cities.length} stops)</option>` +
    cities.map(c => `<option value="${c.id}">📍 ${escapeHtml(c.city_name)} (${escapeHtml(c.country || '')})</option>`).join("");

  if (prev && (prev === "all" || cities.some(c => c.id === prev))) {
    citySelect.value = prev;
  }
}

async function updateLocalAgentPublications(cityId) {
  const pubsList = document.getElementById("localAgentPubsList");
  if (!pubsList) return;

  if (!cityId || cityId === "all") {
    const cities = getTripItineraryCities();
    const cityNames = cities.map(c => c.city_name).join(", ");
    pubsList.innerHTML = `<span style="color:var(--text-muted);">The agent will dynamically discover and read local newspapers, weekly publications, and culture calendars for: <strong>${escapeHtml(cityNames || 'all itinerary stops')}</strong>.</span>`;
    return;
  }

  pubsList.innerHTML = `<span style="color:var(--text-muted); font-style:italic;">Scanning local press and media registry for this destination...</span>`;

  try {
    const res = await fetch(`/api/trips/${currentTripId}/cities/${cityId}/publications`, {
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (!res.ok) throw new Error("Could not fetch publications");
    const data = await res.json();

    if (data.publications && data.publications.length > 0) {
      pubsList.innerHTML = data.publications.map(p => `
        <div style="margin-bottom:0.35rem; display:flex; align-items:center; flex-wrap:wrap; gap:0.35rem;">
          <strong>• ${escapeHtml(p.name)}</strong>
          <span style="color:var(--text-muted); font-size:0.75rem;">(${escapeHtml(p.type)})</span>
          ${p.url ? `<a href="${sanitizeUrl(p.url)}" target="_blank" rel="noopener noreferrer" style="color:#38bdf8; text-decoration:none; font-size:0.75rem; margin-left:0.2rem;">🔗 Visit Media</a>` : ''}
        </div>
      `).join("");
    } else {
      pubsList.innerHTML = `<span style="color:var(--text-muted);">The agent will execute live web searches to identify local alternative weeklies, community guides, and cultural calendars for ${escapeHtml(data.city_name)}.</span>`;
    }
  } catch (err) {
    pubsList.innerHTML = `<span style="color:var(--text-muted);">Local press discovery will be executed live during the agent run.</span>`;
  }
}


function addSearchResultToWishlist(index) {
  if (window._lastSearchResults && window._lastSearchResults[index]) {
    addToWishlist(window._lastSearchResults[index]);
  }
}

async function addToWishlist(itemObj) {
  try {
    // Find city ID
    let cityId = null;
    if (currentTripData) {
      const allCities = getTripItineraryCities();
      const foundCity = allCities.find(c => c.city_name.toLowerCase() === (itemObj.city_name || "").toLowerCase());
      if (foundCity) cityId = foundCity.id;
      else if (currentTripData.cities && currentTripData.cities.length > 0) cityId = currentTripData.cities[0].id;
    }

    const payload = {
      city_segment_id: cityId,
      city_name: itemObj.city_name,
      title: itemObj.title,
      category: itemObj.category || "gems",
      neighborhood: itemObj.neighborhood,
      address: itemObj.address,
      lat: itemObj.lat,
      lon: itemObj.lon,
      cost: itemObj.cost || "Free",
      highlight: itemObj.highlight,
      description: itemObj.description,
      url: itemObj.url,
      source_platform: itemObj.source_platform || "Web Scout",
      assigned_date: "todo"
    };

    const res = await fetch(`/api/trips/${currentTripId}/items`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      credentials: "include",
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert(`Added "${itemObj.title}" to your To-Do Wishlist!`);
      await refreshTrip();
    } else {
      const err = await res.json().catch(() => ({}));
      alert("Failed to add to wishlist: " + (err.detail || res.statusText));
    }
  } catch (err) {
    alert("Failed to add to wishlist: " + err.message);
  }
}

// 11. Multi-City Leaflet Map (Powered by OpenStreetMap - 100% Free, Zero API Key Required)
function initMap() {
  const mapEl = document.getElementById("scoutMap");
  if (!mapEl || typeof L === "undefined") return;

  // Determine initial center dynamically from current trip's cities
  let initialCenter = [20.0, 0.0];
  let initialZoom = 2;
  if (currentTripData && currentTripData.cities && currentTripData.cities.length > 0) {
    const firstValidCity = currentTripData.cities.find(c => c.lat && c.lon && (c.lat !== 0 || c.lon !== 0));
    if (firstValidCity) {
      initialCenter = [firstValidCity.lat, firstValidCity.lon];
      initialZoom = 9;
    }
  }

  leafletMap = L.map("scoutMap", {
    center: initialCenter,
    zoom: initialZoom,
  });

  // OpenStreetMap Tile Layer - 100% Free, Community-Hosted, No API Key Required
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(leafletMap);

  mapRouteGroup = L.layerGroup().addTo(leafletMap);
  mapMarkersGroup = L.layerGroup().addTo(leafletMap);

  renderMapLocations();

  const jumpSelect = document.getElementById("mapCityJump");
  if (jumpSelect) {
    jumpSelect.addEventListener("change", (e) => {
      const cityId = e.target.value;
      if (cityId === "all") {
        fitMapBounds();
      } else if (currentTripData) {
        const c = currentTripData.cities.find(ci => ci.id === cityId);
        if (c && c.lat && c.lon) {
          leafletMap.flyTo([c.lat, c.lon], 13, { duration: 1.2 });
        }
      }
      renderMapLocations();
    });
  }

  const daySelect = document.getElementById("mapDaySelect");
  if (daySelect) {
    daySelect.addEventListener("change", () => renderMapLocations());
  }

  const routeCheck = document.getElementById("mapRouteCheck");
  if (routeCheck) {
    routeCheck.addEventListener("change", () => renderMapLocations());
  }

  const staysCheck = document.getElementById("mapStaysCheck");
  if (staysCheck) {
    staysCheck.addEventListener("change", () => renderMapLocations());
  }
}

async function renderMapLocations() {
  if (!leafletMap || !currentTripId) return;

  try {
    const res = await fetch(`/api/trips/${currentTripId}/map`);
    const data = await res.json();

    mapMarkersGroup.clearLayers();
    mapRouteGroup.clearLayers();

    // Populate day filter if options not yet loaded
    const daySelect = document.getElementById("mapDaySelect");
    if (daySelect && currentTripData && currentTripData.available_dates) {
      const currentSelectedDay = daySelect.value || "all";
      const existingVals = Array.from(daySelect.options).map(o => o.value);
      const allDates = currentTripData.available_dates || [];
      const needsUpdate = allDates.some(d => !existingVals.includes(d));
      if (needsUpdate || existingVals.length <= 2) {
        daySelect.innerHTML = `
          <option value="all">All Dates</option>
          <option value="todo">📋 To-Do / Bucket List</option>
          ${allDates.map(d => `<option value="${d}">📅 ${d}</option>`).join("")}
        `;
        if (existingVals.includes(currentSelectedDay)) {
          daySelect.value = currentSelectedDay;
        }
      }
    }

    const cityFilter = document.getElementById("mapCityJump")?.value || "all";
    const dayFilter = document.getElementById("mapDaySelect")?.value || "all";
    const showStays = document.getElementById("mapStaysCheck") ? document.getElementById("mapStaysCheck").checked : true;
    const drawRoute = document.getElementById("mapRouteCheck") ? document.getElementById("mapRouteCheck").checked : true;

    // Filter Stays / Hotels
    if (showStays) {
      let filteredStays = data.stays;
      if (cityFilter !== "all") {
        filteredStays = filteredStays.filter(s => s.city_id === cityFilter);
      }

      filteredStays.forEach(s => {
        if (s.lat && s.lon) {
          const hotelIcon = L.divIcon({
            className: 'custom-hotel-pin',
            html: `<div style="background:#0284c7; color:#fff; border:2px solid #fff; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; font-size:15px; box-shadow:0 3px 10px rgba(0,0,0,0.6);">🏨</div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 16]
          });

          L.marker([s.lat, s.lon], { icon: hotelIcon })
            .addTo(mapMarkersGroup)
            .bindPopup(`
              <div style="color:#020617; padding:0.4rem; min-width:190px;">
                <strong style="color:#0284c7; font-size:1rem;">🏨 ${escapeHtml(s.name)}</strong>
                <div style="font-size:0.8rem; color:#475569; margin-top:0.2rem;">📍 ${escapeHtml(s.address)}</div>
                <div style="font-size:0.75rem; color:#d97706; font-weight:bold; margin-top:0.3rem;">📅 Active: ${s.start_date} &rarr; ${s.end_date}</div>
                ${s.notes ? `<div style="font-size:0.75rem; color:#64748b; margin-top:0.2rem;">${escapeHtml(s.notes)}</div>` : ''}
                <div style="margin-top:0.5rem; display:flex; gap:0.35rem; flex-wrap:wrap;">
                  <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(s.name + ', ' + s.address)}" target="_blank" rel="noopener noreferrer" style="font-size:0.72rem; padding:0.25rem 0.5rem; background:#0284c7; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600; display:inline-block;" title="Open Google Maps directions with hotel pre-populated as destination">
                    🧭 Directions to Hotel ↗
                  </a>
                  <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(s.name + ' ' + s.address)}" target="_blank" rel="noopener noreferrer" style="font-size:0.72rem; padding:0.25rem 0.5rem; background:rgba(0,0,0,0.06); border:1px solid #94a3b8; color:#0f172a; border-radius:4px; text-decoration:none; font-weight:600; display:inline-block;" title="View hotel location in Google Maps">
                    📍 View on Map ↗
                  </a>
                </div>
              </div>
            `);
        }
      });
    }

    // Filter Items
    let filteredItems = data.items;
    if (cityFilter !== "all") {
      filteredItems = filteredItems.filter(it => it.city_id === cityFilter);
    }
    if (dayFilter !== "all") {
      if (dayFilter === "todo") {
        filteredItems = filteredItems.filter(it => !it.assigned_date || it.assigned_date === "todo");
      } else {
        filteredItems = filteredItems.filter(it => it.assigned_date === dayFilter);
      }
    }

    const validItems = filteredItems.filter(it => it.lat && it.lon);

    const sidebarList = document.getElementById("mapSidebarList");
    const sidebarCount = document.getElementById("mapSidebarCount");
    if (sidebarCount) sidebarCount.textContent = `${validItems.length} Stops`;

    // Item markers & Sequence Numbers
    const sidebarItemsHtml = [];
    const routeCoords = [];

    // Prepend active lodging for this specific day as starting origin
    const isSingleDay = Boolean(dayFilter && dayFilter !== "all" && dayFilter !== "todo");
    const activeDayStay = isSingleDay ? getLodgingForDate(dayFilter) : null;
    if (activeDayStay && activeDayStay.lat && activeDayStay.lon) {
      routeCoords.push([activeDayStay.lat, activeDayStay.lon]);
      sidebarItemsHtml.push(`
        <div style="background:rgba(2,132,199,0.12); border:1px solid rgba(56,189,248,0.4); border-radius:6px; padding:0.6rem; margin-bottom:0.5rem; cursor:pointer;" onclick="zoomToCoord(${activeDayStay.lat}, ${activeDayStay.lon})">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-weight:700; font-size:0.85rem; color:#38bdf8; display:flex; align-items:center; gap:0.4rem;">
              <span>🏨</span>
              <span>START: ${escapeHtml(activeDayStay.name)}</span>
            </div>
            <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(activeDayStay.name + ', ' + (activeDayStay.address || ''))}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" style="color:#38bdf8; font-size:0.75rem; text-decoration:none; padding:0.1rem 0.3rem;" title="Directions to lodging">↗</a>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.2rem;">
            ${escapeHtml(activeDayStay.address || 'Lodging Base')} &bull; 📍 Day Starting Origin
          </div>
        </div>
      `);
    }

    validItems.forEach((it, idx) => {
      const stopNumber = idx + 1;
      routeCoords.push([it.lat, it.lon]);

      const itemIcon = L.divIcon({
        className: 'custom-item-pin',
        html: `<div style="background:#f43f5e; color:#fff; border:2px solid #fff; border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; box-shadow:0 3px 8px rgba(0,0,0,0.5);">${stopNumber}</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      });

      const targetUrl = it.url || `https://www.google.com/search?q=${encodeURIComponent(it.title + ' ' + it.city_name)}`;
      const itemStay = isSingleDay ? activeDayStay : (getLodgingForDate(it.assigned_date, it.city_id));
      const stayLabel = itemStay?.name || "Hotel";
      const directTransitUrl = it.transit?.transit_url || getDirectionsUrlFromLodging(it, isSingleDay ? dayFilter : it.assigned_date);
      const directWalkUrl = it.transit?.walking_url || getDirectionsUrlFromLodging(it, isSingleDay ? dayFilter : it.assigned_date);

      L.marker([it.lat, it.lon], { icon: itemIcon })
        .addTo(mapMarkersGroup)
        .bindPopup(`
          <div style="color:#020617; padding:0.4rem; min-width:210px;">
            <div style="font-size:0.75rem; color:#f43f5e; font-weight:700;">STOP #${stopNumber} &bull; ${it.assigned_date && it.assigned_date !== 'todo' ? `📅 ${it.assigned_date}` : '📋 Bucket List'}</div>
            <strong style="font-size:0.95rem; margin-top:0.2rem; display:block;">${escapeHtml(it.title)}</strong>
            <div style="font-size:0.8rem; color:#475569; margin-top:0.2rem;">${escapeHtml(it.city_name)} &bull; ${escapeHtml(it.cost || 'Free')}</div>
            ${it.transit?.transit_line ? `
              <div style="font-size:0.74rem; color:#0284c7; margin-top:0.3rem; font-weight:600; line-height:1.3;">
                🚌 ${escapeHtml(it.transit.transit_line)} <span style="font-size:0.70rem; color:#0369a1;">(${escapeHtml(it.transit.transit_time || '')})</span>
              </div>
            ` : ''}
            ${it.transit?.miles ? `
              <div style="font-size:0.72rem; color:#64748b; margin-top:0.15rem;">
                🚶 ${it.transit.miles} mi (${escapeHtml(it.transit.walk_time || '')}) &bull; <span style="color:${it.transit.is_walkable ? '#16a34a' : '#d97706'}; font-weight:600;">${it.transit.is_walkable ? 'Walkable' : 'Transit advised'}</span>
              </div>
            ` : ''}
            <div style="font-size:0.72rem; color:#64748b; margin-top:0.2rem;">👤 Added by: ${escapeHtml(it.added_by.name)}</div>
            <div style="margin-top:0.5rem; display:flex; gap:0.35rem; flex-wrap:wrap;">
              <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" style="font-size:0.72rem; padding:0.25rem 0.5rem; background:#0284c7; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;" title="Open official website">
                🌐 Web ↗
              </a>
              <a href="${escapeHtml(directTransitUrl)}" target="_blank" rel="noopener noreferrer" style="font-size:0.72rem; padding:0.25rem 0.5rem; background:#0ea5e9; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;" title="Live Bus &amp; Transit Directions from ${escapeHtml(stayLabel)}">
                🚌 Transit from Hotel ↗
              </a>
              <a href="${escapeHtml(directWalkUrl)}" target="_blank" rel="noopener noreferrer" style="font-size:0.72rem; padding:0.25rem 0.5rem; background:#10b981; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;" title="Walking Route from ${escapeHtml(stayLabel)}">
                🚶 Walk from Hotel ↗
              </a>
            </div>
          </div>
        `);

      sidebarItemsHtml.push(`
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:6px; padding:0.6rem; cursor:pointer;" onclick="zoomToCoord(${it.lat}, ${it.lon})">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-weight:600; font-size:0.85rem; color:var(--text-main); display:flex; align-items:center; gap:0.4rem;">
              <span style="background:#f43f5e; color:#fff; border-radius:50%; width:18px; height:18px; display:inline-flex; align-items:center; justify-content:center; font-size:10px; font-weight:700;">${stopNumber}</span>
              <span>${escapeHtml(it.title)}</span>
            </div>
            <a href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" style="color:#38bdf8; font-size:0.75rem; text-decoration:none; padding:0.1rem 0.3rem;" title="Open site">↗</a>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.2rem;">
            ${escapeHtml(it.city_name)} &bull; ${escapeHtml(it.cost || 'Free')} &bull; ${it.assigned_date && it.assigned_date !== 'todo' ? `📅 ${it.assigned_date}` : '📋 Bucket List'}
          </div>
        </div>
      `);
    });

    // Draw Day Route Polylines
    if (drawRoute && routeCoords.length >= 2) {
      L.polyline(routeCoords, {
        color: '#38bdf8',
        weight: 4,
        opacity: 0.85,
        dashArray: '6, 8',
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(mapRouteGroup);
    }

    if (sidebarList) {
      if (sidebarItemsHtml.length === 0) {
        sidebarList.innerHTML = `<div style="color:var(--text-muted); font-size:0.82rem; text-align:center; padding:1.5rem 0.5rem;">No stops match the current filters.</div>`;
      } else {
        sidebarList.innerHTML = sidebarItemsHtml.join("");
      }
    }
    fitMapBounds();
  } catch (err) {
    console.error("Map fetch error:", err);
  }
}

function zoomToCoord(lat, lon) {
  if (leafletMap) {
    leafletMap.flyTo([lat, lon], 15, { duration: 1.0 });
  }
}

function fitMapBounds() {
  if (!leafletMap || !mapMarkersGroup) return;
  const bounds = [];
  mapMarkersGroup.eachLayer(l => {
    if (l.getLatLng) bounds.push(l.getLatLng());
  });
  if (bounds.length > 0) {
    leafletMap.fitBounds(L.latLngBounds(bounds), { padding: [40, 40], maxZoom: 14 });
  } else if (currentTripData && currentTripData.cities && currentTripData.cities.length > 0) {
    const validCities = currentTripData.cities.filter(c => c.lat && c.lon && (c.lat !== 0 || c.lon !== 0));
    if (validCities.length > 1) {
      leafletMap.fitBounds(L.latLngBounds(validCities.map(c => [c.lat, c.lon])), { padding: [40, 40], maxZoom: 12 });
    } else if (validCities.length === 1) {
      leafletMap.setView([validCities[0].lat, validCities[0].lon], 12);
    }
  }
}

// 12. Collaborative Budget & Expense Tracker
async function loadTripExpenses() {
  if (!currentTripId) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}/expenses`, {
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (!res.ok) return;
    const data = await res.json();
    const summary = data.summary || {};
    const expenses = data.expenses || [];
    const collaborators = data.collaborators || [];
    const sym = summary.currency === "USD" ? "$" : (summary.currency === "GBP" ? "£" : (summary.currency === "JPY" ? "¥" : "€"));

    // 1. KPI Cards
    const totalEl = document.getElementById("expenseTotalAmount");
    if (totalEl) totalEl.textContent = `${sym}${(summary.total_spent || 0).toFixed(2)}`;

    const perPersonEl = document.getElementById("expensePerPersonAmount");
    if (perPersonEl) perPersonEl.textContent = `${sym}${(summary.per_person || 0).toFixed(2)}`;

    const memberTextEl = document.getElementById("expenseMemberCountText");
    if (memberTextEl) memberTextEl.textContent = `Split equally among ${summary.member_count || 1} traveler${(summary.member_count || 1) > 1 ? 's' : ''}`;

    // Top Category
    let topCat = "None";
    let topCatAmt = 0;
    const catTotals = summary.category_totals || {};
    for (const [c, amt] of Object.entries(catTotals)) {
      if (amt > topCatAmt) {
        topCat = c;
        topCatAmt = amt;
      }
    }
    const catLabels = {
      dining: "🍽️ Dining & Drinks",
      lodging: "🏨 Lodging",
      tickets: "🎟️ Tickets & Events",
      transit: "🚆 Transit & Rides",
      activities: "🛶 Activities",
      shopping: "🛍️ Shopping",
      other: "📦 Other"
    };
    const topCatEl = document.getElementById("expenseTopCategory");
    if (topCatEl) topCatEl.textContent = topCat !== "None" ? (catLabels[topCat] || topCat) : "None";
    const topCatDetailEl = document.getElementById("expenseTopCategoryDetail");
    if (topCatDetailEl) topCatDetailEl.textContent = topCatAmt > 0 ? `${sym}${topCatAmt.toFixed(2)} total spend` : "No expenses logged yet";

    // 2. Settlement Table
    const settlementList = document.getElementById("settlementList");
    if (settlementList) {
      const settlements = summary.settlements || [];
      if (settlements.length === 0) {
        settlementList.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; text-align:center; padding:1rem 0;">🎉 All balances settled! Everyone is even.</div>`;
      } else {
        settlementList.innerHTML = settlements.map(s => {
          const sSym = s.currency === "USD" ? "$" : (s.currency === "GBP" ? "£" : (s.currency === "JPY" ? "¥" : "€"));
          return `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:8px; padding:0.6rem 0.85rem;">
              <div style="font-size:0.85rem;">
                <strong style="color:#f43f5e;">${escapeHtml(s.from_user)}</strong> owes <strong style="color:#22c55e;">${escapeHtml(s.to_user)}</strong>
              </div>
              <div style="font-weight:700; color:#38bdf8; font-size:0.95rem;">
                ${sSym}${s.amount.toFixed(2)}
              </div>
            </div>
          `;
        }).join("");
      }
    }

    // 3. Category Breakdown Bars
    const categoryBars = document.getElementById("expenseCategoryBars");
    if (categoryBars) {
      const entries = Object.entries(catTotals);
      if (entries.length === 0) {
        categoryBars.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; text-align:center; padding:1rem 0;">No spending recorded yet.</div>`;
      } else {
        const total = summary.total_spent || 1;
        categoryBars.innerHTML = entries.map(([cat, amt]) => {
          const pct = Math.min(100, Math.round((amt / total) * 100));
          const label = catLabels[cat] || cat;
          return `
            <div>
              <div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:0.25rem;">
                <span>${label}</span>
                <span style="font-weight:600;">${sym}${amt.toFixed(2)} (${pct}%)</span>
              </div>
              <div style="background:rgba(255,255,255,0.08); border-radius:999px; height:8px; overflow:hidden;">
                <div style="background:#38bdf8; height:100%; width:${pct}%; border-radius:999px;"></div>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    // 4. Ledger Table
    const countEl = document.getElementById("expenseLedgerCount");
    if (countEl) countEl.textContent = `${expenses.length} Expense${expenses.length === 1 ? '' : 's'}`;

    const bodyEl = document.getElementById("expenseLedgerBody");
    if (bodyEl) {
      if (expenses.length === 0) {
        bodyEl.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-muted);">No expenses logged yet. Click "Log New Expense" above to add meals, tickets, or transport!</td></tr>`;
      } else {
        bodyEl.innerHTML = expenses.map(e => {
          const eSym = e.currency === "USD" ? "$" : (e.currency === "GBP" ? "£" : (e.currency === "JPY" ? "¥" : "€"));
          const payerName = e.paid_by?.name || "Traveler";
          const payerAvatar = e.paid_by?.avatar_color || "#38bdf8";
          return `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
              <td style="padding:0.65rem; color:var(--text-muted); white-space:nowrap; font-size:0.82rem;">${escapeHtml(e.expense_date || '—')}</td>
              <td style="padding:0.65rem;">
                <div style="font-weight:600; color:var(--text-main);">${escapeHtml(e.title)}</div>
                ${e.notes ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.15rem;">${escapeHtml(e.notes)}</div>` : ''}
              </td>
              <td style="padding:0.65rem; font-size:0.82rem; color:#94a3b8;">${catLabels[e.category] || escapeHtml(e.category)}</td>
              <td style="padding:0.65rem; font-size:0.82rem;">
                <div style="display:flex; align-items:center; gap:0.4rem;">
                  <span style="display:inline-block; width:18px; height:18px; border-radius:50%; background:${payerAvatar}; font-size:10px; line-height:18px; text-align:center; color:#fff; font-weight:700;">
                    ${payerName.slice(0, 1).toUpperCase()}
                  </span>
                  <span>${escapeHtml(payerName)}</span>
                </div>
              </td>
              <td style="padding:0.65rem; text-align:right; font-weight:700; color:#38bdf8; font-size:0.92rem;">
                ${eSym}${e.amount.toFixed(2)}
              </td>
              <td style="padding:0.65rem; text-align:center;">
                <button type="button" onclick="deleteExpense('${e.id}')" style="background:none; border:none; color:#f43f5e; cursor:pointer; font-size:1.1rem; padding:0.2rem;" title="Delete expense">&times;</button>
              </td>
            </tr>
          `;
        }).join("");
      }
    }

    // 5. Populate payer select in Add Expense Modal
    const payerSelect = document.getElementById("expensePayerSelect");
    if (payerSelect) {
      payerSelect.innerHTML = collaborators.map(c => `
        <option value="${c.id}" ${currentUser && currentUser.id === c.id ? 'selected' : ''}>${escapeHtml(c.name)} (${escapeHtml(c.email)})</option>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load trip expenses:", err);
  }
}

window.deleteExpense = async function(expenseId) {
  if (!confirm("Are you sure you want to remove this expense from the group budget?")) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}/expenses/${expenseId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (res.ok) {
      await loadTripExpenses();
    } else {
      const err = await res.json().catch(() => ({}));
      alert("Failed to delete expense: " + (err.detail || res.statusText));
    }
  } catch (err) {
    alert("Error deleting expense: " + err.message);
  }
};

function initExpenseTracker() {
  const modal = document.getElementById("addExpenseModal");
  const openBtn = document.getElementById("openAddExpenseBtn");
  const cancelBtn = document.getElementById("cancelAddExpenseBtn");
  const form = document.getElementById("addExpenseForm");

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      if (modal) {
        const dateInput = document.getElementById("expenseDateInput");
        if (dateInput && !dateInput.value) {
          dateInput.value = new Date().toISOString().split("T")[0];
        }
        modal.style.display = "flex";
      }
    });
  }
  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      if (modal) modal.style.display = "none";
    });
  }
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        title: document.getElementById("expenseTitleInput").value.trim(),
        amount: parseFloat(document.getElementById("expenseAmountInput").value),
        currency: document.getElementById("expenseCurrencySelect").value,
        category: document.getElementById("expenseCategorySelect").value,
        paid_by_user_id: document.getElementById("expensePayerSelect")?.value || (currentUser ? currentUser.id : null),
        expense_date: document.getElementById("expenseDateInput").value || null,
        notes: document.getElementById("expenseNotesInput").value.trim()
      };

      try {
        const res = await fetch(`/api/trips/${currentTripId}/expenses`, {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          if (modal) modal.style.display = "none";
          form.reset();
          await loadTripExpenses();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to save expense: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error saving expense: " + err.message);
      }
    });
  }
}

// 13. Reservation & Booking Status Tracker
window.openBookingModal = function(itemId, title, status, ref) {
  const itemIdInput = document.getElementById("bookingItemId");
  const itemTitleInput = document.getElementById("bookingItemTitle");
  const statusSelect = document.getElementById("bookingStatusSelect");
  const refInput = document.getElementById("bookingRefInput");
  const modal = document.getElementById("editBookingModal");

  if (itemIdInput) itemIdInput.value = itemId;
  if (itemTitleInput) itemTitleInput.value = title || "Itinerary Stop";
  if (statusSelect) statusSelect.value = status || "unbooked";
  if (refInput) refInput.value = ref || "";
  if (modal) modal.style.display = "flex";
};

function initBookingModal() {
  const modal = document.getElementById("editBookingModal");
  const closeBtn = document.getElementById("closeEditBookingBtn");
  const cancelBtn = document.getElementById("cancelEditBookingBtn");
  const form = document.getElementById("editBookingForm");

  if (closeBtn) closeBtn.addEventListener("click", () => modal.style.display = "none");
  if (cancelBtn) cancelBtn.addEventListener("click", () => modal.style.display = "none");

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const itemId = document.getElementById("bookingItemId").value;
      const status = document.getElementById("bookingStatusSelect").value;
      const ref = document.getElementById("bookingRefInput").value.trim();

      try {
        const res = await fetch(`/api/trips/${currentTripId}/items/${itemId}/booking`, {
          method: "PUT",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({ booking_status: status, booking_ref: ref })
        });
        if (res.ok) {
          modal.style.display = "none";
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to update booking status: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error updating booking status: " + err.message);
      }
    });
  }
}

// 14. One-Click Calendar Sync (.ics Export)
function initCalendarExport() {
  const btn = document.getElementById("exportCalendarBtn");
  if (btn) {
    btn.addEventListener("click", () => {
      if (!currentTripId) {
        alert("Please select or create an itinerary first.");
        return;
      }
      window.location.href = `/api/trips/${currentTripId}/export/calendar.ics`;
    });
  }
}

// 15. Manual Itinerary Card Creation Modal
window.openAddItemModal = function(preselectedDate = "todo", preselectedCity = null) {
  if (!currentUser) {
    alert("🔒 Please sign in with your Google or Gmail account before adding custom stops.");
    if (window.openLogin) window.openLogin();
    return;
  }
  if (!currentTripId) {
    alert("Please select or create an itinerary first.");
    return;
  }

  const modal = document.getElementById("addItemModal");
  if (!modal) {
    console.error("addItemModal element not found in DOM");
    return;
  }

  try {
    // Populate cities dropdown
    const citySelect = document.getElementById("manualItemCity");
    if (citySelect) {
      const cities = (currentTripData && Array.isArray(currentTripData.cities)) ? currentTripData.cities : [];
      if (cities.length === 0) {
        citySelect.innerHTML = `<option value="">General Trip</option>`;
      } else {
        const presCityStr = (typeof preselectedCity === "string" && preselectedCity.trim()) ? preselectedCity.trim().toLowerCase() : null;
        citySelect.innerHTML = cities.map(c => {
          const cName = c.city_name || "City";
          const cCountry = c.country || "Region";
          const isSelected = presCityStr && (cName.toLowerCase().trim() === presCityStr || String(c.id) === String(preselectedCity));
          return `<option value="${escapeHtml(String(c.id))}" ${isSelected ? 'selected' : ''}>
            ${escapeHtml(cName)} (${escapeHtml(cCountry)})
          </option>`;
        }).join("");
      }
    }

    // Populate dates dropdown
    const dateSelect = document.getElementById("manualItemDate");
    if (dateSelect) {
      const availDates = (currentTripData && Array.isArray(currentTripData.available_dates)) ? currentTripData.available_dates : [];
      const isTodoSelected = !preselectedDate || preselectedDate === "todo";
      dateSelect.innerHTML = `
        <option value="todo" ${isTodoSelected ? 'selected' : ''}>📋 To-Do / Bucket List (Unscheduled)</option>
        ${availDates.map(d => `
          <option value="${escapeHtml(String(d))}" ${preselectedDate === d ? 'selected' : ''}>📅 ${escapeHtml(String(d))}</option>
        `).join("")}
      `;
    }

    // Clear / reset inputs
    const titleInput = document.getElementById("manualItemTitle");
    if (titleInput) titleInput.value = "";
    const costInput = document.getElementById("manualItemCost");
    if (costInput) costInput.value = "Free";
    const neighInput = document.getElementById("manualItemNeighborhood");
    if (neighInput) neighInput.value = "";
    const addrInput = document.getElementById("manualItemAddress");
    if (addrInput) addrInput.value = "";
    const urlInput = document.getElementById("manualItemUrl");
    if (urlInput) urlInput.value = "";
    const statusSelect = document.getElementById("manualItemBookingStatus");
    if (statusSelect) statusSelect.value = "unbooked";
    const refInput = document.getElementById("manualItemBookingRef");
    if (refInput) refInput.value = "";
    const hlInput = document.getElementById("manualItemHighlight");
    if (hlInput) hlInput.value = "";

    modal.style.display = "flex";
    if (titleInput) {
      setTimeout(() => titleInput.focus(), 80);
    }
  } catch (err) {
    console.error("Error opening add item modal:", err);
    modal.style.display = "flex";
  }
};

function initAddItemModal() {
  const modal = document.getElementById("addItemModal");
  if (!modal) return;

  const openBtn = document.getElementById("openAddItemBtn");
  const openHeaderBtn = document.getElementById("openAddItemHeaderBtn");
  const closeBtn = document.getElementById("closeAddItemBtn");
  const cancelBtn = document.getElementById("cancelAddItemBtn");
  const form = document.getElementById("addItemForm");

  const openHandler = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    openAddItemModal("todo");
  };

  if (openBtn) openBtn.addEventListener("click", openHandler);
  if (openHeaderBtn) openHeaderBtn.addEventListener("click", openHandler);
  if (closeBtn) closeBtn.addEventListener("click", () => modal.style.display = "none");
  if (cancelBtn) cancelBtn.addEventListener("click", () => modal.style.display = "none");

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.style.display === "flex") {
      modal.style.display = "none";
    }
  });

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!currentUser) {
        alert("🔒 Please sign in with your Google or Gmail account before adding custom stops.");
        if (window.openLogin) window.openLogin();
        return;
      }
      if (!currentTripId) {
        alert("Please select or create an itinerary first.");
        return;
      }

      const title = document.getElementById("manualItemTitle").value.trim();
      if (!title) {
        alert("Please enter an activity or venue title.");
        return;
      }

      const citySegmentId = document.getElementById("manualItemCity")?.value || null;
      const category = document.getElementById("manualItemCategory")?.value || "gems";
      const assignedDate = document.getElementById("manualItemDate")?.value || "todo";
      const cost = document.getElementById("manualItemCost")?.value.trim() || "Free";
      const neighborhood = document.getElementById("manualItemNeighborhood")?.value.trim() || null;
      const address = document.getElementById("manualItemAddress")?.value.trim() || null;
      const url = document.getElementById("manualItemUrl")?.value.trim() || null;
      const bookingStatus = document.getElementById("manualItemBookingStatus")?.value || "unbooked";
      const bookingRef = document.getElementById("manualItemBookingRef")?.value.trim() || null;
      const highlight = document.getElementById("manualItemHighlight")?.value.trim() || null;

      const payload = {
        title,
        city_segment_id: citySegmentId,
        category,
        assigned_date: assignedDate,
        cost,
        is_free: cost.toLowerCase() === "free" || cost === "$0" || cost === "0",
        neighborhood,
        address,
        url,
        booking_status: bookingStatus,
        booking_ref: bookingRef,
        highlight,
        description: highlight,
        source_platform: "Custom Entry"
      };

      const submitBtn = form.querySelector("button[type='submit']");
      const originalText = submitBtn ? submitBtn.textContent : "➕ Add to Itinerary";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "⏳ Adding...";
      }

      try {
        const res = await fetch(`/api/trips/${currentTripId}/items`, {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          modal.style.display = "none";
          form.reset();
          await refreshTrip();
        } else {
          const err = await res.json().catch(() => ({}));
          alert("Failed to add itinerary stop: " + (err.detail || res.statusText));
        }
      } catch (err) {
        alert("Error adding stop: " + err.message);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[m]);
}

function sanitizeUrl(rawUrl) {
  if (!rawUrl) return "";
  const trimmed = String(rawUrl).trim();
  if (!trimmed) return "";
  try {
    if (/^(javascript|data|vbscript):/i.test(trimmed)) {
      return "";
    }
    return trimmed;
  } catch (e) {
    return "";
  }
}

