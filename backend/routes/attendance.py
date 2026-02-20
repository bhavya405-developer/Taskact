"""
Attendance management routes for TaskAct
Handles clock in/out, geofencing, holidays, and attendance reports
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import io
import pandas as pd

router = APIRouter(tags=["Attendance"])

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
AttendanceType = None
AttendanceCreate = None
GeofenceSettingsUpdate = None
AttendanceRulesUpdate = None
HolidayCreate = None
parse_from_mongo = None
prepare_for_mongo = None
create_notification = None
get_geofence_settings = None
check_within_any_geofence = None
reverse_geocode = None
format_ist_datetime = None
logger = None


def init_attendance_routes(
    _db, _secret_key, _algorithm,
    _user_role, _user_response,
    _attendance_type, _attendance_create, 
    _geofence_settings_update, _attendance_rules_update, _holiday_create,
    _parse_mongo, _prepare_mongo, _create_notification,
    _get_geofence_settings, _check_within_any_geofence, _reverse_geocode,
    _format_ist_datetime, _logger
):
    """Initialize attendance routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM
    global UserRole, UserResponse, AttendanceType, AttendanceCreate
    global GeofenceSettingsUpdate, AttendanceRulesUpdate, HolidayCreate
    global parse_from_mongo, prepare_for_mongo, create_notification
    global get_geofence_settings, check_within_any_geofence, reverse_geocode
    global format_ist_datetime, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    UserRole = _user_role
    UserResponse = _user_response
    AttendanceType = _attendance_type
    AttendanceCreate = _attendance_create
    GeofenceSettingsUpdate = _geofence_settings_update
    AttendanceRulesUpdate = _attendance_rules_update
    HolidayCreate = _holiday_create
    parse_from_mongo = _parse_mongo
    prepare_for_mongo = _prepare_mongo
    create_notification = _create_notification
    get_geofence_settings = _get_geofence_settings
    check_within_any_geofence = _check_within_any_geofence
    reverse_geocode = _reverse_geocode
    format_ist_datetime = _format_ist_datetime
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


# ==================== GEOFENCE SETTINGS ROUTES ====================

@router.get("/attendance/settings")
async def get_attendance_settings(current_user=Depends(get_current_user)):
    """Get geofence settings"""
    settings = await get_geofence_settings()
    return settings


@router.put("/attendance/settings")
async def update_attendance_settings(
    settings_update: dict,
    current_user=Depends(get_current_partner)
):
    """Update geofence settings (Partners only)"""
    update_data = {k: v for k, v in settings_update.items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_by"] = current_user.name
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # If locations are updated, reverse geocode addresses for any without addresses
    if "locations" in update_data:
        locations = update_data["locations"]
        if len(locations) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 locations allowed")
        for loc in locations:
            if loc.get("latitude") and loc.get("longitude") and not loc.get("address"):
                address = await reverse_geocode(loc["latitude"], loc["longitude"])
                if address:
                    loc["address"] = address
    
    await db.geofence_settings.update_one(
        {"id": "geofence_settings"},
        {"$set": update_data},
        upsert=True
    )
    
    settings = await get_geofence_settings()
    return settings


# ==================== ATTENDANCE RULES ROUTES ====================

@router.get("/attendance/rules")
async def get_attendance_rules(current_user=Depends(get_current_user)):
    """Get attendance rules"""
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    if not rules:
        # Return defaults
        return {
            "id": "attendance_rules",
            "min_hours_full_day": 8.0,
            "working_days": [0, 1, 2, 3, 4, 5],  # Mon-Sat
            "working_days_names": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        }
    rules = parse_from_mongo(rules)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    rules["working_days_names"] = [day_names[d] for d in rules.get("working_days", [])]
    return rules


@router.put("/attendance/rules")
async def update_attendance_rules(
    rules_update: dict,
    current_user=Depends(get_current_partner)
):
    """Update attendance rules (Partners only)"""
    update_data = {k: v for k, v in rules_update.items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_by"] = current_user.name
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.attendance_rules.update_one(
        {"id": "attendance_rules"},
        {"$set": update_data},
        upsert=True
    )
    
    return await get_attendance_rules(current_user)


# ==================== HOLIDAY MANAGEMENT ROUTES ====================

@router.get("/attendance/holidays")
async def get_holidays(
    year: Optional[int] = None,
    current_user=Depends(get_current_user)
):
    """Get holidays for a year"""
    query = {}
    if year:
        query["date"] = {"$regex": f"^{year}"}
    
    holidays = await db.holidays.find(query).sort("date", 1).to_list(length=5000)
    return [parse_from_mongo(h) for h in holidays]


@router.post("/attendance/holidays")
async def add_holiday(
    holiday: dict,
    current_user=Depends(get_current_partner)
):
    """Add a holiday (Partners only)"""
    # Check if holiday already exists for this date
    existing = await db.holidays.find_one({"date": holiday.get("date")})
    if existing:
        raise HTTPException(status_code=400, detail="Holiday already exists for this date")
    
    holiday_dict = {
        "id": str(uuid.uuid4()),
        "date": holiday.get("date"),
        "name": holiday.get("name"),
        "is_paid": holiday.get("is_paid", True),
        "created_by": current_user.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.holidays.insert_one(holiday_dict)
    return parse_from_mongo(holiday_dict)


@router.delete("/attendance/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_user=Depends(get_current_partner)
):
    """Delete a holiday (Partners only)"""
    result = await db.holidays.delete_one({"id": holiday_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"message": "Holiday deleted successfully"}


# ==================== CLOCK IN/OUT ROUTES ====================

@router.post("/attendance/clock-in")
async def clock_in(
    attendance_data: dict,
    current_user=Depends(get_current_user)
):
    """Clock in with GPS location"""
    # Check if already clocked in today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing_clock_in = await db.attendance.find_one({
        "user_id": current_user.id,
        "type": AttendanceType.CLOCK_IN.value,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    if existing_clock_in:
        raise HTTPException(status_code=400, detail="Already clocked in today")
    
    now_utc = datetime.now(timezone.utc)
    
    # Get geofence settings
    settings = await get_geofence_settings()
    
    # Calculate distance from office locations if geofence is configured
    is_within_geofence = None
    distance_from_office = None
    nearest_location = None
    gps_accuracy = attendance_data.get("accuracy", 0)
    
    locations = settings.get("locations", [])
    if settings.get("enabled") and locations:
        is_within_geofence, distance_from_office, nearest_location = check_within_any_geofence(
            attendance_data.get("latitude"), attendance_data.get("longitude"),
            locations, settings.get("radius_meters", 100),
            gps_accuracy
        )
        
        if not is_within_geofence:
            # Calculate effective radius for error message
            tolerance = min(gps_accuracy, 50) if gps_accuracy else 0
            effective_radius = settings.get('radius_meters', 100) + tolerance
            accuracy_note = f" (GPS accuracy: ±{gps_accuracy:.0f}m)" if gps_accuracy else ""
            raise HTTPException(
                status_code=400, 
                detail=f"You are {distance_from_office:.0f}m away from the nearest office ({nearest_location}). Must be within {effective_radius:.0f}m to clock in.{accuracy_note}"
            )
    
    # Reverse geocode the address
    address = await reverse_geocode(attendance_data.get("latitude"), attendance_data.get("longitude"))
    
    attendance_dict = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "user_name": current_user.name,
        "type": AttendanceType.CLOCK_IN.value,
        "timestamp": now_utc.isoformat(),
        "timestamp_ist": format_ist_datetime(now_utc),
        "latitude": attendance_data.get("latitude"),
        "longitude": attendance_data.get("longitude"),
        "accuracy": gps_accuracy,
        "address": address,
        "is_within_geofence": is_within_geofence,
        "distance_from_office": distance_from_office,
        "nearest_location": nearest_location,
        "device_info": attendance_data.get("device_info")
    }
    
    attendance_dict = prepare_for_mongo(attendance_dict)
    await db.attendance.insert_one(attendance_dict)
    
    # Create notification for successful clock-in
    await create_notification(
        user_id=current_user.id,
        title="Clocked In",
        message=f"You clocked in at {format_ist_datetime(now_utc)}"
    )
    
    return {
        "message": "Clocked in successfully",
        "attendance": parse_from_mongo(attendance_dict),
        "address": address
    }


@router.post("/attendance/clock-out")
async def clock_out(
    attendance_data: dict,
    current_user=Depends(get_current_user)
):
    """Clock out with GPS location"""
    # Check if clocked in today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing_clock_in = await db.attendance.find_one({
        "user_id": current_user.id,
        "type": AttendanceType.CLOCK_IN.value,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    if not existing_clock_in:
        raise HTTPException(status_code=400, detail="You haven't clocked in today")
    
    # Check if already clocked out
    existing_clock_out = await db.attendance.find_one({
        "user_id": current_user.id,
        "type": AttendanceType.CLOCK_OUT.value,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    if existing_clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out today")
    
    now_utc = datetime.now(timezone.utc)
    
    # Get geofence settings
    settings = await get_geofence_settings()
    
    # Calculate distance from office (for record, not enforced on clock out)
    is_within_geofence = None
    distance_from_office = None
    nearest_location = None
    gps_accuracy = attendance_data.get("accuracy", 0)
    
    locations = settings.get("locations", [])
    if locations:
        is_within_geofence, distance_from_office, nearest_location = check_within_any_geofence(
            attendance_data.get("latitude"), attendance_data.get("longitude"),
            locations, settings.get("radius_meters", 100),
            gps_accuracy
        )
    
    # Reverse geocode the address
    address = await reverse_geocode(attendance_data.get("latitude"), attendance_data.get("longitude"))
    
    attendance_dict = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "user_name": current_user.name,
        "type": AttendanceType.CLOCK_OUT.value,
        "timestamp": now_utc.isoformat(),
        "timestamp_ist": format_ist_datetime(now_utc),
        "latitude": attendance_data.get("latitude"),
        "longitude": attendance_data.get("longitude"),
        "accuracy": gps_accuracy,
        "address": address,
        "is_within_geofence": is_within_geofence,
        "distance_from_office": distance_from_office,
        "nearest_location": nearest_location,
        "device_info": attendance_data.get("device_info")
    }
    
    attendance_dict = prepare_for_mongo(attendance_dict)
    await db.attendance.insert_one(attendance_dict)
    
    # Calculate work duration
    clock_in_time = parse_datetime(existing_clock_in["timestamp"])
    if clock_in_time:
        work_duration = now_utc - clock_in_time
        hours = work_duration.total_seconds() / 3600
    else:
        hours = 0
    
    # Create notification
    await create_notification(
        user_id=current_user.id,
        title="Clocked Out",
        message=f"You clocked out at {format_ist_datetime(now_utc)}. Work duration: {round(hours, 2)} hours"
    )
    
    return {
        "message": "Clocked out successfully",
        "attendance": parse_from_mongo(attendance_dict),
        "address": address,
        "work_duration_hours": round(hours, 2)
    }


@router.get("/attendance/today")
async def get_today_attendance(current_user=Depends(get_current_user)):
    """Get today's attendance status for current user"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    records = await db.attendance.find({
        "user_id": current_user.id,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    }).sort("timestamp", 1).to_list(length=5000)
    
    clock_in = None
    clock_out = None
    
    for record in records:
        parsed_record = parse_from_mongo(record)
        if parsed_record["type"] == AttendanceType.CLOCK_IN:
            clock_in = parsed_record
        elif parsed_record["type"] == AttendanceType.CLOCK_OUT:
            clock_out = parsed_record
    
    work_duration = None
    if clock_in and clock_out:
        in_time = parse_datetime(clock_in["timestamp"])
        out_time = parse_datetime(clock_out["timestamp"])
        if in_time and out_time:
            work_duration = round((out_time - in_time).total_seconds() / 3600, 2)
    
    return {
        "clock_in": clock_in,
        "clock_out": clock_out,
        "is_clocked_in": clock_in is not None and clock_out is None,
        "work_duration_hours": work_duration
    }


@router.get("/attendance/history")
async def get_attendance_history(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Get attendance history. Partners can view all users, others only their own."""
    query = {}
    
    # Filter by tenant_id
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    
    # Non-partners can only view their own attendance
    if current_user.role != UserRole.PARTNER:
        query["user_id"] = current_user.id
    elif user_id:
        query["user_id"] = user_id
    
    # Date filtering
    if start_date:
        query.setdefault("timestamp", {})["$gte"] = start_date
    if end_date:
        query.setdefault("timestamp", {})["$lte"] = end_date
    
    records = await db.attendance.find(query).sort("timestamp", -1).to_list(length=500)
    
    return [parse_from_mongo(record) for record in records]


@router.delete("/attendance/{attendance_id}")
async def delete_attendance_record(
    attendance_id: str,
    current_user=Depends(get_current_partner)
):
    """Delete an attendance record (Partners only)"""
    # Find the attendance record
    record = await db.attendance.find_one({"id": attendance_id})
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Delete the record
    result = await db.attendance.delete_one({"id": attendance_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Create notification for the user whose attendance was deleted
    await create_notification(
        user_id=record["user_id"],
        title="Attendance Record Deleted",
        message=f"Your {record['type']} record for {record.get('timestamp_ist', 'N/A')} has been deleted by {current_user.name}"
    )
    
    return {"message": "Attendance record deleted successfully"}


# ==================== ATTENDANCE REPORT ROUTES ====================

@router.get("/attendance/report")
async def get_attendance_report(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user=Depends(get_current_partner)
):
    """Get monthly attendance report for all users (Partners only)"""
    now = datetime.now(timezone.utc)
    report_month = month or now.month
    report_year = year or now.year
    
    # Calculate date range
    start_date = datetime(report_year, report_month, 1, tzinfo=timezone.utc)
    if report_month == 12:
        end_date = datetime(report_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(report_year, report_month + 1, 1, tzinfo=timezone.utc)
    
    # Get attendance rules
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    min_hours_full_day = rules.get("min_hours_full_day", 8.0) if rules else 8.0
    working_days = rules.get("working_days", [0, 1, 2, 3, 4, 5]) if rules else [0, 1, 2, 3, 4, 5]  # Mon-Sat
    
    # Get holidays for the month
    holidays = await db.holidays.find({
        "date": {"$regex": f"^{report_year}-{report_month:02d}"}
    }).to_list(length=5000)
    holiday_dates = {h["date"] for h in holidays}
    
    # Calculate working days in the month (excluding Sundays and holidays)
    total_working_days = 0
    total_sundays = 0
    total_holidays = 0
    current_date = start_date
    while current_date < end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        
        if weekday == 6:  # Sunday
            total_sundays += 1
        elif date_str in holiday_dates:
            total_holidays += 1
        elif weekday in working_days:
            total_working_days += 1
        
        current_date += timedelta(days=1)
    
    # Get all users
    users = await db.users.find({"active": True}).to_list(length=5000)
    
    report = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=5000)
        
        # Group by date
        clock_ins = [r for r in records if r["type"] == AttendanceType.CLOCK_IN.value]
        clock_outs = [r for r in records if r["type"] == AttendanceType.CLOCK_OUT.value]
        
        full_days = 0
        half_days = 0
        total_hours = 0
        daily_details = []
        
        for cin in clock_ins:
            cin_dt = parse_datetime(cin["timestamp"])
            if not cin_dt:
                continue
            cin_date = cin_dt.date()
            date_str = cin_date.strftime("%Y-%m-%d")
            
            matching_out = next(
                (co for co in clock_outs 
                 if parse_datetime(co["timestamp"]) and parse_datetime(co["timestamp"]).date() == cin_date),
                None
            )
            
            if matching_out:
                in_time = parse_datetime(cin["timestamp"])
                out_time = parse_datetime(matching_out["timestamp"])
                if in_time and out_time:
                    hours = (out_time - in_time).total_seconds() / 3600
                    total_hours += hours
                    
                    # Determine if full day or half day
                    if hours >= min_hours_full_day:
                        full_days += 1
                        day_type = "full"
                    else:
                        half_days += 1
                        day_type = "half"
                    
                    daily_details.append({
                        "date": date_str,
                        "hours": round(hours, 2),
                        "type": day_type
                    })
            else:
                # Clock in without clock out - mark as incomplete
                daily_details.append({
                    "date": date_str,
                    "hours": 0,
                    "type": "incomplete"
                })
        
        # Calculate absent days (working days - present days)
        present_dates = {d["date"] for d in daily_details}
        absent_days = 0
        current_date = start_date
        while current_date < end_date and current_date.date() <= now.date():
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()
            
            # Skip Sundays and holidays
            if weekday != 6 and date_str not in holiday_dates and weekday in working_days:
                if date_str not in present_dates:
                    absent_days += 1
            
            current_date += timedelta(days=1)
        
        # Calculate effective days (full days + half days * 0.5)
        effective_days = full_days + (half_days * 0.5)
        
        report.append({
            "user_id": user["id"],
            "user_name": user["name"],
            "role": user["role"],
            "department": user.get("department", ""),
            "full_days": full_days,
            "half_days": half_days,
            "effective_days": effective_days,
            "absent_days": absent_days,
            "total_hours": round(total_hours, 2),
            "average_hours_per_day": round(total_hours / (full_days + half_days), 2) if (full_days + half_days) > 0 else 0
        })
    
    return {
        "month": report_month,
        "year": report_year,
        "summary": {
            "total_working_days": total_working_days,
            "total_sundays": total_sundays,
            "total_holidays": total_holidays,
            "min_hours_full_day": min_hours_full_day,
            "holidays": [{"date": h["date"], "name": h["name"]} for h in holidays]
        },
        "report": sorted(report, key=lambda x: x["user_name"])
    }


@router.get("/attendance/report/export")
async def export_attendance_report(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user=Depends(get_current_partner)
):
    """Export monthly attendance report as Excel file (Partners only)"""
    now = datetime.now(timezone.utc)
    report_month = month or now.month
    report_year = year or now.year
    
    # Calculate date range
    start_date = datetime(report_year, report_month, 1, tzinfo=timezone.utc)
    if report_month == 12:
        end_date = datetime(report_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(report_year, report_month + 1, 1, tzinfo=timezone.utc)
    
    # Get attendance rules
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    min_hours_full_day = rules.get("min_hours_full_day", 8.0) if rules else 8.0
    working_days = rules.get("working_days", [0, 1, 2, 3, 4, 5]) if rules else [0, 1, 2, 3, 4, 5]
    
    # Get holidays for the month
    holidays = await db.holidays.find({
        "date": {"$regex": f"^{report_year}-{report_month:02d}"}
    }).to_list(length=5000)
    holiday_dates = {h["date"] for h in holidays}
    
    # Calculate working days summary
    total_working_days = 0
    total_sundays = 0
    total_holidays = 0
    current_date = start_date
    while current_date < end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = current_date.weekday()
        
        if weekday == 6:
            total_sundays += 1
        elif date_str in holiday_dates:
            total_holidays += 1
        elif weekday in working_days:
            total_working_days += 1
        
        current_date += timedelta(days=1)
    
    # Get all users
    users = await db.users.find({"active": True}).to_list(length=5000)
    
    report_data = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=5000)
        
        clock_ins = [r for r in records if r["type"] == AttendanceType.CLOCK_IN.value]
        clock_outs = [r for r in records if r["type"] == AttendanceType.CLOCK_OUT.value]
        
        full_days = 0
        half_days = 0
        total_hours = 0
        
        for cin in clock_ins:
            cin_dt = parse_datetime(cin["timestamp"])
            if not cin_dt:
                continue
            cin_date = cin_dt.date()
            matching_out = next(
                (co for co in clock_outs 
                 if parse_datetime(co["timestamp"]) and parse_datetime(co["timestamp"]).date() == cin_date),
                None
            )
            
            if matching_out:
                in_time = parse_datetime(cin["timestamp"])
                out_time = parse_datetime(matching_out["timestamp"])
                if in_time and out_time:
                    hours = (out_time - in_time).total_seconds() / 3600
                    total_hours += hours
                    
                    if hours >= min_hours_full_day:
                        full_days += 1
                    else:
                        half_days += 1
        
        # Calculate absent days
        present_dates = set()
        for cin in clock_ins:
            cin_dt = parse_datetime(cin["timestamp"])
            if cin_dt:
                present_dates.add(cin_dt.strftime("%Y-%m-%d"))
        
        absent_days = 0
        current_date = start_date
        while current_date < end_date and current_date.date() <= now.date():
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()
            
            if weekday != 6 and date_str not in holiday_dates and weekday in working_days:
                if date_str not in present_dates:
                    absent_days += 1
            
            current_date += timedelta(days=1)
        
        effective_days = full_days + (half_days * 0.5)
        
        report_data.append({
            "Name": user["name"],
            "Department": user.get("department", ""),
            "Role": user["role"],
            "Full Days": full_days,
            "Half Days": half_days,
            "Effective Days": effective_days,
            "Absent Days": absent_days,
            "Total Hours": round(total_hours, 2),
            "Avg Hours/Day": round(total_hours / (full_days + half_days), 2) if (full_days + half_days) > 0 else 0
        })
    
    # Create daily detail data (employee-wise in/out times)
    daily_detail_data = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=5000)
        
        # Build dictionaries safely handling datetime objects
        clock_ins = {}
        clock_outs = {}
        for r in records:
            r_dt = parse_datetime(r["timestamp"])
            if r_dt:
                date_key = r_dt.strftime("%Y-%m-%d")
                if r["type"] == AttendanceType.CLOCK_IN.value:
                    clock_ins[date_key] = r
                elif r["type"] == AttendanceType.CLOCK_OUT.value:
                    clock_outs[date_key] = r
        
        # Iterate through each day of the month
        current_date = start_date
        while current_date < end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()
            day_name = current_date.strftime("%A")
            
            cin = clock_ins.get(date_str)
            cout = clock_outs.get(date_str)
            
            in_time_str = ""
            out_time_str = ""
            hours_worked = ""
            day_type = ""
            status = ""
            clock_in_location = ""
            clock_out_location = ""
            
            # Determine status
            if weekday == 6:
                status = "Weekly Off"
            elif date_str in holiday_dates:
                holiday_name = next((h["name"] for h in holidays if h["date"] == date_str), "Holiday")
                status = f"Holiday ({holiday_name})"
            elif weekday not in working_days:
                status = "Weekly Off"
            elif cin:
                # Convert to IST for display
                in_time = parse_datetime(cin["timestamp"])
                if in_time:
                    in_time_ist = in_time + timedelta(hours=5, minutes=30)
                    in_time_str = in_time_ist.strftime("%I:%M %p")
                
                # Get clock-in location
                clock_in_location = cin.get("address", "")
                
                if cout:
                    out_time = parse_datetime(cout["timestamp"])
                    if out_time:
                        out_time_ist = out_time + timedelta(hours=5, minutes=30)
                        out_time_str = out_time_ist.strftime("%I:%M %p")
                    
                    # Get clock-out location
                    clock_out_location = cout.get("address", "")
                    
                    if in_time and out_time:
                        hours = (out_time - in_time).total_seconds() / 3600
                        hours_worked = f"{hours:.2f}"
                        day_type = "Full Day" if hours >= min_hours_full_day else "Half Day"
                    status = "Present"
                else:
                    status = "Clocked In (No Clock Out)"
            elif current_date.date() <= now.date():
                status = "Absent"
            else:
                status = "-"  # Future date
            
            daily_detail_data.append({
                "Date": date_str,
                "Day": day_name,
                "Employee": user["name"],
                "Department": user.get("department", ""),
                "Clock In": in_time_str,
                "Clock In Location": clock_in_location,
                "Clock Out": out_time_str,
                "Clock Out Location": clock_out_location,
                "Hours Worked": hours_worked,
                "Day Type": day_type,
                "Status": status
            })
            
            current_date += timedelta(days=1)
    
    # Create summary data
    month_names = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]
    
    summary_data = [
        {"Summary": "Month", "Value": f"{month_names[report_month-1]} {report_year}"},
        {"Summary": "Working Days", "Value": total_working_days},
        {"Summary": "Weekly Offs (Sundays)", "Value": total_sundays},
        {"Summary": "Holidays", "Value": total_holidays},
        {"Summary": "Min Hours for Full Day", "Value": min_hours_full_day},
    ]
    
    # Add holiday list
    for i, h in enumerate(holidays):
        summary_data.append({"Summary": f"Holiday {i+1}", "Value": f"{h['date']}: {h['name']}"})
    
    # Create Excel file with multiple sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Report sheet (employee-wise monthly summary)
        df_report = pd.DataFrame(sorted(report_data, key=lambda x: x["Name"]))
        df_report.to_excel(writer, sheet_name='Monthly Summary', index=False)
        
        # Daily detail sheet (employee-wise daily in/out times)
        df_daily = pd.DataFrame(daily_detail_data)
        # Sort by date then by employee name
        df_daily = df_daily.sort_values(by=['Date', 'Employee'])
        df_daily.to_excel(writer, sheet_name='Daily Details', index=False)
        
        # Adjust column widths for Daily Details sheet
        worksheet = writer.sheets['Daily Details']
        column_widths = {
            'A': 12,  # Date
            'B': 12,  # Day
            'C': 20,  # Employee
            'D': 15,  # Department
            'E': 12,  # Clock In
            'F': 40,  # Clock In Location
            'G': 12,  # Clock Out
            'H': 40,  # Clock Out Location
            'I': 14,  # Hours Worked
            'J': 12,  # Day Type
            'K': 25,  # Status
        }
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
    
    output.seek(0)
    
    filename = f"Attendance_Report_{month_names[report_month-1]}_{report_year}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
