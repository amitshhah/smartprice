/**
 * SmartPrice — Frontend JS
 * Features: tab switching, search, link compare, price chart, buy now, save
 */

// ── State ──────────────────────────────────────────────────────────────────
let allResults   = [];
let savedItems   = JSON.parse(localStorage.getItem("sp_saved") || "[]");
let activeFilter = "all";
let activeSort   = "price-asc";
let loadingTimer = null;

// ── Init ───────────────────────────────────────────────────────────────────
updateSavedBadge();

document.getElementById("keywordInput").addEventListener("keydown", e => {
  if (e.key === "Enter") doKeywordSearch();
});
document.getElementById("linkInput").addEventListener("keydown", e => {
  if (e.key === "Enter") doLinkCompare();
});
document.getElementById("filterRow").addEventListener("click", e => {
  const btn = e.target.closest(".ftab");
  if (!btn) return;
  document.querySelectorAll(".ftab").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");
  activeFilter = btn.dataset.store;
  applySortFilter();
});

// ── Tab Switching ──────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".ntab").forEach(b => b.classList.remove("active"));

  document.getElementById(`tab-${tab}`).classList.add("active");
  document.querySelector(`.ntab[data-tab="${tab}"]`).classList.add("active");

  if (tab === "saved") renderSaved();
}

// ── Search ─────────────────────────────────────────────────────────────────
function quickSearch(q) {
  switchTab("search");
  document.getElementById("keywordInput").value = q;
  doKeywordSearch();
}

async function doKeywordSearch() {
  const q = document.getElementById("keywordInput").value.trim();
  if (!q) { shakeInput("keywordInput"); return; }

  showLoading();
  hideSourcePanel();

  try {
    const res  = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Search failed");
    handleResults(data);
  } catch (err) {
    showError(err.message);
  }
}

// ── Link Compare ───────────────────────────────────────────────────────────
async function doLinkCompare() {
  const url = document.getElementById("linkInput").value.trim();
  if (!url) { shakeInput("linkInput"); return; }
  if (!isValidUrl(url)) { showError("Please enter a valid product URL (e.g. https://www.amazon.in/…)"); return; }

  showLoading();

  try {
    const res  = await fetch("/api/compare-link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not compare this link");
    handleResults(data, true);
  } catch (err) {
    showError(err.message);
  }
}

// ── Handle Results ─────────────────────────────────────────────────────────
function handleResults(data, isLinkMode = false) {
  hideLoading();
  allResults = data.results || [];

  if (!allResults.length) {
    showError("No results found. Try a different search or check back later.");
    return;
  }

  // Stats bar
  const savings = data.savings || 0;
  document.getElementById("sStores").textContent  = data.stores_count || allResults.length;
  document.getElementById("sSavings").textContent = savings > 0 ? "₹" + fmtPrice(savings) : "—";
  document.getElementById("sBest").textContent    = data.best_store || "—";
  document.getElementById("sTime").textContent    = data.elapsed ? data.elapsed + "s" : "—";

  // Winner banner — only if we have a real best price
  const bestResult = allResults.find(r => r.is_best && r.price > 0);
  if (bestResult) {
    document.getElementById("winnerStore").textContent = bestResult.site;
    document.getElementById("winnerPrice").textContent = "₹" + fmtPrice(bestResult.price);
    document.getElementById("winnerSave").textContent  = savings > 0
      ? `Save ₹${fmtPrice(savings)} vs most expensive` : "";
    const winnerBtn = document.getElementById("winnerBtn");
    winnerBtn.href = bestResult.link || "#";
    winnerBtn.style.pointerEvents = bestResult.link ? "auto" : "none";
    document.getElementById("winnerBanner").style.display = "flex";
  } else {
    document.getElementById("winnerBanner").style.display = "none";
  }

  // Source product (link mode)
  if (isLinkMode && data.source_site) {
    const src = allResults.find(r => r.site === data.source_site) || allResults[0];
    renderSourceCard(src);
    document.getElementById("sourceWrap").style.display = "block";
  } else {
    hideSourcePanel();
  }

  // Price chart
  renderPriceChart(allResults);

  // Reset sort/filter controls
  activeFilter = "all";
  activeSort   = "price-asc";
  document.querySelectorAll(".ftab").forEach(t => t.classList.remove("active"));
  document.querySelector(".ftab[data-store='all']").classList.add("active");
  document.getElementById("sortSelect").value = "price-asc";

  // Show layout
  document.getElementById("resultsArea").style.display = "block";
  document.getElementById("statsRow").style.display    = "flex";
  document.getElementById("controls").style.display    = "flex";
  document.getElementById("errorState").style.display  = "none";

  renderCards(allResults);

  setTimeout(() => {
    document.getElementById("resultsArea").scrollIntoView({ behavior: "smooth", block: "start" });
  }, 100);
}

// ── Price Chart ────────────────────────────────────────────────────────────
function renderPriceChart(results) {
  const valid = results.filter(r => r.price > 0);
  if (valid.length < 2) {
    document.getElementById("priceChart").style.display = "none";
    return;
  }

  const maxP = Math.max(...valid.map(r => r.price));
  const minP = Math.min(...valid.map(r => r.price));

  const colors = {
    amazon: "#ff9900", flipkart: "#2874f0", meesho: "#f43397", croma: "#e31e26"
  };

  document.getElementById("chartBars").innerHTML = valid.map(r => {
    const pct   = Math.max(30, (r.price / maxP) * 100);
    const color = colors[r.site.toLowerCase()] || "#6c63ff";
    const isBest = r.price === minP;
    return `
      <div class="chart-row">
        <div class="chart-label" style="color:${color}">${r.site}</div>
        <div class="chart-bar-wrap">
          <div class="chart-bar ${isBest ? 'best' : ''}"
               style="width:${pct}%;background:${isBest ? '' : color + '33'};color:${isBest ? '#000' : color}">
            ${isBest ? '🏆' : ''}
          </div>
        </div>
        <div class="chart-price" style="color:${isBest ? 'var(--green)' : 'var(--text)'}">
          ₹${fmtPrice(r.price)}${isBest ? ' ✓' : ''}
        </div>
      </div>`;
  }).join("");

  document.getElementById("priceChart").style.display = "block";
}

// ── Render Cards ───────────────────────────────────────────────────────────
function renderCards(results) {
  const grid = document.getElementById("resultsGrid");
  if (!results.length) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:60px;color:var(--text-3)">No results for this filter.</div>`;
    return;
  }
  grid.innerHTML = results.map(r => cardHTML(r)).join("");
}

function cardHTML(r) {
  const hasPrize   = r.price > 0;
  const hasLink    = r.link && r.link !== "#";
  const isBest     = r.is_best && hasPrize;
  const siteCls    = `site-${r.site.toLowerCase()}`;
  const disc       = r.discount_pct || 0;
  const isSaved    = savedItems.some(s => s.link === r.link);

  const priceStr   = hasPrize ? "₹" + fmtPrice(r.price) : "—";
  const origStr    = (r.original_price > r.price && r.original_price > 0)
    ? "₹" + fmtPrice(r.original_price) : "";

  const imgHtml = r.image
    ? `<img class="card-img" src="${escHtml(r.image)}" alt="${escHtml(r.title)}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'img-placeholder\\'>🛍️</div>'">`
    : `<div class="img-placeholder">🛍️</div>`;

  const ratingHtml = r.rating > 0 ? `
    <div class="rating-row">
      <span class="stars">${renderStars(r.rating)}</span>
      <span class="rating-val">${r.rating}</span>
      ${r.reviews ? `<span class="review-cnt">· ${escHtml(r.reviews)}</span>` : ""}
    </div>` : "";

  const deliveryHtml = `
    <div class="delivery-row">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v3"/><polyline points="9 11 12 14 22 9"/><line x1="5.4" y1="10" x2="12" y2="10"/></svg>
      ${r.delivery === "Free"
        ? `<span class="free-tag">Free delivery</span>`
        : `<span>${escHtml(r.delivery)} shipping</span>`}
      ${r.delivery_date ? `<span>· ${escHtml(r.delivery_date)}</span>` : ""}
    </div>`;

  const buyBtnHtml = hasLink
    ? `<a href="${escHtml(r.link)}" target="_blank" rel="noopener noreferrer" class="buy-btn">
         Buy Now ↗
       </a>`
    : `<span class="buy-btn-disabled">Unavailable</span>`;

  return `
  <div class="pcard ${isBest ? 'best-card' : ''} ${r.is_mock ? 'mock-card' : ''} ${siteCls}">
    ${isBest ? '<div class="best-badge">Best Price</div>' : ''}
    <div class="store-label">
      <div class="store-dot"></div>
      <span class="store-name">${escHtml(r.site)}</span>
    </div>
    <div class="card-img-wrap">${imgHtml}</div>
    <div class="card-body">
      <div class="card-title">${escHtml(r.title) || "Product from " + escHtml(r.site)}</div>
      ${hasPrize ? `
        <div class="price-row">
          <span class="price-main">${priceStr}</span>
          ${origStr ? `<span class="price-orig">${origStr}</span>` : ""}
          ${disc > 0 ? `<span class="disc-badge">-${disc}%</span>` : ""}
        </div>
      ` : `<div class="unavailable-tag">Price unavailable — click to check site</div>`}
      ${ratingHtml}
      ${deliveryHtml}
    </div>
    <div class="card-footer">
      ${buyBtnHtml}
      <button class="heart-btn ${isSaved ? 'saved' : ''}"
        onclick="toggleSave(this, ${escJson(r)})"
        title="${isSaved ? 'Remove from saved' : 'Save for later'}">
        ${isSaved ? '♥' : '♡'}
      </button>
    </div>
  </div>`;
}

// ── Source Card ────────────────────────────────────────────────────────────
function renderSourceCard(r) {
  const price = r.price > 0 ? "₹" + fmtPrice(r.price) : "—";
  document.getElementById("sourceCard").innerHTML = `
    <div class="source-card">
      <div class="source-info">
        <div class="source-site">${escHtml(r.site)}</div>
        <div class="source-title">${escHtml(r.title)}</div>
        <div class="source-price">${price}</div>
      </div>
      ${r.link ? `<a href="${escHtml(r.link)}" target="_blank" rel="noopener" class="buy-btn" style="width:auto;padding:10px 20px">Open ↗</a>` : ""}
    </div>`;
}

// ── Sort & Filter ──────────────────────────────────────────────────────────
function applySortFilter() {
  activeSort = document.getElementById("sortSelect").value;
  let filtered = activeFilter === "all"
    ? [...allResults]
    : allResults.filter(r => r.site.toLowerCase() === activeFilter);

  if (activeSort === "price-asc")  filtered.sort((a, b) => (a.price || 999999) - (b.price || 999999));
  if (activeSort === "price-desc") filtered.sort((a, b) => (b.price || 0) - (a.price || 0));
  if (activeSort === "discount")   filtered.sort((a, b) => (b.discount_pct || 0) - (a.discount_pct || 0));
  if (activeSort === "rating")     filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));

  renderCards(filtered);
}

// ── Saved Items ────────────────────────────────────────────────────────────
function toggleSave(btn, item) {
  const idx = savedItems.findIndex(s => s.link === item.link);
  if (idx > -1) {
    savedItems.splice(idx, 1);
    btn.textContent = "♡";
    btn.classList.remove("saved");
  } else {
    savedItems.push(item);
    btn.textContent = "♥";
    btn.classList.add("saved");
  }
  localStorage.setItem("sp_saved", JSON.stringify(savedItems));
  updateSavedBadge();
}

function renderSaved() {
  const list  = document.getElementById("savedList");
  const empty = document.getElementById("savedEmpty");
  if (!savedItems.length) {
    list.innerHTML = "";
    empty.style.display = "flex";
    return;
  }
  empty.style.display = "none";
  list.innerHTML = savedItems.map((r, i) => `
    <div class="saved-item">
      <div>
        <div class="saved-title">${escHtml(r.site)} — ${escHtml(r.title || "Product")}</div>
        <div class="saved-price">${r.price > 0 ? "₹" + fmtPrice(r.price) : "—"}</div>
      </div>
      <div class="saved-links">
        ${r.link ? `<a href="${escHtml(r.link)}" target="_blank" rel="noopener" class="saved-open">Open ↗</a>` : ""}
        <button class="saved-del" onclick="removeSaved(${i})" title="Remove">✕</button>
      </div>
    </div>`).join("");
}

function removeSaved(idx) {
  savedItems.splice(idx, 1);
  localStorage.setItem("sp_saved", JSON.stringify(savedItems));
  updateSavedBadge();
  renderSaved();
}

function updateSavedBadge() {
  const cnt = document.getElementById("savedCount");
  if (savedItems.length > 0) {
    cnt.textContent = savedItems.length;
    cnt.style.display = "inline";
  } else {
    cnt.style.display = "none";
  }
}

// ── Loading / Error ────────────────────────────────────────────────────────
function showLoading() {
  document.getElementById("resultsArea").style.display    = "block";
  document.getElementById("loadingState").style.display   = "block";
  document.getElementById("resultsGrid").innerHTML        = "";
  document.getElementById("errorState").style.display     = "none";
  document.getElementById("controls").style.display       = "none";
  document.getElementById("statsRow").style.display       = "none";
  document.getElementById("winnerBanner").style.display   = "none";
  document.getElementById("priceChart").style.display     = "none";
  hideSourcePanel();

  const stores = ["ls-amazon", "ls-flipkart", "ls-meesho", "ls-croma"];
  stores.forEach(id => { document.getElementById(id).className = "ls"; });
  let i = 0;
  loadingTimer = setInterval(() => {
    if (i < stores.length) {
      document.getElementById(stores[i]).className = "ls active";
      if (i > 0) document.getElementById(stores[i - 1]).className = "ls done";
    } else {
      clearInterval(loadingTimer);
    }
    i++;
  }, 400);
}

function hideLoading() {
  clearInterval(loadingTimer);
  document.getElementById("loadingState").style.display = "none";
}

function showError(msg) {
  hideLoading();
  document.getElementById("resultsGrid").innerHTML    = "";
  document.getElementById("controls").style.display  = "none";
  document.getElementById("statsRow").style.display  = "none";
  document.getElementById("errorState").style.display = "block";
  document.getElementById("errorMsg").textContent    = msg;
  document.getElementById("resultsArea").style.display = "block";
}

function hideError() {
  document.getElementById("errorState").style.display = "none";
}

function hideSourcePanel() {
  document.getElementById("sourceWrap").style.display = "none";
}

// ── Utilities ──────────────────────────────────────────────────────────────
function fmtPrice(n) {
  return Number(n).toLocaleString("en-IN");
}

function renderStars(rating) {
  const full = Math.floor(rating);
  const half = (rating % 1) >= 0.5 ? 1 : 0;
  return "★".repeat(full) + (half ? "½" : "") + "☆".repeat(Math.max(0, 5 - full - half));
}

function isValidUrl(s) {
  try {
    const u = new URL(s);
    return u.protocol.startsWith("http");
  } catch { return false; }
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escJson(obj) {
  return "'" + JSON.stringify(obj).replace(/'/g, "\\'") + "'";
}

function shakeInput(id) {
  const el = document.getElementById(id);
  el.style.animation = "none";
  void el.offsetHeight;
  el.style.animation = "shake 0.35s ease";
  el.focus();
}
