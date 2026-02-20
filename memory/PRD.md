# TaskAct - Professional Task Management Platform

## Product Requirements Document (PRD)

---

## 1. Overview

**TaskAct** is a comprehensive task management application designed for professional firms (CA, CS, Law firms, etc.). It enables efficient task tracking, team management, attendance monitoring, timesheets, and supports **multi-tenant architecture** for managing multiple companies/organizations.

---

## 2. Core Features

### 2.1 Authentication & Authorization
- **Multi-Tenant Login**: Users login with Company Code (4-8 alphanumeric) + Email + Password
- **Role-Based Access**: Partner (admin), Associate (team member), Super Admin
- **Admin Login**: Company Code **TASKACT1** for platform administrators
- **Forgot Password**: OTP-based password reset via partner notification (Admin OTPs go to SCO1 partners)

### 2.2 Multi-Tenant Architecture ✅
- **Tenant/Company Management**: Each company has unique code (e.g., SCO1)
- **Data Isolation**: All data filtered by tenant_id
- **Super Admin Features** (via normal login with TASKACT1):
  - View all tenants with statistics
  - Edit tenant details (name, plan, max users, contact info)
  - Create global project templates
- **Existing Tenants**: 
  - Sundesha & Co LLP (Code: SCO1, Premium)
  - TaskAct Platform Admin (Code: TASKACT1, Enterprise)

### 2.3 Task Management
- Create, view, edit, delete tasks
- Assign tasks to team members
- Task status workflow: Pending → In Progress → Completed/On Hold
- Priority levels: High, Medium, Low
- Due date tracking with overdue alerts
- Task history with timestamps (IST)
- Bulk import/export via Excel

### 2.4 Project Management ✅
- **Projects with Sub-tasks**: Create projects containing multiple sub-tasks
- **Project Templates**: Save and reuse project structures
  - **Global Templates**: Created by admin, available to all tenants
  - **Tenant Templates**: Organization-specific templates
- **Project Status**: Draft → Ready → Allocated → In Progress → Completed
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

### 2.8 PWA & Push Notifications ✅
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

### 3.2 Frontend
- **Framework**: React 18
- **Styling**: Tailwind CSS + Shadcn UI
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Icons**: Lucide React

### 3.3 Key Routes
```
/                   - Login page (no placeholders)
/dashboard          - Main dashboard
/tasks              - Task list
/projects           - Project management
/admin-panel        - Admin panel (super admin only)
/admin              - Old super admin portal (deprecated)
```

---

## 4. User Credentials

### Tenant Users (Sundesha & Co LLP - Code: SCO1)
- **Partner**: bhavika@sundesha.in / password123
- **Associate**: sonurajpurohit980@gmail.com / password123

### Super Admin (Code: TASKACT1)
- **Email**: admin@taskact.com
- **Password**: admin123

---

## 5. What's Implemented ✅

### February 2026 Session - Latest Changes

#### UI/UX Improvements (Feb 20, 2026)
1. **Admin Panel Dark Theme**
   - Converted Admin Panel to dark theme (slate-900 background)
   - All modals (Edit Tenant, Create Tenant, Create Template) have dark styling
   - Table and form elements styled with dark color scheme

2. **Add New Tenant Button Restored**
   - "Add New Tenant" button added to Admin Panel Tenants tab
   - Create Tenant modal with all required fields (Name, Code, Email, Plan, Max Users)
   - Full functionality for adding new companies

3. **Navigation Improvements**
   - Company badge with visual divider for better separation
   - Gradient profile avatar styling
   - Better spacing in navigation tabs
   - Improved responsiveness for medium screens

4. **Previous Changes**
   - Admin Login via Normal Login Page
   - Super admin now logs in using Company Code: TASKACT1
   - No separate /admin login required for normal operations
   - Forgot password for admin sends OTP to SCO1 partners

5. **Tenant Editing in Admin Panel**
   - Edit tenant details (name, email, phone, plan, max users)
   - View all tenants with user counts and status

6. **Global Project Templates**
   - Admin can create templates available to all tenants
   - Templates tab in Admin Panel

7. **Profile Dropdown**
   - Profile dropdown on desktop (Click name → Change Password, Admin Panel, Logout)
   - Cleaner company badge styling (no code shown, just company name)
   - Admin badge for super admin users

---

## 6. Backlog / Future Tasks

### P1 - High Priority
- [ ] Finalize Forgot Password with real email service (Resend integration)
- [ ] Complete backend refactoring (notifications, categories, clients, dashboard routes)

### P2 - Medium Priority
- [ ] Real push notification server (VAPID keys)
- [ ] Project-to-Task conversion
- [ ] Project reports and analytics

### P3 - Low Priority / Future
- [ ] Mobile app (React Native)
- [ ] Advanced reporting and analytics
- [ ] Integration with external calendars
- [ ] Client portal for task visibility

---

## 7. Known Mocked Features

- **Push Notifications**: VAPID keys are placeholder - needs real push server
- **Forgot Password Email**: Using notification panel instead of actual email

---

*Last Updated: February 2026*
