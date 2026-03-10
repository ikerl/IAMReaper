# HTML Templates - Templates

## Description
Template system using Jinja2 with Bootstrap 5 and HTMX.

## Structure

```
templates/
├── base.html                    # Base template
├── index.html                   # Main dashboard
└── components/
    └── module_results.html      # Results component
```

---

## base.html

### Description
Base template with navbar, styles, and common scripts.

### Components

#### Navbar
- AWS region selector
- Active project indicator

#### Styles (CDN)
- Bootstrap 5.3 CSS
- Bootstrap Icons

#### Scripts (CDN)
- Bootstrap 5.3 JS Bundle
- HTMX 1.9.10
- Custom JS: `static/js/main.js`

### Jinja2 Blocks

```html
{% block title %}...{% endblock %}
{% block content %}...{% endblock %}
{% block scripts %}...{% endblock %}
```

---

## index.html

### Description
Main application dashboard.

### Sections

#### Projects Panel
- List of existing projects
- Project creation form
- Activate project button

#### Modules Panel
- List of available modules
- Run buttons
- Loading state

#### Results Panel
- Run history
- Command list with filters
- JSON export

### Command Filters

| Filter | Description |
|--------|-------------|
| search | Search in command/description |
| status | Filter by status (success/failed/all) |
| limit | Results limit |
| offset | Pagination |

---

## components/module_results.html

### Description
HTMX component for displaying module results.

### Elements

#### Summary Cards
- Total commands
- Successful
- Failed
- Access Denied

#### Command List
- Accordion with expandable commands
- Status badge (✅/⚠️/❌)
- Copy command button
- Formatted JSON

---

## static/css/custom.css

### Main Styles

```css
/* Custom scrollbar */
::-webkit-scrollbar { ... }

/* Cards */
.card { ... }

/* Code command display */
.command-display {
    font-family: monospace;
    background: #f5f5f5;
    padding: 0.5rem;
    border-radius: 4px;
}

/* Loading spinner */
.loading-spinner { ... }
```

---

## static/js/main.js

### JS Functions

#### HTMX Configuration
```javascript
htmx.config.defaultSwapStyle = 'outerHTML';
```

#### Handlers

| Function | Description |
|---------|-------------|
| `handleRegionChange(region)` | Changes AWS region |
| `copyToClipboard(text)` | Copies to clipboard |
| `formatJSON(str)` | Formats JSON |
| `showAlert(message, type)` | Shows alert |

---

## HTMX Integration

### Common Attributes

| Attribute | Description |
|----------|-------------|
| `hx-post` | URL for POST |
| `hx-get` | URL for GET |
| `hx-target` | Target element |
| `hx-swap` | Swap method |
| `hx-indicator` | Loading element |
| `hx-boost` | Progressive enhancement |

### Example

```html
<button hx-post="/api/modules/iam/run"
        hx-target="#results"
        hx-indicator="#loading">
    Run IAM
</button>
```

---

## See also

- [app.py](app.md) - API endpoints
- [modules/modules.md](modules.md) - Modules
