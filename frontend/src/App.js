import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import Tasks from "./components/Tasks";
import TeamMembers from "./components/TeamMembers";
import CreateTask from "./components/CreateTask";
import CategoryManager from "./components/CategoryManager";
import ClientManager from "./components/ClientManager";
import Navigation from "./components/Navigation";
import Attendance from "./components/Attendance";
import Timesheet from "./components/Timesheet";
import Projects from "./components/Projects";
import AdminPanel from "./components/AdminPanel";
import SuperAdminApp from "./components/SuperAdminApp";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Component to handle dashboard redirect on login
const DashboardRedirect = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  useEffect(() => {
    // If user just logged in and not already on dashboard, redirect to dashboard
    if (user && location.pathname === '/') {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate, location.pathname]);
  
  return null;
};

// Impersonation Banner Component
const ImpersonationBanner = () => {
  const impersonationData = localStorage.getItem('impersonation');
  
  if (!impersonationData) return null;
  
  try {
    const data = JSON.parse(impersonationData);
    
    const endImpersonation = () => {
      // Clear impersonation and redirect to admin
      localStorage.removeItem('token');
      localStorage.removeItem('tenant');
      localStorage.removeItem('impersonation');
      window.location.href = '/admin';
    };
    
    return (
      <div className="bg-amber-500 text-amber-900 px-4 py-2 text-center text-sm font-medium">
        <span className="mr-2">
          You are impersonating this user as support. Actions are logged.
        </span>
        <button
          onClick={endImpersonation}
          className="underline hover:no-underline font-semibold"
        >
          End Impersonation
        </button>
      </div>
    );
  } catch {
    return null;
  }
};

const AppContent = () => {
  const { user, loading: authLoading, isPartner } = useAuth();
  const [users, setUsers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      // Partners can see inactive users for management
      const includeInactive = isPartner ? isPartner() : false;
      const response = await axios.get(`${API}/users${includeInactive ? '?include_inactive=true' : ''}`);
      setUsers(response.data);
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API}/tasks`);
      setTasks(response.data);
    } catch (error) {
      console.error("Error fetching tasks:", error);
    }
  };

  useEffect(() => {
    if (user) {
      const loadData = async () => {
        await Promise.all([fetchUsers(), fetchTasks()]);
        setLoading(false);
      };
      loadData();
    }
  }, [user]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading TaskAct...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <ImpersonationBanner />
        <DashboardRedirect />
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route 
              path="/dashboard" 
              element={<Dashboard users={users} tasks={tasks} onTaskUpdate={fetchTasks} />} 
            />
            <Route 
              path="/tasks" 
              element={
                <Tasks 
                  tasks={tasks} 
                  users={users} 
                  onTaskUpdate={fetchTasks} 
                />
              } 
            />
            <Route 
              path="/team" 
              element={
                <TeamMembers 
                  users={users} 
                  tasks={tasks} 
                  onUserAdded={fetchUsers} 
                />
              } 
            />
            <Route 
              path="/categories" 
              element={<CategoryManager />} 
            />
            <Route 
              path="/clients" 
              element={<ClientManager />} 
            />
            <Route 
              path="/attendance" 
              element={<Attendance />} 
            />
            <Route 
              path="/timesheet" 
              element={<Timesheet users={users} />} 
            />
            <Route 
              path="/projects" 
              element={<Projects users={users} />} 
            />
            <Route 
              path="/admin-panel" 
              element={<AdminPanel />} 
            />
            <Route 
              path="/create-task" 
              element={
                <CreateTask 
                  users={users} 
                  onTaskCreated={fetchTasks} 
                />
              } 
            />
            {/* Catch-all route - redirect any unmatched routes to dashboard */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

// Main App with Super Admin Route
function App() {
  // Check if we're on the admin route
  const path = window.location.pathname;
  
  if (path === '/admin' || path.startsWith('/admin/')) {
    return <SuperAdminApp />;
  }
  
  return (
    <div className="App">
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </div>
  );
}

export default App;
