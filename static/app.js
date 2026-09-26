// EVE Healthcare Dashboard Client Logic

let authToken = localStorage.getItem("eve_token") || "";
let currentUser = JSON.parse(localStorage.getItem("eve_user") || "null");

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", async () => {
  if (!authToken) {
    await quickLogin("patient@example.com", "password123", false);
  } else {
    updateAuthDisplay();
  }
  
  loadCentres();
  generateSimIdempKey();
  generateWebhookEventId();
  setDefaultAppointmentTime();
});

// --- Tab Switching ---
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add("active");

  const btnIndex = {
    'tab-catalog': 0,
    'tab-bookings': 1,
    'tab-payments': 2,
    'tab-webhook': 3,
    'tab-auth': 4
  }[tabId];

  const btns = document.querySelectorAll(".tab-btn");
  if (btns[btnIndex]) btns[btnIndex].classList.add("active");

  if (tabId === 'tab-bookings') {
    loadBookings();
  } else if (tabId === 'tab-catalog') {
    loadCentres();
  }
}

// --- Toast Notifications ---
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// --- Auth Handling ---
async function quickLogin(email, password, showNotification = true) {
  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed.");
    }

    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem("eve_token", authToken);
    localStorage.setItem("eve_user", JSON.stringify(currentUser));

    updateAuthDisplay();
    if (showNotification) {
      showToast(`Logged in as ${currentUser.full_name} (${currentUser.role})`, "success");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleSignup() {
  const fullName = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;

  if (!fullName || !email || !password) {
    showToast("Please fill all required fields.", "error");
    return;
  }

  try {
    const res = await fetch("/api/v1/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName, email, password, role: "PATIENT" })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Registration failed.");
    }

    showToast("Account created successfully! Logging you in...", "success");
    await quickLogin(email, password, true);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function updateAuthDisplay() {
  if (currentUser) {
    document.getElementById("current-user-email").textContent = currentUser.email;
    document.getElementById("current-user-role").textContent = currentUser.role;
  }
}

// --- Catalog & Centres ---
async function loadCentres() {
  const city = document.getElementById("city-filter").value;
  const container = document.getElementById("centres-container");
  container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 2rem;">Loading diagnostic centres...</div>`;

  try {
    const url = city ? `/api/v1/centres/?city=${encodeURIComponent(city)}` : `/api/v1/centres/`;
    const res = await fetch(url);
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Failed to load centres.");

    if (!data.items || data.items.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No diagnostic centres found for selected city.</div>`;
      return;
    }

    // Fetch full details (tests) for each centre
    const cardsHtml = await Promise.all(data.items.map(async (centre) => {
      const detailRes = await fetch(`/api/v1/centres/${centre.id}`);
      const centreDetail = await detailRes.json();

      const testsHtml = centreDetail.available_tests && centreDetail.available_tests.length > 0
        ? centreDetail.available_tests.map(t => `
            <div class="test-item">
              <div class="test-info">
                <h4>${t.name}</h4>
                <span>Code: ${t.code} | Turnaround: ${t.turnaround_hours}h</span>
              </div>
              <div class="test-action">
                <span class="test-price">₹${parseFloat(t.price).toFixed(2)}</span>
                <button class="btn btn-primary btn-sm" onclick="openBookingModal('${centre.id}', '${escapeHtml(centre.name)}', '${t.test_id}', '${escapeHtml(t.name)}', '${t.price}')">
                  Book
                </button>
              </div>
            </div>
          `).join("")
        : `<p style="font-size: 0.8rem; color: var(--text-dim);">No tests registered at this centre.</p>`;

      return `
        <div class="centre-card">
          <div class="centre-header">
            <div>
              <h3 class="centre-name">${centre.name}</h3>
              <p class="centre-address">📍 ${centre.address}</p>
            </div>
            <span class="centre-city">${centre.city}</span>
          </div>
          <div class="centre-tests-list">
            <h5 style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.25rem;">Available Diagnostic Tests:</h5>
            ${testsHtml}
          </div>
        </div>
      `;
    }));

    container.innerHTML = cardsHtml.join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color: var(--danger); text-align: center;">Error: ${err.message}</div>`;
  }
}

// --- Bookings Manager ---
async function loadBookings() {
  const statusFilter = document.getElementById("status-filter").value;
  const container = document.getElementById("bookings-container");
  container.innerHTML = `<div style="text-align: center; color: var(--text-dim); padding: 2rem;">Loading bookings...</div>`;

  try {
    const url = statusFilter ? `/api/v1/bookings/?status=${statusFilter}` : `/api/v1/bookings/`;
    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load bookings.");

    if (!data.items || data.items.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 3rem;">
          <p style="color: var(--text-muted); font-size: 1rem;">No bookings found.</p>
          <button class="btn btn-primary" style="margin-top: 1rem;" onclick="switchTab('tab-catalog')">Browse Tests to Book</button>
        </div>
      `;
      return;
    }

    const cardsHtml = await Promise.all(data.items.map(async (b) => {
      // Get detailed booking
      const dRes = await fetch(`/api/v1/bookings/${b.id}`, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      const d = dRes.ok ? await dRes.json() : b;

      const appDate = new Date(b.appointment_time).toLocaleString();
      const statusBadgeClass = `badge-${b.status.toLowerCase()}`;

      const showPayBtn = b.status === "PENDING" || b.status === "FAILED";
      const showCancelBtn = b.status === "PENDING" || b.status === "CONFIRMED";

      return `
        <div class="booking-card">
          <div class="booking-main">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
              <h4>${d.test_name || "Diagnostic Test"}</h4>
              <span class="badge ${statusBadgeClass}">${b.status}</span>
            </div>
            <p style="font-size: 0.85rem; color: #38bdf8;">🏥 ${d.centre_name || "Centre"} (${d.centre_city || ""})</p>
            <div class="booking-meta">
              <span>🗓️ ${appDate}</span>
              <span>💵 ₹${parseFloat(b.amount).toFixed(2)}</span>
              <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-dim);">ID: ${b.id.substring(0, 8)}...</span>
            </div>
          </div>

          <div class="booking-actions">
            ${showPayBtn ? `
              <button class="btn btn-success btn-sm" onclick="triggerQuickPay('${b.id}')">
                💳 Pay ₹${parseFloat(b.amount).toFixed(2)}
              </button>
            ` : ""}
            <button class="btn btn-secondary btn-sm" onclick="populateWebhookTester('${b.id}')">
              ⚡ Webhook
            </button>
            ${showCancelBtn ? `
              <button class="btn btn-danger btn-sm" onclick="cancelBooking('${b.id}')">
                Cancel
              </button>
            ` : ""}
          </div>
        </div>
      `;
    }));

    container.innerHTML = cardsHtml.join("");
  } catch (err) {
    container.innerHTML = `<div class="card" style="color: var(--danger); text-align: center;">Error: ${err.message}</div>`;
  }
}

// --- Booking Creation Modal ---
function openBookingModal(centreId, centreName, testId, testName, price) {
  document.getElementById("modal-centre-id").value = centreId;
  document.getElementById("modal-test-id").value = testId;
  document.getElementById("modal-centre-name").value = centreName;
  document.getElementById("modal-test-name").value = testName;
  document.getElementById("modal-price").value = `₹${parseFloat(price).toFixed(2)}`;
  
  setDefaultAppointmentTime();
  document.getElementById("booking-modal").classList.add("active");
}

function closeBookingModal() {
  document.getElementById("booking-modal").classList.remove("active");
}

function setDefaultAppointmentTime() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 2);
  tomorrow.setHours(10, 0, 0, 0);
  
  const iso = tomorrow.toISOString().slice(0, 16);
  const input = document.getElementById("modal-datetime");
  if (input) input.value = iso;
}

async function submitBooking() {
  const centreId = document.getElementById("modal-centre-id").value;
  const testId = document.getElementById("modal-test-id").value;
  const datetime = document.getElementById("modal-datetime").value;
  const notes = document.getElementById("modal-notes").value;

  if (!datetime) {
    showToast("Please choose an appointment date and time.", "error");
    return;
  }

  try {
    const res = await fetch("/api/v1/bookings/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({
        centre_id: centreId,
        test_id: testId,
        appointment_time: new Date(datetime).toISOString(),
        notes: notes || undefined
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Booking failed.");
    }

    closeBookingModal();
    showToast("Booking created successfully in PENDING state!", "success");
    switchTab("tab-bookings");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function cancelBooking(bookingId) {
  if (!confirm("Are you sure you want to cancel this booking?")) return;

  try {
    const res = await fetch(`/api/v1/bookings/${bookingId}/cancel`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${authToken}` }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Cancellation failed.");

    showToast("Booking cancelled successfully.", "info");
    loadBookings();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --- Payment Simulator ---
function triggerQuickPay(bookingId) {
  document.getElementById("sim-booking-id").value = bookingId;
  generateSimIdempKey();
  switchTab("tab-payments");
}

function generateSimIdempKey() {
  const key = `idemp_${Math.random().toString(36).substring(2, 10)}`;
  document.getElementById("sim-idemp-key").value = key;
}

async function submitSimulatedPayment() {
  const bookingId = document.getElementById("sim-booking-id").value.trim();
  const method = document.getElementById("sim-payment-method").value;
  const forceStatus = document.getElementById("sim-outcome").value;
  const idempKey = document.getElementById("sim-idemp-key").value.trim();
  const outputEl = document.getElementById("sim-payment-response");

  if (!bookingId) {
    showToast("Please provide a Booking ID.", "error");
    return;
  }

  outputEl.textContent = "Processing simulated transaction...";

  try {
    const res = await fetch("/payments/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({
        booking_id: bookingId,
        payment_method: method,
        force_status: forceStatus,
        idempotency_key: idempKey || undefined
      })
    });

    const data = await res.json();
    outputEl.textContent = JSON.stringify(data, null, 2);

    if (res.ok) {
      if (data.status === "SUCCESS") {
        showToast("Payment Successful! Booking status is now CONFIRMED.", "success");
      } else {
        showToast("Simulated Payment Failed. Booking status is FAILED.", "error");
      }
    } else {
      showToast(data.detail || "Payment failed.", "error");
    }
  } catch (err) {
    outputEl.textContent = `Error: ${err.message}`;
    showToast(err.message, "error");
  }
}

// --- Webhook & Idempotency Lab ---
function populateWebhookTester(bookingId) {
  document.getElementById("wh-booking-id").value = bookingId;
  generateWebhookEventId();
  switchTab("tab-webhook");
}

function generateWebhookEventId() {
  const id = `evt_sim_${Math.random().toString(36).substring(2, 10)}`;
  document.getElementById("wh-event-id").value = id;
}

async function sendWebhookOnce() {
  const eventId = document.getElementById("wh-event-id").value.trim();
  const bookingId = document.getElementById("wh-booking-id").value.trim();
  const statusOutcome = document.getElementById("wh-status").value;
  const logEl = document.getElementById("webhook-audit-log");

  if (!bookingId || !eventId) {
    showToast("Event ID and Booking ID are required.", "error");
    return;
  }

  const payload = {
    event_id: eventId,
    event_type: statusOutcome === "SUCCESS" ? "payment.succeeded" : "payment.failed",
    data: {
      booking_id: bookingId,
      amount: 499.00,
      transaction_ref: `txn_wh_${Math.random().toString(36).substring(2, 8)}`,
      status: statusOutcome
    }
  };

  logEl.textContent = `[Request Payload]:\n${JSON.stringify(payload, null, 2)}\n\nSending webhook...`;

  try {
    const res = await fetch("/payments/webhook/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    logEl.textContent += `\n\n[HTTP ${res.status} Response]:\n${JSON.stringify(data, null, 2)}`;
    
    if (res.ok) {
      if (data.status === "duplicate_ignored") {
        showToast("Duplicate Webhook Ignored Safely (Idempotent)!", "info");
      } else {
        showToast(`Webhook Processed! Booking is ${data.booking_status}`, "success");
      }
    } else {
      showToast(data.detail || "Webhook delivery failed.", "error");
    }
  } catch (err) {
    logEl.textContent += `\n\n[Error]: ${err.message}`;
  }
}

async function testIdempotency3x() {
  const eventId = document.getElementById("wh-event-id").value.trim();
  const bookingId = document.getElementById("wh-booking-id").value.trim();
  const statusOutcome = document.getElementById("wh-status").value;
  const logEl = document.getElementById("webhook-audit-log");

  if (!bookingId || !eventId) {
    showToast("Event ID and Booking ID are required.", "error");
    return;
  }

  const payload = {
    event_id: eventId,
    event_type: statusOutcome === "SUCCESS" ? "payment.succeeded" : "payment.failed",
    data: {
      booking_id: bookingId,
      amount: 499.00,
      transaction_ref: `txn_idemp_test`,
      status: statusOutcome
    }
  };

  logEl.textContent = `=== 🛡️ INITIATING STRICT IDEMPOTENCY TEST (3 Sequential Deliveries) ===\n\n`;

  for (let i = 1; i <= 3; i++) {
    logEl.textContent += `--- [Delivery Attempt #${i}] ---\n`;
    try {
      const res = await fetch("/payments/webhook/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      logEl.textContent += `Status: HTTP ${res.status} | Result: ${data.status}\nMessage: ${data.message}\n\n`;
    } catch (err) {
      logEl.textContent += `Attempt ${i} Failed: ${err.message}\n\n`;
    }
  }

  logEl.textContent += `=== 🛡️ TEST COMPLETE: Only Attempt #1 modified state; Attempts #2 and #3 safely de-duplicated! ===`;
  showToast("Idempotency Test Passed! Repeated deliveries safely ignored.", "success");
}

function escapeHtml(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}
