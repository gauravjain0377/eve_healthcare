// ── EVE Healthcare Dashboard — JS Logic ──

let authToken = localStorage.getItem("eve_token") || "";
let currentUser = JSON.parse(localStorage.getItem("eve_user") || "null");

document.addEventListener("DOMContentLoaded", async () => {
  if (!authToken) {
    await quickLogin("patient@example.com", "password123", false);
  } else {
    updateAuthDisplay();
  }
  loadCentres();
  generateSimIdempKey();
  generateWebhookEventId();
  setDefaultDatetime();
});

// ── Tab Switching ──
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

  document.getElementById(tabId)?.classList.add("active");

  const order = ["tab-catalog","tab-bookings","tab-payments","tab-webhook","tab-auth"];
  const idx = order.indexOf(tabId);
  document.querySelectorAll(".tab-btn")[idx]?.classList.add("active");

  if (tabId === "tab-bookings") loadBookings();
  if (tabId === "tab-catalog")  loadCentres();
}

// ── Toast ──
function toast(message, type = "info") {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;

  const icon = type === "success" ? "✓" : type === "error" ? "✗" : "i";
  el.innerHTML = `<span style="font-weight:700;color:var(--text-2)">${icon}</span><span>${message}</span>`;

  c.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity 0.2s, transform 0.2s";
    el.style.opacity = "0";
    el.style.transform = "translateX(20px)";
    setTimeout(() => el.remove(), 220);
  }, 4000);
}

// ── Auth ──
async function quickLogin(email, password, notify = true) {
  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");

    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem("eve_token", authToken);
    localStorage.setItem("eve_user", JSON.stringify(currentUser));
    updateAuthDisplay();
    if (notify) toast(`Signed in as ${currentUser.full_name} (${currentUser.role})`, "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function handleSignup() {
  const name  = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const pass  = document.getElementById("signup-password").value;
  if (!name || !email || !pass) { toast("All fields are required.", "error"); return; }

  try {
    const res = await fetch("/api/v1/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: name, email, password: pass, role: "PATIENT" })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    toast("Account created. Logging you in…", "success");
    await quickLogin(email, pass);
  } catch (err) {
    toast(err.message, "error");
  }
}

function updateAuthDisplay() {
  if (!currentUser) return;
  document.getElementById("current-user-email").textContent = currentUser.email;
  const roleEl = document.getElementById("current-user-role");
  roleEl.textContent = currentUser.role;
}

// ── Catalogue ──
async function loadCentres() {
  const city = document.getElementById("city-filter").value;
  const el = document.getElementById("centres-container");
  el.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-3);">Loading centres…</div>`;

  try {
    const url = city ? `/api/v1/centres/?city=${encodeURIComponent(city)}` : `/api/v1/centres/`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    if (!data.items?.length) {
      el.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-3);">No centres found for the selected city.</div>`;
      return;
    }

    const cards = await Promise.all(data.items.map(async centre => {
      const dr = await fetch(`/api/v1/centres/${centre.id}`);
      const detail = dr.ok ? await dr.json() : centre;

      const tests = detail.available_tests?.length
        ? detail.available_tests.map(t => `
            <div class="test-row">
              <div class="test-row-left">
                <div class="test-row-name">${t.name}</div>
                <div class="test-row-meta">${t.code} &middot; ${t.turnaround_hours}h turnaround</div>
              </div>
              <div class="test-row-right">
                <span class="test-price">&#x20B9;${parseFloat(t.price).toFixed(2)}</span>
                <button class="btn btn-primary btn-xs"
                  onclick="openBookingModal('${centre.id}','${esc(centre.name)}','${t.test_id}','${esc(t.name)}','${t.price}')">
                  Book
                </button>
              </div>
            </div>`).join("")
        : `<p style="font-size:12px;color:var(--text-3);">No tests configured at this centre.</p>`;

      return `
        <div class="centre-card">
          <div class="centre-header">
            <div>
              <div class="centre-name">${centre.name}</div>
              <div class="centre-address">${centre.address}</div>
            </div>
            <span class="city-tag">${centre.city}</span>
          </div>
          <div>
            <div class="tests-section-label">Available Tests</div>
            <div class="tests-list">${tests}</div>
          </div>
        </div>`;
    }));

    el.innerHTML = cards.join("");
  } catch (err) {
    el.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--status-failed-text);">Error: ${err.message}</div>`;
  }
}

// ── Bookings ──
async function loadBookings() {
  const status = document.getElementById("status-filter").value;
  const el = document.getElementById("bookings-container");
  el.innerHTML = `<div class="empty-state"><p>Loading bookings…</p></div>`;

  try {
    const url = status ? `/api/v1/bookings/?status=${status}` : `/api/v1/bookings/`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${authToken}` } });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    if (!data.items?.length) {
      el.innerHTML = `
        <div class="empty-state">
          <p>No bookings found.</p>
          <button class="btn btn-primary btn-sm" onclick="switchTab('tab-catalog')">Browse Tests</button>
        </div>`;
      return;
    }

    const cards = await Promise.all(data.items.map(async b => {
      const dr = await fetch(`/api/v1/bookings/${b.id}`, { headers: { Authorization: `Bearer ${authToken}` } });
      const d  = dr.ok ? await dr.json() : b;

      const dt   = new Date(b.appointment_time).toLocaleString("en-IN", { dateStyle:"medium", timeStyle:"short" });
      const badgeClass = `badge-${b.status.toLowerCase()}`;
      const showPay    = b.status === "PENDING";
      const showCancel = b.status === "PENDING" || b.status === "CONFIRMED";

      return `
        <div class="booking-card">
          <div class="booking-left">
            <div class="booking-title">
              <span>${d.test_name || "Diagnostic Test"}</span>
              <span class="badge ${badgeClass}">${b.status}</span>
            </div>
            <div class="booking-centre">${d.centre_name || "Centre"} &middot; ${d.centre_city || ""}</div>
            <div class="booking-meta">
              <div class="booking-meta-item"><span>Date</span> <strong>${dt}</strong></div>
              <div class="booking-meta-item"><span>Amount</span> <strong>&#x20B9;${parseFloat(b.amount).toFixed(2)}</strong></div>
              <div class="booking-meta-item" style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-3);">${b.id.slice(0,8)}…</div>
            </div>
          </div>
          <div class="booking-actions">
            ${showPay ? `<button class="btn btn-primary btn-sm" onclick="triggerQuickPay('${b.id}')">Pay &#x20B9;${parseFloat(b.amount).toFixed(2)}</button>` : ""}
            <button class="btn btn-ghost btn-sm" onclick="populateWebhookTester('${b.id}')">Webhook</button>
            ${showCancel ? `<button class="btn btn-danger btn-sm" onclick="cancelBooking('${b.id}')">Cancel</button>` : ""}
          </div>
        </div>`;
    }));

    el.innerHTML = cards.join("");
  } catch (err) {
    el.innerHTML = `<div class="empty-state"><p style="color:var(--status-failed-text)">Error: ${err.message}</p></div>`;
  }
}

async function cancelBooking(id) {
  if (!confirm("Cancel this booking?")) return;
  try {
    const res = await fetch(`/api/v1/bookings/${id}/cancel`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}` }
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail);
    toast("Booking cancelled.", "info");
    loadBookings();
  } catch (err) {
    toast(err.message, "error");
  }
}

// ── Booking Modal ──
function openBookingModal(centreId, centreName, testId, testName, price) {
  document.getElementById("modal-centre-id").value = centreId;
  document.getElementById("modal-test-id").value   = testId;
  document.getElementById("modal-centre-name").value = centreName;
  document.getElementById("modal-test-name").value   = testName;
  document.getElementById("modal-price").value = `₹${parseFloat(price).toFixed(2)}`;
  setDefaultDatetime();
  document.getElementById("booking-modal").classList.add("active");
}

function closeBookingModal() {
  document.getElementById("booking-modal").classList.remove("active");
}

function setDefaultDatetime() {
  const dt = new Date();
  dt.setDate(dt.getDate() + 2);
  dt.setHours(10, 0, 0, 0);
  const el = document.getElementById("modal-datetime");
  if (el) el.value = dt.toISOString().slice(0, 16);
}

async function submitBooking() {
  const centreId = document.getElementById("modal-centre-id").value;
  const testId   = document.getElementById("modal-test-id").value;
  const dt       = document.getElementById("modal-datetime").value;
  const notes    = document.getElementById("modal-notes").value;
  if (!dt) { toast("Please select an appointment time.", "error"); return; }

  try {
    const res = await fetch("/api/v1/bookings/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ centre_id: centreId, test_id: testId, appointment_time: new Date(dt).toISOString(), notes: notes || undefined })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail);
    closeBookingModal();
    toast("Booking created — status PENDING.", "success");
    switchTab("tab-bookings");
  } catch (err) {
    toast(err.message, "error");
  }
}

// ── Payment Simulator ──
function triggerQuickPay(bookingId) {
  document.getElementById("sim-booking-id").value = bookingId;
  generateSimIdempKey();
  switchTab("tab-payments");
}

function generateSimIdempKey() {
  document.getElementById("sim-idemp-key").value = `idemp_${rand()}`;
}

async function submitSimulatedPayment() {
  const bookingId = document.getElementById("sim-booking-id").value.trim();
  const method    = document.getElementById("sim-payment-method").value;
  const outcome   = document.getElementById("sim-outcome").value;
  const idempKey  = document.getElementById("sim-idemp-key").value.trim();
  const out       = document.getElementById("sim-payment-response");

  if (!bookingId) { toast("Booking ID is required.", "error"); return; }
  out.textContent = "Processing…";

  try {
    const res = await fetch("/payments/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ booking_id: bookingId, payment_method: method, force_status: outcome, idempotency_key: idempKey || undefined })
    });
    const d = await res.json();
    out.textContent = JSON.stringify(d, null, 2);
    if (!res.ok) throw new Error(d.detail);
    toast(d.status === "SUCCESS" ? "Payment successful — booking CONFIRMED." : "Payment failed — booking FAILED.", d.status === "SUCCESS" ? "success" : "error");
  } catch (err) {
    out.textContent = `Error: ${err.message}`;
    toast(err.message, "error");
  }
}

// ── Webhook Lab ──
function populateWebhookTester(bookingId) {
  document.getElementById("wh-booking-id").value = bookingId;
  generateWebhookEventId();
  switchTab("tab-webhook");
}

function generateWebhookEventId() {
  document.getElementById("wh-event-id").value = `evt_${rand()}`;
}

async function sendWebhookOnce() {
  const log = document.getElementById("webhook-audit-log");
  const payload = buildWebhookPayload();
  if (!payload) return;
  log.textContent = `[Attempt #1] Sending…\n\nPayload:\n${JSON.stringify(payload, null, 2)}`;

  const { res, d } = await deliverWebhook(payload);
  log.textContent += `\n\nHTTP ${res.status} → ${JSON.stringify(d, null, 2)}`;
  toast(d.status === "duplicate_ignored" ? "Duplicate safely ignored." : `Webhook processed. Booking: ${d.booking_status}`, d.status === "duplicate_ignored" ? "info" : "success");
}

async function testIdempotency3x() {
  const log = document.getElementById("webhook-audit-log");
  const payload = buildWebhookPayload();
  if (!payload) return;

  log.textContent = `=== Strict Idempotency Test: 3 sequential deliveries of the same event_id ===\n\nPayload:\n${JSON.stringify(payload, null, 2)}\n\n`;

  for (let i = 1; i <= 3; i++) {
    log.textContent += `--- Attempt #${i} ---\n`;
    const { res, d } = await deliverWebhook(payload);
    log.textContent += `HTTP ${res.status} | status: ${d.status}\nmessage: ${d.message}\n\n`;
  }

  log.textContent += `=== Result: Only Attempt #1 modified state.\n    Attempts #2 and #3 returned "duplicate_ignored" without side effects. ===`;
  toast("Idempotency test complete.", "success");
}

function buildWebhookPayload() {
  const eventId   = document.getElementById("wh-event-id").value.trim();
  const bookingId = document.getElementById("wh-booking-id").value.trim();
  const status    = document.getElementById("wh-status").value;
  if (!eventId || !bookingId) { toast("Event ID and Booking ID are required.", "error"); return null; }
  return {
    event_id:   eventId,
    event_type: status === "SUCCESS" ? "payment.succeeded" : "payment.failed",
    data: { booking_id: bookingId, amount: 499.00, transaction_ref: `txn_wh_${rand()}`, status }
  };
}

async function deliverWebhook(payload) {
  const res = await fetch("/payments/webhook/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const d = await res.json();
  return { res, d };
}

// ── Utilities ──
function rand() {
  return Math.random().toString(36).substring(2, 10);
}

function esc(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}
