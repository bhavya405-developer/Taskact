"""
Task management routes for TaskAct
Handles task CRUD, bulk import/export, and task templates
"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import io
import pandas as pd
from passlib.context import CryptContext

router = APIRouter(tags=["Tasks"])

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def format_date_for_display(date_value, format_str="%Y-%m-%d"):
    """
    Safely format a date value for display.
    Handles both datetime objects (from MongoDB Atlas) and ISO strings (from local MongoDB).
    Returns empty string if value is None or invalid.
    """
    if date_value is None:
        return ''
    try:
        if isinstance(date_value, datetime):
            return date_value.strftime(format_str)
        elif isinstance(date_value, str):
            # Parse string and format
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime(format_str)
        else:
            return str(date_value)[:10] if date_value else ''
    except Exception:
        return ''


def parse_datetime(date_value):
    """
    Safely parse a date value to datetime object.
    Handles both datetime objects and ISO strings.
    Returns None if value is None or invalid.
    """
    if date_value is None:
        return None
    try:
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        else:
            return None
    except Exception:
        return None


# These will be set by server.py when including the router
db = None
SECRET_KEY = None
ALGORITHM = None
UserRole = None
UserResponse = None
Task = None
TaskCreate = None
TaskUpdate = None
TaskStatus = None
BulkImportResult = None
PasswordVerifyRequest = None
parse_from_mongo = None
prepare_for_mongo = None
create_notification = None
update_overdue_tasks = None
get_ist_now = None
format_ist_datetime = None
logger = None


def init_tasks_routes(
    _db, _secret_key, _algorithm,
    _user_role, _user_response, 
    _task, _task_create, _task_update, _task_status,
    _bulk_import_result, _password_verify_request,
    _parse_mongo, _prepare_mongo, _create_notification,
    _update_overdue_tasks, _get_ist_now, _format_ist_datetime,
    _logger
):
    """Initialize tasks routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM
    global UserRole, UserResponse, Task, TaskCreate, TaskUpdate, TaskStatus
    global BulkImportResult, PasswordVerifyRequest
    global parse_from_mongo, prepare_for_mongo, create_notification
    global update_overdue_tasks, get_ist_now, format_ist_datetime, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    UserRole = _user_role
    UserResponse = _user_response
    Task = _task
    TaskCreate = _task_create
    TaskUpdate = _task_update
    TaskStatus = _task_status
    BulkImportResult = _bulk_import_result
    PasswordVerifyRequest = _password_verify_request
    parse_from_mongo = _parse_mongo
    prepare_for_mongo = _prepare_mongo
    create_notification = _create_notification
    update_overdue_tasks = _update_overdue_tasks
    get_ist_now = _get_ist_now
    format_ist_datetime = _format_ist_datetime
    logger = _logger


# ==================== HELPER FUNCTIONS ====================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id, "active": True})
    if user is None:
        raise credentials_exception
    
    user_response = UserResponse(**parse_from_mongo(user))
    user_response.tenant_id = user.get("tenant_id") or tenant_id
    return user_response


async def get_current_partner(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user


async def get_tenant_id(current_user):
    """Helper to get tenant_id from current user"""
    user_doc = await db.users.find_one({"id": current_user.id})
    return user_doc.get("tenant_id") if user_doc else None


# ==================== ROUTES ====================

# Task Template and Bulk Import/Export endpoints (Partners only) - Must come before parameterized routes
@router.get("/tasks/download-template")
async def download_tasks_template(current_user=Depends(get_current_partner)):
    """Download Excel template for bulk task import"""
    tenant_id = await get_tenant_id(current_user)
    
    # Get active users, clients, and categories for reference (within tenant)
    query = {"active": True}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    users = await db.users.find(query).to_list(length=5000)
    clients = await db.clients.find(query).to_list(length=5000)
    categories = await db.categories.find(query).to_list(length=5000)
    
    # Create sample data with headers
    template_data = {
        'Title': ['Review Contract for ABC Corp', 'Prepare Tax Filing', 'Client Meeting Follow-up'],
        'Description': [
            'Review and analyze the contract terms',
            'Prepare quarterly tax filing documents',
            'Follow up on action items from client meeting'
        ],
        'Client Name': [clients[0]['name'] if clients else 'Sample Client', 
                       clients[1]['name'] if len(clients) > 1 else 'Sample Client',
                       clients[0]['name'] if clients else 'Sample Client'],
        'Category': [categories[0]['name'] if categories else 'General',
                    categories[1]['name'] if len(categories) > 1 else 'General',
                    categories[0]['name'] if categories else 'General'],
        'Assignee Name': [users[1]['name'] if len(users) > 1 else users[0]['name'],
                          users[2]['name'] if len(users) > 2 else users[0]['name'],
                          users[1]['name'] if len(users) > 1 else users[0]['name']],
        'Priority': ['high', 'medium', 'low'],
        'Due Date': [
            (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%d-%b-%Y'),
            (datetime.now(timezone.utc) + timedelta(days=14)).strftime('%d-%b-%Y'),
            (datetime.now(timezone.utc) + timedelta(days=3)).strftime('%d-%b-%Y')
        ]
    }
    
    df = pd.DataFrame(template_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write data
        df.to_excel(writer, sheet_name='Tasks', index=False)
        
        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Tasks']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3B82F6',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 35)  # Title
        worksheet.set_column('B:B', 45)  # Description
        worksheet.set_column('C:C', 25)  # Client Name
        worksheet.set_column('D:D', 20)  # Category
        worksheet.set_column('E:E', 25)  # Assignee Name
        worksheet.set_column('F:F', 12)  # Priority
        worksheet.set_column('G:G', 15)  # Due Date
        
        # Add reference sheets
        # Users reference
        users_data = {'Name': [u['name'] for u in users], 'Role': [u['role'] for u in users]}
        users_df = pd.DataFrame(users_data)
        users_df.to_excel(writer, sheet_name='Team Members (Reference)', index=False)
        
        # Clients reference
        if clients:
            clients_data = {'Client Name': [c['name'] for c in clients]}
            clients_df = pd.DataFrame(clients_data)
            clients_df.to_excel(writer, sheet_name='Clients (Reference)', index=False)
        
        # Categories reference
        if categories:
            categories_data = {'Category Name': [c['name'] for c in categories]}
            categories_df = pd.DataFrame(categories_data)
            categories_df.to_excel(writer, sheet_name='Categories (Reference)', index=False)
        
        # Add instructions sheet
        instructions_data = {
            'Instructions': [
                '1. Fill in the task information in the "Tasks" sheet',
                '2. Title: Required - Task title/name',
                '3. Description: Optional - Detailed task description',
                '4. Client Name: Required - Must match existing client name exactly',
                '5. Category: Required - Must match existing category name exactly',
                '6. Assignee Name: Required - Name of team member to assign task',
                '7. Priority: Required - Must be: low, medium, high, or urgent',
                '8. Due Date: Optional - Format: DD-MMM-YYYY (e.g., 15-Jan-2025)',
                '',
                'Reference sheets are provided for:',
                '- Team Members: List of all active users with their names',
                '- Clients: List of all active clients',
                '- Categories: List of all active categories',
                '',
                'Notes:',
                '- All tasks will be created with "pending" status',
                '- Creator will be set to the partner uploading the file',
                '- Save the file and upload it back to import tasks'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=tasks_template.xlsx"}
    )


@router.post("/tasks/bulk-import")
async def bulk_import_tasks(
    file: UploadFile = File(...),
    current_user=Depends(get_current_partner)
):
    """Bulk import tasks from Excel/CSV file"""
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name='Tasks')
        
        # Validate required columns
        required_columns = ['Title', 'Client Name', 'Category', 'Assignee Name', 'Priority']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Get all users for name lookup
        users = await db.users.find({"active": True}).to_list(length=5000)
        name_to_user = {u['name'].lower(): u for u in users}
        
        # Get all clients and categories for validation
        clients = await db.clients.find({"active": True}).to_list(length=5000)
        client_names = {c['name'].lower(): c['name'] for c in clients}
        
        categories = await db.categories.find({"active": True}).to_list(length=5000)
        category_names = {c['name'].lower(): c['name'] for c in categories}
        
        success_count = 0
        error_count = 0
        errors = []
        created_items = []
        
        # Valid priorities
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row['Title']) or str(row['Title']).strip() == '':
                    continue
                
                title = str(row['Title']).strip()
                
                # Validate and get assignee by name
                assignee_name = str(row['Assignee Name']).strip().lower()
                if assignee_name not in name_to_user:
                    errors.append(f"Row {index + 2}: Assignee name '{row['Assignee Name']}' not found")
                    error_count += 1
                    continue
                assignee = name_to_user[assignee_name]
                
                # Validate client
                client_name = str(row['Client Name']).strip()
                if client_name.lower() not in client_names:
                    errors.append(f"Row {index + 2}: Client '{client_name}' not found")
                    error_count += 1
                    continue
                actual_client_name = client_names[client_name.lower()]
                
                # Validate category
                category = str(row['Category']).strip()
                if category.lower() not in category_names:
                    errors.append(f"Row {index + 2}: Category '{category}' not found")
                    error_count += 1
                    continue
                actual_category = category_names[category.lower()]
                
                # Validate priority
                priority = str(row['Priority']).strip().lower()
                if priority not in valid_priorities:
                    errors.append(f"Row {index + 2}: Invalid priority '{row['Priority']}'. Must be: low, medium, high, or urgent")
                    error_count += 1
                    continue
                
                # Parse due date if provided (DD-MMM-YYYY format like 15-Jan-2025)
                due_date = None
                if 'Due Date' in row and pd.notna(row['Due Date']):
                    try:
                        date_str = str(row['Due Date']).strip()
                        # Try DD-MMM-YYYY format first (e.g., 15-Jan-2025)
                        try:
                            due_date = datetime.strptime(date_str, '%d-%b-%Y')
                        except ValueError:
                            # Fallback: try pandas date parsing for Excel date values
                            due_date = pd.to_datetime(row['Due Date'])
                        due_date = due_date.replace(tzinfo=timezone.utc)
                    except Exception:
                        errors.append(f"Row {index + 2}: Invalid date format '{row['Due Date']}'. Use DD-MMM-YYYY (e.g., 15-Jan-2025)")
                        error_count += 1
                        continue
                
                # Create task
                task_dict = {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "description": str(row.get('Description', '')).strip() if pd.notna(row.get('Description')) else None,
                    "client_name": actual_client_name,
                    "category": actual_category,
                    "assignee_id": assignee['id'],
                    "assignee_name": assignee['name'],
                    "creator_id": current_user.id,
                    "creator_name": current_user.name,
                    "status": TaskStatus.PENDING,
                    "priority": priority,
                    "due_date": due_date.isoformat() if due_date else None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "completed_at": None
                }
                
                task_dict = prepare_for_mongo(task_dict)
                await db.tasks.insert_one(task_dict)
                
                # Create notification for assignee
                if assignee['id'] != current_user.id:
                    await create_notification(
                        user_id=assignee['id'],
                        title="New Task Assigned",
                        message=f"You have been assigned a new task: {title}",
                        task_id=task_dict['id']
                    )
                
                success_count += 1
                created_items.append(title)
                
            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
        
        return BulkImportResult(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            created_items=created_items
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@router.get("/tasks/export")
async def export_tasks(current_user=Depends(get_current_partner)):
    """Export all tasks to Excel file"""
    
    # Update overdue tasks before export
    await update_overdue_tasks()
    
    # Get all tasks
    tasks = await db.tasks.find({}).sort("created_at", -1).to_list(length=5000)
    
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found to export")
    
    # Prepare data for export
    export_data = []
    for task in tasks:
        export_data.append({
            'Task ID': task['id'],
            'Title': task['title'],
            'Description': task.get('description') or '',
            'Client Name': task.get('client_name') or '',
            'Category': task.get('category') or '',
            'Assignee': task.get('assignee_name') or '',
            'Creator': task.get('creator_name') or '',
            'Status': task.get('status') or '',
            'Priority': task.get('priority') or '',
            'Due Date': format_date_for_display(task.get('due_date')),
            'Created At': format_date_for_display(task.get('created_at')),
            'Updated At': format_date_for_display(task.get('updated_at')),
            'Completed At': format_date_for_display(task.get('completed_at'))
        })
    
    df = pd.DataFrame(export_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='All Tasks', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['All Tasks']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3B82F6',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 36)  # Task ID
        worksheet.set_column('B:B', 35)  # Title
        worksheet.set_column('C:C', 45)  # Description
        worksheet.set_column('D:D', 25)  # Client Name
        worksheet.set_column('E:E', 20)  # Category
        worksheet.set_column('F:F', 20)  # Assignee
        worksheet.set_column('G:G', 20)  # Creator
        worksheet.set_column('H:H', 12)  # Status
        worksheet.set_column('I:I', 10)  # Priority
        worksheet.set_column('J:M', 12)  # Dates
        
        # Add summary sheet
        status_counts = df['Status'].value_counts().to_dict()
        priority_counts = df['Priority'].value_counts().to_dict()
        
        summary_data = {
            'Metric': ['Total Tasks', 'Pending', 'On Hold', 'Overdue', 'Completed', '', 
                      'Low Priority', 'Medium Priority', 'High Priority', 'Urgent'],
            'Count': [
                len(tasks),
                status_counts.get('pending', 0),
                status_counts.get('on_hold', 0),
                status_counts.get('overdue', 0),
                status_counts.get('completed', 0),
                '',
                priority_counts.get('low', 0),
                priority_counts.get('medium', 0),
                priority_counts.get('high', 0),
                priority_counts.get('urgent', 0)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    output.seek(0)
    
    # Generate filename with current date
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f"tasks_export_{current_date}.xlsx"
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/tasks")
async def create_task(task_data: dict, current_user=Depends(get_current_user)):
    """Create a new task"""
    # Get assignee and creator names
    assignee = await db.users.find_one({"id": task_data.get("assignee_id")})
    creator = await db.users.find_one({"id": current_user.id})  # Use current user as creator
    
    if not assignee or not creator:
        raise HTTPException(status_code=404, detail="Assignee or creator not found")
    
    # Get current IST time
    now_utc = datetime.now(timezone.utc)
    
    task_dict = task_data.copy()
    task_dict["creator_id"] = current_user.id  # Set current user as creator
    task_dict["assignee_name"] = assignee["name"]
    task_dict["creator_name"] = creator["name"]
    task_dict["created_at"] = now_utc
    task_dict["updated_at"] = now_utc
    task_dict["id"] = str(uuid.uuid4())
    task_dict["status"] = task_dict.get("status", TaskStatus.PENDING)
    
    # Initialize status history with creation entry
    task_dict["status_history"] = [{
        "status": TaskStatus.PENDING,
        "changed_at": now_utc.isoformat(),
        "changed_at_ist": format_ist_datetime(now_utc),
        "changed_by": current_user.name,
        "action": "created"
    }]
    
    task_dict = prepare_for_mongo(task_dict)
    await db.tasks.insert_one(task_dict)
    
    # Create notification for assignee if not assigning to self
    if task_data.get("assignee_id") != current_user.id:
        await create_notification(
            user_id=task_data.get("assignee_id"),
            title="New Task Assigned",
            message=f"You have been assigned a new task: {task_dict['title']}",
            task_id=task_dict['id']
        )
    
    return Task(**parse_from_mongo(task_dict))


@router.get("/tasks")
async def get_tasks(
    current_user=Depends(get_current_user),
    status: Optional[str] = None, 
    assignee_id: Optional[str] = None,
    client_name: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all tasks with optional filters (tenant-filtered)"""
    # Update overdue tasks before fetching
    await update_overdue_tasks()
    
    # Get tenant_id for filtering
    tenant_id = await get_tenant_id(current_user)
    
    query = {}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    # Non-partners can only see their own tasks unless they're partners
    if current_user.role != UserRole.PARTNER:
        query["assignee_id"] = current_user.id
    
    if status:
        query["status"] = status
    if assignee_id:
        query["assignee_id"] = assignee_id
    if client_name:
        query["client_name"] = {"$regex": client_name, "$options": "i"}  # Case-insensitive search
    if category:
        query["category"] = category
    
    tasks = await db.tasks.find(query).sort("created_at", -1).to_list(length=5000)
    return [Task(**parse_from_mongo(task)) for task in tasks]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, current_user=Depends(get_current_user)):
    """Get a specific task by ID"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": task_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    task = await db.tasks.find_one(query)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user can view this task (partners can view all, others only their own)
    if current_user.role != UserRole.PARTNER and task["assignee_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own tasks")
    
    return Task(**parse_from_mongo(task))


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, task_update: dict, current_user=Depends(get_current_user)):
    """Update a task"""
    tenant_id = await get_tenant_id(current_user)
    
    # Get the existing task (within tenant)
    query = {"id": task_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    existing_task = await db.tasks.find_one(query)
    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Prevent editing completed tasks (immutable once completed) - except for partners
    if existing_task.get("status") == TaskStatus.COMPLETED and current_user.role != UserRole.PARTNER:
        raise HTTPException(status_code=403, detail="Cannot edit completed tasks. Completed tasks are immutable.")
    
    # Check permissions: partners can edit any task, others can only update status of their own tasks
    if current_user.role != UserRole.PARTNER:
        if existing_task["assignee_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update your own tasks")
        # Non-partners can only update status and actual_hours (for completing tasks)
        allowed_fields = {"status", "actual_hours"}
        update_fields = set(k for k, v in task_update.items() if v is not None)
        if not update_fields.issubset(allowed_fields):
            raise HTTPException(status_code=403, detail="You can only update task status")
    
    
    update_data = {k: v for k, v in task_update.items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Store original assignee for notification comparison
    original_assignee_id = existing_task["assignee_id"]
    now_utc = datetime.now(timezone.utc)
    
    # Update assignee name if assignee_id is changed
    if "assignee_id" in update_data:
        assignee = await db.users.find_one({"id": update_data["assignee_id"]})
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        update_data["assignee_name"] = assignee["name"]
    
    # Record status change in history
    if "status" in update_data:
        old_status = existing_task.get("status")
        new_status = update_data["status"]
        
        # Require actual_hours when completing a task (mandatory for timesheet)
        if new_status == TaskStatus.COMPLETED:
            actual_hours = update_data.get("actual_hours") or existing_task.get("actual_hours")
            if not actual_hours:
                raise HTTPException(
                    status_code=400, 
                    detail="Time spent (actual_hours) is required when completing a task for timesheet tracking"
                )
        
        # Get existing status history or create new
        status_history = existing_task.get("status_history", [])
        
        # Add new status change entry
        status_entry = {
            "status": new_status,
            "previous_status": old_status,
            "changed_at": now_utc.isoformat(),
            "changed_at_ist": format_ist_datetime(now_utc),
            "changed_by": current_user.name,
            "action": "status_changed"
        }
        status_history.append(status_entry)
        update_data["status_history"] = status_history
        
        # Set completed_at when status changes to completed
        if new_status == TaskStatus.COMPLETED:
            update_data["completed_at"] = now_utc.isoformat()
    
    update_data["updated_at"] = now_utc.isoformat()
    
    result = await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    updated_task = await db.tasks.find_one({"id": task_id})
    
    # Create notifications
    if current_user.role == UserRole.PARTNER:
        # If assignee changed, notify both old and new assignee
        if "assignee_id" in update_data and update_data["assignee_id"] != original_assignee_id:
            # Notify new assignee
            if update_data["assignee_id"] != current_user.id:
                await create_notification(
                    user_id=update_data["assignee_id"],
                    title="Task Reassigned to You",
                    message=f"You have been assigned to task: {updated_task['title']}",
                    task_id=task_id
                )
            
            # Notify old assignee (if different from partner and new assignee)
            if original_assignee_id != current_user.id and original_assignee_id != update_data["assignee_id"]:
                await create_notification(
                    user_id=original_assignee_id,
                    title="Task Reassigned",
                    message=f"Task '{updated_task['title']}' has been reassigned",
                    task_id=task_id
                )
        else:
            # Task was edited but assignee didn't change, notify current assignee
            if updated_task["assignee_id"] != current_user.id:
                await create_notification(
                    user_id=updated_task["assignee_id"],
                    title="Task Updated",
                    message=f"Task '{updated_task['title']}' has been updated by {current_user.name}",
                    task_id=task_id
                )
    
    return Task(**parse_from_mongo(updated_task))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user=Depends(get_current_partner)):
    """Delete a task (Partners only)"""
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


@router.post("/tasks/bulk-delete/completed")
async def delete_all_completed_tasks(
    password_verify: dict,
    current_user=Depends(get_current_partner)
):
    """Delete all completed tasks (Partners only, requires password verification)"""
    # Verify password
    user = await db.users.find_one({"id": current_user.id})
    if not user or not verify_password(password_verify.get("password"), user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Count completed tasks before deletion
    count = await db.tasks.count_documents({"status": TaskStatus.COMPLETED})
    
    if count == 0:
        return {"message": "No completed tasks to delete", "deleted_count": 0}
    
    # Delete all completed tasks
    result = await db.tasks.delete_many({"status": TaskStatus.COMPLETED})
    
    return {
        "message": f"Successfully deleted {result.deleted_count} completed task(s)",
        "deleted_count": result.deleted_count
    }


@router.post("/tasks/bulk-delete/all")
async def delete_all_tasks(
    password_verify: dict,
    current_user=Depends(get_current_partner)
):
    """Delete all tasks regardless of status (Partners only, requires password verification)"""
    # Verify password
    user = await db.users.find_one({"id": current_user.id})
    if not user or not verify_password(password_verify.get("password"), user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Count all tasks before deletion
    count = await db.tasks.count_documents({})
    
    if count == 0:
        return {"message": "No tasks to delete", "deleted_count": 0}
    
    # Delete all tasks
    result = await db.tasks.delete_many({})
    
    return {
        "message": f"Successfully deleted {result.deleted_count} task(s)",
        "deleted_count": result.deleted_count
    }
