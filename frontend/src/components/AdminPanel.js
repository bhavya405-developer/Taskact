import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { 
  Building2, Users, ClipboardList, Plus, Search, Edit2,
  ChevronRight, X, Check, Save, FolderKanban, FileText,
  Clock, Trash2, Shield, MoreVertical, Power, AlertTriangle
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from './ui/dropdown-menu';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdminPanel = () => {
  const { isSuperAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('tenants');
  const [tenants, setTenants] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Modal states
  const [showEditTenant, setShowEditTenant] = useState(false);
  const [showCreateTenant, setShowCreateTenant] = useState(false);
  const [showCreateTemplate, setShowCreateTemplate] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState(null);
  
  // Form states
  const [tenantForm, setTenantForm] = useState({
    name: '',
    contact_email: '',
    contact_phone: '',
    plan: 'standard',
    max_users: 50
  });
  
  // New tenant form
  const [newTenant, setNewTenant] = useState({
    name: '',
    code: '',
    contact_email: '',
    contact_phone: '',
    plan: 'standard',
    max_users: 50
  });
  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    category: '',
    estimated_hours: '',
    sub_tasks: []
  });
  const [newSubTask, setNewSubTask] = useState({ title: '', estimated_hours: '', priority: 'medium' });
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    if (isSuperAdmin()) {
      fetchData();
    }
  }, [isSuperAdmin]);

  const fetchData = async () => {
    try {
      const [tenantsRes, templatesRes] = await Promise.all([
        axios.get(`${API_URL}/api/tenants`),
        axios.get(`${API_URL}/api/project-templates`)
      ]);
      setTenants(tenantsRes.data);
      setTemplates(templatesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEditTenant = (tenant) => {
    setSelectedTenant(tenant);
    setTenantForm({
      name: tenant.name,
      contact_email: tenant.contact_email || '',
      contact_phone: tenant.contact_phone || '',
      plan: tenant.plan,
      max_users: tenant.max_users
    });
    setShowEditTenant(true);
  };

  const handleSaveTenant = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError('');

    try {
      await axios.put(`${API_URL}/api/tenants/${selectedTenant.id}`, tenantForm);
      setShowEditTenant(false);
      fetchData();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to update tenant');
    } finally {
      setFormLoading(false);
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

  const handleCreateGlobalTemplate = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError('');

    try {
      const payload = {
        ...templateForm,
        estimated_hours: templateForm.estimated_hours ? parseFloat(templateForm.estimated_hours) : null,
        scope: 'global',
        sub_tasks: templateForm.sub_tasks.map((st, i) => ({
          ...st,
          order: i,
          estimated_hours: st.estimated_hours ? parseFloat(st.estimated_hours) : null
        }))
      };

      await axios.post(`${API_URL}/api/project-templates`, payload);
      setShowCreateTemplate(false);
      setTemplateForm({
        name: '',
        description: '',
        category: '',
        estimated_hours: '',
        sub_tasks: []
      });
      fetchData();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to create template');
    } finally {
      setFormLoading(false);
    }
  };

  const addSubTask = () => {
    if (!newSubTask.title.trim()) return;
    setTemplateForm(prev => ({
      ...prev,
      sub_tasks: [...prev.sub_tasks, { ...newSubTask }]
    }));
    setNewSubTask({ title: '', estimated_hours: '', priority: 'medium' });
  };

  const removeSubTask = (index) => {
    setTemplateForm(prev => ({
      ...prev,
      sub_tasks: prev.sub_tasks.filter((_, i) => i !== index)
    }));
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/project-templates/${templateId}`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete template');
    }
  };

  const handleDeactivateTenant = async () => {
    if (!selectedTenant) return;
    setFormLoading(true);
    setFormError('');
    
    try {
      await axios.delete(`${API_URL}/api/tenants/${selectedTenant.id}`);
      setShowDeactivateConfirm(false);
      setSelectedTenant(null);
      fetchData();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to deactivate tenant');
    } finally {
      setFormLoading(false);
    }
  };

  const handleReactivateTenant = async (tenant) => {
    try {
      await axios.put(`${API_URL}/api/tenants/${tenant.id}/reactivate`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reactivate tenant');
    }
  };

  const handleDeleteTenant = async () => {
    if (!selectedTenant) return;
    setFormLoading(true);
    setFormError('');
    
    try {
      await axios.delete(`${API_URL}/api/tenants/${selectedTenant.id}/permanent`);
      setShowDeleteConfirm(false);
      setSelectedTenant(null);
      fetchData();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to delete tenant');
    } finally {
      setFormLoading(false);
    }
  };

  const openDeactivateConfirm = (tenant) => {
    setSelectedTenant(tenant);
    setFormError('');
    setShowDeactivateConfirm(true);
  };

  const openDeleteConfirm = (tenant) => {
    setSelectedTenant(tenant);
    setFormError('');
    setShowDeleteConfirm(true);
  };

  if (!isSuperAdmin()) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Access Denied</h2>
        <p className="text-gray-500 mt-2">You don't have permission to access this page.</p>
      </div>
    );
  }

  const filteredTenants = tenants.filter(t => 
    t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredTemplates = templates.filter(t =>
    t.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center bg-slate-900 rounded-xl">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-400"></div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 -mx-4 sm:-mx-6 lg:-mx-8 -my-8 px-4 sm:px-6 lg:px-8 py-8 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 p-2 rounded-lg">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Admin Panel</h1>
            <p className="text-slate-400 text-sm">Manage tenants and global templates</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700 mb-6">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('tenants')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'tenants'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-500'
            }`}
            data-testid="tab-tenants"
          >
            <Building2 className="h-4 w-4 inline mr-2" />
            Tenants ({tenants.length})
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'templates'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-500'
            }`}
            data-testid="tab-templates"
          >
            <FolderKanban className="h-4 w-4 inline mr-2" />
            Global Templates ({templates.filter(t => t.scope === 'global').length})
          </button>
        </nav>
      </div>

      {/* Search and Action Buttons */}
      <div className="flex items-center justify-between mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder={`Search ${activeTab}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        
        {activeTab === 'tenants' && (
          <button
            onClick={() => setShowCreateTenant(true)}
            className="flex items-center ml-4 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            data-testid="create-tenant-button"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add New Tenant
          </button>
        )}
        
        {activeTab === 'templates' && (
          <button
            onClick={() => setShowCreateTemplate(true)}
            className="flex items-center ml-4 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            data-testid="create-global-template"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Global Template
          </button>
        )}
      </div>

      {/* Content */}
      {activeTab === 'tenants' && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-700">
            <thead className="bg-slate-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Company</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Code</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Users</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-300 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filteredTenants.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-slate-700/30 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <Building2 className="h-5 w-5 text-slate-400 mr-3" />
                      <div>
                        <div className="text-sm font-medium text-white">{tenant.name}</div>
                        <div className="text-xs text-slate-400">{tenant.contact_email || '-'}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 bg-indigo-900/50 text-indigo-300 rounded text-sm font-mono">
                      {tenant.code}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      tenant.plan === 'premium' ? 'bg-amber-900/50 text-amber-300' :
                      tenant.plan === 'enterprise' ? 'bg-purple-900/50 text-purple-300' :
                      tenant.plan === 'standard' ? 'bg-blue-900/50 text-blue-300' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {tenant.plan?.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-300">
                    {tenant.user_count || 0} / {tenant.max_users}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      tenant.active ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
                    }`}>
                      {tenant.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button 
                          className="p-1.5 hover:bg-slate-600 rounded-lg transition-colors"
                          data-testid={`tenant-actions-${tenant.code}`}
                        >
                          <MoreVertical className="h-5 w-5 text-slate-400" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
                        <DropdownMenuItem 
                          onClick={() => handleEditTenant(tenant)}
                          className="text-slate-300 hover:text-white hover:bg-slate-700 cursor-pointer"
                        >
                          <Edit2 className="h-4 w-4 mr-2" />
                          Edit Details
                        </DropdownMenuItem>
                        
                        <DropdownMenuSeparator className="bg-slate-700" />
                        
                        {tenant.active ? (
                          <DropdownMenuItem 
                            onClick={() => openDeactivateConfirm(tenant)}
                            className="text-amber-400 hover:text-amber-300 hover:bg-slate-700 cursor-pointer"
                            disabled={tenant.code === 'TASKACT1'}
                          >
                            <Power className="h-4 w-4 mr-2" />
                            Deactivate
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem 
                            onClick={() => handleReactivateTenant(tenant)}
                            className="text-green-400 hover:text-green-300 hover:bg-slate-700 cursor-pointer"
                          >
                            <Check className="h-4 w-4 mr-2" />
                            Reactivate
                          </DropdownMenuItem>
                        )}
                        
                        {tenant.code !== 'TASKACT1' && (
                          <>
                            <DropdownMenuSeparator className="bg-slate-700" />
                            <DropdownMenuItem 
                              onClick={() => openDeleteConfirm(tenant)}
                              className="text-red-400 hover:text-red-300 hover:bg-slate-700 cursor-pointer"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete Permanently
                            </DropdownMenuItem>
                          </>
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
      )}

      {activeTab === 'templates' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.filter(t => t.scope === 'global').map((template) => (
            <div key={template.id} className="bg-slate-800 rounded-lg border border-slate-700 p-4 hover:bg-slate-750 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-medium text-white">{template.name}</h3>
                  {template.description && (
                    <p className="text-sm text-slate-400 mt-1 line-clamp-2">{template.description}</p>
                  )}
                </div>
                <span className="px-2 py-0.5 bg-indigo-900/50 text-indigo-300 rounded text-xs font-medium ml-2">
                  Global
                </span>
              </div>
              
              <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
                {template.category && (
                  <span className="px-2 py-0.5 bg-slate-700 rounded">{template.category}</span>
                )}
                <span className="flex items-center">
                  <FileText className="h-3 w-3 mr-1" />
                  {template.sub_tasks?.length || 0} tasks
                </span>
                {template.estimated_hours && (
                  <span className="flex items-center">
                    <Clock className="h-3 w-3 mr-1" />
                    {template.estimated_hours}h
                  </span>
                )}
              </div>
              
              <div className="mt-4 pt-3 border-t border-slate-700">
                <button
                  onClick={() => handleDeleteTemplate(template.id)}
                  className="text-red-400 hover:text-red-300 text-sm flex items-center transition-colors"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </button>
              </div>
            </div>
          ))}
          
          {filteredTemplates.filter(t => t.scope === 'global').length === 0 && (
            <div className="col-span-full text-center py-12 bg-slate-800 rounded-lg border border-slate-700">
              <FolderKanban className="h-12 w-12 mx-auto text-slate-500 mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No global templates</h3>
              <p className="text-slate-400">Create a global template to make it available for all tenants.</p>
            </div>
          )}
        </div>
      )}

      {/* Edit Tenant Modal */}
      <Dialog open={showEditTenant} onOpenChange={setShowEditTenant}>
        <DialogContent className="sm:max-w-md bg-slate-800 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="text-white">Edit Tenant</DialogTitle>
            <DialogDescription className="text-slate-400">
              Update tenant information for {selectedTenant?.name}
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleSaveTenant} className="space-y-4">
            {formError && (
              <div className="bg-red-900/50 border border-red-500 rounded-md p-3">
                <div className="text-sm text-red-300">{formError}</div>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Company Name *</label>
              <input
                type="text"
                value={tenantForm.name}
                onChange={(e) => setTenantForm({ ...tenantForm, name: e.target.value })}
                required
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Contact Email</label>
              <input
                type="email"
                value={tenantForm.contact_email}
                onChange={(e) => setTenantForm({ ...tenantForm, contact_email: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Contact Phone</label>
              <input
                type="text"
                value={tenantForm.contact_phone}
                onChange={(e) => setTenantForm({ ...tenantForm, contact_phone: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Plan</label>
                <select
                  value={tenantForm.plan}
                  onChange={(e) => setTenantForm({ ...tenantForm, plan: e.target.value })}
                  className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="free">Free</option>
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Max Users</label>
                <input
                  type="number"
                  value={tenantForm.max_users}
                  onChange={(e) => setTenantForm({ ...tenantForm, max_users: parseInt(e.target.value) })}
                  min={1}
                  className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowEditTenant(false)}
                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                {formLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Create Tenant Modal */}
      <Dialog open={showCreateTenant} onOpenChange={setShowCreateTenant}>
        <DialogContent className="sm:max-w-md bg-slate-800 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="text-white">Create New Tenant</DialogTitle>
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
              <label className="block text-sm font-medium text-slate-300 mb-1">Company Name *</label>
              <input
                type="text"
                value={newTenant.name}
                onChange={(e) => setNewTenant({ ...newTenant, name: e.target.value })}
                required
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g., Acme Corporation"
                data-testid="new-tenant-name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Company Code (4-8 chars, optional)</label>
              <input
                type="text"
                value={newTenant.code}
                onChange={(e) => setNewTenant({ ...newTenant, code: e.target.value.toUpperCase() })}
                maxLength={8}
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white uppercase placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Auto-generated if empty"
                data-testid="new-tenant-code"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Contact Email</label>
              <input
                type="email"
                value={newTenant.contact_email}
                onChange={(e) => setNewTenant({ ...newTenant, contact_email: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="admin@company.com"
                data-testid="new-tenant-email"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Plan</label>
                <select
                  value={newTenant.plan}
                  onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value })}
                  className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="new-tenant-plan"
                >
                  <option value="free">Free</option>
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Max Users</label>
                <input
                  type="number"
                  value={newTenant.max_users}
                  onChange={(e) => setNewTenant({ ...newTenant, max_users: e.target.value })}
                  min={1}
                  className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  data-testid="new-tenant-max-users"
                />
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowCreateTenant(false)}
                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 transition-colors"
                data-testid="submit-create-tenant"
              >
                {formLoading ? 'Creating...' : 'Create Tenant'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Create Global Template Modal */}
      <Dialog open={showCreateTemplate} onOpenChange={setShowCreateTemplate}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto bg-slate-800 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="text-white">Create Global Template</DialogTitle>
            <DialogDescription className="text-slate-400">
              This template will be available for all tenants
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateGlobalTemplate} className="space-y-4">
            {formError && (
              <div className="bg-red-900/50 border border-red-500 rounded-md p-3">
                <div className="text-sm text-red-300">{formError}</div>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Template Name *</label>
              <input
                type="text"
                value={templateForm.name}
                onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                required
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Description</label>
              <textarea
                value={templateForm.description}
                onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                rows={2}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Category</label>
                <input
                  type="text"
                  value={templateForm.category}
                  onChange={(e) => setTemplateForm({ ...templateForm, category: e.target.value })}
                  className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Estimated Hours</label>
                <input
                  type="number"
                  value={templateForm.estimated_hours}
                  onChange={(e) => setTemplateForm({ ...templateForm, estimated_hours: e.target.value })}
                  className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  step="0.5"
                  min="0"
                />
              </div>
            </div>
            
            {/* Sub-tasks */}
            <div className="border-t border-slate-700 pt-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3">Sub-tasks</h4>
              
              {templateForm.sub_tasks.length > 0 && (
                <div className="space-y-2 mb-4">
                  {templateForm.sub_tasks.map((st, index) => (
                    <div key={index} className="flex items-center gap-2 bg-slate-700 p-2 rounded-lg">
                      <span className="flex-1 text-sm text-white">{st.title}</span>
                      <span className="text-xs text-slate-400">{st.estimated_hours}h</span>
                      <button
                        type="button"
                        onClick={() => removeSubTask(index)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newSubTask.title}
                  onChange={(e) => setNewSubTask({ ...newSubTask, title: e.target.value })}
                  className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Sub-task title"
                />
                <input
                  type="number"
                  value={newSubTask.estimated_hours}
                  onChange={(e) => setNewSubTask({ ...newSubTask, estimated_hours: e.target.value })}
                  className="w-20 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Hours"
                  step="0.5"
                  min="0"
                />
                <select
                  value={newSubTask.priority}
                  onChange={(e) => setNewSubTask({ ...newSubTask, priority: e.target.value })}
                  className="w-24 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <button
                  type="button"
                  onClick={addSubTask}
                  className="px-3 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg transition-colors"
                >
                  <Plus className="h-4 w-4 text-white" />
                </button>
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowCreateTemplate(false)}
                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                {formLoading ? 'Creating...' : 'Create Template'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminPanel;
