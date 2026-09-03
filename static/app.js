// Travel Scout Multi-City Collaborative Client
let currentTripId = null;
let currentUser = null;
let currentTripData = null;
let leafletMap = null;
let mapMarkersGroup = null;
let mapRouteGroup = null;

document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  initModals();
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
    const res = await fetch("/auth/me");
    const data = await res.json();
    currentUser = data.current_user;

    const avatarEl = document.getElementById("currentUserAvatar");
    const nameEl = document.getElementById("currentUserName");
    if (avatarEl && currentUser) {
      avatarEl.style.background = currentUser.avatar_color || "#38bdf8";
      avatarEl.textContent = currentUser.name.slice(0, 2).toUpperCase();
    }
    if (nameEl && currentUser) {
      nameEl.textContent = currentUser.name;
    }

    const switcher = document.getElementById("userSwitcherSelect");
    if (switcher) {
      switcher.addEventListener("change", async (e) => {
        const val = e.target.value;
        if (val === "new") {
          const name = prompt("Enter new collaborator name (e.g. Alex Rivera):");
          const email = prompt("Enter collaborator email (e.g. alex@gmail.com):");
          if (name && email) {
            await loginAs(email, name);
          }
        } else if (val) {
          const userObj = data.available_users.find(u => u.email === val);
          if (userObj) {
            await loginAs(userObj.email, userObj.name);
          }
        }
      });
    }
  } catch (err) {
    console.error("Auth check error:", err);
  }
}

async function loginAs(email, name) {
  try {
    await fetch("/auth/dev-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name })
    });
    window.location.reload();
  } catch (err) {
    alert("Login failed: " + err.message);
  }
}

// 3. Load Trip Details & Switcher
async function loadTripsDropdown() {
  const switcher = document.getElementById("tripSwitcherSelect");
  if (!switcher) return;
  try {
    const res = await fetch("/api/trips");
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
    const res = await fetch("/api/trips");
    const trips = await res.json();
    if (trips.length > 0) {
      currentTripId = trips[0].id;
      await loadTripsDropdown();
      await refreshTrip();
    }
  } catch (err) {
    console.error("Failed to load initial trip:", err);
  }
}

async function refreshTrip() {
  if (!currentTripId) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}`);
    currentTripData = await res.json();

    if (currentTripData.trip) {
      const sub = document.getElementById("tripSubtitle");
      if (sub) {
        const desc = currentTripData.trip.description ? ` &bull; ${escapeHtml(currentTripData.trip.description)}` : "";
        sub.innerHTML = `${escapeHtml(currentTripData.trip.title)}${desc}`;
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
    if (leafletMap) renderMapLocations();
  } catch (err) {
    console.error("Failed to refresh trip:", err);
  }
}

// 4. Render Collaborators Avatar Stack
function renderCollaborators() {
  const bar = document.getElementById("collaboratorsBar");
  if (!bar || !currentTripData) return;

  bar.innerHTML = currentTripData.collaborators.map(c => `
    <div class="collab-avatar" style="background:${c.avatar_color || '#38bdf8'};" title="${escapeHtml(c.name)} (${escapeHtml(c.email)}) - ${c.role}">
      ${c.name.slice(0, 2).toUpperCase()}
    </div>
  `).join("");
}

// 5. Render Cities & Stays Manager Tab
function renderCitiesTab() {
  const container = document.getElementById("citiesList");
  if (!container || !currentTripData) return;

  if (currentTripData.cities.length === 0) {
    container.innerHTML = `<p style="color:var(--text-muted); text-align:center; padding:3rem;">No destination cities added yet. Click "Add Destination City" above to start your journey!</p>`;
    return;
  }

  container.innerHTML = currentTripData.cities.map(city => `
    <div class="city-card">
      <div class="city-card-header">
        <div class="city-card-title-group">
          <div class="city-order-badge">${city.order_index}</div>
          <div>
            <div class="city-name">${escapeHtml(city.city_name)}, <span style="color:var(--text-muted); font-size:1rem; font-weight:400;">${escapeHtml(city.country)}</span></div>
            <div class="city-dates">📅 ${city.start_date} &rarr; ${city.end_date}</div>
          </div>
        </div>
        <div style="display:flex; gap:0.5rem;">
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
        ${city.stays.map(stay => `
          <div class="stay-box">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
              <div class="stay-box-title">🏨 ${escapeHtml(stay.name)}</div>
              ${city.stays.length > 1 ? `
                <button onclick="deleteStay('${stay.id}')" style="background:none; border:none; color:#f43f5e; cursor:pointer; font-size:0.8rem;" title="Delete this stay">&times;</button>
              ` : ''}
            </div>
            <div class="stay-box-dates">Check-in: ${stay.start_date} &bull; Check-out: ${stay.end_date}</div>
            <div class="stay-box-address">📍 ${escapeHtml(stay.address)}</div>
            ${stay.notes ? `<div style="font-size:0.75rem; color:#94a3b8; margin-top:0.3rem;"><em>${escapeHtml(stay.notes)}</em></div>` : ''}
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
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
    todoGrid.innerHTML = `<p style="grid-column:1/-1; color:var(--text-muted); font-size:0.85rem; text-align:center; padding:1.5rem 0;">No unscheduled items in this city. Scout new places or assign dates below!</p>`;
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

    return `
      <div class="day-block">
        <div class="day-header">
          <div class="day-title">📅 Date: <strong>${day.date}</strong></div>
          <span class="badge" style="background:rgba(56,189,248,0.15); color:#38bdf8;">${dayItems.length} Stops</span>
        </div>
        ${dayItems.length === 0 ? `
          <p style="color:var(--text-muted); font-size:0.85rem; padding:1rem 0;">No stops scheduled for this day yet. Select a date from To-Do above!</p>
        ` : `
          <div class="cards-grid">
            ${dayItems.map(it => renderCard(it, availDates)).join("")}
          </div>
        `}
      </div>
    `;
  }).join("");

  attachCardEventListeners();
}

function renderCard(item, availableDates) {
  const author = item.added_by || { name: "Traveler", avatar_color: "#38bdf8" };
  const transit = item.transit || {};

  return `
    <div class="itin-card" data-item-id="${item.id}">
      <div class="card-top-row">
        <div>
          <div class="card-title">${escapeHtml(item.title)}</div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.2rem;">
            <span>📍 ${escapeHtml(item.neighborhood || item.city_name || 'City')}</span> &bull; 
            <span style="color:#fbbf24; font-weight:600;">${item.cost || 'Free'}</span>
          </div>
        </div>
        <span class="card-city-badge">${escapeHtml(item.city_name || 'General')}</span>
      </div>

      <!-- Date-Matched Hotel Transit Box -->
      <div class="card-transit-box">
        <div>🚶 <strong>${transit.miles || '?'} mi from ${escapeHtml(transit.stay_name || 'hotel')}</strong> (${transit.walk_time || ''})</div>
        <div style="font-size:0.75rem; margin-top:0.15rem;">${escapeHtml(transit.best_mode || transit.summary || '')}</div>
      </div>

      ${item.highlight ? `
        <div style="font-size:0.82rem; color:#cbd5e1; line-height:1.4;">
          ${escapeHtml(item.highlight)}
        </div>
      ` : ''}

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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ assigned_date: newDate })
        });
        await refreshTrip();
      } catch (err) {
        alert("Failed to assign date: " + err.message);
      }
    });
  });
}

// 7. City Actions (Add & Delete)
async function deleteCity(cityId, cityName) {
  if (!confirm(`Are you sure you want to remove ${cityName} and all its stays from your journey?`)) return;

  try {
    const res = await fetch(`/api/trips/${currentTripId}/cities/${cityId}`, { method: "DELETE" });
    if (res.ok) {
      await refreshTrip();
    } else {
      alert("Failed to delete city");
    }
  } catch (err) {
    alert("Error deleting city: " + err.message);
  }
}

async function deleteStay(stayId) {
  if (!confirm("Remove this hotel stay location?")) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}/stays/${stayId}`, { method: "DELETE" });
    if (res.ok) await refreshTrip();
  } catch (err) {
    alert("Error deleting stay: " + err.message);
  }
}

async function deleteItem(itemId) {
  if (!confirm("Delete this stop from the itinerary?")) return;
  try {
    const res = await fetch(`/api/trips/${currentTripId}/items/${itemId}`, { method: "DELETE" });
    if (res.ok) await refreshTrip();
  } catch (err) {
    alert("Error deleting item: " + err.message);
  }
}

// 8. Modals Management
function initModals() {
  const addCityModal = document.getElementById("addCityModal");
  const openAddCityBtn = document.getElementById("openAddCityBtn");
  const closeAddCityBtn = document.getElementById("closeAddCityBtn");
  const cancelAddCityBtn = document.getElementById("cancelAddCityBtn");
  const addCityForm = document.getElementById("addCityForm");

  if (openAddCityBtn) openAddCityBtn.addEventListener("click", () => addCityModal.style.display = "flex");
  if (closeAddCityBtn) closeAddCityBtn.addEventListener("click", () => addCityModal.style.display = "none");
  if (cancelAddCityBtn) cancelAddCityBtn.addEventListener("click", () => addCityModal.style.display = "none");

  if (addCityForm) {
    addCityForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        city_name: document.getElementById("newCityName").value.trim(),
        country: document.getElementById("newCityCountry").value.trim(),
        start_date: document.getElementById("newCityStart").value,
        end_date: document.getElementById("newCityEnd").value,
        hotel_name: document.getElementById("newCityHotel").value.trim(),
        hotel_address: document.getElementById("newCityAddress").value.trim(),
      };

      try {
        const res = await fetch(`/api/trips/${currentTripId}/cities`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          addCityModal.style.display = "none";
          addCityForm.reset();
          await refreshTrip();
        } else {
          alert("Failed to add city");
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          addStayModal.style.display = "none";
          addStayForm.reset();
          await refreshTrip();
        }
      } catch (err) {
        alert("Error adding stay: " + err.message);
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          inviteModal.style.display = "none";
          inviteForm.reset();
          alert(`Invitation sent to ${payload.email}! They can now view and edit this itinerary.`);
          await refreshTrip();
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, description })
        });
        if (res.ok) {
          editTripModal.style.display = "none";
          await loadTripsDropdown();
          await refreshTrip();
        } else {
          alert("Failed to update trip details");
        }
      } catch (err) {
        alert("Error updating trip: " + err.message);
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
      const hotel_name = document.getElementById("newTripHotel").value.trim();

      try {
        const res = await fetch("/api/trips", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title,
            first_city_name,
            start_date,
            end_date,
            hotel_name,
            hotel_address: hotel_name
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
          alert("Failed to create new trip");
        }
      } catch (err) {
        alert("Error creating trip: " + err.message);
      }
    });
  }
}

function openAddStayModal(cityId, cityName) {
  document.getElementById("stayCityId").value = cityId;
  const modal = document.getElementById("addStayModal");
  modal.querySelector("h3").textContent = `🏨 Add Hotel / Stay in ${cityName}`;
  modal.style.display = "flex";
}

// 9. Dropdown helpers
function populateCityDropdowns() {
  const itinSelect = document.getElementById("itineraryCityFilter");
  const scoutSelect = document.getElementById("scoutTargetCity");
  const mapCitySelect = document.getElementById("mapCityJump");

  if (!currentTripData) return;

  const cities = currentTripData.cities;

  if (itinSelect) {
    const prev = itinSelect.value;
    itinSelect.innerHTML = `<option value="all">🌐 All Cities (Unified Timeline)</option>` +
      cities.map(c => `<option value="${c.id}">${escapeHtml(c.city_name)}</option>`).join("");
    itinSelect.value = prev || "all";
    itinSelect.onchange = () => renderItineraryTab();
  }

  if (scoutSelect) {
    scoutSelect.innerHTML = cities.map(c => `<option value="${escapeHtml(c.city_name)}">🏙️ ${escapeHtml(c.city_name)}</option>`).join("");
  }

  if (mapCitySelect) {
    mapCitySelect.innerHTML = `<option value="all">🌍 Whole Journey Overview</option>` +
      cities.map(c => `<option value="${c.id}">${escapeHtml(c.city_name)}</option>`).join("");
  }
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
          headers: { "Content-Type": "application/json" },
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
          grid.innerHTML = data.results.map(r => `
            <div class="itin-card">
              <div class="card-top-row">
                <div class="card-title">${escapeHtml(r.title)}</div>
                <span class="card-city-badge">${escapeHtml(city)}</span>
              </div>
              <div style="font-size:0.8rem; color:#38bdf8;">Platform: <strong>${r.source_platform}</strong></div>
              <p style="font-size:0.82rem; color:var(--text-muted);">${escapeHtml(r.highlight)}</p>
              <div class="card-footer-actions">
                <button class="btn btn-primary btn-sm" onclick='addToWishlist(${JSON.stringify(r).replace(/'/g, "&apos;")})'>
                  ➕ Add to To-Do List
                </button>
              </div>
            </div>
          `).join("");
        }
      } catch (err) {
        loading.style.display = "none";
        grid.innerHTML = `<p style="color:#f43f5e; text-align:center;">Error: ${err.message}</p>`;
      }
    });
  }

  // Quick chips
  document.querySelectorAll(".scout-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const city = chip.dataset.city;
      const q = chip.dataset.q;
      const ch = chip.dataset.ch;
      if (city && citySelect) citySelect.value = city;
      if (q && queryInput) queryInput.value = q;
      if (ch && chSelect) chSelect.value = ch;
      btn.click();
    });
  });

  // Daily Scan
  if (dailyBtn) {
    dailyBtn.addEventListener("click", async () => {
      dailyBtn.disabled = true;
      dailyBtn.textContent = "⏳ Scanning all trip destination cities...";
      try {
        const res = await fetch(`/api/trips/${currentTripId}/scan/daily`, { method: "POST" });
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
}

async function addToWishlist(itemObj) {
  try {
    // Find city ID
    let cityId = null;
    if (currentTripData) {
      const foundCity = currentTripData.cities.find(c => c.city_name.toLowerCase() === (itemObj.city_name || "").toLowerCase());
      if (foundCity) cityId = foundCity.id;
      else if (currentTripData.cities.length > 0) cityId = currentTripData.cities[0].id;
    }

    const payload = {
      city_segment_id: cityId,
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert(`Added "${itemObj.title}" to your To-Do Wishlist!`);
      await refreshTrip();
    }
  } catch (err) {
    alert("Failed to add to wishlist: " + err.message);
  }
}

// 11. Multi-City Leaflet Map
function initMap() {
  const mapEl = document.getElementById("scoutMap");
  if (!mapEl || typeof L === "undefined") return;

  leafletMap = L.map("scoutMap", {
    center: [39.5, -8.0], // Center on Portugal
    zoom: 7,
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
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
    });
  }
}

async function renderMapLocations() {
  if (!leafletMap || !currentTripId) return;

  try {
    const res = await fetch(`/api/trips/${currentTripId}/map`);
    const data = await res.json();

    mapMarkersGroup.clearLayers();
    mapRouteGroup.clearLayers();

    const sidebarList = document.getElementById("mapSidebarList");
    const sidebarCount = document.getElementById("mapSidebarCount");
    if (sidebarCount) sidebarCount.textContent = `${data.items.length} Stops`;

    // Stays / Hotels Markers
    data.stays.forEach(s => {
      if (s.lat && s.lon) {
        const hotelIcon = L.divIcon({
          className: 'custom-hotel-pin',
          html: `<div style="background:#0284c7; color:#fff; border:2px solid #fff; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-size:14px; box-shadow:0 3px 10px rgba(0,0,0,0.6);">🏨</div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        });

        L.marker([s.lat, s.lon], { icon: hotelIcon })
          .addTo(mapMarkersGroup)
          .bindPopup(`
            <div style="color:#020617; padding:0.4rem;">
              <strong style="color:#0284c7; font-size:1rem;">🏨 ${escapeHtml(s.name)}</strong>
              <div style="font-size:0.8rem; color:#475569;">📍 ${escapeHtml(s.address)}</div>
              <div style="font-size:0.75rem; color:#d97706; font-weight:bold; margin-top:0.3rem;">📅 Active: ${s.start_date} &rarr; ${s.end_date}</div>
              ${s.notes ? `<div style="font-size:0.75rem; color:#64748b; margin-top:0.2rem;">${escapeHtml(s.notes)}</div>` : ''}
            </div>
          `);
      }
    });

    // Item markers
    const sidebarItemsHtml = [];
    data.items.forEach(it => {
      if (it.lat && it.lon) {
        const itemIcon = L.divIcon({
          className: 'custom-item-pin',
          html: `<div style="background:#f43f5e; color:#fff; border:2px solid #fff; border-radius:50%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; font-size:11px; box-shadow:0 3px 8px rgba(0,0,0,0.5);">📍</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });

        L.marker([it.lat, it.lon], { icon: itemIcon })
          .addTo(mapMarkersGroup)
          .bindPopup(`
            <div style="color:#020617; padding:0.4rem;">
              <strong style="font-size:0.95rem;">${escapeHtml(it.title)}</strong>
              <div style="font-size:0.8rem; color:#475569;">${escapeHtml(it.city_name)} &bull; ${it.cost}</div>
              <div style="font-size:0.75rem; color:#0284c7; margin-top:0.3rem;">👤 Added by: ${escapeHtml(it.added_by.name)}</div>
            </div>
          `);

        sidebarItemsHtml.push(`
          <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:6px; padding:0.6rem; cursor:pointer;" onclick="zoomToCoord(${it.lat}, ${it.lon})">
            <div style="font-weight:600; font-size:0.85rem; color:var(--text-main);">${escapeHtml(it.title)}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(it.city_name)} &bull; ${it.cost}</div>
          </div>
        `);
      }
    });

    if (sidebarList) sidebarList.innerHTML = sidebarItemsHtml.join("");
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
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[m]);
}
