// StatusMonkey Lead Finder v1.5 - Frontend JavaScript

let allLeads = [];
// TASK 26: Status tracking variables
let currentStatusFilter = "all";
let statusCounts = {};
// TASK 28: Pin tracking
let pinnedLeads = new Set(); // Store pinned lead IDs
// TASK 31: Quick action tracking
let currentQuickActionLead = null;

let currentFilter = "all";
let templates = {};
// TASK 32: Bulk Actions
let selectedLeads = new Set();
let isTop10Expanded = false; // State for toggle
// TASK: Top 10 Batch State
let top10BatchIds = new Set();
let top10BatchIndices = new Map(); // Maps ID -> #Rank (1-10)



// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  loadLeads();
  loadStats();
  loadTemplates();

  // Default to Today view
});
// Load all leads
async function loadLeads() {
  try {
    const response = await fetch("/api/leads");
    allLeads = await response.json();

    // TASK 28: Load saved pins from localStorage
    const savedPins = localStorage.getItem("pinnedLeads");
    if (savedPins) {
      pinnedLeads = new Set(JSON.parse(savedPins));
    }

    updateStatusCounts();

    // ✅ Default view = Today (after leads are loaded)
    filterLeads("today");
  } catch (error) {
    console.error("Error loading leads:", error);
    showError("Failed to load leads");
  }
}

// Load statistics
async function loadStats() {
  try {
    const response = await fetch("/api/stats");
    const stats = await response.json();

    document.getElementById("stat-total").textContent = stats.total;
    document.getElementById("stat-emergency").textContent =
      stats.emergency || 0;
    document.getElementById("stat-hot").textContent = stats.hot;
    document.getElementById("stat-warm").textContent = stats.warm;
    document.getElementById("stat-cold").textContent = stats.cold;
    document.getElementById("stat-contacted").textContent = stats.contacted;
    document.getElementById("stat-converted").textContent = stats.converted;
    document.getElementById("stat-revenue").textContent =
      "$" + (stats.revenue || 0);
  } catch (error) {
    console.error("Error loading stats:", error);
  }
}

// Load reply templates
async function loadTemplates() {
  try {
    const response = await fetch("/api/templates");
    templates = await response.json();
  } catch (error) {
    console.error("Error loading templates:", error);
  }
}

// Display leads
function displayLeads(leads, options = {}) {
  const container = document.getElementById("leads-container");

  // ⛔️ IMPORTANT: Skip status filtering when explicitly told (Today view)
  if (!options.bypassStatus) {
    leads = leads.filter((lead) => {
      const leadStatus = lead.status || "new";

      if (currentStatusFilter === "all") {
        // "All" shows only uncategorized leads (new, unread)
        return leadStatus === "new" || leadStatus === "unread";
      } else {
        // Other tabs show only their specific status
        return leadStatus === currentStatusFilter;
      }
    });
  }

  if (leads.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <h2>📭 No Leads Found</h2>
        <p>Click "Scan Reddit Now" to find potential customers for StatusMonkey.co</p>
        <button class="btn btn-primary" onclick="scanReddit()">🔍 Start Scanning</button>
      </div>
    `;
    return;
  }

  container.innerHTML = leads.map((lead, index) => {
      // Use fixed batch index if available (Top 10 mode), otherwise regular index
      const displayIndex = (options.isTop10 && top10BatchIndices.has(lead.id)) 
          ? top10BatchIndices.get(lead.id) 
          : index + 1;
      return createLeadCard(lead, displayIndex);
  }).join("");
  
  // Re-apply selections
  selectedLeads.forEach(id => {
      const checkbox = document.querySelector(`.lead-checkbox[data-id="${id}"]`);
      if(checkbox) checkbox.checked = true;
      
      const card = document.querySelector(`.lead-card[data-id="${id}"]`);
      if(card) card.classList.add('selected');
  });
  
  updateBulkToolbar();
}

// Create lead card HTML
function createLeadCard(lead, index) {
  const priorityClass = `priority-${lead.priority}`;
  const statusBadge =
    lead.status !== "new"
      ? `<span class="badge badge-${
          lead.status
        }">${lead.status.toUpperCase()}</span>`
      : "";
  const convertedBadge = lead.converted
    ? `<span class="badge badge-converted">✓ CONVERTED</span>`
    : "";

  return `
   <div class="lead-card ${priorityClass}" data-id="${
    lead.id
  }" ondblclick="copyFullPost('${lead.id}')" style="cursor: pointer;">



       
            <div class="lead-header">
                <div class="lead-title">
                    <input type="checkbox" class="lead-checkbox" data-id="${lead.id}" onclick="event.stopPropagation(); toggleSelect('${lead.id}')">
                    <span class="lead-index">#${index}</span> 
                    ${escapeHtml(lead.title)}
                </div>
                <div class="lead-badges">
                    <span class="badge badge-${
                      lead.priority
                    }">${lead.priority.toUpperCase()} - Score: ${
    lead.score
  }</span>
                    ${statusBadge ? " " + statusBadge : ""}
                    ${convertedBadge ? " " + convertedBadge : ""}
                    ${
                      lead.status === "new"
                        ? ' <span class="badge badge-new">NEW</span>'
                        : ""
                    }
                </div>

            </div>
            
            <div class="lead-meta">
                <span>👤 u/${lead.author}</span>
                <span>📍 r/${lead.subreddit}</span>
                <span>⬆️ ${lead.score} upvotes</span>
                <span>💬 ${lead.comments} comments</span>
                <span>🕐 ${lead.created_readable}</span>
            </div>
            
            ${
              lead.text
                ? `<div class="lead-text">${escapeHtml(lead.text)}</div>`
                : ""
            }
            
            ${
              lead.matched_keywords && lead.matched_keywords.length > 0
                ? `
                <div class="lead-keywords">
                    <strong>🎯 Matched Keywords:</strong>
                    ${lead.matched_keywords
                      .map(
                        (kw) =>
                          `<span class="keyword-tag">${escapeHtml(kw)}</span>`
                      )
                      .join("")}
                </div>
            `
                : ""
            }
            
            ${
              lead.suggested_template
                ? `
                <div class="suggested-template">
                    <strong>💡 Suggested Reply:</strong> ${lead.suggested_template}
                </div>
            `
                : ""
            }
            
            <div class="lead-actions">
                <button class="btn-small btn-link" onclick="event.stopPropagation(); openPost('${
                  lead.url
                }')">
                    🔗 Open Post
                </button>
                <button class="btn-small btn-copy-full" onclick="event.stopPropagation(); copyFullPost('${
                  lead.id
                }')">
    📋 Copy Full Post
</button>

              
                <button class="btn-small btn-pin ${
                  pinnedLeads.has(lead.id) ? "pinned" : ""
                }" 
                        onclick="event.stopPropagation(); togglePin('${
                          lead.id
                        }')">
                    ${pinnedLeads.has(lead.id) ? "📌 Pinned" : "📍 Pin"}
                </button>


                <button class="btn-small btn-template" onclick="event.stopPropagation(); showTemplate('${
                  lead.id
                }', '${lead.suggested_template || "recommendation"}')">
                    📝 Get Reply Template
                </button>
                <button class="btn-small btn-contacted" onclick="event.stopPropagation(); updateStatus('${
                  lead.id
                }', 'contacted')">
                    📧 Mark Contacted
                </button>
                <button class="btn-small btn-converted" onclick="event.stopPropagation(); markConverted('${
                  lead.id
                }')">
                    💰 Mark Converted
                </button>
                <button class="btn-small btn-ignore" onclick="event.stopPropagation(); updateStatus('${
                  lead.id
                }', 'ignored')">
                    ❌ Ignore
                </button>
            </div>

        </div>
    `;
}

// Show reply template modal
function showTemplate(leadId, templateType) {
  const lead = allLeads.find((l) => l.id === leadId);
  if (!lead) return;

  let templateText = templates[templateType] || templates["recommendation"];

  // Replace [COMPETITOR] placeholder if needed
  if (templateType === "competitor_complaint") {
    const competitorMatch = lead.matched_keywords.find((k) =>
      k.includes("competitor:")
    );
    if (competitorMatch) {
      const competitor = competitorMatch.split(":")[1];
      templateText = templateText.replace("[COMPETITOR]", competitor);
    }
  }

  document.getElementById("template-text").value = templateText;
  document.getElementById("template-modal").style.display = "flex";
}

// Close template modal
function closeTemplateModal() {
  document.getElementById("template-modal").style.display = "none";
}

// Copy template to clipboard
function copyTemplate() {
  const text = document.getElementById("template-text").value;
  navigator.clipboard
    .writeText(text)
    .then(() => {
      showNotification("✅ Template copied to clipboard!");
      closeTemplateModal();
    })
    .catch((err) => {
      showError("Failed to copy to clipboard");
    });
}

// Scan Reddit for new leads
async function scanReddit() {
  const loadingDiv = document.getElementById("loading");
  loadingDiv.style.display = "block";

  try {
    const response = await fetch("/api/scan", {
      method: "POST",
    });
    const result = await response.json();

    loadingDiv.style.display = "none";

    if (result.success) {
      showNotification(`✅ Scan complete! Found ${result.new_leads} new leads`);
      loadLeads();
      loadStats();
    } else {
      showError("Scan failed");
    }
  } catch (error) {
    loadingDiv.style.display = "none";
    console.error("Error scanning:", error);
    showError("Failed to scan Reddit");
  }
}

// Update lead status

async function updateStatus(leadId, status) {
  try {
    const response = await fetch(`/api/lead/${leadId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status: status }),
    });

    if (response.ok) {
      // ✅ UPDATE: Update lead in memory FIRST
      const lead = allLeads.find((l) => l.id === leadId);
      if (lead) {
        lead.status = status;
      }

      // ✅ UPDATE: Refresh counts immediately
      updateStatusCounts();

      // ✅ FIX: Stay on current filter (today, hot, emergency, etc.)
      filterLeads(currentFilter);

      showNotification(`✅ Lead marked as ${status}`);
      loadStats();
    }
  } catch (error) {
    console.error("Error updating status:", error);
    showError("Failed to update lead");
  }
}

// Mark lead as converted
async function markConverted(leadId) {
  try {
    const response = await fetch(`/api/lead/${leadId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status: "converted",
        converted: true,
      }),
    });

    if (response.ok) {
      showNotification("🎉 Lead marked as CONVERTED! +$5.99 revenue");
      loadLeads();
      loadStats();
    }
  } catch (error) {
    console.error("Error marking converted:", error);
    showError("Failed to mark as converted");
  }
}

// Filter leads
function filterLeads(filter) {
  // Reset tab UI
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
  });

  const todayBtn = document.getElementById("today-btn");
  currentFilter = filter;

  let filtered = allLeads;

  if (filter === "today") {
    const today = new Date().toISOString().split("T")[0];

    // ✅ Filter: Found today + NOT contacted/ignored/converted
    const filtered = allLeads.filter((lead) => {
      if (!lead.found_at) return false;

      const foundToday = lead.found_at.startsWith(today);
      const status = lead.status || "new";
      const isHandled = ["contacted", "ignored", "converted"].includes(status);

      return foundToday && !isHandled; // ✅ Only show unhandled leads
    });

    displayLeads(filtered, { bypassStatus: true }); // Keep this - it's fine now

    document.getElementById("today-btn")?.classList.add("active");
    return;
  }

  // normal filters
  if (filter === "emergency") {
    filtered = allLeads.filter((lead) => lead.priority === "emergency");
  } else if (filter === "hot") {
    // ✅ NEW: Hot = hot priority + NOT contacted/ignored/converted
    filtered = allLeads.filter(
      (lead) =>
        lead.priority === "hot" &&
        !["contacted", "ignored", "converted"].includes(lead.status || "new")
    );

    // ✅ Make Hot tab active
    document
      .querySelectorAll(".tab-btn")
      .forEach((btn) => btn.classList.remove("active"));
    document
      .querySelector("[onclick=\"filterLeads('hot')\"]")
      ?.classList.add("active");

    displayLeads(filtered, { bypassStatus: true });
    return;
  } else if (filter === "warm") {
    filtered = allLeads.filter((lead) => lead.priority === "warm");
  } else if (filter === "cold") {
    filtered = allLeads.filter((lead) => lead.priority === "cold");
  } else if (filter === "new") {
    filtered = allLeads.filter((lead) => lead.status === "new");
  } else if (filter === "top10") {
      // ✅ Top 10 Batch Logic
      
      // 1. Check if we have active items in the current batch
      let currentBatchValid = false;
      if (top10BatchIds.size > 0) {
          // Check if ANY of the batch items are still active (not ignored/contacted/converted)
          const activeBatchItems = allLeads.filter(l => 
              top10BatchIds.has(l.id) && 
              !["contacted", "ignored", "converted"].includes(l.status)
          );
          
          if (activeBatchItems.length > 0) {
              currentBatchValid = true;
          }
      }

      // 2. If no valid batch, create a NEW one
      if (!currentBatchValid) {
          console.log("Creating new Top 10 batch...");
          // Find potential candidates
          const candidates = allLeads
              .filter(lead => !["contacted", "ignored", "converted"].includes(lead.status))
              .sort((a, b) => b.score - a.score)
              .slice(0, 10);
          
          if (candidates.length === 0) {
             showNotification("⚠️ No active leads available for Top 10!");
          }

          // Reset batch state
          top10BatchIds.clear();
          top10BatchIndices.clear();

          candidates.forEach((lead, index) => {
              top10BatchIds.add(lead.id);
              top10BatchIndices.set(lead.id, index + 1); // fixed rank #1-10
          });
      }

      // 3. Filter leads to show ONLY what remains of the batch
      // We want to show items that are IN the batch AND are still active
      filtered = allLeads.filter(lead => 
          top10BatchIds.has(lead.id) && 
          !["contacted", "ignored", "converted"].includes(lead.status)
      );
      
      // Sort them by their ORIGINAL batch index to keep order
      filtered.sort((a, b) => {
          return (top10BatchIndices.get(a.id) || 999) - (top10BatchIndices.get(b.id) || 999);
      });

      // Update tab UI manually since it's a custom filter
       document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.classList.remove("active");
      });
      document.querySelector("[onclick=\"filterLeads('top10')\"]").classList.add("active");

      // Show the Expand All button
      checkHideControls('top10');
      
      // Reset expansion state when entering tab
      isTop10Expanded = false;
      const btn = document.getElementById("btn-expand-toggle");
      if(btn) btn.innerHTML = "➕ EXPAND ALL 10 POSTS";

      displayLeads(filtered, { bypassStatus: true, isTop10: true });
      return;
  }
  
  checkHideControls(filter);
  displayLeads(filtered);
}

// Helper to hide custom controls if not needed
function checkHideControls(filter) {
    const top10Controls = document.getElementById("top10-controls");
    const allControls = document.getElementById("all-controls");
    
    // Default to hidden
    if(top10Controls) top10Controls.style.display = 'none';
    if(allControls) allControls.style.display = 'none';

    if(filter === 'top10') {
        if(top10Controls) top10Controls.style.display = 'block';
    } else if (filter === 'all') {
        if(allControls) allControls.style.display = 'block';
    }
}

// Search leads
function searchLeads() {
  const searchTerm = document.getElementById("searchInput").value.toLowerCase();
  
  // Hide special controls when searching
  document.getElementById("top10-controls").style.display = "none";


  if (!searchTerm) {
    displayLeads(allLeads);
    return;
  }

  const filtered = allLeads.filter(
    (lead) =>
      lead.title.toLowerCase().includes(searchTerm) ||
      lead.text.toLowerCase().includes(searchTerm) ||
      lead.author.toLowerCase().includes(searchTerm) ||
      lead.subreddit.toLowerCase().includes(searchTerm) ||
      (lead.matched_keywords &&
        lead.matched_keywords.some((k) => k.toLowerCase().includes(searchTerm)))
  );

  displayLeads(filtered);
}

// Export leads to CSV
function exportLeads() {
  if (allLeads.length === 0) {
    showError("No leads to export");
    return;
  }

  // Create CSV content
  const headers = [
    "Title",
    "Author",
    "Subreddit",
    "Score",
    "Comments",
    "Priority",
    "Status",
    "Converted",
    "Revenue",
    "URL",
    "Created",
  ];
  const rows = allLeads.map((lead) => [
    lead.title,
    lead.author,
    lead.subreddit,
    lead.score,
    lead.comments,
    lead.priority,
    lead.status,
    lead.converted ? "Yes" : "No",
    lead.revenue || 0,
    lead.url,
    lead.created_readable,
  ]);

  let csv = headers.join(",") + "\n";
  rows.forEach((row) => {
    csv +=
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",") +
      "\n";
  });

  // Download CSV
  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `statusmonkey_leads_${
    new Date().toISOString().split("T")[0]
  }.csv`;
  a.click();
  window.URL.revokeObjectURL(url);

  showNotification("✅ Leads exported to CSV");
}

// Open Reddit post in new tab
function openPost(url) {
  window.open(url, "_blank");
}

// Show notification
function showNotification(message) {
  console.log(message); // Silent - just log to console
}

// Show error
function showError(message) {
  console.error("❌ Error: " + message); // Silent - just log to console
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
// ============================================
// TASK 26: Filter leads by status tab
// ============================================
function filterByStatus(status) {
  currentStatusFilter = status;

  // Update active tab styling
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
  });
  const activeBtn = document.querySelector(`[data-status="${status}"]`);
  if (activeBtn) {
    activeBtn.classList.add("active");
  }

  // Re-render leads with new filter
  displayLeads(allLeads);
  
  // Update controls visibility
  checkHideControls(status);
}
// ============================================
// TASK 26: Count leads per status
// ============================================
function updateStatusCounts() {
  statusCounts = {
    all: 0, // new + unread
    unread: 0,
    read: 0,
    contacted: 0,
    replied: 0,
    converted: 0,
    ignored: 0,
    today: 0, // found today
    hot: 0, // ✅ NEW: hot priority count
  };

  const today = new Date().toISOString().split("T")[0];

  allLeads.forEach((lead) => {
    const status = lead.status || "new";
    const priority = lead.priority || "cold";

    // ✅ All = uncategorized inbox (exclude contacted/ignored/converted)
    if (["new", "unread"].includes(status)) {
      statusCounts.all++;
    }

    // ✅ Count individual statuses safely
    if (statusCounts.hasOwnProperty(status)) {
      statusCounts[status]++;
    }

    // ✅ NEW: Count HOT priority (exclude contacted/ignored/converted)
    if (
      priority === "hot" &&
      !["contacted", "ignored", "converted"].includes(status)
    ) {
      statusCounts.hot++;
    }

    // ✅ Today = found today (exclude contacted/ignored/converted)
    if (
      lead.found_at &&
      lead.found_at.startsWith(today) &&
      !["contacted", "ignored", "converted"].includes(status)
    ) {
      statusCounts.today++;
    }
  });

  // ✅ Update tab counters
  Object.keys(statusCounts).forEach((key) => {
    const el = document.getElementById(`count-${key}`);
    if (el) {
      el.textContent = statusCounts[key];
    }
  });
}

// ============================================
// TASK 26: Update lead status via backend
// ============================================
async function updateLeadStatus(leadId, newStatus) {
  try {
    const response = await fetch("/update_status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lead_id: leadId,
        status: newStatus,
      }),
    });

    if (response.ok) {
      // Update lead in memory
      const lead = allLeads.find((l) => l.id === leadId);
      if (lead) {
        lead.status = newStatus;
      }

      // Refresh counts and display
      updateStatusCounts();
      displayLeads(allLeads);

      showNotification(`✅ Lead marked as ${newStatus}!`);
    }
  } catch (error) {
    console.error("Error updating status:", error);
    showError("Failed to update status");
  }
}
// ============================================
// TASK 28: Toggle pinned navigation panel
// ============================================
function togglePinnedNav() {
  const panel = document.getElementById("pinned-nav");
  if (panel.style.display === "none" || panel.style.display === "") {
    panel.style.display = "block";
    updatePinnedList();
  } else {
    panel.style.display = "none";
  }
}

function closePinnedNav() {
  document.getElementById("pinned-nav").style.display = "none";
}

// ============================================
// TASK 28: Toggle pin on a lead
// ============================================
function togglePin(leadId) {
  if (pinnedLeads.has(leadId)) {
    // Unpin
    pinnedLeads.delete(leadId);
  } else {
    // Pin
    pinnedLeads.add(leadId);
  }

  // Save to localStorage
  localStorage.setItem("pinnedLeads", JSON.stringify([...pinnedLeads]));

  // Update display
  updatePinnedList();
  displayLeads(allLeads);
  updateStatusCounts();
}

// ============================================
// TASK 28: Update pinned list display
// ============================================
function updatePinnedList() {
  const listContainer = document.getElementById("pinned-list");
  const pinnedArray = allLeads.filter((lead) => pinnedLeads.has(lead.id));

  if (pinnedArray.length === 0) {
    listContainer.innerHTML =
      '<div style="color: #888; text-align: center; padding: 20px;">No pinned leads yet</div>';
    return;
  }

  listContainer.innerHTML = pinnedArray
    .map(
      (lead) => `
    <div class="pinned-item" onclick="scrollToLead('${lead.id}')">
      <div class="pinned-item-title">${escapeHtml(lead.title)}</div>
      <div class="pinned-item-meta">r/${lead.subreddit} • ${lead.priority}</div>
    </div>
  `
    )
    .join("");

  // Update count badge
  document.getElementById("count-pinned").textContent = pinnedArray.length;
}

// ============================================
// TASK 28: Scroll to pinned lead (Telegram style!)
// ============================================
function scrollToLead(leadId) {
  const leadCard = document.querySelector(`[data-id="${leadId}"]`);
  if (leadCard) {
    // Close pinned panel
    closePinnedNav();

    // Scroll to lead
    leadCard.scrollIntoView({ behavior: "smooth", block: "center" });

    // Highlight it temporarily
    leadCard.classList.add("highlight");
    setTimeout(() => {
      leadCard.classList.remove("highlight");
    }, 2000);
  }
}
// ============================================
// TASK 31: Quick action overlay functions
// ============================================
function showQuickActionOverlay(leadId) {
  const lead = allLeads.find((l) => l.id === leadId);
  if (!lead) return;

  currentQuickActionLead = lead;

  const overlay = document.getElementById("quick-action-overlay");
  const titleElement = document.getElementById("quick-lead-title");

  titleElement.textContent = lead.title;
  overlay.style.display = "flex";
}

function closeQuickOverlay() {
  document.getElementById("quick-action-overlay").style.display = "none";
  currentQuickActionLead = null;
}

function quickAction(action) {
  if (currentQuickActionLead) {
    updateStatus(currentQuickActionLead.id, action);
    closeQuickOverlay();
  }
}

// ============================================
// SUBREDDIT MANAGEMENT - v2.3
// ============================================

function openSubredditSettings() {
  loadSubreddits();
  document.getElementById("subreddit-modal").style.display = "flex";
}

function closeSubredditModal() {
  document.getElementById("subreddit-modal").style.display = "none";
}

async function loadSubreddits() {
  try {
    const response = await fetch("/api/subreddits");
    const subreddits = await response.json();

    const listContainer = document.getElementById("subreddit-list");

    if (subreddits.length === 0) {
      listContainer.innerHTML =
        '<p style="color: #888;">No subreddits configured</p>';
      return;
    }

    listContainer.innerHTML = subreddits
      .map(
        (sub) => `
      <div class="subreddit-item">
        <div class="subreddit-info">
          <span class="subreddit-name">r/${sub.name}</span>
          <span class="subreddit-priority ${
            sub.priority
          }">${sub.priority.replace("_", " ")}</span>
        </div>
        <button class="btn-delete" onclick="deleteSubreddit('${sub.name}')">
          ❌ Remove
        </button>
      </div>
    `
      )
      .join("");
  } catch (error) {
    console.error("Error loading subreddits:", error);
    showError("Failed to load subreddits");
  }
}

async function addSubreddit() {
  const input = document.getElementById("new-subreddit-input");
  const subredditName = input.value.trim();

  if (!subredditName) {
    showError("Please enter a subreddit name");
    return;
  }

  try {
    const response = await fetch("/api/subreddits", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: subredditName,
        priority: "medium_priority",
      }),
    });

    const result = await response.json();

    if (result.success) {
      showNotification(`✅ ${result.message}`);
      input.value = "";
      loadSubreddits();
    } else {
      showError(result.error);
    }
  } catch (error) {
    console.error("Error adding subreddit:", error);
    showError("Failed to add subreddit");
  }
}

async function deleteSubreddit(name) {
  if (!confirm(`Remove r/${name} from tracking?`)) {
    return;
  }

  try {
    const response = await fetch(`/api/subreddits/${name}`, {
      method: "DELETE",
    });

    const result = await response.json();

    if (result.success) {
      showNotification(`✅ ${result.message}`);
      loadSubreddits();
    } else {
      showError(result.error);
    }
  } catch (error) {
    console.error("Error deleting subreddit:", error);
    showError("Failed to delete subreddit");
  }
}

// ============================================
// QUICK PASTE HELPER - v2.0
// ============================================

async function copyFullPost(leadId) {
  // Show loading
  const loadingDiv = document.getElementById("loading");
  loadingDiv.style.display = "block";

  try {
    const response = await fetch(`/api/reddit/full/${leadId}`);
    const data = await response.json();

    loadingDiv.style.display = "none";

    if (data.success) {
      data.leadId = leadId; // Add lead ID to the data
      showFullPostModal(data);
    } else {
      showError("Failed to fetch full post: " + data.error);
    }
  } catch (error) {
    loadingDiv.style.display = "none";
    console.error("Error fetching full post:", error);
    showError("Failed to fetch full post");
  }
}

function showFullPostModal(postData) {
  // Format the content
  let content = `TITLE: ${postData.title}\n\n`;
  content += `AUTHOR: u/${postData.author}\n`;
  content += `SCORE: ${postData.score} upvotes | ${postData.num_comments} comments\n`;
  content += `URL: ${postData.url}\n\n`;
  content += `POST:\n${postData.selftext || "[No text content]"}\n\n`;

  if (postData.comments && postData.comments.length > 0) {
    content += `COMMENTS (${postData.comments.length}):\n`;
    content += "=".repeat(50) + "\n\n";

    postData.comments.forEach((comment, index) => {
      const indent = "  ".repeat(comment.depth);
      content += `${indent}[${index + 1}] u/${comment.author} (${
        comment.score
      } points):\n`;
      content += `${indent}${comment.body}\n\n`;
    });
  } else {
    content += "No comments yet.\n";
  }

  /// Show modal and store lead ID + post URL
  document.getElementById("full-post-content").value = content;
  document
    .getElementById("full-post-modal")
    .setAttribute("data-lead-id", postData.leadId);
  document
    .getElementById("full-post-modal")
    .setAttribute("data-post-url", postData.url);
  document.getElementById("full-post-modal").style.display = "flex";
}

function closeFullPostModal() {
  document.getElementById("full-post-modal").style.display = "none";
}

function copyFullPostToClipboard() {
  const content = document.getElementById("full-post-content").value;

  navigator.clipboard
    .writeText(content)
    .then(() => {
      showNotification("✅ Full post copied to clipboard!");
    })
    .catch((err) => {
      showError("Failed to copy to clipboard");
    });
}

function openPerplexitySpace() {
  window.open(
    "https://www.perplexity.ai/search/reddit-marketing-YYe7.MtmTc6D1AANKfrUSQ",
    "_blank"
  );
  showNotification("💡 Perplexity space opened! Paste the content there.");
}

function quickContactFromModal() {
  const modal = document.getElementById("full-post-modal");
  const leadId = modal.getAttribute("data-lead-id");

  if (leadId) {
    closeFullPostModal(); // ✅ Close modal FIRST
    updateStatus(leadId, "contacted"); // ✅ This already refreshes everything
  }
}

function quickIgnoreFromModal() {
  const modal = document.getElementById("full-post-modal");
  const leadId = modal.getAttribute("data-lead-id");

  if (leadId) {
    closeFullPostModal(); // ✅ Close modal FIRST
    updateStatus(leadId, "ignored"); // ✅ This already refreshes everything
  }
}

function openPostFromModal() {
  const modal = document.getElementById("full-post-modal");
  const postUrl = modal.getAttribute("data-post-url");

  if (postUrl) {
    window.open(postUrl, "_blank");
  }
}

// ============================================
// TOP 10 EXPAND ALL FEATURE
// ============================================

// ============================================
// TOP 10 EXPAND ALL FEATURE
// ============================================

async function toggleTop10View() {
    const btn = document.getElementById("btn-expand-toggle");
    
    if (isTop10Expanded) {
        // CONTRACT
        contractAllTop10();
        btn.innerHTML = "➕ EXPAND ALL 10 POSTS";
        isTop10Expanded = false;
    } else {
        // EXPAND
        await expandAllTop10();
        btn.innerHTML = "➖ CONTRACT (COMPACT VIEW)";
        isTop10Expanded = true;
    }
}

function contractAllTop10() {
    const cards = document.querySelectorAll("#leads-container .lead-card");
    cards.forEach(card => {
        card.classList.add("compact-view");
    });
}

async function expandAllTop10() {
    // 1. Get all currently displayed lead cards
    const cards = document.querySelectorAll("#leads-container .lead-card");
    if(cards.length === 0) {
        showError("No leads to expand");
        return;
    }

    // Remove compact view class first
    cards.forEach(card => {
        card.classList.remove("compact-view");
    });

    // 2. Iterate and fetch full content for each
    const promises = Array.from(cards).map(async (card) => {
        const leadId = card.getAttribute("data-id");
        
        // Show loading state inline
        const textContainer = card.querySelector(".lead-text") || card.querySelector(".lead-meta");
        const loadingMsg = document.createElement("div");
        loadingMsg.className = "loading-inline";
        loadingMsg.innerHTML = "⏳ Fetching full post content...";
        loadingMsg.style.color = "#00ff41";
        loadingMsg.style.padding = "10px";
        loadingMsg.style.fontStyle = "italic";
        
        if(card.querySelector(".lead-text")) {
             card.querySelector(".lead-text").appendChild(loadingMsg);
        } else {
             card.appendChild(loadingMsg);
        }

        try {
            const response = await fetch(`/api/reddit/full/${leadId}`);
            const data = await response.json();
            
            if(data.success) {
                // Update the card content with full post details
                updateCardWithFullContent(card, data);
            } else {
                loadingMsg.textContent = "❌ Failed to load content";
            }
        } catch(err) {
            console.error(err);
             loadingMsg.textContent = "❌ Error loading content";
        }
    });
    
    await Promise.all(promises);
    showNotification("✅ Expanded top 10 posts!");
}

function updateCardWithFullContent(card, data) {
    // Remove existing text/template previews to avoid duplicates if re-run
    const existingText = card.querySelector(".lead-text");
    if(existingText) existingText.remove();
    
    const existingTemplate = card.querySelector(".suggested-template");
    if(existingTemplate) existingTemplate.remove();

    // Create full content view
    const fullContentDiv = document.createElement("div");
    fullContentDiv.className = "full-content-expanded";
    fullContentDiv.style.marginTop = "15px";
    fullContentDiv.style.padding = "15px";
    fullContentDiv.style.background = "#0d1117";
    fullContentDiv.style.border = "1px solid #30363d";
    fullContentDiv.style.borderRadius = "6px";
    fullContentDiv.style.fontSize = "14px";
    fullContentDiv.style.whiteSpace = "pre-wrap"; 

    let contentHTML = `<div style="color: #fff; margin-bottom: 10px;"><strong>📄 FULL POST:</strong></div>`;
    contentHTML += `<div style="color: #c9d1d9;">${escapeHtml(data.selftext || "[No text]")}</div>`;
    
    // Add Comments
    if(data.comments && data.comments.length > 0) {
        contentHTML += `<div style="margin-top: 20px; padding-top: 10px; border-top: 1px solid #30363d;"><strong>💬 ALL COMMENTS (${data.comments.length}):</strong></div>`;
        
        // Removed limit: Show all comments
        data.comments.forEach(comment => {
             contentHTML += `
                <div style="margin-top: 10px; padding-left: 10px; border-left: 2px solid #30363d;">
                    <div style="color: #8b949e; font-size: 12px;">u/${comment.author} • ${comment.score} pts</div>
                    <div style="color: #c9d1d9;">${escapeHtml(comment.body)}</div>
                </div>
             `;
        });
    }
    
    fullContentDiv.innerHTML = contentHTML;
    
    // Append to card
    const metaDiv = card.querySelector(".lead-meta");
    metaDiv.insertAdjacentElement('afterend', fullContentDiv);
    
    // Remove loading indicators
    const loaders = card.querySelectorAll(".loading-inline");
    loaders.forEach(l => l.remove());
}

// ============================================
// BULK ACTION LOGIC
// ============================================

function toggleSelect(leadId) {
    const card = document.querySelector(`.lead-card[data-id="${leadId}"]`);
    const checkbox = document.querySelector(`.lead-checkbox[data-id="${leadId}"]`);
    
    if(selectedLeads.has(leadId)) {
        selectedLeads.delete(leadId);
        if(card) card.classList.remove('selected');
        if(checkbox) checkbox.checked = false;
    } else {
        selectedLeads.add(leadId);
        if(card) card.classList.add('selected');
        if(checkbox) checkbox.checked = true;
    }
    
    updateBulkToolbar();
}

function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.lead-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(cb => {
        const leadId = cb.getAttribute('data-id');
        if(!allChecked) {
             if(!selectedLeads.has(leadId)) toggleSelect(leadId);
        } else {
             if(selectedLeads.has(leadId)) toggleSelect(leadId);
        }
    });
}

function updateBulkToolbar() {
    const toolbar = document.getElementById('bulk-toolbar');
    const countSpan = document.getElementById('selected-count');
    
    if(selectedLeads.size > 0) {
        toolbar.style.display = 'flex';
        countSpan.textContent = selectedLeads.size;
    } else {
        toolbar.style.display = 'none';
    }
}

async function bulkUpdateStatus(status) {
    if(selectedLeads.size === 0) return;
    
    const count = selectedLeads.size;
    if(!confirm(`Mark ${count} selected leads as ${status.toUpperCase()}?`)) return;
    
    // Process all updates
    const promises = Array.from(selectedLeads).map(id => updateStatus(id, status));
    await Promise.all(promises);
    
    // Clear selection
    selectedLeads.clear();
    updateBulkToolbar();
    
    showNotification(`✅ Bulk update complete: ${count} leads marked as ${status}`);
}

async function copyAllVisible() {
    const cards = document.querySelectorAll("#leads-container .lead-card");
    if(cards.length === 0) {
        showError("No leads to copy");
        return;
    }
    
    let fullText = "🔥 STATUSMONKEY TOP LEADS EXPORT\n=================================\n\n";
    
    // We scrape the text from the DOM elements
    cards.forEach((card, index) => {
        const title = card.querySelector(".lead-title").innerText.replace(/#\d+\s/, ''); // Remove index
        const meta = card.querySelector(".lead-meta").innerText;
        
        let body = "";
        // Check for expanded content first
        const expanded = card.querySelector(".full-content-expanded");
        if(expanded) {
            body = expanded.innerText;
        } else {
            // Fallback to preview text
            const preview = card.querySelector(".lead-text");
            body = preview ? preview.innerText : "[No text / Not expanded]";
        }
        
        fullText += `LEAD #${index + 1}\n`;
        fullText += `TITLE: ${title}\n`;
        fullText += `META: ${meta}\n`;
        fullText += `CONTENT:\n${body}\n`;
        fullText += "\n---------------------------------\n\n";
    });
    
    try {
        await navigator.clipboard.writeText(fullText);
        showNotification(`✅ Copied ${cards.length} leads to clipboard!`);
    } catch(err) {
        console.error(err);
        showError("Failed to copy to clipboard");
    }
}

async function clearSelectedLeads() {
    if(selectedLeads.size === 0) {
        showError("No leads selected to clear");
        return;
    }
    
    const count = selectedLeads.size;
    if(!confirm(`🗑️ Clear ${count} leads? They will be removed from this list but can be re-discovered if found again.`)) return;
    
    // Process all deletions
    const promises = Array.from(selectedLeads).map(async (id) => {
        try {
            const response = await fetch(`/api/lead/${id}`, {
                method: "DELETE"
            });
            if(response.ok) {
                // Remove from local memory
                const index = allLeads.findIndex(l => l.id === id);
                if(index > -1) allLeads.splice(index, 1);
            }
        } catch(err) {
            console.error(err);
        }
    });

    await Promise.all(promises);
    
    // Clear selection and refresh
    selectedLeads.clear();
    updateBulkToolbar();
    updateStatusCounts();
    displayLeads(allLeads); // Re-render
    
    showNotification(`✅ Cleared ${count} leads!`);
}
