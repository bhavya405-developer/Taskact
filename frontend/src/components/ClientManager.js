import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import BulkImportModal from './BulkImportModal';
import { Upload, Plus, Edit, Trash2, Building2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ClientManager = () => {
  const { isPartner } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    company_type: '',
    industry: '',
    contact_person: '',
    email: '',
    phone: '',
    address: '',
    notes: ''
  });

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/clients`);
      setClients(response.data);
    } catch (error) {
      console.error('Error fetching clients:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (editingClient) {
        await axios.put(`${API}/clients/${editingClient.id}`, formData);
      } else {
        await axios.post(`${API}/clients`, formData);
      }
      
      await fetchClients();
      handleCancel();
    } catch (error) {
      console.error('Error saving client:', error);
      alert(error.response?.data?.detail || 'Failed to save client');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (client) => {
    setEditingClient(client);
    setFormData({
      name: client.name,
      company_type: client.company_type || '',
      industry: client.industry || '',
      contact_person: client.contact_person || '',
      email: client.email || '',
      phone: client.phone || '',
      address: client.address || '',
      notes: client.notes || ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (clientId) => {
    if (!window.confirm('Are you sure you want to delete this client?')) {
      return;
    }

    try {
      await axios.delete(`${API}/clients/${clientId}`);
      await fetchClients();
    } catch (error) {
      console.error('Error deleting client:', error);
      alert(error.response?.data?.detail || 'Failed to delete client');
    }
  };

  const handleCancel = () => {
    setShowAddForm(false);
    setEditingClient(null);
    setFormData({
      name: '',
      company_type: '',
      industry: '',
      contact_person: '',
      email: '',
      phone: '',
      address: '',
      notes: ''
    });
  };

  const companyTypes = [
    'Corporation',
    'LLC',
    'Partnership',
    'Individual',
    'Non-Profit',
    'Government',
    'Startup',
    'Trust',
    'Estate'
  ];

  const industries = [
    'Technology',
    'Healthcare',
    'Finance',
    'Manufacturing',
    'Retail',
    'Real Estate',
    'Education',
    'Entertainment',
    'Energy',
    'Transportation',
    'Consulting',
    'Legal Services',
    'Other'
  ];

  if (!isPartner()) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Access Denied</h3>
        <p className="text-gray-600">Only partners can manage clients.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center">
          <Building2 size={32} className="text-blue-600 mr-3" />
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Client Management</h2>
            <p className="mt-2 text-gray-600">Manage your client database</p>
          </div>
        </div>
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button
            onClick={() => setShowBulkImport(true)}
            className="btn-secondary"
            data-testid="bulk-import-clients-button"
          >
            📤 Bulk Import
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="btn-primary"
            data-testid="add-client-button"
          >
            Add Client
          </button>
        </div>
      </div>

      {/* Add/Edit Client Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-fade-in">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            {editingClient ? 'Edit Client' : 'Add New Client'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div>
              <h4 className="text-md font-medium text-gray-900 mb-3">Basic Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Client Name *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="client-name-input"
                    required
                    placeholder="e.g., TechCorp Inc."
                  />
                </div>
                <div>
                  <label className="form-label">Company Type</label>
                  <select
                    name="company_type"
                    value={formData.company_type}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="company-type-select"
                  >
                    <option value="">Select type...</option>
                    {companyTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="form-label">Industry</label>
                  <select
                    name="industry"
                    value={formData.industry}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="industry-select"
                  >
                    <option value="">Select industry...</option>
                    {industries.map(industry => (
                      <option key={industry} value={industry}>{industry}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="form-label">Contact Person</label>
                  <input
                    type="text"
                    name="contact_person"
                    value={formData.contact_person}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="contact-person-input"
                    placeholder="Primary contact name"
                  />
                </div>
              </div>
            </div>

            {/* Contact Information */}
            <div>
              <h4 className="text-md font-medium text-gray-900 mb-3">Contact Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Email</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="client-email-input"
                    placeholder="client@company.com"
                  />
                </div>
                <div>
                  <label className="form-label">Phone</label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    className="form-input"
                    data-testid="client-phone-input"
                    placeholder="+1 (555) 123-4567"
                  />
                </div>
              </div>
              <div className="mt-4">
                <label className="form-label">Address</label>
                <textarea
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  rows={3}
                  className="form-input resize-none"
                  data-testid="client-address-input"
                  placeholder="Street address, city, state, postal code"
                />
              </div>
            </div>

            {/* Additional Notes */}
            <div>
              <label className="form-label">Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                rows={3}
                className="form-input resize-none"
                data-testid="client-notes-input"
                placeholder="Additional notes about the client..."
              />
            </div>

            <div className="flex gap-3 pt-4 border-t border-gray-200">
              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
                data-testid="save-client-button"
              >
                {loading ? 'Saving...' : (editingClient ? 'Update Client' : 'Add Client')}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="btn-secondary"
                data-testid="cancel-client-button"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Clients List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {loading && clients.length === 0 ? (
          <div className="p-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading clients...</p>
          </div>
        ) : clients.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-4xl mb-4">🏢</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No clients yet</h3>
            <p className="text-gray-600 mb-4">Add your first client to get started</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="btn-primary"
            >
              Add First Client
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            <div className="px-6 py-4 bg-gray-50">
              <h3 className="text-lg font-semibold text-gray-900">
                All Clients ({clients.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="table-header">Client Name</th>
                    <th className="table-header">Type</th>
                    <th className="table-header">Industry</th>
                    <th className="table-header">Contact</th>
                    <th className="table-header">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {clients.map((client) => (
                    <tr key={client.id} className="hover:bg-gray-50 transition-colors" data-testid={`client-row-${client.id}`}>
                      <td className="table-cell">
                        <div>
                          <div className="font-medium text-gray-900">{client.name}</div>
                          {client.contact_person && (
                            <div className="text-sm text-gray-600">Contact: {client.contact_person}</div>
                          )}
                        </div>
                      </td>
                      <td className="table-cell">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {client.company_type || 'Not specified'}
                        </span>
                      </td>
                      <td className="table-cell text-gray-600">
                        {client.industry || 'Not specified'}
                      </td>
                      <td className="table-cell">
                        <div className="text-sm">
                          {client.email && (
                            <div className="text-gray-900">{client.email}</div>
                          )}
                          {client.phone && (
                            <div className="text-gray-600">{client.phone}</div>
                          )}
                        </div>
                      </td>
                      <td className="table-cell">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleEdit(client)}
                            className="text-gray-400 hover:text-blue-600 p-1"
                            data-testid={`edit-client-${client.id}`}
                            title="Edit client"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDelete(client.id)}
                            className="text-gray-400 hover:text-red-600 p-1"
                            data-testid={`delete-client-${client.id}`}
                            title="Delete client"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Bulk Import Modal */}
      <BulkImportModal
        isOpen={showBulkImport}
        onClose={() => setShowBulkImport(false)}
        type="clients"
        onImportComplete={fetchClients}
      />
    </div>
  );
};

export default ClientManager;