# TaskAct - Product Requirements Document

## Overview
TaskAct is a comprehensive task management application designed for professional firms. It enables teams to create, assign, track, and manage tasks with role-based access control.

## Core Features

### 1. Authentication & Authorization
- JWT-based authentication
- Role-based access: Partner, Associate, Junior
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

### 3. Team Management
- Partners can add/edit team members
- View team performance stats
- Password reset by partners

### 4. Data Management
- Master lists for Clients and Categories
- Bulk import/export via Excel templates
- MongoDB database

### 5. Dashboard
- Task counts by status
- Overdue and Pending task lists prominently displayed
- Team performance analytics
- Client and category analytics

### 6. Notifications
- Task assignment notifications
- Task update notifications
- Password reset notifications

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
- [x] Client and Category management
- [x] Bulk import/export with Excel templates
- [x] Dashboard with analytics
- [x] Notification system
- [x] Mobile responsive design (hamburger menu, card layout)
- [x] Custom TaskAct branding (logo, favicon)
- [x] **Forgot Password with OTP** (Dev Mode)

### Pending Features
- [ ] Team Member Deletion/Deactivation (P1)
  - Delete user if no tasks assigned
  - Deactivate user if tasks exist
  - Block deactivated users from login
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

### Users
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `PUT /api/users/{id}/password` - Reset password (by Partner)

### Dashboard
- `GET /api/dashboard` - Dashboard analytics

## Notes
- OTP is currently shown on screen (Dev Mode) for testing
- For production, configure RESEND_API_KEY in backend/.env
- JWT secret is stored in SECRET_KEY environment variable
