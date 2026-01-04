// StatusMonkey Lead Finder v1.5 - Frontend JavaScript

let allLeads = [];
// TASK 26: Status tracking variables
let currentStatusFilter = "all";
let statusCounts = {};

let currentFilter = "all";
let templates = {};

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  loadLeads();
  loadStats();
  loadTemplates();
});

// Load all leads
async function loadLeads() {
  try {
    const response = await fetch("/api/leads");
    allLeads = await response.json();
    updateStatusCounts();
    displayLeads(allLeads);
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
function displayLeads(leads) {
  const container = document.getElementById("leads-container");
  // TASK 26: Filter by status tab
  if (currentStatusFilter !== "all") {
    leads = leads.filter((lead) => {
      const leadStatus = lead.status || "unread";
      return leadStatus === currentStatusFilter;
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

  container.innerHTML = leads.map((lead) => createLeadCard(lead)).join("");
}

// Create lead card HTML
function createLeadCard(lead) {
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
        <div class="lead-card ${priorityClass}" data-id="${lead.id}">
            <div class="lead-header">
                <div class="lead-title">${escapeHtml(lead.title)}</div>
                <div class="lead-badges">
                    <span class="badge badge-${
                      lead.priority
                    }">${lead.priority.toUpperCase()} - Score: ${
    lead.score
  }</span>
                    ${statusBadge}
                    ${convertedBadge}
                    ${
                      lead.status === "new"
                        ? '<span class="badge badge-new">NEW</span>'
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
                <button class="btn-small btn-link" onclick="openPost('${
                  lead.url
                }')">
                    🔗 Open Post
                </button>
                <button class="btn-small btn-template" onclick="showTemplate('${
                  lead.id
                }', '${lead.suggested_template || "recommendation"}')">
                    📝 Get Reply Template
                </button>
                <button class="btn-small btn-contacted" onclick="updateStatus('${
                  lead.id
                }', 'contacted')">
                    📧 Mark Contacted
                </button>
                <button class="btn-small btn-converted" onclick="markConverted('${
                  lead.id
                }')">
                    💰 Mark Converted
                </button>
                <button class="btn-small btn-ignore" onclick="updateStatus('${
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
      showNotification(`✅ Lead marked as ${status}`);
      loadLeads();
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
  currentFilter = filter;
  let filtered = allLeads;

  if (filter === "emergency") {
    filtered = allLeads.filter((lead) => lead.priority === "emergency");
  } else if (filter === "hot") {
    filtered = allLeads.filter((lead) => lead.priority === "hot");
  } else if (filter === "warm") {
    filtered = allLeads.filter((lead) => lead.priority === "warm");
  } else if (filter === "cold") {
    filtered = allLeads.filter((lead) => lead.priority === "cold");
  } else if (filter === "new") {
    filtered = allLeads.filter((lead) => lead.status === "new");
  }

  displayLeads(filtered);
}

// Search leads
function searchLeads() {
  const searchTerm = document.getElementById("searchInput").value.toLowerCase();

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
  alert(message); // Simple for now, can upgrade to toast notifications later
}

// Show error
function showError(message) {
  alert("❌ Error: " + message);
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
}
// ============================================
// TASK 26: Count leads per status
// ============================================
function updateStatusCounts() {
  statusCounts = {
    all: allLeads.length,
    unread: 0,
    read: 0,
    contacted: 0,
    replied: 0,
    converted: 0,
    ignored: 0,
  };

  // Count each status
  allLeads.forEach((lead) => {
    const status = lead.status || "unread";
    if (statusCounts[status] !== undefined) {
      statusCounts[status]++;
    }
  });

  // Update tab badges
  Object.keys(statusCounts).forEach((status) => {
    const badge = document.getElementById(`count-${status}`);
    if (badge) {
      badge.textContent = statusCounts[status];
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
