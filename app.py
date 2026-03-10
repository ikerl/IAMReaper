"""IAMReaper - AWS Enumeration Tool."""

import os
import json
import uuid
import configparser
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, Response

from modules.executor import AWSExecutor
from modules.iam import IAMModule
from modules.kms import KMSModule
from modules.s3 import S3Module
from modules.secretsmanager import SecretsManagerModule
from modules.ec2 import EC2Module
from modules.ssm import SSMModule
from modules.elb import ELBModule
from modules.lightsail import LightsailModule
from modules.aws_lambda import LambdaModule
from modules.apigateway import APIGatewayModule
from modules.efs import EFSModule
from modules.rds import RDSModule
from modules.dynamodb import DynamoDBModule
from modules.ecr import ECRModule
from modules.ecs import ECSModule
from modules.beanstalk import BeanstalkModule
from modules.codebuild import CodeBuildModule
from modules.sqs import SQSModule
from modules.sns import SNSModule
from modules.eventbridge import EventBridgeSchedulerModule
from modules.cognito import CognitoModule
from modules.stepfunctions import StepFunctionsModule
from database.schema import init_db
from database import db
from models.project import Project


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database on startup
init_db()


# ==================== PROJECT FUNCTIONS ====================

def get_aws_executor():
    """Get or create AWS executor with project profile."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if there's an active project
    project_id = session.get('active_project_id')
    logger.info(f"get_aws_executor: project_id={project_id}")
    
    if project_id:
        project = db.get_project(project_id)
        if project:
            logger.info(f"get_aws_executor: project={project['name']}, profile={project['profile_name']}")
            return AWSExecutor(
                region=project['aws_region'],
                profile_name=project['profile_name']
            )
    
    # Fallback to session region
    region = session.get('aws_region', 'us-east-1')
    logger.info(f"get_aws_executor: no project, using region={region}")
    return AWSExecutor(region=region)


def get_active_project():
    """Get the currently active project."""
    project_id = session.get('active_project_id')
    if project_id:
        return db.get_project(project_id)
    return None


def sync_project_to_aws_credentials(project_data):
    """Sync project credentials to ~/.aws/credentials file."""
    aws_dir = os.path.expanduser("~/.aws")
    credentials_file = os.path.join(aws_dir, "credentials")
    config_file = os.path.join(aws_dir, "config")
    
    # Ensure ~/.aws directory exists
    os.makedirs(aws_dir, exist_ok=True)
    
    # Read existing credentials or create new config
    config = configparser.ConfigParser()
    if os.path.exists(credentials_file):
        config.read(credentials_file)
    
    # Add/update profile
    profile_name = project_data['profile_name']
    if not config.has_section(profile_name):
        config.add_section(profile_name)
    
    config.set(profile_name, 'aws_access_key_id', project_data['aws_access_key_id'])
    config.set(profile_name, 'aws_secret_access_key', project_data['aws_access_secret'])
    config.set(profile_name, 'region', project_data.get('aws_region', 'us-east-1'))
    
    if project_data.get('aws_session_token'):
        config.set(profile_name, 'aws_session_token', project_data['aws_session_token'])
    
    # Write back to credentials file
    with open(credentials_file, 'w') as f:
        config.write(f)
    
    # Also update config file with region
    config_file_parser = configparser.ConfigParser()
    if os.path.exists(config_file):
        config_file_parser.read(config_file)
    
    # Config file uses "profile " prefix
    config_profile_name = f"profile {profile_name}"
    if not config_file_parser.has_section(config_profile_name):
        config_file_parser.add_section(config_profile_name)
    
    config_file_parser.set(config_profile_name, 'region', project_data.get('aws_region', 'us-east-1'))
    
    # Write back to config file
    with open(config_file, 'w') as f:
        config_file_parser.write(f)
    
    return True


# ==================== BASIC ENDPOINTS ====================

@app.route('/')
def index():
    """Main dashboard page."""
    active_project = get_active_project()
    projects = db.get_all_projects()
    runs = []
    
    if active_project:
        runs = db.get_runs_by_project(active_project['id'])
    
    return render_template('index.html', 
                         active_project=active_project,
                         projects=projects,
                         runs=runs)


@app.route('/run/<int:run_id>')
def run_view(run_id):
    """Standalone page showing run results."""
    run = db.get_run(run_id)
    if not run:
        return "Run not found", 404
    
    project = db.get_project(run['project_id'])
    commands = db.get_commands_by_run(run_id)
    
    return render_template('run.html',
                         run=run,
                         project=project,
                         commands=commands)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
    """Simple test endpoint."""
    return jsonify({"message": "Test works!", "method": request.method})


# ==================== PROJECT ENDPOINTS ====================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects."""
    projects = db.get_all_projects()
    # Mask credentials
    for p in projects:
        p['aws_access_key_id'] = p['aws_access_key_id'][:4] + "****" if p.get('aws_access_key_id') else ""
        p['aws_access_secret'] = "****"
    return jsonify({"projects": projects})


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project."""
    data = request.get_json()
    
    # Validate required fields
    required = ['name', 'profile_name', 'aws_access_key_id', 'aws_access_secret', 'aws_region']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Check if name or profile already exists
    if db.get_project_by_name(data['name']):
        return jsonify({"error": "Project name already exists"}), 400
    
    # Create project in database
    project_id = db.create_project(
        name=data['name'],
        profile_name=data['profile_name'],
        description=data.get('description', ''),
        aws_access_key_id=data['aws_access_key_id'],
        aws_access_secret=data['aws_access_secret'],
        aws_region=data['aws_region'],
        aws_session_token=data.get('aws_session_token')
    )
    
    # Sync credentials to ~/.aws/credentials
    project = db.get_project(project_id)
    sync_project_to_aws_credentials(project)
    
    # Set as active project
    db.set_active_project(project_id)
    session['active_project_id'] = project_id
    session['aws_region'] = project['aws_region']
    
    return jsonify({"id": project_id, "message": "Project created", "active": True}), 201


@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details."""
    project = db.get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Mask credentials
    project['aws_access_key_id'] = project['aws_access_key_id'][:4] + "****"
    project['aws_access_secret'] = "****"
    return jsonify(project)


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project."""
    data = request.get_json()
    
    project = db.get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Update in database
    db.update_project(
        project_id=project_id,
        name=data.get('name'),
        profile_name=data.get('profile_name'),
        description=data.get('description'),
        aws_access_key_id=data.get('aws_access_key_id'),
        aws_access_secret=data.get('aws_access_secret'),
        aws_region=data.get('aws_region'),
        aws_session_token=data.get('aws_session_token')
    )
    
    # Re-sync credentials if credentials changed
    if data.get('aws_access_key_id') or data.get('aws_access_secret'):
        project = db.get_project(project_id)
        sync_project_to_aws_credentials(project)
    
    # Set as active project
    db.set_active_project(project_id)
    session['active_project_id'] = project_id
    session['aws_region'] = project['aws_region']
    
    return jsonify({"message": "Project updated", "active": True})


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project."""
    if not db.delete_project(project_id):
        return jsonify({"error": "Project not found"}), 404
    
    return jsonify({"message": "Project deleted"})


@app.route('/api/projects', methods=['DELETE'])
def delete_all_projects():
    """Delete all projects."""
    projects = db.get_all_projects()
    deleted_count = 0
    for project in projects:
        if db.delete_project(project['id']):
            deleted_count += 1
    
    # Clear active project from session
    session.pop('active_project_id', None)
    session.pop('aws_region', None)
    
    return jsonify({"message": f"Deleted {deleted_count} projects"})


@app.route('/api/projects/<int:project_id>/activate', methods=['POST'])
def activate_project(project_id):
    """Activate a project."""
    project = db.get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Set as active in database
    db.set_active_project(project_id)
    
    # Store in session
    session['active_project_id'] = project_id
    session['aws_region'] = project['aws_region']
    
    return jsonify({
        "message": "Project activated",
        "project": {
            "id": project['id'],
            "name": project['name'],
            "profile_name": project['profile_name'],
            "aws_region": project['aws_region']
        }
    })


@app.route('/api/projects/<int:project_id>/region', methods=['POST'])
def update_project_region(project_id):
    """Update project region and sync to AWS credentials."""
    data = request.get_json()
    new_region = data.get('region')
    
    if not new_region:
        return jsonify({"error": "Region is required"}), 400
    
    # Get current project
    project = db.get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Update region in database
    db.update_project(project_id, aws_region=new_region)
    
    # Update the project data with new region for credentials sync
    project['aws_region'] = new_region
    
    # Sync to AWS credentials file
    sync_project_to_aws_credentials(project)
    
    # Update session
    session['aws_region'] = new_region
    
    return jsonify({
        "message": "Region updated",
        "region": new_region,
        "profile": project['profile_name']
    })


@app.route('/api/projects/sync-credentials', methods=['POST'])
def sync_all_credentials():
    """Sync all project credentials to ~/.aws/credentials."""
    projects = db.get_all_projects()
    
    for project in projects:
        sync_project_to_aws_credentials(project)
    
    return jsonify({"message": f"Synced {len(projects)} projects to ~/.aws/credentials"})


@app.route('/api/projects/active', methods=['GET'])
def get_active_project_info():
    """Get currently active project with credentials."""
    project = get_active_project()
    if not project:
        return jsonify({"active": False})
    
    return jsonify({
        "active": True,
        "id": project['id'],
        "name": project['name'],
        "profile_name": project['profile_name'],
        "aws_region": project['aws_region'],
        "aws_access_key_id": project['aws_access_key_id'],
        "aws_access_secret": project['aws_access_secret']
    })


# ==================== RUN ENDPOINTS ====================

@app.route('/api/projects/<int:project_id>/runs', methods=['GET'])
def get_runs(project_id):
    """Get runs for a project."""
    runs = db.get_runs_by_project(project_id)
    return jsonify({"runs": runs})


@app.route('/api/projects/<int:project_id>/runs', methods=['POST'])
def create_run(project_id):
    """Create and run a module."""
    # Accept JSON or form data
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()
    
    module_name = data.get('module_name', 'iam')
    
    # Check project exists
    project = db.get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Create run in database
    run_id = db.create_run(project_id, module_name)
    
    # Get executor with project profile
    executor = AWSExecutor(
        region=project['aws_region'],
        profile_name=project['profile_name']
    )
    
    # Run module
    if module_name == "iam":
        module = IAMModule(executor)
    elif module_name == "kms":
        module = KMSModule(executor)
    elif module_name == "s3":
        module = S3Module(executor)
    elif module_name == "secretsmanager":
        module = SecretsManagerModule(executor)
    elif module_name == "ec2":
        module = EC2Module(executor)
    elif module_name == "ssm":
        module = SSMModule(executor)
    elif module_name == "elb":
        module = ELBModule(executor)
    elif module_name == "lightsail":
        module = LightsailModule(executor)
    elif module_name == "lambda":
        module = LambdaModule(executor)
    elif module_name == "apigateway":
        module = APIGatewayModule(executor)
    elif module_name == "efs":
        module = EFSModule(executor)
    elif module_name == "rds":
        module = RDSModule(executor)
    elif module_name == "dynamodb":
        module = DynamoDBModule(executor)
    elif module_name == "ecr":
        module = ECRModule(executor)
    elif module_name == "ecs":
        module = ECSModule(executor)
    elif module_name == "beanstalk":
        module = BeanstalkModule(executor)
    elif module_name == "codebuild":
        module = CodeBuildModule(executor)
    elif module_name == "sqs":
        module = SQSModule(executor)
    elif module_name == "sns":
        module = SNSModule(executor)
    elif module_name == "eventbridge":
        module = EventBridgeSchedulerModule(executor)
    elif module_name == "cognito":
        module = CognitoModule(executor)
    elif module_name == "stepfunctions":
        module = StepFunctionsModule(executor)
    else:
        return jsonify({"error": f"Unknown module: {module_name}"}), 404
    
    module_results = module.run_all()
    
    # Save commands to database
    summary_success = 0
    summary_failed = 0
    summary_access_denied = 0
    
    for cmd in module.commands_executed:
        db.create_command(
            run_id=run_id,
            command=cmd['command'],
            description=cmd.get('description', ''),
            success=cmd['success'],
            stdout=cmd.get('stdout', ''),
            stderr=cmd.get('stderr', ''),
            return_code=cmd.get('return_code', 0),
            duration_ms=cmd.get('duration_ms', 0),
            error_type=cmd.get('error_type'),
            data=cmd.get('data')
        )
        
        if cmd['success']:
            summary_success += 1
        else:
            summary_failed += 1
            if cmd.get('error_type') == 'access_denied':
                summary_access_denied += 1
    
    # Update run summary
    db.update_run_summary(
        run_id=run_id,
        summary_success=summary_success,
        summary_failed=summary_failed,
        summary_access_denied=summary_access_denied,
        status='completed'
    )
    
    # Return results
    run = db.get_run(run_id)
    
    return jsonify({
        "run": run,
        "commands_count": len(module.commands_executed)
    })


@app.route('/api/runs/<int:run_id>', methods=['GET'])
def get_run(run_id):
    """Get run details."""
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(run)


@app.route('/api/runs/<int:run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Delete a run and its commands."""
    if not db.delete_run(run_id):
        return jsonify({"error": "Run not found"}), 404
    return jsonify({"message": "Run deleted"})


@app.route('/api/projects/<int:project_id>/runs', methods=['DELETE'])
def delete_all_runs(project_id):
    """Delete all runs for a project (clear history)."""
    project = db.get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    runs = db.get_runs_by_project(project_id)
    deleted_count = 0
    
    for run in runs:
        if db.delete_run(run['id']):
            deleted_count += 1
    
    return jsonify({"message": f"Deleted {deleted_count} runs", "deleted": deleted_count})


@app.route('/api/runs/<int:run_id>/commands', methods=['GET'])
def get_run_commands(run_id):
    """Get commands for a run with filters."""
    search = request.args.get('search', '')
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 1000))
    offset = int(request.args.get('offset', 0))
    
    commands = db.get_commands_by_run(run_id, search, status, limit, offset)
    total = db.get_command_count(run_id, search, status)
    
    return jsonify({
        "commands": commands,
        "total": total,
        "limit": limit,
        "offset": offset
    })


# ==================== MODULE ENDPOINTS ====================

@app.route('/api/modules', methods=['GET'])
def list_modules():
    """List available modules."""
    modules = [
        {
            "name": "iam",
            "display_name": "AWS IAM Enumeration",
            "description": "Enumerate IAM users, groups, roles, policies, and providers"
        },
        {
            "name": "kms",
            "display_name": "AWS KMS Enumeration",
            "description": "Enumerate KMS keys, policies, grants, and custom key stores across all regions"
        },
        {
            "name": "s3",
            "display_name": "AWS S3 Enumeration",
            "description": "Enumerate S3 buckets, objects, ACLs, policies, and security configurations"
        },
        {
            "name": "secretsmanager",
            "display_name": "AWS Secrets Manager Enumeration",
            "description": "Enumerate Secrets Manager secrets, versions, values, and resource policies"
        },
        {
            "name": "ec2",
            "display_name": "AWS EC2 Enumeration",
            "description": "Enumerate EC2 instances, VPCs, security groups, volumes, snapshots, and networking"
        },
        {
            "name": "ssm",
            "display_name": "AWS SSM Enumeration",
            "description": "Enumerate Systems Manager managed instances, parameters, sessions, and patches"
        },
        {
            "name": "elb",
            "display_name": "AWS ELB Enumeration",
            "description": "Enumerate Classic and Application/Network Load Balancers, listeners, and configurations"
        },
        {
            "name": "lightsail",
            "display_name": "AWS Lightsail Enumeration",
            "description": "Enumerate Lightsail instances, databases, disks, snapshots, load balancers, static IPs, and key pairs"
        },
        {
            "name": "lambda",
            "display_name": "AWS Lambda Enumeration",
            "description": "Enumerate Lambda functions, layers, versions, aliases, and configurations"
        },
        {
            "name": "apigateway",
            "display_name": "AWS API Gateway Enumeration",
            "description": "Enumerate API Gateway REST APIs, stages, resources, authorizers, models, and API keys"
        },
        {
            "name": "efs",
            "display_name": "AWS EFS Enumeration",
            "description": "Enumerate EFS file systems, mount targets, security groups, access points, and replication configurations"
        },
        {
            "name": "rds",
            "display_name": "AWS RDS Enumeration",
            "description": "Enumerate RDS clusters, instances, snapshots, security groups, backups, and proxies"
        },
        {
            "name": "dynamodb",
            "display_name": "AWS DynamoDB Enumeration",
            "description": "Enumerate DynamoDB tables, backups, global tables, exports, and endpoints"
        },
        {
            "name": "ecr",
            "display_name": "AWS ECR Enumeration",
            "description": "Enumerate ECR repositories, images, scanning configurations, lifecycle policies, and access policies"
        },
        {
            "name": "ecs",
            "display_name": "AWS ECS Enumeration",
            "description": "Enumerate ECS clusters, container instances, services, tasks, and task definitions"
        },
        {
            "name": "beanstalk",
            "display_name": "AWS Elastic Beanstalk Enumeration",
            "description": "Enumerate Beanstalk applications, environments, configurations, resources, and events"
        },
        {
            "name": "codebuild",
            "display_name": "AWS CodeBuild Enumeration",
            "description": "Enumerate CodeBuild projects, builds, reports, source credentials, and sensitive environment variables"
        },
        {
            "name": "sqs",
            "display_name": "AWS SQS Enumeration",
            "description": "Enumerate SQS queues and their attributes"
        },
        {
            "name": "sns",
            "display_name": "AWS SNS Enumeration",
            "description": "Enumerate SNS topics and subscriptions"
        },
        {
            "name": "eventbridge",
            "display_name": "AWS EventBridge Scheduler Enumeration",
            "description": "Enumerate EventBridge Scheduler schedules and schedule groups"
        },
        {
            "name": "cognito",
            "display_name": "AWS Cognito Enumeration",
            "description": "Enumerate Cognito identity pools, user pools, users, groups, and security configurations"
        },
        {
            "name": "stepfunctions",
            "display_name": "AWS Step Functions Enumeration",
            "description": "Enumerate Step Functions state machines, executions, activities, and map runs"
        }
    ]
    return jsonify({"modules": modules})


@app.route('/api/modules/<module_name>/run', methods=['POST', 'GET'])
def run_module(module_name):
    """Run a module using active project."""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    project = get_active_project()
    if not project:
        return jsonify({"error": "No active project. Please select a project first."}), 400
    
    try:
        logger.info(f"Starting module: {module_name}")
        
        executor = get_aws_executor()
        logger.info(f"Executor created with profile: {executor.profile_name}, region: {executor.region}")
        
        if module_name == "iam":
            module = IAMModule(executor)
        elif module_name == "kms":
            module = KMSModule(executor)
        elif module_name == "s3":
            module = S3Module(executor)
        elif module_name == "secretsmanager":
            module = SecretsManagerModule(executor)
        elif module_name == "ec2":
            module = EC2Module(executor)
        elif module_name == "ssm":
            module = SSMModule(executor)
        elif module_name == "elb":
            module = ELBModule(executor)
        elif module_name == "lightsail":
            module = LightsailModule(executor)
        elif module_name == "lambda":
            module = LambdaModule(executor)
        elif module_name == "apigateway":
            module = APIGatewayModule(executor)
        elif module_name == "efs":
            module = EFSModule(executor)
        elif module_name == "rds":
            module = RDSModule(executor)
        elif module_name == "dynamodb":
            module = DynamoDBModule(executor)
        elif module_name == "ecr":
            module = ECRModule(executor)
        elif module_name == "ecs":
            module = ECSModule(executor)
        elif module_name == "beanstalk":
            module = BeanstalkModule(executor)
        elif module_name == "codebuild":
            module = CodeBuildModule(executor)
        elif module_name == "sqs":
            module = SQSModule(executor)
        elif module_name == "sns":
            module = SNSModule(executor)
        elif module_name == "eventbridge":
            module = EventBridgeSchedulerModule(executor)
        elif module_name == "cognito":
            module = CognitoModule(executor)
        elif module_name == "stepfunctions":
            module = StepFunctionsModule(executor)
        else:
            return jsonify({"error": f"Unknown module: {module_name}"}), 404
        
        logger.info(f"Running module {module_name}...")
        module_results = module.run_all()
        logger.info(f"Module {module_name} completed with {len(module.commands_executed)} commands")
        
        # Debug: log how many commands are in results
        if 'commands_executed' in module_results:
            total_cmds = len(module_results['commands_executed'])
            policy_version_cmds = [c for c in module_results['commands_executed'] if 'get-policy-version' in c.get('command', '')]
            logger.info(f"Results contains {total_cmds} commands, {len(policy_version_cmds)} are get-policy-version")
        
        # If HTMX request - return HTML
        if request.headers.get('HX-Request'):
            return render_template('components/module_results.html', 
                                module_name=module_name, 
                                module_data=module_results)
        
        return jsonify(module_results)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LEGACY ENDPOINTS (for compatibility) ====================

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get current results (legacy)."""
    project = get_active_project()
    if not project:
        return jsonify({"module_results": {}})
    
    runs = db.get_runs_by_project(project['id'])
    return jsonify({"runs": runs})


@app.route('/api/clear', methods=['POST'])
def clear_results():
    """Clear session data."""
    session.pop('active_project_id', None)
    session.pop('aws_region', None)
    return jsonify({"status": "cleared"})


@app.route('/api/region', methods=['GET', 'POST'])
def handle_region():
    """Get or set AWS region."""
    if request.method == 'POST':
        data = request.get_json()
        region = data.get('region', 'us-east-1')
        session['aws_region'] = region
        return jsonify({"region": region})
    
    region = session.get('aws_region', 'us-east-1')
    return jsonify({"region": region})


@app.route('/api/export/<module_name>', methods=['GET'])
def export_results(module_name):
    """Export results as JSON."""
    project = get_active_project()
    if not project:
        return jsonify({"error": "No active project"}), 404
    
    latest_run = db.get_latest_run(project['id'], module_name)
    
    if not latest_run:
        return jsonify({"error": "No results to export for this module"}), 404
    
    commands = db.get_commands_by_run(latest_run['id'])
    
    return Response(
        json.dumps({
            "module": module_name,
            "run": latest_run,
            "commands": commands
        }, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename={module_name}_results.json'}
    )


@app.route('/api/commands/execute', methods=['POST'])
def execute_command():
    """
    Execute a single AWS CLI command.
    
    Request body:
    {
        "command": "aws iam list-users --profile myprofile",
        "description": "List all IAM users"
    }
    
    Returns:
    {
        "command": "...",
        "description": "...",
        "success": true/false,
        "stdout": "...",
        "stderr": "...",
        "return_code": 0,
        "duration_ms": 123.45,
        "error_type": null or "access_denied",
        "data": {...},
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Get request data
    data = request.get_json() or {}
    command = data.get('command')
    description = data.get('description', '')
    
    if not command:
        return jsonify({"error": "Command is required"}), 400
    
    # Get active project
    project = get_active_project()
    if not project:
        return jsonify({"error": "No active project. Please select a project first."}), 400
    
    try:
        logger.info(f"Executing single command: {command}")
        
        # Create executor with project profile
        executor = AWSExecutor(
            region=project['aws_region'],
            profile_name=project['profile_name']
        )
        
        # Execute the command
        result = executor.execute(command, description)
        
        logger.info(f"Command executed: success={result.success}, duration={result.duration_ms}ms")
        
        return jsonify({
            "command": result.command,
            "description": result.description,
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "duration_ms": result.duration_ms,
            "error_type": result.error_type,
            "data": result.data,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
