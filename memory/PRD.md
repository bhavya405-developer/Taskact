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

### 7. GPS-Based Attendance (NEW - Jan 2026)
- **Clock In/Out**: Users can clock in and out with GPS location capture
- **Reverse Geocoding**: Addresses displayed using OpenStreetMap (Nominatim API)
- **Today's Status**: Shows current day's clock in/out times and work duration
- **Attendance History**: View past attendance records with location details
- **Geofence Settings** (Partners only):
  - Enable/disable geofence restriction
  - Set office coordinates and radius
  - Use Current Location button
- **Monthly Report** (Partners only): View team attendance statistics

## Technical Stack
- **Backend**: FastAPI (Python), Motor (async MongoDB)
- **Frontend**: React, Tailwind CSS, Shadcn UI, Lucide React
- **Database**: MongoDB
- **Authentication**: JWT with bcrypt password hashing
- **Email**: Resend (for OTP delivery)

## What's Been Implemented (Jan 2025)

### Completed Features
- [x] Full authentication system with JWT
- [x] Role-based access control (Partner, Associate, Junior)
- [x] Task CRUD with all attributes
- [x] 4-status task system with auto-overdue
- [x] Completed tasks immutability
- [x] Team management (add, edit users)
- [x] **Team Member Delete/Deactivate** (Jan 2025)
- [x] Client and Category management
- [x] Bulk import/export with Excel templates (Clients, Categories)
- [x] **Bulk Task Import/Export** (Jan 2025) - Partners only
- [x] Dashboard with analytics
- [x] Notification system
- [x] Mobile responsive design (hamburger menu, card layout)
- [x] Custom TaskAct branding (logo, favicon)
- [x] **Forgot Password with OTP** (Dev Mode)

### Pending Features
- [x] **Team Member Deletion/Deactivation** (Completed Jan 2025)
  - Delete user if no tasks ever assigned (permanent removal)
  - Deactivate user if tasks exist (preserves history, blocks login)
  - Reactivate deactivated users
  - Confirmation modals for all actions
- [ ] Production email delivery (requires Resend API key)

## Demo Accounts
- Partner: sarah@firm.com / newpassword123
- Associate: michael@firm.com / password123
- Junior: emma@firm.com / password123

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/forgot-password` - Request OTP
- `POST /api/auth/verify-otp` - Verify OTP
- `POST /api/auth/reset-password` - Reset password with OTP

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `GET /api/tasks/download-template` - Download bulk import template (Partner)
- `POST /api/tasks/bulk-import` - Bulk import tasks from Excel (Partner)
- `GET /api/tasks/export` - Export all tasks to Excel (Partner)

### Users
- `GET /api/users` - List users (partners can add `?include_inactive=true`)
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `PUT /api/users/{id}/password` - Reset password (by Partner)
- `DELETE /api/users/{id}` - Delete user (only if no tasks)
- `PUT /api/users/{id}/deactivate` - Deactivate user
- `PUT /api/users/{id}/reactivate` - Reactivate user

### Dashboard
- `GET /api/dashboard` - Dashboard analytics

## Notes
- OTP is currently shown on screen (Dev Mode) for testing
- For production, configure RESEND_API_KEY in backend/.env
- JWT secret is stored in SECRET_KEY environment variable
