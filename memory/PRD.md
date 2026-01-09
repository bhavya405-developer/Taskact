# TaskAct - Product Requirements Document

## Overview
TaskAct is a comprehensive task management application designed for professional firms. It enables teams to create, assign, track, and manage tasks with role-based access control.

## Core Features

### 1. Authentication & Authorization
- JWT-based authentication
- Role-based access: Partner, Associate, Junior, Intern
- **Forgot Password with OTP** (Dev Mode - OTP shown on screen for testing)
  - 3-step flow: Email → OTP Verification → New Password
  - OTP valid for 10 minutes
  - Uses Resend email service (requires API key for production)

### 2. Task Management
- Create, view, edit, delete tasks
- Task attributes: title, description, client, category, assignee, priority, due date
- 4-status system: Pending (default), On Hold, Overdue (auto), Completed
- Completed tasks are immutable
- Automatic overdue detection
- **Status History**: All status changes are recorded with IST timestamps
- **Sortable Columns**: Click column headers to sort tasks
- **Horizontal Scrolling**: Wide tables support horizontal scroll

### 3. Team Management
- Partners can add/edit team members
- **Delete/Deactivate Users**: Delete if no task history, deactivate otherwise
- View team performance stats (partners only)
- Password reset by partners

### 4. Data Management
- Master lists for Clients and Categories
- Bulk import/export via Excel templates
- **Bulk Task Import/Export** (Partners only)
  - Uses assignee names (not emails)
  - DD-MMM-YYYY date format
- **Simplified Client Import**: Name only required
- MongoDB database

### 5. Dashboard
- Task counts by status
- **Team-wide overdue and pending tasks** (partners only)
- Team performance analytics (partners only)
- Client and category analytics

### 6. Notifications
- Task assignment notifications
- Task update notifications
- Password reset notifications

### 7. GPS-Based Attendance (Enhanced - Jan 2026)
- **Clock In/Out**: Users can clock in and out with GPS location capture
- **Reverse Geocoding**: Addresses displayed using OpenStreetMap (Nominatim API)
- **Today's Status**: Shows current day's clock in/out times and work duration
- **Attendance History**: View past attendance records with location details and day type (Full/Half)
- **Multi-Location Geofence Settings** (Partners only):
  - Enable/disable geofence restriction
  - **Up to 5 office locations** supported
  - Set radius for all locations
  - Add locations using current GPS coordinates
- **Attendance Rules** (Partners only):
  - **Minimum hours for full day**: Default 8 hours (configurable)
  - **Working days**: Monday to Saturday (Sunday is weekly off by default)
  - Hours below minimum = Half Day
- **Holiday Management** (Partners only):
  - Add/delete office holidays (paid holidays)
  - Holidays excluded from working day calculations
- **Enhanced Monthly Report** (Partners only):
  - Summary: Working days, Weekly offs (Sundays), Holidays, Min hours setting
  - Per user: Full days, Half days, Effective days, Absent days, Total hours, Avg hours
  - Shows holidays for the month
- **Monthly Report** (Partners only): View team attendance statistics

## Technical Stack
- **Backend**: FastAPI (Python), Motor (async MongoDB), httpx (HTTP client)
- **Frontend**: React, Tailwind CSS, Shadcn UI, Lucide React
- **Database**: MongoDB
- **Authentication**: JWT with bcrypt password hashing
- **Email**: Resend (for OTP delivery)
- **Geolocation**: Browser Geolocation API + OpenStreetMap Nominatim (reverse geocoding)

## What's Been Implemented (Jan 2026)

### Completed Features
- [x] Full authentication system with JWT
- [x] Role-based access control (Partner, Associate, Junior, Intern)
- [x] Task CRUD with all attributes
- [x] 4-status task system with auto-overdue
- [x] Completed tasks immutability
- [x] **IST Timestamps**: Task creation and status changes recorded in IST
- [x] **Sortable Task Columns**: Click headers to sort
- [x] **Horizontal Scrolling**: Wide tables support horizontal scroll
- [x] Team management (add, edit users)
- [x] **Team Member Delete/Deactivate**
- [x] **Department Categories Updated**: Audit and Assurance, Tax and Regulatory Compliance, Accounting, Certification, Tax Litigation, Advisory, Administrative, Management, Others
- [x] Client and Category management
- [x] Bulk import/export with Excel templates (Clients, Categories)
- [x] **Bulk Task Import/Export** (Partners only) - Uses names & DD-MMM-YYYY format
- [x] **Simplified Client Import** - Name only required
- [x] Dashboard with analytics
- [x] **Partner Dashboard**: Team-wide overdue/pending tasks
- [x] Notification system
- [x] Mobile responsive design (hamburger menu, card layout)
- [x] Custom TaskAct branding (logo, favicon)
- [x] **Forgot Password with OTP** (Dev Mode)
- [x] **GPS-Based Attendance** (Enhanced)
  - Clock in/out with GPS location
  - Reverse geocoding (addresses)
  - Today's status view with Full/Half day indicator
  - Attendance history with day type
  - **Multi-location geofence** (up to 5 locations)
  - **Attendance rules** (min hours, working days)
  - **Holiday management** (add/delete paid holidays)
  - **Enhanced monthly report** (full/half days, absents, effective days)

### Pending/Future Features
- [ ] Production email delivery (requires Resend API key from user)

## Demo Accounts
All accounts use password: `password123`
- Partner: bhavika@sundesha.in
- Partner: bhavya@sundesha.in
- Associates: namita@example.com, nitish@example.com, etc.

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/request-otp` - Request password reset OTP
- `POST /api/auth/verify-otp` - Verify OTP
- `POST /api/auth/reset-password` - Reset password with OTP

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `GET /api/tasks/template` - Download bulk import template (Partner)
- `POST /api/tasks/bulk-import` - Bulk import tasks from Excel (Partner)
- `GET /api/tasks/export` - Export all tasks to Excel (Partner)
- `POST /api/tasks/bulk-delete/completed` - Delete all completed tasks (Partner, requires password)
- `POST /api/tasks/bulk-delete/all` - Delete all tasks (Partner, requires password)

### Users
- `GET /api/users` - List users (partners can add `?include_inactive=true`)
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `PUT /api/users/{id}/password` - Reset password (by Partner)
- `DELETE /api/users/{id}` - Delete user (only if no tasks)
- `PUT /api/users/{id}/deactivate` - Deactivate user
- `PUT /api/users/{id}/reactivate` - Reactivate user

### Attendance (Enhanced)
- `GET /api/attendance/settings` - Get geofence settings (multi-location)
- `PUT /api/attendance/settings` - Update geofence settings (Partner)
- `GET /api/attendance/rules` - Get attendance rules
- `PUT /api/attendance/rules` - Update attendance rules (Partner)
- `GET /api/attendance/holidays` - Get holidays for a year
- `POST /api/attendance/holidays` - Add a holiday (Partner)
- `DELETE /api/attendance/holidays/{id}` - Delete a holiday (Partner)
- `POST /api/attendance/clock-in` - Clock in with GPS location
- `POST /api/attendance/clock-out` - Clock out with GPS location
- `GET /api/attendance/today` - Get today's attendance status
- `GET /api/attendance/history` - Get attendance history
- `DELETE /api/attendance/{id}` - Delete attendance record (Partner only)
- `GET /api/attendance/report` - Get enhanced monthly attendance report (Partner)

### Dashboard
- `GET /api/dashboard` - Dashboard analytics

## Notes
- OTP is currently shown on screen (Dev Mode) for testing
- For production email, configure RESEND_API_KEY in backend/.env
- JWT secret is stored in SECRET_KEY environment variable
- Geolocation requires HTTPS in production (works on localhost for testing)
