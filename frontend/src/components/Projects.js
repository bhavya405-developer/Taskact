import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import {
  FolderKanban, Plus, Search, ChevronDown, ChevronRight,
  User, Calendar, Clock, CheckCircle, XCircle, PlayCircle,
  PauseCircle, MoreVertical, AlertTriangle, FileText, Copy,
  Trash2, UserPlus, Filter, Save, Users, Edit2, Eye
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const statusConfig = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700', icon: FileText },
  active: { label: 'Active', color: 'bg-blue-100 text-blue-700', icon: PlayCircle },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  on_hold: { label: 'On Hold', color: 'bg-orange-100 text-orange-700', icon: PauseCircle },
};

const priorityConfig = {
  high: { color: 'bg-red-100 text-red-700', dot: 'bg-red-500' },
  medium: { color: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  low: { color: 'bg-green-100 text-green-700', dot: 'bg-green-500' },
};

const Projects = ({ users = [], clients = [], categories = [] }) => {
  const { isPartner, isSuperAdmin } = useAuth();
  const [projects, setProjects] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expandedProjects, setExpandedProjects] = useState(new Set());
  const [activeTab, setActiveTab] = useState('projects');
  
  // Modal states
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showCreateTemplate, setShowCreateTemplate] = useState(false);
  const [showProjectDetail, setShowProjectDetail] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  
  // Form states
  const [projectForm, setProjectForm] = useState({
    name: '',
    description: '',
    client_id: '',
    category: '',
    due_date: '',
    template_id: '',
    save_as_template: false,
    template_name: '',
    tasks: []
  });
  
  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    client_id: '',
    category: '',
    tasks: []
  });
  
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium',
    category: '',
    assignee_id: '',
    due_date: ''
  });
  
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);

  // Fetch clients and categories
  const [clientsList, setClientsList] = useState([]);
  const [categoriesList, setCategoriesList] = useState([]);

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/clients`);
      setClientsList(response.data);
    } catch (error) {
      console.error('Error fetching clients:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/categories`);
      setCategoriesList(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchTemplates();
    fetchClients();
    fetchCategories();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/projects`);
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/project-templates`);
      setTemplates(response.data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError('');

    try {
      // Validate
      if (!projectForm.name) {
        throw new Error('Project name is required');
      }
      if (!projectForm.due_date) {
        throw new Error('Due date is required');
      }
      if (projectForm.tasks.length === 0 && !projectForm.template_id) {
        throw new Error('At least one task is required');
      }

      const payload = {
        name: projectForm.name,
        description: projectForm.description,
        client_id: projectForm.client_id || null,
        category: projectForm.category || null,
        due_date: projectForm.due_date,
        template_id: projectForm.template_id || null,
        tasks: projectForm.tasks,
        save_as_template: projectForm.save_as_template,
        template_name: projectForm.template_name || null
      };

      await axios.post(`${API_URL}/api/projects`, payload);
      
      setShowCreateProject(false);
      resetProjectForm();
      fetchProjects();
      fetchTemplates();
    } catch (error) {
      setFormError(error.response?.data?.detail || error.message || 'Failed to create project');
    } finally {
      setFormLoading(false);
    }
  };

  const handleCreateTemplate = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError('');

    try {
      if (!templateForm.name) {
        throw new Error('Template name is required');
      }
      if (templateForm.tasks.length === 0) {
        throw new Error('At least one task is required');
      }

      const payload = {
        name: templateForm.name,
        description: templateForm.description,
        client_id: templateForm.client_id || null,
        category: templateForm.category || null,
        tasks: templateForm.tasks.map((t, idx) => ({
          title: t.title,
          description: t.description,
          priority: t.priority,
          category: t.category,
          order: idx
        }))
      };

      await axios.post(`${API_URL}/api/project-templates`, payload);
      
      setShowCreateTemplate(false);
      resetTemplateForm();
      fetchTemplates();
    } catch (error) {
      setFormError(error.response?.data?.detail || error.message || 'Failed to create template');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (!window.confirm('Delete this project and all its tasks?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/projects/${projectId}`);
      fetchProjects();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete project');
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm('Delete this template?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/project-templates/${templateId}`);
      fetchTemplates();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete template');
    }
  };

  const handleViewProject = async (projectId) => {
    try {
      const response = await axios.get(`${API_URL}/api/projects/${projectId}`);
      setSelectedProject(response.data);
      setShowProjectDetail(true);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to load project');
    }
  };

  const addTaskToForm = () => {
    if (!newTask.title) return;
    
    setProjectForm(prev => ({
      ...prev,
      tasks: [...prev.tasks, { ...newTask }]
    }));
    
    setNewTask({
      title: '',
      description: '',
      priority: 'medium',
      category: '',
      assignee_id: '',
      due_date: ''
    });
  };

  const addTaskToTemplateForm = () => {
    if (!newTask.title) return;
    
    setTemplateForm(prev => ({
      ...prev,
      tasks: [...prev.tasks, {
        title: newTask.title,
        description: newTask.description,
        priority: newTask.priority,
        category: newTask.category
      }]
    }));
    
    setNewTask({
      title: '',
      description: '',
      priority: 'medium',
      category: '',
      assignee_id: '',
      due_date: ''
    });
  };

  const removeTaskFromForm = (index) => {
    setProjectForm(prev => ({
      ...prev,
      tasks: prev.tasks.filter((_, i) => i !== index)
    }));
  };

  const removeTaskFromTemplateForm = (index) => {
    setTemplateForm(prev => ({
      ...prev,
      tasks: prev.tasks.filter((_, i) => i !== index)
    }));
  };

  const handleTemplateSelect = (template) => {
    setProjectForm(prev => ({
      ...prev,
      template_id: template.id,
      category: template.category || prev.category,
      client_id: template.client_id || prev.client_id,
      tasks: template.tasks?.map(t => ({
        title: t.title,
        description: t.description,
        priority: t.priority || 'medium',
        category: t.category || template.category,
        assignee_id: '',
        due_date: ''
      })) || []
    }));
  };

  const resetProjectForm = () => {
    setProjectForm({
      name: '',
      description: '',
      client_id: '',
      category: '',
      due_date: '',
      template_id: '',
      save_as_template: false,
      template_name: '',
      tasks: []
    });
    setNewTask({
      title: '',
      description: '',
      priority: 'medium',
      category: '',
      assignee_id: '',
      due_date: ''
    });
    setFormError('');
  };

  const resetTemplateForm = () => {
    setTemplateForm({
      name: '',
      description: '',
      client_id: '',
      category: '',
      tasks: []
    });
    setFormError('');
  };

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         project.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const filteredTemplates = templates.filter(template =>
    template.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getClientName = (clientId) => {
    const client = clientsList.find(c => c.id === clientId);
    return client?.name || '';
  };
  
  // Use internal state for clients and categories (fallback to props for backward compatibility)
  const effectiveClients = clientsList.length > 0 ? clientsList : clients;
  const effectiveCategories = categoriesList.length > 0 ? categoriesList : categories;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center">
          <FolderKanban className="h-8 w-8 text-blue-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
            <p className="text-sm text-gray-500">Manage projects and templates</p>
          </div>
        </div>
        
        {isPartner() && (
          <div className="flex gap-2">
            <button
              onClick={() => { resetTemplateForm(); setShowCreateTemplate(true); }}
              className="flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
              data-testid="create-template-btn"
            >
              <FileText className="h-4 w-4 mr-2" />
              New Template
            </button>
            <button
              onClick={() => { resetProjectForm(); setShowCreateProject(true); }}
              className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              data-testid="create-project-btn"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('projects')}
            className={`py-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'projects'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FolderKanban className="h-4 w-4 inline mr-2" />
            Projects ({projects.length})
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={`py-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'templates'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <FileText className="h-4 w-4 inline mr-2" />
            Templates ({templates.length})
          </button>
        </nav>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder={`Search ${activeTab}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        {activeTab === 'projects' && (
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="on_hold">On Hold</option>
          </select>
        )}
      </div>

      {/* Projects Tab */}
      {activeTab === 'projects' && (
        <div className="grid gap-4">
          {filteredProjects.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg border">
              <FolderKanban className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No projects found</h3>
              <p className="text-gray-500 mt-1">Create a new project to get started</p>
            </div>
          ) : (
            filteredProjects.map(project => {
              const status = statusConfig[project.status] || statusConfig.active;
              const StatusIcon = status.icon;
              
              return (
                <div
                  key={project.id}
                  className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-medium text-gray-900">{project.name}</h3>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${status.color}`}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {status.label}
                        </span>
                      </div>
                      
                      {project.description && (
                        <p className="text-sm text-gray-600 mb-3">{project.description}</p>
                      )}
                      
                      <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                        {project.client_name && (
                          <span className="flex items-center">
                            <User className="h-4 w-4 mr-1" />
                            {project.client_name}
                          </span>
                        )}
                        {project.due_date && (
                          <span className="flex items-center">
                            <Calendar className="h-4 w-4 mr-1" />
                            {new Date(project.due_date).toLocaleDateString()}
                          </span>
                        )}
                        <span className="flex items-center">
                          <CheckCircle className="h-4 w-4 mr-1" />
                          {project.completed_tasks || 0}/{project.total_tasks || 0} tasks
                        </span>
                      </div>
                      
                      {/* Progress bar */}
                      {project.total_tasks > 0 && (
                        <div className="mt-3">
                          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                            <span>Progress</span>
                            <span>{Math.round(project.progress || 0)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all"
                              style={{ width: `${project.progress || 0}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {project.can_edit && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="p-1 hover:bg-gray-100 rounded">
                            <MoreVertical className="h-5 w-5 text-gray-400" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleViewProject(project.id)}>
                            <Eye className="h-4 w-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleDeleteProject(project.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.length === 0 ? (
            <div className="col-span-full text-center py-12 bg-white rounded-lg border">
              <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No templates found</h3>
              <p className="text-gray-500 mt-1">Create a template to reuse project structures</p>
            </div>
          ) : (
            filteredTemplates.map(template => (
              <div
                key={template.id}
                className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-medium text-gray-900">{template.name}</h3>
                    {template.scope === 'global' && (
                      <span className="text-xs text-purple-600">Global Template</span>
                    )}
                  </div>
                  
                  {template.can_edit && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="p-1 hover:bg-gray-100 rounded">
                          <MoreVertical className="h-5 w-5 text-gray-400" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="text-red-600"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
                
                {template.description && (
                  <p className="text-sm text-gray-600 mb-3 line-clamp-2">{template.description}</p>
                )}
                
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">
                    {template.tasks?.length || 0} tasks
                  </span>
                  
                  <button
                    onClick={() => {
                      resetProjectForm();
                      handleTemplateSelect(template);
                      setShowCreateProject(true);
                    }}
                    className="text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Use Template
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create Project Modal */}
      <Dialog open={showCreateProject} onOpenChange={setShowCreateProject}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
            <DialogDescription>
              Create a project with tasks. You can start from a template or define tasks directly.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateProject} className="space-y-4">
            {formError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-600">{formError}</p>
              </div>
            )}
            
            {/* Project Details */}
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Project Name *</label>
                <input
                  type="text"
                  value={projectForm.name}
                  onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })}
                  required
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter project name"
                />
              </div>
              
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={projectForm.description}
                  onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Project description"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
                <select
                  value={projectForm.client_id}
                  onChange={(e) => setProjectForm({ ...projectForm, client_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Client</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>{client.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={projectForm.category}
                  onChange={(e) => setProjectForm({ ...projectForm, category: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Category</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.name}>{cat.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Due Date *</label>
                <input
                  type="date"
                  value={projectForm.due_date}
                  onChange={(e) => setProjectForm({ ...projectForm, due_date: e.target.value })}
                  required
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Template (Optional)</label>
                <select
                  value={projectForm.template_id}
                  onChange={(e) => {
                    const template = templates.find(t => t.id === e.target.value);
                    if (template) {
                      handleTemplateSelect(template);
                    } else {
                      setProjectForm({ ...projectForm, template_id: '', tasks: [] });
                    }
                  }}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Start from scratch</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name} ({t.tasks?.length || 0} tasks)</option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Tasks Section */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Tasks</h4>
              
              {/* Existing tasks */}
              {projectForm.tasks.length > 0 && (
                <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
                  {projectForm.tasks.map((task, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                      <div className="flex-1">
                        <span className="text-sm font-medium">{task.title}</span>
                        {task.assignee_id && (
                          <span className="text-xs text-gray-500 ml-2">
                            → {users.find(u => u.id === task.assignee_id)?.name || 'Unknown'}
                          </span>
                        )}
                      </div>
                      <select
                        value={task.assignee_id}
                        onChange={(e) => {
                          const newTasks = [...projectForm.tasks];
                          newTasks[idx].assignee_id = e.target.value;
                          setProjectForm({ ...projectForm, tasks: newTasks });
                        }}
                        className="text-xs px-2 py-1 border rounded"
                      >
                        <option value="">Assign to...</option>
                        {users.map(user => (
                          <option key={user.id} value={user.id}>{user.name}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => removeTaskFromForm(idx)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Add new task */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  placeholder="Task title"
                  className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={newTask.assignee_id}
                  onChange={(e) => setNewTask({ ...newTask, assignee_id: e.target.value })}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="">Assign to</option>
                  {users.map(user => (
                    <option key={user.id} value={user.id}>{user.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addTaskToForm}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>
            
            {/* Save as Template Option */}
            <div className="border-t pt-4">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={projectForm.save_as_template}
                  onChange={(e) => setProjectForm({ ...projectForm, save_as_template: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Save as template for future use</span>
              </label>
              
              {projectForm.save_as_template && (
                <input
                  type="text"
                  value={projectForm.template_name}
                  onChange={(e) => setProjectForm({ ...projectForm, template_name: e.target.value })}
                  placeholder="Template name (optional)"
                  className="mt-2 w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              )}
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowCreateProject(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
              >
                {formLoading ? 'Creating...' : 'Create Project'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Create Template Modal */}
      <Dialog open={showCreateTemplate} onOpenChange={setShowCreateTemplate}>
        <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Project Template</DialogTitle>
            <DialogDescription>
              Define task blueprints that can be reused across projects.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateTemplate} className="space-y-4">
            {formError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-600">{formError}</p>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Template Name *</label>
              <input
                type="text"
                value={templateForm.name}
                onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                required
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={templateForm.description}
                onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Default Category</label>
                <select
                  value={templateForm.category}
                  onChange={(e) => setTemplateForm({ ...templateForm, category: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Category</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.name}>{cat.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Default Client</label>
                <select
                  value={templateForm.client_id}
                  onChange={(e) => setTemplateForm({ ...templateForm, client_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Client</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>{client.name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Tasks */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Task Blueprints</h4>
              
              {templateForm.tasks.length > 0 && (
                <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
                  {templateForm.tasks.map((task, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                      <span className="flex-1 text-sm">{task.title}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${priorityConfig[task.priority]?.color || 'bg-gray-100'}`}>
                        {task.priority}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeTaskFromTemplateForm(idx)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  placeholder="Task title"
                  className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={newTask.priority}
                  onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <button
                  type="button"
                  onClick={addTaskToTemplateForm}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>
            
            <DialogFooter>
              <button
                type="button"
                onClick={() => setShowCreateTemplate(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
              >
                {formLoading ? 'Creating...' : 'Create Template'}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Project Detail Modal */}
      <Dialog open={showProjectDetail} onOpenChange={setShowProjectDetail}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedProject?.name}</DialogTitle>
            <DialogDescription>
              {selectedProject?.description || 'Project details and tasks'}
            </DialogDescription>
          </DialogHeader>
          
          {selectedProject && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Client:</span>
                  <span className="ml-2 font-medium">{selectedProject.client_name || '-'}</span>
                </div>
                <div>
                  <span className="text-gray-500">Category:</span>
                  <span className="ml-2 font-medium">{selectedProject.category || '-'}</span>
                </div>
                <div>
                  <span className="text-gray-500">Due Date:</span>
                  <span className="ml-2 font-medium">
                    {selectedProject.due_date ? new Date(selectedProject.due_date).toLocaleDateString() : '-'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Progress:</span>
                  <span className="ml-2 font-medium">
                    {selectedProject.completed_tasks}/{selectedProject.total_tasks} tasks ({Math.round(selectedProject.progress || 0)}%)
                  </span>
                </div>
              </div>
              
              <div className="border-t pt-4">
                <h4 className="font-medium mb-3">Tasks</h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {selectedProject.tasks?.map(task => (
                    <div
                      key={task.id}
                      className={`p-3 rounded-lg border ${
                        task.status === 'completed' ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {task.status === 'completed' ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <Clock className="h-4 w-4 text-gray-400" />
                          )}
                          <span className={task.status === 'completed' ? 'line-through text-gray-500' : ''}>
                            {task.title}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {task.assignee_name || 'Unassigned'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Projects;
