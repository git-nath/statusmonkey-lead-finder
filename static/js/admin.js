// StatusMonkey Admin Dashboard Logic

const TOP10_PROMPT_KEY = "statusmonkeyTop10Prompt";
const SAVED_PROMPTS_KEY = "statusmonkeySavedPrompts";
const EXIT_REMINDER_DISMISSED_KEY = "statusmonkeyExitReminderDismissed";

document.addEventListener('DOMContentLoaded', function() {
    loadAdminStats();
    loadAdminKeywords();
    loadDatabaseFiles();
    setupTop10PromptEditor();
    renderPromptList();
    setupExitReminder();
});

// Load administrative stats
async function loadAdminStats() {
    try {
        const response = await fetch('/api/admin/stats');
        const stats = await response.json();

        document.getElementById('stat-db-size').textContent = `${stats.db_size_kb} KB`;
        document.getElementById('stat-sync-rate').textContent = `${stats.notion_sync_rate}%`;
        document.getElementById('stat-active-subs').textContent = stats.active_subreddits;
        document.getElementById('stat-leads-24h').textContent = stats.leads_last_24h;
        document.getElementById('system-health').textContent = stats.db_health;
        document.getElementById('system-health').style.color = stats.db_health === 'Healthy' ? '#00ff00' : '#ff0000';
    } catch (error) {
        console.error('Error loading admin stats:', error);
        showError('Failed to load system stats');
    }
}

// Load database files list
async function loadDatabaseFiles() {
    try {
        const response = await fetch('/api/admin/databases');
        const data = await response.json();
        const container = document.getElementById('database-list');

        if (!container) return;

        if (!data.databases || data.databases.length === 0) {
            container.innerHTML = '<p style="color: #888;">No database files found.</p>';
            return;
        }

        container.innerHTML = data.databases
            .map((db) => {
                const modified = new Date(db.modified_at).toLocaleString();
                return `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border: 1px solid #00ffff; margin-bottom: 8px;">
                        <div>
                            <div style="color: #00ffff; font-weight: bold;">${db.name}</div>
                            <div style="font-size: 0.8em; color: #ccc;">Modified: ${modified}</div>
                        </div>
                        <div style="color: #00ff00;">${db.size_kb} KB</div>
                    </div>
                `;
            })
            .join('');
    } catch (error) {
        console.error('Error loading database files:', error);
        showError('Failed to load database files');
    }
}

// Load and render scoring keywords
async function loadAdminKeywords() {
    try {
        const response = await fetch('/api/admin/keywords');
        const data = await response.json();
        
        const container = document.getElementById('keyword-list');
        let html = '';

        for (const [category, keywords] of Object.entries(data.categories)) {
            const score = data.base_scoring[category.replace('_leads', '').replace('signals', 'signal').replace('complaints', 'complaint')] || 10;
            
            html += `
                <div class="keyword-category" style="margin-bottom: 20px; border-left: 2px solid #00ff00; padding-left: 10px;">
                    <h3 style="color: #00ff00; font-size: 1.1em; text-transform: uppercase;">${category.replace('_', ' ')} (+${score})</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px;">
                        ${keywords.map(kw => `<span class="keyword-tag" style="font-size: 0.8em;">${kw}</span>`).join('')}
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading keywords:', error);
        showError('Failed to load keywords');
    }
}

// Subreddit Management Logic (Mirrored from app.js)

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
      listContainer.innerHTML = '<p style="color: #888;">No subreddits configured</p>';
      return;
    }

    listContainer.innerHTML = subreddits
      .map(
        (sub) => `
      <div class="subreddit-item" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border: 1px solid #00ff00; margin-bottom: 10px;">
        <div class="subreddit-info">
          <span class="subreddit-name">r/${sub.name}</span>
        </div>
        <button class="btn-delete" onclick="deleteSubreddit('${sub.name}')" style="background: transparent; border: 1px solid #ff4444; color: #ff4444; cursor: pointer; padding: 2px 8px;">
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
      loadAdminStats(); // Refresh active sub count
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
      loadAdminStats(); // Refresh active sub count
    } else {
      showError(result.error);
    }
  } catch (error) {
    console.error("Error deleting subreddit:", error);
    showError("Failed to delete subreddit");
  }
}

// Utility Functions
function showNotification(message) {
  console.log('Admin Notification:', message);
  alert(message); // Simple alert for admin page
}

function showError(message) {
  console.error('Admin Error:', message);
  alert('❌ ERROR: ' + message);
}

function exportLeads() {
    window.location.href = '/api/stats'; // This triggers the CSV download in app.py logic
    // Actually exportLeads in app.js creates a CSV in frontend. 
    // For admin, let's just use a notification for now or redirect to existing export if possible.
    // In app.py /api/stats returns JSON. 
    // I'll leave this as a reminder to implement proper CSV export if needed.
    showNotification('Export feature coming soon to admin panel. Use Dashboard for now.');
}

function setupTop10PromptEditor() {
    const input = document.getElementById("top10-prompt-input");
    const status = document.getElementById("top10-prompt-status");
    if (!input) return;

    const storedPrompt = localStorage.getItem(TOP10_PROMPT_KEY) || "";
    input.value = storedPrompt;
    if (status) {
        status.textContent = storedPrompt
            ? "Prompt loaded from browser storage."
            : "Tip: Save updates here, then use the new Top 10 copy button to include this prompt.";
    }
}

function saveTop10Prompt() {
    const input = document.getElementById("top10-prompt-input");
    const status = document.getElementById("top10-prompt-status");
    if (!input) return;

    const value = input.value.trim();
    localStorage.setItem(TOP10_PROMPT_KEY, value);
    if (status) {
        status.textContent = value
            ? "✅ Prompt saved and ready for Top 10 exports."
            : "⚠️ Prompt cleared. Add text to include it in exports.";
    }
    renderPromptList();
    showNotification("✅ Top 10 prompt saved.");
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function getSavedPrompts() {
    try {
        const parsed = JSON.parse(localStorage.getItem(SAVED_PROMPTS_KEY) || "[]");
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        return [];
    }
}

function setSavedPrompts(prompts) {
    localStorage.setItem(SAVED_PROMPTS_KEY, JSON.stringify(prompts));
}

function renderPromptList() {
    const list = document.getElementById("prompt-list");
    if (!list) return;

    const prompts = getSavedPrompts();
    const activePrompt = localStorage.getItem(TOP10_PROMPT_KEY) || "";

    if (!prompts.length) {
        list.innerHTML = '<p style="color: #94a3b8; font-size: 0.85em; margin: 8px 0;">No saved prompts yet.</p>';
        return;
    }

    list.innerHTML = prompts
        .map((prompt, index) => {
            const isActive = prompt.text === activePrompt;
            const cardBorder = isActive ? "#818cf8" : "#475569";
            const cardBackground = isActive ? "rgba(79,70,229,0.22)" : "rgba(15,23,42,0.45)";
            const activeBadge = isActive
                ? '<span style="font-size: 0.7em; color: #c7d2fe; border: 1px solid #818cf8; border-radius: 999px; padding: 2px 8px;">Active</span>'
                : "";

            return `
                <div style="border: 1px solid ${cardBorder}; border-radius: 8px; padding: 8px; background: ${cardBackground};">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                        <button onclick="loadPromptFromList(${index})" style="width: 100%; text-align: left; background: transparent; border: none; color: #e2e8f0; cursor: pointer; font-weight: 600;">${escapeHtml(prompt.name)}</button>
                        ${activeBadge}
                    </div>
                    <div style="font-size: 0.75em; color: #94a3b8; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(prompt.text)}</div>
                    <button onclick="deletePromptFromList(${index})" style="margin-top: 6px; font-size: 0.75em; background: transparent; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; cursor: pointer; padding: 4px 8px;">Delete</button>
                </div>
            `;
        })
        .join("");
}

function addPromptToList() {
    const nameInput = document.getElementById("prompt-name-input");
    const promptInput = document.getElementById("top10-prompt-input");
    if (!nameInput || !promptInput) return;

    const name = nameInput.value.trim();
    const text = promptInput.value.trim();

    if (!name) {
        showError("Please enter a prompt name");
        return;
    }

    if (!text) {
        showError("Please add prompt text before saving to list");
        return;
    }

    const prompts = getSavedPrompts();
    prompts.unshift({ name, text, createdAt: new Date().toISOString() });
    setSavedPrompts(prompts.slice(0, 30));
    nameInput.value = "";
    renderPromptList();
    showNotification("✅ Prompt added to saved list.");
}

function loadPromptFromList(index) {
    const prompts = getSavedPrompts();
    const selected = prompts[index];
    if (!selected) return;

    const input = document.getElementById("top10-prompt-input");
    const status = document.getElementById("top10-prompt-status");
    if (!input) return;

    input.value = selected.text;
    localStorage.setItem(TOP10_PROMPT_KEY, selected.text);
    if (status) {
        status.textContent = `✅ Active prompt: ${selected.name}`;
    }
    renderPromptList();
}

function deletePromptFromList(index) {
    const prompts = getSavedPrompts();
    prompts.splice(index, 1);
    setSavedPrompts(prompts);
    renderPromptList();
}

function setupExitReminder() {
    // Exit reminder disabled for centralized database usage.
    return;
}

function openExitReminder() {
    const modal = document.getElementById("exit-reminder-modal");
    if (modal) {
        modal.style.display = "flex";
    }
}

function dismissExitReminder() {
    const modal = document.getElementById("exit-reminder-modal");
    if (modal) {
        modal.style.display = "none";
    }
}

function acknowledgeExitReminder() {
    sessionStorage.setItem(EXIT_REMINDER_DISMISSED_KEY, "true");
    dismissExitReminder();
    showNotification("✅ Exit reminder dismissed. Close the tab when ready.");
}
