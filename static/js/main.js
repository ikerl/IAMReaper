/**
 * IAMReaper - Main JavaScript
 */

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('IAMReaper loaded');
    
    // Initialize HTMX extensions if needed
    initHTMX();
    
    // Set up event listeners
    setupEventListeners();
});

/**
 * Initialize HTMX configuration
 */
function initHTMX() {
    // Log HTMX events for debugging
    document.addEventListener('htmx:configRequest', function(event) {
        console.log('HTMX Request:', event.detail);
    });
    
    document.addEventListener('htmx:afterSwap', function(event) {
        console.log('HTMX Swap:', event.detail);
    });
    
    document.addEventListener('htmx:responseError', function(event) {
        console.error('HTMX Error:', event.detail);
        showAlert('Error communicating with server', 'danger');
    });
}

/**
 * Set up global event listeners
 */
function setupEventListeners() {
    // Region selector
    const regionSelect = document.getElementById('region-select');
    if (regionSelect) {
        regionSelect.addEventListener('change', function() {
            const region = this.value;
            fetch('/api/region', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({region: region})
            })
            .then(response => response.json())
            .then(data => {
                console.log('Region set to:', data.region);
            })
            .catch(error => {
                console.error('Error setting region:', error);
            });
        });
    }
    
    // Export button
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            window.location.href = '/api/export/iam';
        });
    }
}

/**
 * Show an alert message
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text)
            .then(() => showAlert('Copied to clipboard!', 'success'))
            .catch(err => {
                console.error('Failed to copy:', err);
                showAlert('Failed to copy to clipboard', 'danger');
            });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showAlert('Copied to clipboard!', 'success');
    }
}

/**
 * Copy command from data attribute (handles HTML entities)
 */
function copyCommandFromData(buttonElement) {
    let command = buttonElement.getAttribute('data-command');
    
    // Decode HTML entities
    const textarea = document.createElement('textarea');
    textarea.innerHTML = command;
    command = textarea.value;
    
    copyToClipboard(command);
}

/**
 * Format JSON for display
 */
function formatJSON(json) {
    if (typeof json === 'string') {
        try {
            json = JSON.parse(json);
        } catch (e) {
            return json;
        }
    }
    return JSON.stringify(json, null, 2);
}

/**
 * Get status badge HTML
 */
function getStatusBadge(success, errorType, duration) {
    if (success) {
        return `<span class="badge bg-success"><i class="bi bi-check-circle"></i> ${duration}ms</span>`;
    } else if (errorType === 'access_denied') {
        return `<span class="badge bg-warning text-dark"><i class="bi bi-shield-exclamation"></i> Access Denied</span>`;
    } else {
        return `<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Error</span>`;
    }
}

/**
 * Global error handler for uncaught errors
 */
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
});

/**
 * Export functions for use in inline scripts
 */
window.copyToClipboard = copyToClipboard;
window.formatJSON = formatJSON;
window.getStatusBadge = getStatusBadge;
window.fetchCredentials = fetchCredentials;
window.copyAllCredentials = copyAllCredentials;

/**
 * Fetch and display credentials
 */
function fetchCredentials() {
    fetch('/api/projects/active')
        .then(response => response.json())
        .then(data => {
            if (!data.active) {
                showAlert('No hay proyecto activo', 'warning');
                return;
            }
            
            const creds = `Profile: ${data.profile_name}\nRegion: ${data.aws_region}\nAccess Key: ${data.aws_access_key_id}\nSecret Key: ${data.aws_access_secret}`;
            
            copyToClipboard(data.aws_access_key_id);
            showAlert(`Access Key copiado: ${data.aws_access_key_id}`, 'success');
            
            console.log('Credenciales:', {
                profile: data.profile_name,
                region: data.aws_region,
                access_key: data.aws_access_key_id,
                secret_key: data.aws_access_secret
            });
        })
        .catch(err => {
            console.error(err);
            showAlert('Error obteniendo credenciales', 'danger');
        });
}

/**
 * Copy all credentials to clipboard
 */
function copyAllCredentials() {
    fetch('/api/projects/active')
        .then(response => response.json())
        .then(data => {
            if (!data.active) {
                showAlert('No hay proyecto activo', 'warning');
                return;
            }
            
            const creds = `[default]
aws_access_key_id = ${data.aws_access_key_id}
aws_secret_access_key = ${data.aws_access_secret}

# o para profile:
[${data.profile_name}]
aws_access_key_id = ${data.aws_access_key_id}
aws_secret_access_key = ${data.aws_access_secret}
region = ${data.aws_region}`;
            
            copyToClipboard(creds);
            showAlert('Credenciales copiadas al portapapeles!', 'success');
        })
        .catch(err => {
            console.error(err);
            showAlert('Error copiando credenciales', 'danger');
        });
}

/**
 * Re-run a command and update the results
 */
function reRunCommand(command, description, buttonElement) {
    console.log('Re-running command:', command);
    console.log('Command length:', command ? command.length : 0);
    console.log('Command raw:', JSON.stringify(command));
    
    // Show loading state on button
    const icon = buttonElement.querySelector('i');
    if (icon) {
        icon.className = 'bi bi-hourglass-split spinning';
    }
    buttonElement.disabled = true;
    
    // Add spinning animation style if not exists
    if (!document.getElementById('spinning-style')) {
        const style = document.createElement('style');
        style.id = 'spinning-style';
        style.textContent = `
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .spinning {
                animation: spin 1s linear infinite;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Make API call
    fetch('/api/commands/execute', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            command: command,
            description: description
        })
    })
    .then(response => {
        console.log('Response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        // Find the card element - try multiple selectors
        let card = buttonElement.closest('.command-item');
        if (!card) {
            card = buttonElement.closest('.accordion-item');
        }
        if (!card) {
            card = buttonElement.closest('.card');
        }
        
        console.log('Card element found:', card);
        
        // Update the command card with new results
        if (card) {
            updateCommandCard(card, data);
        }
        
        // Update summary if exists
        updateSummaryAfterRerun();
        
        // Visual feedback - flash the card briefly
        if (card) {
            card.classList.add('refreshing');
            setTimeout(() => card.classList.remove('refreshing'), 1000);
        }
        
        // Show success message in the card itself
        const statusDiv = document.createElement('div');
        statusDiv.className = 'alert alert-success mt-2 py-1 px-2';
        statusDiv.style.fontSize = '0.85rem';
        statusDiv.textContent = 'Command re-executed successfully';
        
        // Insert after the button
        const btnContainer = buttonElement.parentElement;
        if (btnContainer) {
            btnContainer.appendChild(statusDiv);
            setTimeout(() => statusDiv.remove(), 3000);
        }
    })
    .catch(err => {
        console.error('Error re-running command:', err);
        alert('Error re-running command: ' + err.message);
    })
    .finally(() => {
        // Restore button state
        if (icon) {
            icon.className = 'bi bi-arrow-clockwise';
        }
        buttonElement.disabled = false;
    });
}

/**
 * Update a command card with new results
 */
function updateCommandCard(cardElement, result) {
    if (!cardElement) return;
    
    // Update status badge
    const statusBadge = cardElement.querySelector('.status-badge, .badge');
    if (statusBadge) {
        if (result.success) {
            statusBadge.className = 'badge bg-success status-badge';
            statusBadge.innerHTML = '<i class="bi bi-check-circle"></i> ' + result.duration_ms + 'ms';
        } else if (result.error_type === 'access_denied') {
            statusBadge.className = 'badge bg-warning text-dark status-badge';
            statusBadge.innerHTML = '<i class="bi bi-shield-exclamation"></i> Access Denied';
        } else {
            statusBadge.className = 'badge bg-danger status-badge';
            statusBadge.innerHTML = '<i class="bi bi-x-circle"></i> Error';
        }
    }
    
    // Update metadata table if exists
    const tableRows = cardElement.querySelectorAll('table tr');
    if (tableRows.length >= 1) {
        const returnCodeRow = tableRows[0].querySelector('td');
        if (returnCodeRow) returnCodeRow.textContent = result.return_code;
    }
    if (tableRows.length >= 2) {
        const durationRow = tableRows[1].querySelector('td');
        if (durationRow) durationRow.textContent = result.duration_ms + 'ms';
    }
    if (tableRows.length >= 3) {
        const timestampRow = tableRows[2].querySelector('td');
        if (timestampRow) timestampRow.textContent = result.timestamp;
    }
    if (tableRows.length >= 4 && result.error_type) {
        const errorTypeRow = tableRows[3].querySelector('td');
        if (errorTypeRow) {
            errorTypeRow.innerHTML = '<span class="badge bg-' + (result.error_type === 'access_denied' ? 'warning' : 'danger') + '">' + result.error_type + '</span>';
        }
    }
    
    // Update stdout/output section
    const allSections = cardElement.querySelectorAll('.mb-3');
    allSections.forEach(section => {
        const h6 = section.querySelector('h6');
        if (h6) {
            const icon = h6.querySelector('i');
            if (icon && icon.classList.contains('bi-check2-all')) {
                // This is the output section
                const preCode = section.querySelector('pre code');
                if (preCode && result.stdout) {
                    preCode.textContent = result.stdout;
                }
                section.style.display = result.stdout ? 'block' : 'none';
            } else if (icon && icon.classList.contains('bi-exclamation-triangle')) {
                // This is the error section
                const preCode = section.querySelector('pre code');
                if (preCode && result.stderr) {
                    preCode.textContent = result.stderr;
                }
                section.style.display = result.stderr ? 'block' : 'none';
            }
        }
    });
    
    // For index.html dynamic display (no accordion structure)
    // Update output div if exists
    const outputCollapse = cardElement.querySelector('[id^="output-"]');
    if (outputCollapse) {
        const preCode = outputCollapse.querySelector('pre code');
        if (preCode && result.stdout) {
            try {
                const parsed = JSON.parse(result.stdout);
                preCode.textContent = JSON.stringify(parsed, null, 2);
            } catch (e) {
                preCode.textContent = result.stdout;
            }
        }
    }
    
    // Update error div if exists
    const errorCollapse = cardElement.querySelector('[id^="error-"]');
    if (errorCollapse) {
        const preCode = errorCollapse.querySelector('pre code');
        if (preCode && result.stderr) {
            preCode.textContent = result.stderr;
        }
        errorCollapse.style.display = result.stderr ? 'block' : 'none';
    }
}

/**
 * Update summary counts after re-running a command
 */
function updateSummaryAfterRerun() {
    // Re-calculate summary from all visible commands
    const commands = document.querySelectorAll('.command-item, .accordion-item');
    let successful = 0, failed = 0, accessDenied = 0;
    
    commands.forEach(cmd => {
        const badge = cmd.querySelector('.status-badge, .badge');
        if (badge) {
            if (badge.classList.contains('bg-success')) successful++;
            else if (badge.classList.contains('bg-warning')) accessDenied++;
            else if (badge.classList.contains('bg-danger')) failed++;
        }
    });
    
    // Update summary cards if they exist
    const summaryRows = document.querySelectorAll('.row.g-3');
    summaryRows.forEach(row => {
        const cards = row.querySelectorAll('.stat-card');
        if (cards.length === 4) {
            const successH3 = cards[0].querySelector('h3');
            const failedH3 = cards[1].querySelector('h3');
            const accessDeniedH3 = cards[2].querySelector('h3');
            const totalH3 = cards[3].querySelector('h3');
            
            if (successH3) successH3.textContent = successful;
            if (failedH3) failedH3.textContent = failed;
            if (accessDeniedH3) accessDeniedH3.textContent = accessDenied;
            if (totalH3) totalH3.textContent = successful + failed;
        }
    });
    
    // Also try the inline HTML summary format
    const successBadges = document.querySelectorAll('.stat-card.success h3');
    const failedBadges = document.querySelectorAll('.stat-card.danger h3');
    const accessDeniedBadges = document.querySelectorAll('.stat-card.warning h3');
    const totalBadges = document.querySelectorAll('.stat-card.info h3');
    
    successBadges.forEach(badge => badge.textContent = successful);
    failedBadges.forEach(badge => badge.textContent = failed);
    accessDeniedBadges.forEach(badge => badge.textContent = accessDenied);
    totalBadges.forEach(badge => badge.textContent = successful + failed);
}

/**
 * Format JSON string with nested JSON objects properly
 */
function formatNestedJSON(input) {
    console.log('formatNestedJSON input:', input ? input.substring(0, 200) : 'empty');
    
    if (!input) return input;
    
    // First try to parse as regular JSON
    try {
        const parsed = JSON.parse(input);
        console.log('Parsed as JSON successfully');
        return JSON.stringify(parsed, null, 2);
    } catch (e) {
        // Not a simple JSON, check for nested JSON strings
        console.log('Not simple JSON, trying to unescape');
    }
    
    // Try to find and unescape JSON strings within the output
    // This handles cases like {"Policy": "{\"Version\":...}"}
    let result = input;
    
    // Replace escaped newlines and quotes - multiple levels of escaping
    result = result.replace(/\\n/g, '\n');
    result = result.replace(/\\"/g, '"');
    result = result.replace(/\\\\/g, '\\');
    
    console.log('After unescaping:', result.substring(0, 200));
    
    // Try to parse again after unescaping
    try {
        const parsed = JSON.parse(result);
        console.log('Parsed after unescaping successfully');
        // Check if any property value is a string that looks like JSON
        const formatted = formatNestedObject(parsed);
        return JSON.stringify(formatted, null, 2);
    } catch (e) {
        console.log('Still not valid JSON after unescaping:', e.message);
        // Still not valid JSON, return original with some cleanup
    }
    
    return result;
}

/**
 * Recursively format nested JSON objects within a parsed object
 */
function formatNestedObject(obj) {
    if (typeof obj !== 'object' || obj === null) {
        return obj;
    }
    
    if (Array.isArray(obj)) {
        return obj.map(item => formatNestedObject(item));
    }
    
    const result = {};
    for (const key in obj) {
        const value = obj[key];
        if (typeof value === 'string') {
            // Try to parse string values that look like JSON
            try {
                const parsed = JSON.parse(value);
                // If parsed successfully, format it
                result[key] = formatNestedObject(parsed);
            } catch (e) {
                // Not JSON, keep as-is
                result[key] = value;
            }
        } else if (typeof value === 'object') {
            result[key] = formatNestedObject(value);
        } else {
            result[key] = value;
        }
    }
    return result;
}

// Export function for global use
window.formatNestedJSON = formatNestedJSON;
