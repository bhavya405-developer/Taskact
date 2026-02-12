"""
Timesheet management routes for TaskAct
Handles individual and team timesheets with export functionality
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone, timedelta
import jwt
import io
import pandas as pd

router = APIRouter(tags=["Timesheets"])

security = HTTPBearer()


def parse_datetime(date_value):
    """
    Safely parse a date value to datetime object.
    Handles both datetime objects (from MongoDB Atlas) and ISO strings (from local MongoDB).
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


def format_date_for_display(date_value, format_str="%Y-%m-%d"):
    """
    Safely format a date value for display.
    Handles both datetime objects and ISO strings.
    Returns empty string if value is None or invalid.
    """
    if date_value is None:
        return ''
    try:
        if isinstance(date_value, datetime):
            return date_value.strftime(format_str)
        elif isinstance(date_value, str):
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime(format_str)
        else:
            return str(date_value)[:10] if date_value else ''
    except Exception:
        return ''


# These will be set by server.py when including the router
db = None
SECRET_KEY = None
ALGORITHM = None
UserRole = None
UserResponse = None
TaskStatus = None
parse_from_mongo = None
logger = None


def init_timesheets_routes(
    _db, _secret_key, _algorithm,
    _user_role, _user_response, _task_status,
    _parse_mongo, _logger
):
    """Initialize timesheets routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM
    global UserRole, UserResponse, TaskStatus
    global parse_from_mongo, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    UserRole = _user_role
    UserResponse = _user_response
    TaskStatus = _task_status
    parse_from_mongo = _parse_mongo
    logger = _logger


# ==================== HELPER FUNCTIONS ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id, "active": True})
    if user is None:
        raise credentials_exception
    return UserResponse(**parse_from_mongo(user))


async def get_current_partner(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user


# ==================== ROUTES ====================

@router.get("/timesheet")
async def get_timesheet(
    period: str = "weekly",  # daily, weekly, monthly
    user_id: Optional[str] = None,
    date: Optional[str] = None,  # YYYY-MM-DD for reference date
    current_user=Depends(get_current_user)
):
    """
    Get timesheet data for a user
    - period: daily, weekly, monthly
    - user_id: Optional, partners can view any user's timesheet
    - date: Reference date (defaults to today)
    """
    # Determine which user's timesheet to fetch
    target_user_id = user_id if user_id and current_user.role == UserRole.PARTNER else current_user.id
    
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range based on period
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d %b %Y")
    elif period == "weekly":
        # Start from Monday
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d %b')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"
    elif period == "monthly":
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B %Y")
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use daily, weekly, or monthly")
    
    # Get completed tasks in the date range for the user
    completed_tasks = await db.tasks.find({
        "assignee_id": target_user_id,
        "status": TaskStatus.COMPLETED,
        "completed_at": {
            "$gte": start_date.isoformat(),
            "$lt": end_date.isoformat()
        }
    }).sort("completed_at", 1).to_list(length=500)
    
    # Get user info
    user = await db.users.find_one({"id": target_user_id})
    user_name = user["name"] if user else "Unknown"
    
    # Build timesheet entries
    entries = []
    total_hours = 0
    
    for task in completed_tasks:
        actual_hours = task.get("actual_hours", 0) or 0
        total_hours += actual_hours
        
        completed_at = task.get("completed_at")
        completed_dt = parse_datetime(completed_at)
        if completed_dt:
            completed_ist = completed_dt + timedelta(hours=5, minutes=30)
            completed_date = completed_ist.strftime("%Y-%m-%d")
            completed_time = completed_ist.strftime("%I:%M %p")
        else:
            completed_date = "N/A"
            completed_time = "N/A"
        
        entries.append({
            "task_id": task["id"],
            "title": task["title"],
            "client_name": task.get("client_name", ""),
            "category": task.get("category", ""),
            "completed_date": completed_date,
            "completed_time": completed_time,
            "estimated_hours": task.get("estimated_hours"),
            "actual_hours": actual_hours,
            "description": task.get("description", "")
        })
    
    # Group by date for summary
    daily_summary = {}
    for entry in entries:
        date_key = entry["completed_date"]
        if date_key not in daily_summary:
            daily_summary[date_key] = {"tasks": 0, "hours": 0}
        daily_summary[date_key]["tasks"] += 1
        daily_summary[date_key]["hours"] += entry["actual_hours"]
    
    return {
        "user_id": target_user_id,
        "user_name": user_name,
        "period": period,
        "period_label": period_label,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_tasks": len(entries),
        "total_hours": round(total_hours, 2),
        "daily_summary": daily_summary,
        "entries": entries
    }


@router.get("/timesheet/team")
async def get_team_timesheet(
    period: str = "weekly",
    date: Optional[str] = None,
    current_user=Depends(get_current_partner)
):
    """Get timesheet summary for all team members (Partners only)"""
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d %b %Y")
    elif period == "weekly":
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d %b')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"
    elif period == "monthly":
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B %Y")
    else:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Get all active users
    users = await db.users.find({"active": True}).to_list(length=100)
    
    team_summary = []
    grand_total_hours = 0
    grand_total_tasks = 0
    
    for user in users:
        # Get completed tasks for this user
        completed_tasks = await db.tasks.find({
            "assignee_id": user["id"],
            "status": TaskStatus.COMPLETED,
            "completed_at": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        }).to_list(length=500)
        
        total_hours = sum(t.get("actual_hours", 0) or 0 for t in completed_tasks)
        task_count = len(completed_tasks)
        
        grand_total_hours += total_hours
        grand_total_tasks += task_count
        
        team_summary.append({
            "user_id": user["id"],
            "user_name": user["name"],
            "department": user.get("department", ""),
            "role": user["role"],
            "tasks_completed": task_count,
            "total_hours": round(total_hours, 2),
            "avg_hours_per_task": round(total_hours / task_count, 2) if task_count > 0 else 0
        })
    
    # Sort by total hours descending
    team_summary.sort(key=lambda x: x["total_hours"], reverse=True)
    
    return {
        "period": period,
        "period_label": period_label,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        "grand_total_tasks": grand_total_tasks,
        "grand_total_hours": round(grand_total_hours, 2),
        "team_summary": team_summary
    }


@router.get("/timesheet/export")
async def export_timesheet(
    period: str = "weekly",
    user_id: Optional[str] = None,
    date: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Export timesheet as Excel file"""
    # Get timesheet data
    target_user_id = user_id if user_id and current_user.role == UserRole.PARTNER else current_user.id
    
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d_%b_%Y")
    elif period == "weekly":
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d%b')}_to_{(end_date - timedelta(days=1)).strftime('%d%b_%Y')}"
    else:  # monthly
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B_%Y")
    
    # Get user info
    user = await db.users.find_one({"id": target_user_id})
    user_name = user["name"] if user else "Unknown"
    
    # Get completed tasks
    completed_tasks = await db.tasks.find({
        "assignee_id": target_user_id,
        "status": TaskStatus.COMPLETED,
        "completed_at": {
            "$gte": start_date.isoformat(),
            "$lt": end_date.isoformat()
        }
    }).sort("completed_at", 1).to_list(length=500)
    
    # Build data for Excel
    timesheet_data = []
    total_hours = 0
    
    for task in completed_tasks:
        actual_hours = task.get("actual_hours", 0) or 0
        total_hours += actual_hours
        
        completed_at = task.get("completed_at")
        if completed_at:
            completed_dt = datetime.fromisoformat(completed_at)
            completed_ist = completed_dt + timedelta(hours=5, minutes=30)
            completed_date = completed_ist.strftime("%d-%b-%Y")
            day_name = completed_ist.strftime("%A")
        else:
            completed_date = "N/A"
            day_name = ""
        
        timesheet_data.append({
            "Date": completed_date,
            "Day": day_name,
            "Task": task["title"],
            "Client": task.get("client_name", ""),
            "Category": task.get("category", ""),
            "Description": task.get("description", "")[:100] if task.get("description") else "",
            "Est. Hours": task.get("estimated_hours", ""),
            "Actual Hours": actual_hours
        })
    
    # Create summary data
    summary_data = [
        {"Field": "Employee", "Value": user_name},
        {"Field": "Period", "Value": period.capitalize()},
        {"Field": "Date Range", "Value": f"{start_date.strftime('%d %b %Y')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"},
        {"Field": "Total Tasks", "Value": len(completed_tasks)},
        {"Field": "Total Hours", "Value": round(total_hours, 2)},
        {"Field": "Avg Hours/Task", "Value": round(total_hours / len(completed_tasks), 2) if completed_tasks else 0}
    ]
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Timesheet details
        if timesheet_data:
            df_timesheet = pd.DataFrame(timesheet_data)
            df_timesheet.to_excel(writer, sheet_name='Timesheet', index=False)
            
            # Adjust column widths
            worksheet = writer.sheets['Timesheet']
            column_widths = {'A': 12, 'B': 12, 'C': 30, 'D': 20, 'E': 15, 'F': 40, 'G': 12, 'H': 12}
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
    
    output.seek(0)
    
    safe_name = user_name.replace(" ", "_")
    filename = f"Timesheet_{safe_name}_{period_label}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/timesheet/team/export")
async def export_team_timesheet(
    period: str = "weekly",
    date: Optional[str] = None,
    current_user=Depends(get_current_partner)
):
    """Export team timesheet as Excel file (Partners only)"""
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d_%b_%Y")
    elif period == "weekly":
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d%b')}_to_{(end_date - timedelta(days=1)).strftime('%d%b_%Y')}"
    else:
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B_%Y")
    
    # Get all users
    users = await db.users.find({"active": True}).to_list(length=100)
    
    # Build team summary
    team_data = []
    all_tasks_data = []
    grand_total_hours = 0
    
    for user in users:
        completed_tasks = await db.tasks.find({
            "assignee_id": user["id"],
            "status": TaskStatus.COMPLETED,
            "completed_at": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        }).sort("completed_at", 1).to_list(length=500)
        
        total_hours = sum(t.get("actual_hours", 0) or 0 for t in completed_tasks)
        grand_total_hours += total_hours
        
        team_data.append({
            "Employee": user["name"],
            "Department": user.get("department", ""),
            "Role": user["role"].capitalize(),
            "Tasks Completed": len(completed_tasks),
            "Total Hours": round(total_hours, 2),
            "Avg Hours/Task": round(total_hours / len(completed_tasks), 2) if completed_tasks else 0
        })
        
        # Add individual task entries
        for task in completed_tasks:
            completed_at = task.get("completed_at")
            if completed_at:
                completed_dt = datetime.fromisoformat(completed_at)
                completed_ist = completed_dt + timedelta(hours=5, minutes=30)
                completed_date = completed_ist.strftime("%d-%b-%Y")
            else:
                completed_date = "N/A"
            
            all_tasks_data.append({
                "Employee": user["name"],
                "Date": completed_date,
                "Task": task["title"],
                "Description": (task.get("description", "") or "")[:150],  # Truncate long descriptions
                "Client": task.get("client_name", ""),
                "Category": task.get("category", ""),
                "Est. Hours": task.get("estimated_hours", ""),
                "Actual Hours": task.get("actual_hours", 0)
            })
    
    # Sort team by hours
    team_data.sort(key=lambda x: x["Total Hours"], reverse=True)
    
    # Create Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary
        summary_data = [
            {"Field": "Period", "Value": period.capitalize()},
            {"Field": "Date Range", "Value": f"{start_date.strftime('%d %b %Y')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"},
            {"Field": "Total Team Hours", "Value": round(grand_total_hours, 2)},
            {"Field": "Total Tasks", "Value": len(all_tasks_data)}
        ]
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Team summary
        df_team = pd.DataFrame(team_data)
        df_team.to_excel(writer, sheet_name='Team Summary', index=False)
        
        # All tasks detail
        if all_tasks_data:
            df_tasks = pd.DataFrame(all_tasks_data)
            df_tasks.to_excel(writer, sheet_name='All Tasks', index=False)
    
    output.seek(0)
    
    filename = f"Team_Timesheet_{period_label}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
