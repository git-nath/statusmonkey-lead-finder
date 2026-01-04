// StatusMonkey Lead Finder - Frontend JavaScript

let allLeads = [];
let currentFilter = "all";

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  loadLeads();
  loadStats();
});

// Load all leads
async function loadLeads() {
  try {
    const response = await fetch("/api/leads");
    allLeads = await response.json();
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
    document.getElementById("stat-hot").textContent = stats.hot;
    document.getElementById("stat-warm").textContent = stats.warm;
    document.getElementById("stat-cold").textContent = stats.cold;
    document.getElementById("stat-contacted").textContent = stats.contacted;
    document.getElementById("stat-converted").textContent = stats.converted;
  } catch (error) {
    console.error("Error loading stats:", error);
  }
}

// Display leads
function displayLeads(leads) {
  const container = document.getElementById("leads-container");

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
              lead.matched_keywords.length > 0
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
            
            <div class="lead-actions">
                <button class="btn-small btn-link" onclick="openPost('${
                  lead.url
                }')">
                    🔗 Open Post
                </button>
                <button class="btn-small btn-contacted" onclick="updateStatus('${
                  lead.id
                }', 'contacted')">
                    📧 Mark Contacted
                </button>
                <button class="btn-small btn-converted" onclick="updateStatus('${
                  lead.id
                }', 'converted')">
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

// Filter leads
function filterLeads(filter) {
  currentFilter = filter;
  let filtered = allLeads;

  if (filter === "hot") {
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
      lead.subreddit.toLowerCase().includes(searchTerm)
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
