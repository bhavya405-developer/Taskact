import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import {
  FolderKanban, Plus, Search, ChevronDown, ChevronRight,
  User, Calendar, Clock, CheckCircle, XCircle, PlayCircle,
  PauseCircle, MoreVertical, AlertTriangle, FileText, Copy,
  Trash2, UserPlus, Filter
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
  ready: { label: 'Ready', color: 'bg-blue-100 text-blue-700', icon: CheckCircle },
  allocated: { label: 'Allocated', color: 'bg-purple-100 text-purple-700', icon: UserPlus },
  in_progress: { label: 'In Progress', color: 'bg-yellow-100 text-yellow-700', icon: PlayCircle },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  on_hold: { label: 'On Hold', color: 'bg-orange-100 text-orange-700', icon: PauseCircle },
};

const priorityConfig = {
  high: { color: 'bg-red-100 text-red-700', dot: 'bg-red-500' },
  medium: { color: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  low: { color: 'bg-green-100 text-green-700', dot: 'bg-green-500' },
};

const Projects = ({ users }) => {
  const { isPartner } = useAuth();
  const [projects, setProjects] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expandedProjects, setExpandedProjects] = useState(new Set());
  
  // Modal states
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showAllocate, setShowAllocate] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  
  // Form states
  const [projectForm, setProjectForm] = useState({
    title: '',
    description: '',
    client_name: '',
    category: '',
    priority: 'medium',
    due_date: '',
    estimated_hours: '',
    assignee_id: '',
    sub_tasks: []
  });
  const [newSubTask, setNewSubTask] = useState({ title: '', estimated_hours: '', priority: 'medium' });
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    fetchProjects();
    fetchTemplates();
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

  const toggleProjectExpand = (projectId) => {
    const newExpanded = new Set(expandedProjects);
    if (newExpanded.has(projectId)) {
      newExpanded.delete(projectId);
    } else {
      newExpanded.add(projectId);
    }
    setExpandedProjects(newExpanded);
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError('');

    try {
      const payload = {
        ...projectForm,
        estimated_hours: projectForm.estimated_hours ? parseFloat(projectForm.estimated_hours) : null,
        assignee_id: projectForm.assignee_id || null,
        sub_tasks: projectForm.sub_tasks.map((st, i) => ({
          ...st,
          order: i,
          estimated_hours: st.estimated_hours ? parseFloat(st.estimated_hours) : null
        }))
      };

      await axios.post(`${API_URL}/api/projects`, payload);
      setShowCreateProject(false);
      resetProjectForm();
      fetchProjects();
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Failed to create project');
    } finally {
      setFormLoading(false);
    }
  };

  const handleUseTemplate = async (template) => {
    setSelectedTemplate(template);
    setProjectForm({
      title: '',
      description: template.description || '',
      client_name: '',
      category: template.category || '',
      priority: 'medium',
      due_date: '',
      estimated_hours: template.estimated_hours || '',
      assignee_id: '',
      sub_tasks: template.sub_tasks.map(st => ({
        title: st.title,
        description: st.description || '',
        estimated_hours: st.estimated_hours || '',
        priority: st.priority || 'medium'
      }))
    });
    setShowTemplates(false);
    setShowCreateProject(true);
  };

  const handleAllocate = async (projectId, assigneeId) => {
    try {
      await axios.post(`${API_URL}/api/projects/${projectId}/allocate?assignee_id=${assigneeId}`);
      fetchProjects();
      setShowAllocate(false);
      setSelectedProject(null);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to allocate project');
    }
  };

  const handleUpdateSubTask = async (projectId, subtaskId, updates) => {
    try {
      await axios.put(`${API_URL}/api/projects/${projectId}/subtasks/${subtaskId}`, updates);
      fetchProjects();
    } catch (error) {
      console.error('Error updating subtask:', error);
    }
  };

  const addSubTask = () => {
    if (!newSubTask.title.trim()) return;
    setProjectForm(prev => ({
      ...prev,
      sub_tasks: [...prev.sub_tasks, { ...newSubTask }]
    }));
    setNewSubTask({ title: '', estimated_hours: '', priority: 'medium' });
  };

  const removeSubTask = (index) => {
    setProjectForm(prev => ({
      ...prev,
      sub_tasks: prev.sub_tasks.filter((_, i) => i !== index)
    }));
  };

  const resetProjectForm = () => {
    setProjectForm({
      title: '',
      description: '',
      client_name: '',
      category: '',
      priority: 'medium',
      due_date: '',
      estimated_hours: '',
      assignee_id: '',
      sub_tasks: []
    });
    setSelectedTemplate(null);
  };

  const filteredProjects = projects.filter(project => {
    const matchesSearch = 
      project.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (project.client_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (project.assignee_name || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center">
            <FolderKanban className="h-7 w-7 mr-2 text-indigo-600" />
            Projects
          </h1>
          <p className="text-gray-500 mt-1">Manage projects with sub-tasks and templates</p>
        </div>
        
        {isPartner() && (
          <div className="flex gap-2">
            <button
              onClick={() => setShowTemplates(true)}
              className="btn-secondary flex items-center"
              data-testid="use-template-button"
            >
              <Copy className="h-4 w-4 mr-2" />
              Use Template
            </button>
            <button
              onClick={() => { resetProjectForm(); setShowCreateProject(true); }}
              className="btn-primary flex items-center"
              data-testid="create-project-button"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10 w-full"
            data-testid="search-projects"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="form-input"
            data-testid="status-filter"
          >
            <option value="all">All Status</option>
            {Object.entries(statusConfig).map(([value, config]) => (
              <option key={value} value={value}>{config.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Projects List */}
      <div className="space-y-4">
        {filteredProjects.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <FolderKanban className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No projects found</h3>
            <p className="text-gray-500">
              {searchTerm || statusFilter !== 'all' 
                ? 'Try adjusting your filters' 
                : 'Create your first project to get started'}
            </p>
          </div>
        ) : (
          filteredProjects.map((project) => {
            const isExpanded = expandedProjects.has(project.id);
            const StatusIcon = statusConfig[project.status]?.icon || FileText;
            
            return (
              <div key={project.id} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                {/* Project Header */}
                <div 
                  className="p-4 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                  onClick={() => toggleProjectExpand(project.id)}
                >
                  <div className="flex items-center flex-1 min-w-0">
                    <button className="mr-3 text-gray-400">
                      {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                    </button>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-gray-900 truncate">{project.title}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig[project.status]?.color}`}>
                          {statusConfig[project.status]?.label}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${priorityConfig[project.priority]?.color}`}>
                          {project.priority}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        {project.client_name && (
                          <span className="flex items-center">
                            <FolderKanban className="h-3.5 w-3.5 mr-1" />
                            {project.client_name}
                          </span>
                        )}
                        {project.assignee_name && (
                          <span className="flex items-center">
                            <User className="h-3.5 w-3.5 mr-1" />
                            {project.assignee_name}
                          </span>
                        )}
                        {project.due_date && (
                          <span className="flex items-center">
                            <Calendar className="h-3.5 w-3.5 mr-1" />
                            {project.due_date}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 ml-4">
                    {/* Progress Bar */}
                    <div className="w-32 hidden sm:block">
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <span>Progress</span>
                        <span>{project.progress}%</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-indigo-600 rounded-full transition-all"
                          style={{ width: `${project.progress}%` }}
                        />
                      </div>
                    </div>
                    
                    {/* Sub-tasks count */}
                    <span className="text-sm text-gray-500 whitespace-nowrap">
                      {project.sub_tasks?.filter(st => st.status === 'completed').length || 0}/
                      {project.sub_tasks?.length || 0} tasks
                    </span>
                    
                    {/* Actions */}
                    {isPartner() && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <button className="p-1 hover:bg-gray-100 rounded">
                            <MoreVertical className="h-5 w-5 text-gray-400" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {(project.status === 'draft' || project.status === 'ready') && (
                            <DropdownMenuItem 
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedProject(project);
                                setShowAllocate(true);
                              }}
                            >
                              <UserPlus className="h-4 w-4 mr-2" />
                              Allocate
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem>
                            <FileText className="h-4 w-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </div>
                
                {/* Expanded Sub-tasks */}
                {isExpanded && project.sub_tasks && project.sub_tasks.length > 0 && (
                  <div className="border-t border-gray-200 bg-gray-50 p-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Sub-tasks</h4>
                    <div className="space-y-2">
                      {project.sub_tasks.map((subtask) => (
                        <div 
                          key={subtask.id}
                          className="flex items-center justify-between bg-white p-3 rounded border border-gray-200"
                        >
                          <div className="flex items-center flex-1">
                            <button
                              onClick={() => handleUpdateSubTask(
                                project.id, 
                                subtask.id, 
                                { status: subtask.status === 'completed' ? 'pending' : 'completed' }
                              )}
                              className={`mr-3 ${
                                subtask.status === 'completed' 
                                  ? 'text-green-500' 
                                  : 'text-gray-300 hover:text-gray-400'
                              }`}
                            >
                              <CheckCircle className="h-5 w-5" />
                            </button>
                            <span className={subtask.status === 'completed' ? 'line-through text-gray-400' : 'text-gray-700'}>
                              {subtask.title}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-3 text-sm">
                            <span className={`w-2 h-2 rounded-full ${priorityConfig[subtask.priority]?.dot}`} />
                            {subtask.estimated_hours && (
                              <span className="text-gray-500 flex items-center">
                                <Clock className="h-3.5 w-3.5 mr-1" />
                                {subtask.estimated_hours}h
                              </span>
                            )}
                            {subtask.completed_by && (
                              <span className="text-gray-400 text-xs">
                                by {subtask.completed_by}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Create Project Modal */}
      <Dialog open={showCreateProject} onOpenChange={setShowCreateProject}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate ? `New Project from "${selectedTemplate.name}"` : 'Create New Project'}
            </DialogTitle>
            <DialogDescription>
              Create a project with sub-tasks. You can save it as draft or allocate directly.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateProject} className="space-y-4">
            {formError && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <div className="text-sm text-red-600">{formError}</div>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="form-label">Project Title *</label>
                <input
                  type="text"
                  value={projectForm.title}
                  onChange={(e) => setProjectForm({ ...projectForm, title: e.target.value })}
                  required
                  className="form-input"
                  placeholder="e.g., Tax Filing Q1 2026"
                  data-testid="project-title-input"
                />
              </div>
              
              <div className="col-span-2">
                <label className="form-label">Description</label>
                <textarea
                  value={projectForm.description}
                  onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
                  className="form-input"
                  rows={2}
                  placeholder="Project description..."
                />
              </div>
              
              <div>
                <label className="form-label">Client</label>
                <input
                  type="text"
                  value={projectForm.client_name}
                  onChange={(e) => setProjectForm({ ...projectForm, client_name: e.target.value })}
                  className="form-input"
                  placeholder="Client name"
                />
              </div>
              
              <div>
                <label className="form-label">Category</label>
                <input
                  type="text"
                  value={projectForm.category}
                  onChange={(e) => setProjectForm({ ...projectForm, category: e.target.value })}
                  className="form-input"
                  placeholder="e.g., Tax, Audit"
                />
              </div>
              
              <div>
                <label className="form-label">Priority</label>
                <select
                  value={projectForm.priority}
                  onChange={(e) => setProjectForm({ ...projectForm, priority: e.target.value })}
                  className="form-input"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              
              <div>
                <label className="form-label">Due Date</label>
                <input
                  type="date"
                  value={projectForm.due_date}
                  onChange={(e) => setProjectForm({ ...projectForm, due_date: e.target.value })}
                  className="form-input"
                />
              </div>
              
              <div>
                <label className="form-label">Estimated Hours</label>
                <input
                  type="number"
                  value={projectForm.estimated_hours}
                  onChange={(e) => setProjectForm({ ...projectForm, estimated_hours: e.target.value })}
                  className="form-input"
                  step="0.5"
                  min="0"
                />
              </div>
              
              <div>
                <label className="form-label">Assign To (Optional)</label>
                <select
                  value={projectForm.assignee_id}
                  onChange={(e) => setProjectForm({ ...projectForm, assignee_id: e.target.value })}
                  className="form-input"
                >
                  <option value="">Save as Draft</option>
                  {users?.filter(u => u.active).map(user => (
                    <option key={user.id} value={user.id}>{user.name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Sub-tasks */}
            <div className="border-t border-gray-200 pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Sub-tasks</h4>
              
              {/* Existing sub-tasks */}
              {projectForm.sub_tasks.length > 0 && (
                <div className="space-y-2 mb-4">
                  {projectForm.sub_tasks.map((st, index) => (
                    <div key={index} className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                      <span className="flex-1 text-sm">{st.title}</span>
                      <span className="text-xs text-gray-500">{st.estimated_hours}h</span>
                      <span className={`w-2 h-2 rounded-full ${priorityConfig[st.priority]?.dot}`} />
                      <button
                        type="button"
                        onClick={() => removeSubTask(index)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Add new sub-task */}
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
                onClick={() => { setShowCreateProject(false); resetProjectForm(); }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formLoading}
                className="btn-primary"
                data-testid="submit-create-project"
              >
                {formLoading ? 'Creating...' : (projectForm.assignee_id ? 'Create & Allocate' : 'Save as Draft')}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Templates Modal */}
      <Dialog open={showTemplates} onOpenChange={setShowTemplates}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Project Templates</DialogTitle>
            <DialogDescription>
              Select a template to create a new project
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {templates.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No templates available. Create one to reuse project structures.
              </div>
            ) : (
              templates.map((template) => (
                <div
                  key={template.id}
                  className="p-4 border border-gray-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer transition-colors"
                  onClick={() => handleUseTemplate(template)}
                  data-testid={`template-${template.id}`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900">{template.name}</h4>
                      {template.description && (
                        <p className="text-sm text-gray-500 mt-1">{template.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                        {template.category && (
                          <span className="px-2 py-0.5 bg-gray-100 rounded">{template.category}</span>
                        )}
                        <span>{template.sub_tasks?.length || 0} sub-tasks</span>
                        {template.estimated_hours && (
                          <span className="flex items-center">
                            <Clock className="h-3 w-3 mr-1" />
                            {template.estimated_hours}h
                          </span>
                        )}
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          template.scope === 'global' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                        }`}>
                          {template.scope === 'global' ? 'Global' : 'Custom'}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Allocate Modal */}
      <Dialog open={showAllocate} onOpenChange={setShowAllocate}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Allocate Project</DialogTitle>
            <DialogDescription>
              Assign "{selectedProject?.title}" to a team member
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {users?.filter(u => u.active).map((user) => (
              <div
                key={user.id}
                className="p-3 border border-gray-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer transition-colors flex items-center justify-between"
                onClick={() => handleAllocate(selectedProject?.id, user.id)}
              >
                <div className="flex items-center">
                  <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-sm font-medium mr-3">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{user.name}</div>
                    <div className="text-xs text-gray-500">{user.role}</div>
                  </div>
                </div>
                <UserPlus className="h-4 w-4 text-gray-400" />
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Projects;
