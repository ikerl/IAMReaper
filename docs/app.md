# Flask Application - app.py

## Description
Flask application entry point. Handles all API routes, templates, and configuration.

## Structure

### Main Endpoints

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/` | GET | Main dashboard page |
| `/api/health` | GET | Health check |
| `/api/modules` | GET | List available modules |
| `/api/modules/<module_name>/run` | POST, GET | Run a module |
| `/api/projects` | GET, POST | Projects CRUD |
| `/api/projects/<int:project_id>/runs` | GET, POST | Project runs |
| `/api/runs/<int:run_id>` | GET | Run details |
| `/api/region` | GET, POST | Region management |

### Main Functions

#### [`get_aws_executor()`](app.py:26)
Creates an AWS executor with the active project's region.

```python
def get_aws_executor() -> AWSExecutor:
    # Get region from project or session
    return AWSExecutor(region=project['aws_region'], profile_name=project['profile_name'])
```

#### [`sync_project_to_aws_credentials()`](app.py:52)
Synchronizes project credentials to `~/.aws/credentials`.

### Module Integration

```python
from modules.iam import IAMModule
from modules.kms import KMSModule

# In run_module():
if module_name == "iam":
    module = IAMModule(executor)
elif module_name == "kms":
    module = KMSModule(executor)
```

## Configuration

- **Secret Key**: Automatically generated with `os.urandom(24)`
- **Database**: SQLite at `iamreaper.db`
- **Port**: 5000 (debug mode)

## See also

- [modules/base.py](modules/base.md) - Base module class
- [modules/iam.py](modules/iam.md) - IAM module
- [modules/kms.py](modules/kms.md) - KMS module
