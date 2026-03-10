# AWS Enumeration Modules

## Overview

Modules are extensions that implement enumeration of different AWS services. Each module inherits from [`BaseModule`](modules/base.py) and implements specific AWS CLI commands.

## Module Structure

```
modules/
├── __init__.py      # Exports
├── base.py          # BaseModule (base class)
├── executor.py      # AWSExecutor
├── iam.py           # IAM module
└── kms.py           # KMS module
```

---

## BaseModule

### Description
Abstract base class for all enumeration modules.

### Class Attributes
```python
MODULE_NAME: str = "base"
DISPLAY_NAME: str = "Base Module"
```

### Abstract Methods

#### [`run_all()`](modules/base.py:19)
Main method that executes all enumeration checks.

```python
@abstractmethod
def run_all(self) -> dict[str, Any]:
    """Run all enumeration checks for this module."""
    pass
```

### Helper Methods

#### [`_summarize_commands()`](modules/base.py:67)
Generates execution statistics.

```python
def _summarize_commands(commands: list[dict]) -> dict[str, int]:
    # Returns: {"total": N, "successful": N, "failed": N, "access_denied": N, "other_errors": N}
```

---

## AWSExecutor

### Description
AWS CLI command executor with error handling and automatic profile support.

### Automatic Features
- **Auto-profile**: If `profile_name` is configured, it automatically adds `--profile <name>` to all AWS commands (those starting with `aws `).
- **Error Detection**: Classifies errors (access_denied, throttling, etc.)
- **Timeout**: 120 seconds by default

### Constructor
```python
AWSExecutor(region: str = "us-east-1", profile_name: str = None)
```

### Methods

#### [`execute()`](modules/executor.py:49)
Executes an arbitrary shell command.

```python
def execute(
    self,
    command: str,
    description: str = "",
    parse_json: bool = True
) -> CommandResult:
```

#### [`execute_aws()`](modules/executor.py:117)
Executes an AWS CLI command.

```python
def execute_aws(
    self,
    service: str,
    operation: str,
    description: str = "",
    **kwargs
) -> CommandResult:
```

### Detected Error Types

| Error Type | Description |
|------------|-------------|
| `access_denied` | No permissions |
| `throttling` | Rate limit exceeded |
| `not_found` | Resource does not exist |
| `invalid_credential` | Invalid credential |
| `expired_token` | Session token expired |
| `validation_error` | Invalid input |
| `timeout` | Command expired (>120s) |

---

## IAMModule

### Description
IAM enumeration module. Documented in [modules/iam.py](modules/iam.md)

### Attributes
```python
MODULE_NAME = "iam"
DISPLAY_NAME = "AWS IAM Enumeration"
```

### AWS Commands

| Method | AWS Command | Description |
|--------|------------|-------------|
| `_get_account_authorization_details()` | `aws iam get-account-authorization-details` | Complete IAM snapshot |
| `_list_users()` | `aws iam list-users` | List users |
| `_list_groups()` | `aws iam list-groups` | List groups |
| `_list_roles()` | `aws iam list-roles` | List roles |
| `_list_policies()` | `aws iam list-policies` | List policies |
| `_list_saml_providers()` | `aws iam list-saml-providers` | List SAML providers |
| `_list_open_id_connect_providers()` | `aws iam list-open-id-connect-providers` | List OIDC providers |
| `_get_account_password_policy()` | `aws iam get-account-password-policy` | Password policy |
| `_list_mfa_devices()` | `aws iam list-mfa-devices` | List MFA devices |

---

## KMSModule

### Description
KMS enumeration module with multi-region support.

### Attributes
```python
MODULE_NAME = "kms"
DISPLAY_NAME = "AWS KMS Enumeration"
```

### Methods

#### [`run_all()`](modules/kms.py:36)
Executes KMS enumeration in all regions.

#### [`_get_regions()`](modules/kms.py:89)
Gets list of available AWS regions.

#### AWS Commands

| Method | AWS Command | Description |
|--------|------------|-------------|
| `_list_keys(region)` | `aws kms list-keys` | List KMS keys |
| `_describe_key(key_id, region)` | `aws kms describe-key` | Key details |
| `_list_key_policies(key_id, region)` | `aws kms list-key-policies` | List policies |
| `_get_key_policy(key_id, policy_name, region)` | `aws kms get-key-policy` | Get policy |
| `_list_grants(key_id, region)` | `aws kms list-grants` | List grants |
| `_describe_custom_key_stores(region)` | `aws kms describe-custom-key-stores` | Custom key stores |

### Data Structure

```python
{
    "regions": {
        "us-east-1": {
            "keys": [...],
            "key_count": 5
        }
    },
    "custom_key_stores": [...],
    "total_keys": 5,
    "total_regions": 1
}
```

---

## Adding a New Module

1. Create file in `modules/` (e.g., `modules/ec2.py`)
2. Inherit from `BaseModule`
3. Implement `run_all()`
4. Register in `app.py`

```python
from modules.base import BaseModule

class EC2Module(BaseModule):
    MODULE_NAME = "ec2"
    DISPLAY_NAME = "AWS EC2 Enumeration"
    
    def run_all(self):
        # Enumeration logic
        pass
```

## See also

- [app.py](app.md) - Flask application
- [database/db.md](database/db.md) - Database
