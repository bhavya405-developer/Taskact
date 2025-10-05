import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import Tasks from "./components/Tasks";
import TeamMembers from "./components/TeamMembers";
import CreateTask from "./components/CreateTask";
import Navigation from "./components/Navigation";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [users, setUsers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
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
    const loadData = async () => {
      await Promise.all([fetchUsers(), fetchTasks()]);
      setLoading(false);
    };
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading Task Management System...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route 
                path="/dashboard" 
                element={<Dashboard users={users} tasks={tasks} />} 
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
                path="/create-task" 
                element={
                  <CreateTask 
                    users={users} 
                    onTaskCreated={fetchTasks} 
                  />
                } 
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default App;