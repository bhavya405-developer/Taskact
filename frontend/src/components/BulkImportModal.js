import React, { useState, useCallback } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const BulkImportModal = ({ isOpen, onClose, type, onImportComplete }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  }, []);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file) => {
    const allowedTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv'
    ];
    
    if (!allowedTypes.includes(file.type) && !file.name.endsWith('.xlsx') && !file.name.endsWith('.xls') && !file.name.endsWith('.csv')) {
      alert('Please select an Excel (.xlsx, .xls) or CSV (.csv) file');
      return;
    }
    
    setSelectedFile(file);
    setImportResult(null);
  };

  const downloadTemplate = async () => {
    try {
      const endpoint = type === 'categories' ? '/categories/template' : '/clients/template';
      const filename = type === 'categories' ? 'categories_template.xlsx' : 'clients_template.xlsx';
      
      const response = await axios.get(`${API}${endpoint}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading template:', error);
      alert('Failed to download template');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const endpoint = type === 'categories' ? '/categories/bulk-import' : '/clients/bulk-import';
      const response = await axios.post(`${API}${endpoint}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setImportResult(response.data);
      
      if (response.data.success_count > 0) {
        onImportComplete();
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      alert(error.response?.data?.detail || 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const resetModal = () => {
    setSelectedFile(null);
    setImportResult(null);
    setDragActive(false);
    onClose();
  };

  if (!isOpen) return null;

  const typeName = type === 'categories' ? 'Categories' : 'Clients';
  const typeIcon = type === 'categories' ? '📂' : '🏢';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={resetModal}>
      <div 
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="bulk-import-modal"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center">
            <span className="text-2xl mr-3">{typeIcon}</span>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Bulk Import {typeName}
              </h2>
              <p className="text-sm text-gray-600">Upload Excel or CSV file to import multiple {type}</p>
            </div>
          </div>
          <button
            onClick={resetModal}
            className="text-gray-400 hover:text-gray-600 text-2xl"
            data-testid="close-modal"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {!importResult ? (
            <>
              {/* Step 1: Download Template */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <span className="text-blue-600 font-bold">1.</span>
                  </div>
                  <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-blue-800">Download Template</h3>
                    <p className="text-sm text-blue-700 mt-1">
                      Start by downloading our Excel template with the correct format and sample data.
                    </p>
                    <button
                      onClick={downloadTemplate}
                      className="mt-2 btn-secondary text-sm"
                      data-testid="download-template-button"
                    >
                      📥 Download {typeName} Template
                    </button>
                  </div>
                </div>
              </div>

              {/* Step 2: Upload File */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <span className="text-gray-600 font-bold">2.</span>
                  </div>
                  <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-gray-800">Upload Filled Template</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Fill the template with your data and upload it here.
                    </p>
                    
                    {/* File Upload Area */}
                    <div className="mt-4">
                      <div
                        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                          dragActive 
                            ? 'border-blue-400 bg-blue-50' 
                            : selectedFile
                            ? 'border-green-400 bg-green-50'
                            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
                        }`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        data-testid="file-drop-area"
                      >
                        {selectedFile ? (
                          <div className="text-green-600">
                            <svg className="mx-auto h-12 w-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p className="font-medium">File Selected: {selectedFile.name}</p>
                            <p className="text-sm">Size: {(selectedFile.size / 1024).toFixed(1)} KB</p>
                          </div>
                        ) : (
                          <div className="text-gray-600">
                            <svg className="mx-auto h-12 w-12 mb-3" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                              <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            <p className="font-medium">Drag and drop your file here</p>
                            <p className="text-sm mt-1">or click to browse</p>
                            <p className="text-xs text-gray-500 mt-2">Supports: .xlsx, .xls, .csv</p>
                          </div>
                        )}
                        
                        <input
                          type="file"
                          accept=".xlsx,.xls,.csv"
                          onChange={handleFileSelect}
                          className="hidden"
                          data-testid="file-input"
                        />
                        
                        {!selectedFile && (
                          <button
                            type="button"
                            onClick={() => document.querySelector('[data-testid="file-input"]').click()}
                            className="mt-3 btn-secondary text-sm"
                            data-testid="browse-files-button"
                          >
                            Browse Files
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                <button
                  onClick={resetModal}
                  className="btn-secondary"
                  data-testid="cancel-import-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                  className="btn-primary flex items-center"
                  data-testid="upload-file-button"
                >
                  {uploading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Importing...
                    </>
                  ) : (
                    <>
                      <span className="mr-2">📤</span>
                      Import {typeName}
                    </>
                  )}
                </button>
              </div>
            </>
          ) : (
            /* Import Results */
            <div className="space-y-4">
              <div className="text-center">
                <div className={`text-4xl mb-3 ${importResult.error_count === 0 ? 'text-green-600' : 'text-yellow-600'}`}>
                  {importResult.error_count === 0 ? '✅' : '⚠️'}
                </div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Import {importResult.error_count === 0 ? 'Completed' : 'Completed with Errors'}
                </h3>
              </div>

              {/* Summary */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-600">{importResult.success_count}</div>
                  <div className="text-sm text-green-800">Successfully Imported</div>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-red-600">{importResult.error_count}</div>
                  <div className="text-sm text-red-800">Errors</div>
                </div>
              </div>

              {/* Created Items */}
              {importResult.created_items.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Successfully Created:</h4>
                  <div className="max-h-32 overflow-y-auto bg-green-50 border border-green-200 rounded p-3">
                    <ul className="text-sm text-green-800 space-y-1">
                      {importResult.created_items.map((item, index) => (
                        <li key={index}>✓ {item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Errors */}
              {importResult.errors.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Errors:</h4>
                  <div className="max-h-32 overflow-y-auto bg-red-50 border border-red-200 rounded p-3">
                    <ul className="text-sm text-red-800 space-y-1">
                      {importResult.errors.map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                <button
                  onClick={resetModal}
                  className="btn-primary"
                  data-testid="close-results-button"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BulkImportModal;