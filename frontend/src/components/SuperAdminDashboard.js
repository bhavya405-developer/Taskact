import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Building2, Users, ClipboardList, Plus, Search, 
  MoreVertical, Shield, LogOut, Eye, UserCog,
  ChevronDown, X, Check, AlertCircle
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SuperAdminDashboard = ({ admin, onLogout, onImpersonate }) => {
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [tenantUsers, setTenantUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Modal states
  const [showCreateTenant, setShowCreateTenant] = useState(false);
  const [showTenantUsers, setShowTenantUsers] = useState(false);
  const [showImpersonateConfirm, setShowImpersonateConfirm] = useState(false);
  const [userToImpersonate, setUserToImpersonate] = useState(null);
  
  // Form states
  const [newTenant, setNewTenant] = useState({
    name: '',
    code: '',
    contact_email: '',
    contact_phone: '',
    plan: 'standard',
    max_users: 50
  });
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [dashboardRes, tenantsRes] = await Promise.all([
        axios.get(`${API_URL}/api/super-admin/dashboard`),
        axios.get(`${API_URL}/api/tenants`)
      ]);
      setStats(dashboardRes.data.statistics);
      setTenants(tenantsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTenantUsers = async (tenant) => {
    setSelectedTenant(tenant);
    setShowTenantUsers(true);
    try {
      const response = await axios.get(`${API_URL}/api/tenants/${tenant.id}/users?include_inactive=true`);
      setTenantUsers(response.data);
    } catch (error) {
      console.error('Error fetching tenant users:', error);
    }
  };

  const handleCreateTenant = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError('');

    try {
      const payload = {
        name: newTenant.name,
        code: newTenant.code || undefined,
        contact_email: newTenant.contact_email || undefined,
        contact_phone: newTenant.contact_phone || undefined,
        plan: newTenant.plan,
        max_users: parseInt(newTenant.max_users)
      };

      await axios.post(`${API_URL}/api/tenants`, payload);
      setShowCreateTenant(false);
      setNewTenant({
        name: '',
        code: '',
        contact_email: '',
        contact_phone: '',
        plan: 'standard',
        max_users: 50
      });
      fetchData();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to create tenant');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeactivateTenant = async (tenantId) => {
    if (!window.confirm('Are you sure you want to deactivate this tenant? Users will not be able to login.')) {
      return;
    }
    try {
      await axios.delete(`${API_URL}/api/tenants/${tenantId}`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to deactivate tenant');
    }
  };

  const handleReactivateTenant = async (tenantId) => {
    try {
      await axios.put(`${API_URL}/api/tenants/${tenantId}/reactivate`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reactivate tenant');
    }
  };

  const initiateImpersonate = (user) => {
    setUserToImpersonate(user);
    setShowImpersonateConfirm(true);
  };

  const handleImpersonate = async () => {
    if (!userToImpersonate || !selectedTenant) return;
    
    try {
      const response = await axios.post(`${API_URL}/api/super-admin/impersonate`, {
        user_id: userToImpersonate.id,
        tenant_id: selectedTenant.id
      });
      
      if (onImpersonate) {
        onImpersonate(response.data);
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to impersonate user');
    }
    
    setShowImpersonateConfirm(false);
    setUserToImpersonate(null);
  };

  const filteredTenants = tenants.filter(tenant =>
    tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tenant.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto"></div>
          <p className="mt-4 text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-indigo-600 p-2 rounded-lg">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-white">TaskAct Admin</h1>
                <p className="text-sm text-slate-400">Super Admin Portal</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-slate-300">{admin?.name}</span>
              <button
                onClick={onLogout}
                className="flex items-center text-slate-400 hover:text-white transition-colors"
                data-testid="super-admin-logout"
              >
                <LogOut className="h-5 w-5 mr-1" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Tenants</p>
                <p className="text-3xl font-bold text-white mt-1">{stats?.total_tenants || 0}</p>
                <p className="text-sm text-green-400 mt-1">{stats?.active_tenants || 0} active</p>
              </div>
              <Building2 className="h-10 w-10 text-indigo-500" />
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Users</p>
                <p className="text-3xl font-bold text-white mt-1">{stats?.total_users || 0}</p>
                <p className="text-sm text-green-400 mt-1">{stats?.active_users || 0} active</p>
              </div>
              <Users className="h-10 w-10 text-blue-500" />
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Tasks</p>
                <p className="text-3xl font-bold text-white mt-1">{stats?.total_tasks || 0}</p>
              </div>
              <ClipboardList className="h-10 w-10 text-amber-500" />
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <button
              onClick={() => setShowCreateTenant(true)}
              className="w-full h-full flex flex-col items-center justify-center text-indigo-400 hover:text-indigo-300 transition-colors"
              data-testid="create-tenant-button"
            >
              <Plus className="h-10 w-10 mb-2" />
              <span className="font-medium">Add New Tenant</span>
            </button>
          </div>
        </div>

        {/* Tenants Table */}
        <div className="bg-slate-800 rounded-lg border border-slate-700">
          <div className="p-6 border-b border-slate-700">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">All Tenants</h2>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search tenants..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="search-tenants-input"
                />
              </div>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-700/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Company</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Code</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Plan</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Users</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Tasks</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {filteredTenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-slate-700/30">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Building2 className="h-5 w-5 text-slate-400 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-white">{tenant.name}</div>
                          <div className="text-xs text-slate-400">{tenant.contact_email || 'No email'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 bg-indigo-900/50 text-indigo-300 rounded text-sm font-mono">
                        {tenant.code}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        tenant.plan === 'premium' ? 'bg-amber-900/50 text-amber-300' :
                        tenant.plan === 'standard' ? 'bg-blue-900/50 text-blue-300' :
                        'bg-slate-700 text-slate-300'
                      }`}>
                        {tenant.plan?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                      {tenant.user_count || 0} / {tenant.max_users}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                      {tenant.task_count || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        tenant.active ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
                      }`}>
                        {tenant.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="text-slate-400 hover:text-white p-1">
                            <MoreVertical className="h-5 w-5" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
                          <DropdownMenuItem 
                            onClick={() => fetchTenantUsers(tenant)}
                            className="text-slate-300 hover:text-white hover:bg-slate-700 cursor-pointer"
                          >
                            <Users className="h-4 w-4 mr-2" />
                            View Users
                          </DropdownMenuItem>
                          {tenant.active ? (
                            <DropdownMenuItem 
                              onClick={() => handleDeactivateTenant(tenant.id)}
                              className="text-red-400 hover:text-red-300 hover:bg-slate-700 cursor-pointer"
                            >
                              <X className="h-4 w-4 mr-2" />
                              Deactivate
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem 
                              onClick={() => handleReactivateTenant(tenant.id)}
                              className="text-green-400 hover:text-green-300 hover:bg-slate-700 cursor-pointer"
                            >
                              <Check className="h-4 w-4 mr-2" />
                              Reactivate
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {filteredTenants.length === 0 && (
              <div className="text-center py-12 text-slate-400">
                No tenants found
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Create Tenant Modal */}
      <Dialog open={showCreateTenant} onOpenChange={setShowCreateTenant}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Tenant</DialogTitle>
            <DialogDescription className="text-slate-400">
              Add a new company/organization to TaskAct
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateTenant} className="space-y-4">
            {formError && (
              <div className="bg-red-900/50 border border-red-500 rounded-md p-3">
                <div className="text-sm text-red-300">{formError}</div>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Company Name *
              </label>
              <input
                type="text"
                value={newTenant.name}
                onChange={(e) => setNewTenant({ ...newTenant, name: e.target.value })}
                required
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white"
                placeholder="e.g., Acme Corporation"
                data-testid="new-tenant-name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Company Code (4-8 chars, optional)
              </label>
              <input
                type="text"
                value={newTenant.code}
                onChange={(e) => setNewTenant({ ...newTenant, code: e.target.value.toUpperCase() })}
                maxLength={8}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white uppercase"
                placeholder="Auto-generated if empty"
                data-testid="new-tenant-code"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Contact Email
              </label>
              <input
                type="email"
                value={newTenant.contact_email}
                onChange={(e) => setNewTenant({ ...newTenant, contact_email: e.target.value })}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white"
                placeholder="admin@company.com"
                data-testid="new-tenant-email"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Plan
                </label>
                <select
                  value={newTenant.plan}
                  onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white"
                  data-testid="new-tenant-plan"
                >
                  <option value="free">Free</option>
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Max Users
                </label>
                <input
                  type="number"
                  value={newTenant.max_users}
                  onChange={(e) => setNewTenant({ ...newTenant, max_users: e.target.value })}
                  min={1}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white"
                  data-testid="new-tenant-max-users"
                />
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowCreateTenant(false)}
                className="px-4 py-2 text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                data-testid="submit-create-tenant"
              >
                {formLoading ? 'Creating...' : 'Create Tenant'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Tenant Users Modal */}
      <Dialog open={showTenantUsers} onOpenChange={setShowTenantUsers}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Users - {selectedTenant?.name}</DialogTitle>
            <DialogDescription className="text-slate-400">
              Company Code: {selectedTenant?.code}
            </DialogDescription>
          </DialogHeader>
          
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full">
              <thead className="bg-slate-700/50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-300">Name</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-300">Email</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-300">Role</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-300">Status</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-300">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {tenantUsers.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-3 text-sm text-white">{user.name}</td>
                    <td className="px-4 py-3 text-sm text-slate-300">{user.email}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${
                        user.role === 'partner' ? 'bg-purple-900/50 text-purple-300' :
                        user.role === 'associate' ? 'bg-blue-900/50 text-blue-300' :
                        'bg-slate-700 text-slate-300'
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${
                        user.active ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
                      }`}>
                        {user.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {user.active && (
                        <button
                          onClick={() => initiateImpersonate(user)}
                          className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center"
                          data-testid={`impersonate-${user.id}`}
                        >
                          <UserCog className="h-4 w-4 mr-1" />
                          Impersonate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {tenantUsers.length === 0 && (
              <div className="text-center py-8 text-slate-400">
                No users in this tenant
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Impersonation Confirmation Modal */}
      <Dialog open={showImpersonateConfirm} onOpenChange={setShowImpersonateConfirm}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <AlertCircle className="h-5 w-5 text-amber-500 mr-2" />
              Confirm Impersonation
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              You are about to impersonate a user for support purposes.
            </DialogDescription>
          </DialogHeader>
          
          <div className="bg-slate-700/50 rounded-lg p-4 my-4">
            <p className="text-sm text-slate-300">
              <strong>User:</strong> {userToImpersonate?.name}
            </p>
            <p className="text-sm text-slate-300">
              <strong>Email:</strong> {userToImpersonate?.email}
            </p>
            <p className="text-sm text-slate-300">
              <strong>Tenant:</strong> {selectedTenant?.name}
            </p>
          </div>
          
          <p className="text-sm text-amber-300">
            This action will be logged for audit purposes.
          </p>
          
          <DialogFooter>
            <button
              onClick={() => setShowImpersonateConfirm(false)}
              className="px-4 py-2 text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleImpersonate}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              data-testid="confirm-impersonate"
            >
              Impersonate User
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SuperAdminDashboard;
