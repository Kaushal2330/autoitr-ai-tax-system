class AutoITRApp {
    constructor() {
        this.currentSection = 'home';
        this.uploadedFile = null;
        this.processedData = null; // Store the processed financial data
        this.processingSteps = [
            { id: 'step-upload', name: 'File Upload', progress: 20 },
            { id: 'step-ocr', name: 'OCR Processing', progress: 40 },
            { id: 'step-classify', name: 'AI Classification', progress: 60 },
            { id: 'step-validate', name: 'Data Validation', progress: 80 },
            { id: 'step-generate', name: 'ITR Generation', progress: 100 }
        ];
        this.currentStepIndex = 0;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupNavigation();
        this.setupFileUpload();
    }

    setupEventListeners() {
        // Get started button
        document.getElementById('get-started-btn')?.addEventListener('click', () => {
            this.navigateToSection('upload');
        });

        // Learn more button
        document.getElementById('learn-more-btn')?.addEventListener('click', () => {
            this.showNotification('Learn more about AutoITR features!', 'success');
        });

        // Form submission
        document.getElementById('upload-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFileUpload();
        });

        // Remove file button
        document.getElementById('remove-file')?.addEventListener('click', () => {
            this.removeFile();
        });
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.navigateToSection(section);
            });
        });
    }

    setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');

        // Click to upload
        uploadArea?.addEventListener('click', () => {
            fileInput?.click();
        });

        // File selection
        fileInput?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileSelection(file);
            }
        });

        // Drag and drop
        uploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea?.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelection(files[0]);
            }
        });
    }

    navigateToSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-section') === sectionName) {
                link.classList.add('active');
            }
        });

        // Update sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });

        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.add('active');
            targetSection.classList.add('fade-in');
            this.currentSection = sectionName;
        }
    }

    handleFileSelection(file) {
        // Validate file
        const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
        const maxSize = 16 * 1024 * 1024; // 16MB

        if (!validTypes.includes(file.type)) {
            this.showNotification('Please select a valid file type (PDF, PNG, JPG, JPEG)', 'error');
            return;
        }

        if (file.size > maxSize) {
            this.showNotification('File size must be less than 16MB', 'error');
            return;
        }

        this.uploadedFile = file;
        this.showFilePreview(file);
        this.enableProcessButton();
        this.showNotification('File selected successfully!', 'success');
    }

    showFilePreview(file) {
        const preview = document.getElementById('file-preview');
        const fileName = preview.querySelector('.file-name');
        const fileSize = preview.querySelector('.file-size');

        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);

        preview.style.display = 'block';
        preview.classList.add('fade-in');
    }

    removeFile() {
        this.uploadedFile = null;
        document.getElementById('file-preview').style.display = 'none';
        document.getElementById('file-input').value = '';
        this.disableProcessButton();
        this.showNotification('File removed', 'warning');
    }

    enableProcessButton() {
        const btn = document.getElementById('process-btn');
        btn.disabled = false;
        btn.classList.add('pulse');
    }

    disableProcessButton() {
        const btn = document.getElementById('process-btn');
        btn.disabled = true;
        btn.classList.remove('pulse');
    }

    async handleFileUpload() {
        if (!this.uploadedFile) {
            this.showNotification('Please select a file first', 'error');
            return;
        }

        this.showProcessingStatus();
        this.startProcessingAnimation();

        const formData = new FormData();
        formData.append('file', this.uploadedFile);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                this.completeProcessing();
                this.processedData = result.data; // Store the processed data
                this.showResults(result);
                this.showNotification('Processing completed successfully!', 'success');
                this.navigateToSection('results');
            } else if (response.ok && result.status === 'password_required') {
                // Prompt for password and attempt unlock
                const password = window.prompt('This PDF is password-protected. Enter password to continue:');
                if (!password) {
                    throw new Error('Password is required to unlock the PDF');
                }
                const unlockResp = await fetch('/unlock_pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ temp_path: result.temp_path, password })
                });
                const unlockResult = await unlockResp.json();
                if (unlockResp.ok && unlockResult.status === 'success') {
                    this.completeProcessing();
                    this.processedData = unlockResult.data; // Store the processed data
                    this.showResults(unlockResult);
                    this.showNotification('PDF unlocked and processed successfully!', 'success');
                    this.navigateToSection('results');
                } else {
                    throw new Error(unlockResult.error || 'Failed to unlock PDF');
                }
            } else {
                throw new Error(result.error || 'Processing failed');
            }

        } catch (error) {
            this.showProcessingError(error.message);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    showProcessingStatus() {
        const status = document.getElementById('processing-status');
        status.style.display = 'block';
        status.classList.add('fade-in');
        this.currentStepIndex = 0;
    }

    startProcessingAnimation() {
        const progressFill = document.getElementById('progress-fill');

        this.processingSteps.forEach((step, index) => {
            setTimeout(() => {
                // Update progress bar
                progressFill.style.width = `${step.progress}%`;

                // Update step status
                this.updateProcessingStep(index);

                this.currentStepIndex = index;
            }, index * 2000);
        });
    }

    updateProcessingStep(index) {
        // Remove active class from all steps
        document.querySelectorAll('.processing-step').forEach(step => {
            step.classList.remove('active');
        });

        // Add active class to current step
        const currentStep = document.getElementById(this.processingSteps[index].id);
        if (currentStep) {
            currentStep.classList.add('active');
        }
    }

    completeProcessing() {
        // Mark all steps as complete
        document.querySelectorAll('.processing-step').forEach(step => {
            step.classList.add('active');
        });

        document.getElementById('progress-fill').style.width = '100%';
    }

    showProcessingError(message) {
        const status = document.getElementById('processing-status');
        const header = status.querySelector('.processing-header');

        header.innerHTML = `
            <h3 style="color: var(--error-color);">Processing Failed</h3>
            <p style="color: var(--error-color);">${message}</p>
        `;

        // Reset progress bar
        document.getElementById('progress-fill').style.width = '0%';

        // Reset steps
        document.querySelectorAll('.processing-step').forEach(step => {
            step.classList.remove('active');
        });
    }

    showResults(data) {
        const resultsContent = document.getElementById('results-content');

        if (!data || !data.data) {
            resultsContent.innerHTML = '<p>No results to display</p>';
            return;
        }

        const result = data.data;

        resultsContent.innerHTML = `
            <div class="results-grid">
                <!-- Account Information -->
                <div class="result-card">
                    <div class="result-header">
                        <i class="fas fa-university"></i>
                        <h3>Account Information</h3>
                    </div>
                    <div class="result-content">
                        <div class="info-item">
                            <span class="info-label">Account Number:</span>
                            <span class="info-value">${result.account_info?.account_number || 'Not detected'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Account Holder:</span>
                            <span class="info-value">${result.account_info?.holder_name || 'Not detected'}</span>
                        </div>
                    </div>
                </div>

                <!-- Transaction Summary -->
                <div class="result-card">
                    <div class="result-header">
                        <i class="fas fa-chart-bar"></i>
                        <h3>Transaction Summary</h3>
                    </div>
                    <div class="result-content">
                        <div class="info-item">
                            <span class="info-label">Total Transactions:</span>
                            <span class="info-value">${result.summary?.total_transactions || 0}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Total Credits:</span>
                            <span class="info-value">₹${this.formatCurrency(result.summary?.total_credits || 0)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Total Debits:</span>
                            <span class="info-value">₹${this.formatCurrency(result.summary?.total_debits || 0)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Salary Income:</span>
                            <span class="info-value income">₹${this.formatCurrency(result.summary?.salary_income || 0)}</span>
                        </div>
                    </div>
                </div>

                <!-- ITR Preview -->
                <div class="result-card full-width">
                    <div class="result-header">
                        <i class="fas fa-file-invoice"></i>
                        <h3>ITR Preview</h3>
                    </div>
                    <div class="result-content">
                        ${this.renderITRPreview(result.itr_preview)}
                    </div>
                </div>

                <!-- Transaction Details -->
                <div class="result-card full-width">
                    <div class="result-header">
                        <i class="fas fa-list"></i>
                        <h3>Recent Transactions</h3>
                    </div>
                    <div class="result-content">
                        ${this.renderTransactionTable(result.raw_transactions)}
                    </div>
                </div>

                <!-- Download Actions -->
                <div class="result-card full-width">
                    <div class="result-header">
                        <i class="fas fa-download"></i>
                        <h3>Download ITR Files</h3>
                    </div>
                    <div class="result-content">
                        <div class="download-actions">
                            <button class="btn btn-primary" onclick="app.downloadITR('json')">
                                <i class="fas fa-file-code"></i>
                                Download JSON
                            </button>
                            <button class="btn btn-secondary" onclick="app.downloadITR('xml')">
                                <i class="fas fa-file-alt"></i>
                                Download XML
                            </button>
                        </div>
                        <p class="download-note">
                            <i class="fas fa-info-circle"></i>
                            Please review all data before filing your ITR
                        </p>
                    </div>
                </div>
            </div>
        `;

        // Apply animations
        resultsContent.classList.add('fade-in');
    }

    renderITRPreview(itrPreview) {
        if (!itrPreview) return '<p>ITR preview not available</p>';

        return `
            <div class="itr-preview">
                <div class="preview-item">
                    <span class="preview-label">Recommended Form:</span>
                    <span class="preview-value form-type">${itrPreview.recommended_form || 'ITR1'}</span>
                </div>
                <div class="preview-item">
                    <span class="preview-label">Total Income:</span>
                    <span class="preview-value income">₹${this.formatCurrency(itrPreview.income_summary?.total_income || 0)}</span>
                </div>
                <div class="preview-item">
                    <span class="preview-label">Tax Liability:</span>
                    <span class="preview-value tax">₹${this.formatCurrency(itrPreview.income_summary?.tax_liability || 0)}</span>
                </div>
            </div>
        `;
    }

    renderTransactionTable(transactions) {
        if (!transactions || transactions.length === 0) {
            return '<p>No transactions found</p>';
        }

        // Store transactions for pagination
        this.allTransactions = transactions;
        this.currentPage = 1;
        this.transactionsPerPage = 20;
        this.showAllTransactions = false;

        return this.renderTransactionTableWithPagination();
    }

    renderTransactionTableWithPagination() {
        const transactions = this.allTransactions;
        const totalTransactions = transactions.length;
        
        let displayTransactions;
        let paginationControls = '';
        
        if (this.showAllTransactions) {
            displayTransactions = transactions;
            paginationControls = `
                <div class="pagination-controls">
                    <button class="btn btn-secondary" onclick="app.toggleShowAll(false)">
                        <i class="fas fa-list"></i> Show Paginated View
                    </button>
                    <span class="transaction-count">Showing all ${totalTransactions} transactions</span>
                </div>
            `;
        } else {
            const startIndex = (this.currentPage - 1) * this.transactionsPerPage;
            const endIndex = Math.min(startIndex + this.transactionsPerPage, totalTransactions);
            displayTransactions = transactions.slice(startIndex, endIndex);
            
            const totalPages = Math.ceil(totalTransactions / this.transactionsPerPage);
            
            paginationControls = `
                <div class="pagination-controls">
                    <div class="pagination-buttons">
                        <button class="btn btn-secondary" onclick="app.changePage(${Math.max(1, this.currentPage - 1)})" ${this.currentPage === 1 ? 'disabled' : ''}>
                            <i class="fas fa-chevron-left"></i> Previous
                        </button>
                        <span class="page-info">
                            Page ${this.currentPage} of ${totalPages}
                        </span>
                        <button class="btn btn-secondary" onclick="app.changePage(${Math.min(totalPages, this.currentPage + 1)})" ${this.currentPage === totalPages ? 'disabled' : ''}>
                            Next <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
                    <div class="pagination-options">
                        <button class="btn btn-primary" onclick="app.toggleShowAll(true)">
                            <i class="fas fa-list-alt"></i> Show All ${totalTransactions} Transactions
                        </button>
                        <span class="transaction-count">Showing ${startIndex + 1}-${endIndex} of ${totalTransactions} transactions</span>
                    </div>
                </div>
            `;
        }

        return `
            <div class="transaction-table-container">
                ${paginationControls}
                <div class="transaction-table-wrapper">
                    <table class="transaction-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Description</th>
                                <th>Amount</th>
                                <th>Type</th>
                                <th>Category</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${displayTransactions.map(txn => `
                                <tr>
                                    <td>${txn.date || 'N/A'}</td>
                                    <td class="description" title="${txn.description || 'N/A'}">${(txn.description || 'N/A').substring(0, 60)}${(txn.description || '').length > 60 ? '...' : ''}</td>
                                    <td class="amount ${txn.type}">${txn.type === 'credit' ? '+' : '-'}₹${this.formatCurrency(Math.abs(txn.amount || 0))}</td>
                                    <td><span class="type-badge ${txn.type}">${txn.type || 'N/A'}</span></td>
                                    <td><span class="category-badge">${txn.category || 'unknown'}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                ${paginationControls}
            </div>
        `;
    }

    changePage(page) {
        this.currentPage = page;
        this.updateTransactionTable();
    }

    toggleShowAll(showAll) {
        this.showAllTransactions = showAll;
        this.currentPage = 1;
        this.updateTransactionTable();
    }

    updateTransactionTable() {
        const resultsContent = document.getElementById('results-content');
        if (!resultsContent || !this.allTransactions) return;

        // Find and update the transaction table section
        const transactionSection = resultsContent.querySelector('.transaction-table-container');
        if (transactionSection) {
            const newTableHtml = this.renderTransactionTableWithPagination();
            transactionSection.outerHTML = newTableHtml;
        }
    }

    downloadITR(format) {
        // Get the current financial data from the results
        const resultsContent = document.getElementById('results-content');
        if (!resultsContent) {
            this.showNotification('No data available for download', 'error');
            return;
        }

        // Extract data from the current results (you might need to store this in a variable)
        const currentData = this.getCurrentProcessedData();
        if (!currentData) {
            this.showNotification('No processed data available', 'error');
            return;
        }

        // Generate ITR file and download
        this.generateAndDownloadITR(currentData, format);
    }

    getCurrentProcessedData() {
        // Return the stored processed data
        return this.processedData;
    }

    async generateAndDownloadITR(data, format) {
        try {
            this.showNotification(`Generating ITR file in ${format.toUpperCase()} format...`, 'success');

            // Call the backend to generate ITR file
            const response = await fetch('/generate_itr', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_info: {
                        name: 'User Name', // Default values for now
                        pan: 'PAN1234567',
                        address: 'Address',
                        email: 'user@example.com',
                        phone: '1234567890'
                    },
                    financial_data: data,
                    format: format
                })
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                // Download the generated file
                const downloadUrl = result.download_url;
                const filename = downloadUrl.split('/').pop();
                
                // Create a temporary link to trigger download
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                this.showNotification(`ITR file downloaded successfully!`, 'success');
            } else {
                throw new Error(result.error || 'Failed to generate ITR file');
            }
        } catch (error) {
            this.showNotification(`Download failed: ${error.message}`, 'error');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';

        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');

        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.add('show');

        setTimeout(() => {
            notification.classList.remove('show');
        }, 5000);
    }
}

// Additional styles for results
const additionalStyles = `
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: var(--spacing-xl);
}

.result-card {
    background: var(--surface-color);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-md);
    overflow: hidden;
}

.result-card.full-width {
    grid-column: 1 / -1;
}

.result-header {
    background: var(--gradient);
    color: white;
    padding: var(--spacing-lg);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.result-header h3 {
    margin: 0;
    font-size: var(--font-size-lg);
}

.result-content {
    padding: var(--spacing-lg);
}

.info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-color);
}

.info-item:last-child {
    border-bottom: none;
}

.info-label {
    font-weight: 500;
    color: var(--text-secondary);
}

.info-value {
    font-weight: 600;
}

.info-value.income {
    color: var(--success-color);
}

.itr-preview {
    display: grid;
    gap: var(--spacing-lg);
}

.preview-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md);
    background: var(--background-color);
    border-radius: var(--radius-md);
}

.preview-value.form-type {
    background: var(--primary-color);
    color: white;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
    font-weight: 600;
}

.preview-value.income {
    color: var(--success-color);
    font-weight: 700;
}

.preview-value.tax {
    color: var(--warning-color);
    font-weight: 700;
}

.transaction-table-container {
    margin: var(--spacing-lg) 0;
}

.transaction-table-wrapper {
    overflow-x: auto;
    max-height: 600px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
}

.transaction-table {
    width: 100%;
    border-collapse: collapse;
}

.pagination-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: var(--spacing-md) 0;
    padding: var(--spacing-md);
    background: var(--background-color);
    border-radius: var(--radius-md);
    flex-wrap: wrap;
    gap: var(--spacing-md);
}

.pagination-buttons {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.pagination-options {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.page-info {
    font-weight: 500;
    color: var(--text-primary);
    min-width: 120px;
    text-align: center;
}

.transaction-count {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    font-weight: 500;
}

.pagination-controls .btn {
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-sm);
}

.pagination-controls .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.transaction-table th,
.transaction-table td {
    padding: var(--spacing-sm) var(--spacing-md);
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.transaction-table th {
    background: var(--background-color);
    font-weight: 600;
    color: var(--text-primary);
}

.transaction-table .description {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.transaction-table .amount {
    font-weight: 600;
    text-align: right;
}

.transaction-table .amount.credit {
    color: var(--success-color);
}

.transaction-table .amount.debit {
    color: var(--error-color);
}

.type-badge {
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    font-weight: 500;
    text-transform: uppercase;
}

.type-badge.credit {
    background: rgba(16, 185, 129, 0.1);
    color: var(--success-color);
}

.type-badge.debit {
    background: rgba(239, 68, 68, 0.1);
    color: var(--error-color);
}

.category-badge {
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    font-weight: 500;
    background: rgba(37, 99, 235, 0.1);
    color: var(--primary-color);
    text-transform: capitalize;
}

.table-note {
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    text-align: center;
    margin: var(--spacing-md) 0 0 0;
}

.download-actions {
    display: flex;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    justify-content: center;
}

.download-note {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    text-align: center;
    justify-content: center;
}

@media (max-width: 768px) {
    .results-grid {
        grid-template-columns: 1fr;
    }

    .download-actions {
        flex-direction: column;
    }
    
    .pagination-controls {
        flex-direction: column;
        align-items: stretch;
    }
    
    .pagination-buttons,
    .pagination-options {
        justify-content: center;
    }
    
    .transaction-table-wrapper {
        max-height: 400px;
    }
    
    .transaction-table th,
    .transaction-table td {
        padding: var(--spacing-xs) var(--spacing-sm);
        font-size: var(--font-size-sm);
    }
    
    .transaction-table .description {
        max-width: 150px;
    }
}
`;

// Inject additional styles
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

// Initialize the application
const app = new AutoITRApp();
