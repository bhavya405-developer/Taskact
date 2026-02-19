# TaskAct - Professional Task Management Platform

## Product Requirements Document (PRD)

---

## 1. Overview

**TaskAct** is a comprehensive task management application designed for professional firms (CA, CS, Law firms, etc.). It enables efficient task tracking, team management, attendance monitoring, timesheets, and now supports **multi-tenant architecture** for managing multiple companies/organizations.

---

## 2. Core Features

### 2.1 Authentication & Authorization
- **Multi-Tenant Login**: Users login with Company Code (4-8 alphanumeric) + Email + Password
- **Role-Based Access**: Partner (admin), Associate (team member)
- **Super Admin Portal**: Separate portal at `/admin` for platform administrators
- **Forgot Password**: OTP-based password reset via partner notification

### 2.2 Multi-Tenant Architecture ✅ NEW
- **Tenant/Company Management**: Each company has unique code (e.g., SCO1)
- **Data Isolation**: All data filtered by tenant_id
- **Super Admin Features**:
  - View all tenants with statistics
  - Create/deactivate tenants
  - Impersonate users for support
- **Existing Tenant**: Sundesha & Co LLP (Code: SCO1)

### 2.3 Task Management
- Create, view, edit, delete tasks
- Assign tasks to team members
- Task status workflow: Pending → In Progress → Completed/On Hold
- Priority levels: High, Medium, Low
- Due date tracking with overdue alerts
- Task history with timestamps (IST)
- Bulk import/export via Excel

### 2.4 Project Management ✅ NEW
- **Projects with Sub-tasks**: Create projects containing multiple sub-tasks
- **Project Templates**: Save and reuse project structures
- **Project Status**: Draft → Ready → Allocated → In Progress → Completed
- **Template Scopes**: Global (all tenants) or Tenant-specific
- **Progress Tracking**: Visual progress bar based on sub-task completion

### 2.5 Team Management
- Add/edit/deactivate team members
- View team performance metrics
- Role assignment (Partner/Associate)

### 2.6 GPS Attendance
- Clock in/out with GPS location capture
- Multiple office locations support (up to 5)
- Attendance rules and geofencing
- Holiday calendar management

### 2.7 Timesheet Management
- Log time against tasks
- Daily/weekly/monthly timesheet views
- Excel export functionality
- Automatic timesheet generation

### 2.8 PWA & Push Notifications ✅ NEW
- Service Worker for offline support
- Push notification infrastructure
- Task assignment notifications
- Deadline reminder alerts

### 2.9 Dashboard
- Overview statistics (Total, Pending, Completed, Overdue)
- Overdue tasks panel
- Upcoming tasks panel (Due in 7 days)
- Team performance metrics (Partners)

---

## 3. Technical Architecture

### 3.1 Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB (Motor async driver)
- **Authentication**: JWT tokens
- **Architecture**: Modular routers

```
/app/backend/
├── server.py              # Main app, remaining routes
├── routes/
│   ├── __init__.py
│   ├── auth.py            # Authentication
│   ├── users.py           # User management
│   ├── tasks.py           # Task management
│   ├── attendance.py      # Attendance
│   ├── timesheets.py      # Timesheets
│   ├── tenants.py         # Multi-tenant management
│   └── projects.py        # Project management
├── requirements.txt
└── .env
```

### 3.2 Frontend
- **Framework**: React 18
- **Styling**: Tailwind CSS + Shadcn UI
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Icons**: Lucide React

```
/app/frontend/
├── public/
│   ├── service-worker.js  # PWA Service Worker
│   └── manifest.json      # PWA Manifest
├── src/
│   ├── components/
│   │   ├── Login.js              # Multi-tenant login
│   │   ├── SuperAdminApp.js      # Super Admin portal
│   │   ├── SuperAdminDashboard.js
│   │   ├── Projects.js           # Project management
│   │   └── NotificationSettings.js
│   ├── services/
│   │   └── pushNotificationService.js
│   └── contexts/
│       └── AuthContext.js        # Tenant-aware auth
└── package.json
```

### 3.3 Database Schema (Key Collections)

**tenants**
```json
{
  "id": "uuid",
  "name": "Company Name",
  "code": "SCO1",
  "plan": "premium",
  "max_users": 100,
  "active": true
}
```

**users** (includes tenant_id)
```json
{
  "id": "uuid",
  "tenant_id": "tenant_uuid",
  "email": "user@company.com",
  "role": "partner|associate"
}
```

**projects**
```json
{
  "id": "uuid",
  "tenant_id": "tenant_uuid",
  "title": "Project Name",
  "status": "draft|ready|allocated|in_progress|completed",
  "sub_tasks": [{
    "id": "uuid",
    "title": "Sub-task",
    "status": "pending|completed"
  }],
  "progress": 0.0
}
```

**project_templates**
```json
{
  "id": "uuid",
  "tenant_id": "tenant_uuid|null",
  "scope": "global|tenant",
  "name": "Template Name",
  "sub_tasks": [...]
}
```

---

## 4. API Endpoints

### Authentication
- `POST /api/auth/login` - Login with company_code, email, password
- `GET /api/auth/me` - Get current user with tenant info
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/verify-otp` - Verify OTP
- `POST /api/auth/reset-password` - Reset password

### Tenants
- `GET /api/tenant/lookup/{code}` - Public tenant lookup
- `POST /api/tenants` - Create tenant (Super Admin)
- `GET /api/tenants` - List tenants (Super Admin)
- `PUT /api/tenants/{id}` - Update tenant (Super Admin)
- `DELETE /api/tenants/{id}` - Deactivate tenant (Super Admin)

### Super Admin
- `POST /api/super-admin/login` - Super admin login
- `GET /api/super-admin/dashboard` - Dashboard statistics
- `POST /api/super-admin/impersonate` - Impersonate user

### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects
- `PUT /api/projects/{id}` - Update project
- `POST /api/projects/{id}/allocate` - Allocate project
- `POST /api/projects/{id}/subtasks` - Add sub-task
- `PUT /api/projects/{id}/subtasks/{id}` - Update sub-task

### Project Templates
- `POST /api/project-templates` - Create template
- `GET /api/project-templates` - List templates
- `POST /api/project-templates/{id}/use` - Create project from template

---

## 5. User Credentials

### Tenant Users (Sundesha & Co LLP - Code: SCO1)
- **Partner**: bhavika@sundesha.in / password123
- **Associate**: sonurajpurohit980@gmail.com / password123

### Super Admin
- **Email**: admin@taskact.com
- **Password**: admin123
- **Access**: /admin route

---

## 6. What's Implemented ✅

### February 2026 Session
1. **Multi-Tenant Architecture**
   - Company code login flow
   - Tenant management (create, edit, deactivate)
   - Data isolation by tenant_id
   - Migration of existing data to SCO1

2. **Super Admin Portal**
   - Separate login at /admin
   - Dashboard with tenant statistics
   - User impersonation for support
   - Tenant CRUD operations

3. **Project Management**
   - Projects with sub-tasks
   - Project templates (Global + Tenant-specific)
   - Project allocation workflow
   - Progress tracking

4. **PWA Service Worker**
   - Service worker registration
   - Push notification infrastructure
   - Offline support foundation

---

## 7. Backlog / Future Tasks

### P1 - High Priority
- [ ] Finalize Forgot Password with real email service (Resend integration)
- [ ] Complete backend refactoring (notifications, categories, clients, dashboard routes)

### P2 - Medium Priority
- [ ] Real push notification server (VAPID keys)
- [ ] Project-to-Task conversion (convert project sub-tasks to regular tasks)
- [ ] Project reports and analytics

### P3 - Low Priority / Future
- [ ] Mobile app (React Native)
- [ ] Advanced reporting and analytics
- [ ] Integration with external calendars
- [ ] Client portal for task visibility

---

## 8. Known Mocked Features

- **Push Notifications**: VAPID keys are placeholder - needs real push server for production
- **Forgot Password Email**: Using notification panel instead of actual email

---

## 9. Testing

### Test Credentials
See Section 5 above.

### Test Reports
- `/app/test_reports/iteration_2.json` - Latest test results (100% pass rate)

---

*Last Updated: February 2026*
