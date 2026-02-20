import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { 
  Building2, Users, ClipboardList, Plus, Search, Edit2,
  ChevronRight, X, Check, Save, FolderKanban, FileText,
  Clock, Trash2, Shield
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

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
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Admin Panel</h1>
        <p className="text-gray-500 mt-1">Manage tenants and global templates</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('tenants')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'tenants'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            data-testid="tab-tenants"
          >
            <Building2 className="h-4 w-4 inline mr-2" />
            Tenants ({tenants.length})
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'templates'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            data-testid="tab-templates"
          >
            <FolderKanban className="h-4 w-4 inline mr-2" />
            Global Templates ({templates.filter(t => t.scope === 'global').length})
          </button>
        </nav>
      </div>

      {/* Search */}
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder={`Search ${activeTab}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10 w-full"
          />
        </div>
        
        {activeTab === 'templates' && (
          <button
            onClick={() => setShowCreateTemplate(true)}
            className="btn-primary flex items-center ml-4"
            data-testid="create-global-template"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Global Template
          </button>
        )}
      </div>

      {/* Content */}
      {activeTab === 'tenants' && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Users</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredTenants.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <Building2 className="h-5 w-5 text-gray-400 mr-3" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">{tenant.name}</div>
                        <div className="text-xs text-gray-500">{tenant.contact_email || '-'}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm font-mono">
                      {tenant.code}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      tenant.plan === 'premium' ? 'bg-amber-100 text-amber-700' :
                      tenant.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
                      tenant.plan === 'standard' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {tenant.plan?.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {tenant.user_count || 0} / {tenant.max_users}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      tenant.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {tenant.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleEditTenant(tenant)}
                      className="text-indigo-600 hover:text-indigo-900 flex items-center text-sm"
                      data-testid={`edit-tenant-${tenant.code}`}
                    >
                      <Edit2 className="h-4 w-4 mr-1" />
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredTenants.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No tenants found
            </div>
          )}
        </div>
      )}

      {activeTab === 'templates' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.filter(t => t.scope === 'global').map((template) => (
            <div key={template.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{template.name}</h3>
                  {template.description && (
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{template.description}</p>
                  )}
                </div>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium ml-2">
                  Global
                </span>
              </div>
              
              <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                {template.category && (
                  <span className="px-2 py-0.5 bg-gray-100 rounded">{template.category}</span>
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
              
              <div className="mt-4 pt-3 border-t border-gray-100">
                <button
                  onClick={() => handleDeleteTemplate(template.id)}
                  className="text-red-600 hover:text-red-700 text-sm flex items-center"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </button>
              </div>
            </div>
          ))}
          
          {filteredTemplates.filter(t => t.scope === 'global').length === 0 && (
            <div className="col-span-full text-center py-12 bg-white rounded-lg border border-gray-200">
              <FolderKanban className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No global templates</h3>
              <p className="text-gray-500">Create a global template to make it available for all tenants.</p>
            </div>
          )}
        </div>
      )}

      {/* Edit Tenant Modal */}
      <Dialog open={showEditTenant} onOpenChange={setShowEditTenant}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Tenant</DialogTitle>
            <DialogDescription>
              Update tenant information for {selectedTenant?.name}
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleSaveTenant} className="space-y-4">
            {formError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <div className="text-sm text-red-600">{formError}</div>
              </div>
            )}
            
            <div>
              <label className="form-label">Company Name *</label>
              <input
                type="text"
                value={tenantForm.name}
                onChange={(e) => setTenantForm({ ...tenantForm, name: e.target.value })}
                required
                className="form-input"
              />
            </div>
            
            <div>
              <label className="form-label">Contact Email</label>
              <input
                type="email"
                value={tenantForm.contact_email}
                onChange={(e) => setTenantForm({ ...tenantForm, contact_email: e.target.value })}
                className="form-input"
              />
            </div>
            
            <div>
              <label className="form-label">Contact Phone</label>
              <input
                type="text"
                value={tenantForm.contact_phone}
                onChange={(e) => setTenantForm({ ...tenantForm, contact_phone: e.target.value })}
                className="form-input"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="form-label">Plan</label>
                <select
                  value={tenantForm.plan}
                  onChange={(e) => setTenantForm({ ...tenantForm, plan: e.target.value })}
                  className="form-input"
                >
                  <option value="free">Free</option>
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              
              <div>
                <label className="form-label">Max Users</label>
                <input
                  type="number"
                  value={tenantForm.max_users}
                  onChange={(e) => setTenantForm({ ...tenantForm, max_users: parseInt(e.target.value) })}
                  min={1}
                  className="form-input"
                />
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowEditTenant(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="btn-primary"
              >
                {formLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Create Global Template Modal */}
      <Dialog open={showCreateTemplate} onOpenChange={setShowCreateTemplate}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Global Template</DialogTitle>
            <DialogDescription>
              This template will be available for all tenants
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateGlobalTemplate} className="space-y-4">
            {formError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <div className="text-sm text-red-600">{formError}</div>
              </div>
            )}
            
            <div>
              <label className="form-label">Template Name *</label>
              <input
                type="text"
                value={templateForm.name}
                onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                required
                className="form-input"
              />
            </div>
            
            <div>
              <label className="form-label">Description</label>
              <textarea
                value={templateForm.description}
                onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
                className="form-input"
                rows={2}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="form-label">Category</label>
                <input
                  type="text"
                  value={templateForm.category}
                  onChange={(e) => setTemplateForm({ ...templateForm, category: e.target.value })}
                  className="form-input"
                />
              </div>
              
              <div>
                <label className="form-label">Estimated Hours</label>
                <input
                  type="number"
                  value={templateForm.estimated_hours}
                  onChange={(e) => setTemplateForm({ ...templateForm, estimated_hours: e.target.value })}
                  className="form-input"
                  step="0.5"
                  min="0"
                />
              </div>
            </div>
            
            {/* Sub-tasks */}
            <div className="border-t border-gray-200 pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Sub-tasks</h4>
              
              {templateForm.sub_tasks.length > 0 && (
                <div className="space-y-2 mb-4">
                  {templateForm.sub_tasks.map((st, index) => (
                    <div key={index} className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                      <span className="flex-1 text-sm">{st.title}</span>
                      <span className="text-xs text-gray-500">{st.estimated_hours}h</span>
                      <button
                        type="button"
                        onClick={() => removeSubTask(index)}
                        className="text-red-500 hover:text-red-700"
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
                  className="form-input flex-1"
                  placeholder="Sub-task title"
                />
                <input
                  type="number"
                  value={newSubTask.estimated_hours}
                  onChange={(e) => setNewSubTask({ ...newSubTask, estimated_hours: e.target.value })}
                  className="form-input w-20"
                  placeholder="Hours"
                  step="0.5"
                  min="0"
                />
                <select
                  value={newSubTask.priority}
                  onChange={(e) => setNewSubTask({ ...newSubTask, priority: e.target.value })}
                  className="form-input w-24"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <button
                  type="button"
                  onClick={addSubTask}
                  className="btn-secondary"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowCreateTemplate(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="btn-primary"
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
