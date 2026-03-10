# Implementing New AWS Modules

This guide documents the process for adding new AWS enumeration modules to IAMReaper.

## Overview

When adding a new AWS enumeration module, you must update **4 files** in the codebase:

1. Create module file in `modules/` (e.g., `modules/codebuild.py`)
2. Update `modules/__init__.py`
3. Update `app.py` (3 locations)
4. Update `templates/index.html`

---

## Step 1: Create Module File

Create a new file in `modules/` following the naming convention `modules/<service>.py`:

```python
"""AWS <Service> enumeration module."""

import json
from typing import Any
from datetime import datetime

from modules.base import BaseModule
from modules.executor import AWSExecutor, CommandResult


class <Service>Module(BaseModule):
    """AWS <Service> enumeration module."""

    MODULE_NAME = "<service>"
    DISPLAY_NAME = "AWS <Service> Enumeration"

    def __init__(self, executor: AWSExecutor):
        super().__init__(executor)
        self.commands_executed: list[dict] = []
        # Add module-specific attributes here

    def _add_result(self, result: CommandResult) -> None:
        """Add a command result to the executed commands list."""
        self.commands_executed.append({
            "command": result.command,
            "description": result.description,
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "duration_ms": result.duration_ms,
            "error_type": result.error_type,
            "data": result.data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    def run_all(self) -> dict[str, Any]:
        """Execute all <Service> enumeration checks."""
        self.commands_executed = []
        
        # Add enumeration methods here
        # Example: self._list_resources()
        
        # Generate summary
        summary = self._summarize_commands(self.commands_executed)

        return {
            "module": self.MODULE_NAME,
            "display_name": self.DISPLAY_NAME,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "commands_executed": self.commands_executed,
            "summary": summary,
            "data": self._extract_data()
        )

    # Add enumeration methods here
    # def _list_resources(self) -> None:
    #     """List AWS <Service> resources."""
    #     result = self.executor.execute_aws(
    #         service="<service>",
    #         operation="list-<resources>",
    #         description="List <Service> resources"
    #     )
    #     self._add_result(result)

    def _extract_data(self) -> dict[str, Any]:
        """Extract enumerated data for summary."""
        return {
            # Add extracted data here
        }
```

### Key Patterns

1. **Using AWS Executor**: Use `self.executor.execute_aws()` to run AWS CLI commands:
   ```python
   result = self.executor.execute_aws(
       service="service_name",       # AWS service name (e.g., "codebuild")
       operation="operation_name", # AWS API operation (e.g., "list-projects")
       description="Human-readable description",
       **kwargs                     # Additional parameters
   )
   self._add_result(result)
   ```

2. **Accessing Command Results**: Results are automatically stored in `self.commands_executed` and include:
   - `command`: The CLI command executed
   - `description`: Human-readable description
   - `success`: Boolean indicating success
   - `stdout`: Command output
   - `stderr`: Error output
   - `return_code`: Exit code
   - `duration_ms`: Execution time
   - `error_type`: Error classification (e.g., "access_denied")
   - `data`: Parsed JSON output

3. **Data Extraction**: The `_extract_data()` method should return a dictionary with key information for summary display.

---

## Step 2: Update modules/__init__.py

Add the import and export:

```python
# Add import
from modules.codebuild import CodeBuildModule

# Add to __all__
__all__ = [..., 'CodeBuildModule']
```

---

## Step 3: Update app.py

Update **3 locations** in `app.py`:

### 3.1 Add Import

```python
from modules.codebuild import CodeBuildModule
```

### 3.2 Add to list_modules() Function

Add module info to the modules list (around line 620):

```python
{
    "name": "codebuild",
    "display_name": "AWS CodeBuild Enumeration",
    "description": "Enumerate CodeBuild projects, builds, reports, and more"
},
```

### 3.3 Add to run_module() Function

Add module instantiation (around line 675):

```python
elif module_name == "codebuild":
    module = CodeBuildModule(executor)
```

### 3.4 Add to create_run() Function

Add the same elif clause (around line 433):

```python
elif module_name == "codebuild":
    module = CodeBuildModule(executor)
```

---

## Step 4: Update templates/index.html

Add the module button in the modules panel (find the last module and add after it):

```html
<!-- CodeBuild Module -->
<div class="list-group-item">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <h6 class="mb-1"><i class="bi bi-hammer"></i> CodeBuild</h6>
            <small class="text-muted">Projects, builds, reports</small>
        </div>
        <button class="btn btn-primary btn-sm" 
               onclick="runModule('codebuild', {{ active_project.id }})"
               id="run-codebuild-btn">
            <i class="bi bi-play-fill"></i> Run
        </button>
    </div>
</div>
```

---

## Testing the Module

Verify the module imports correctly:

```bash
python3 -c "from modules.codebuild import CodeBuildModule; print('Import successful')"
```

Verify the Flask app loads:

```bash
python3 -c "from app import app; print('Flask app import successful')"
```

---

## Best Practices

1. **Error Handling**: The executor automatically handles errors. Check `result.success` before processing data.

2. **Sensitive Data**: Look for sensitive information like:
   - Environment variables with secrets
   - IAM credentials in descriptions
   - Private keys in configurations
   - Passwords in attributes

3. **Pagination**: For list operations that may return many results, consider implementing pagination.

4. **Rate Limiting**: AWS services may throttle requests. The executor handles some rate limiting automatically.

5. **Incremental Enumeration**: When enumerating resources, store results in module attributes to enable detailed enumeration of each resource.

---

## Example: CodeBuild Module

See [`modules/codebuild.py`](../modules/codebuild.py) for a complete implementation example that includes:

- Listing source credentials
- Listing and enumerating projects
- Detecting sensitive environment variables
- Listing builds and build batches
- Listing and describing test reports
