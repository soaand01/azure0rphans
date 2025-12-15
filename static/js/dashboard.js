// Dashboard JavaScript - Chart.js Integration and Data Loading

// Global chart instances
let tierChart, locationChart, osChart;

// Global data source variable (initialized from template or default to 'csv')
let currentDataSource = window.initialDataSource || 'csv';

// Get resource type from URL
const pathParts = window.location.pathname.split('/');
const resourceType = pathParts[pathParts.indexOf('analyze') + 1];

// Color palettes
const chartColors = {
    primary: ['#0078d4', '#50e6ff', '#00bcf2', '#0099bc', '#004e8c', '#002050'],
    success: ['#107c10', '#bad80a', '#00b7c3', '#008272', '#004b50', '#002d30'],
    warm: ['#ffb900', '#ff8c00', '#d83b01', '#e81123', '#b4009e', '#5c2d91'],
    mixed: ['#0078d4', '#107c10', '#ffb900', '#d83b01', '#00b7c3', '#8764b8']
};

// Delete uploaded files and reset to sample data
function deleteUploadedFiles() {
    // Show Bootstrap modal instead of browser confirm
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    deleteModal.show();
}

function confirmDeleteFiles() {
    // Hide the modal
    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
    deleteModal.hide();
    
    // Show loading spinner in main content
    document.getElementById('loadingSpinner').innerHTML = `
        <div class="spinner-border text-danger" role="status">
            <span class="visually-hidden">Deleting...</span>
        </div>
        <p class="mt-3">Deleting uploaded files...</p>
    `;
    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('mainContent').style.display = 'none';
    
    fetch(`/delete-uploads/${resourceType}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message briefly then reload
            document.getElementById('loadingSpinner').innerHTML = `
                <div class="alert alert-success d-inline-block">
                    <i class="bi bi-check-circle me-2"></i>
                    ${data.message}
                </div>
                <p class="mt-3">Data cleared. Reloading...</p>
            `;
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            document.getElementById('loadingSpinner').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Error: ${data.error}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error deleting files:', error);
        document.getElementById('loadingSpinner').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Failed to delete files. Please try again.
            </div>
        `;
    });
}

// File upload function
function uploadFile() {
    const formData = new FormData();
    
    // Check if this is a multi-file upload
    const isMultiFile = document.querySelectorAll('[id^="csvFile"]').length > 1;
    
    if (isMultiFile) {
        // Handle multiple files
        let hasAtLeastOneFile = false;
        const fileInputs = document.querySelectorAll('[id^="csvFile"]');
        
        fileInputs.forEach((input, index) => {
            const file = input.files[0];
            
            // Check if this file is optional by looking at the label
            const label = input.parentElement.querySelector('label');
            const isOptional = label && (label.textContent.includes('Optional') || label.textContent.includes('optional'));
            
            if (!file) {
                // Skip optional files that aren't provided
                if (isOptional) {
                    return;
                }
                // For required files, we'll check later if at least one file was uploaded
            } else {
                formData.append(`file${index}`, file);
                hasAtLeastOneFile = true;
            }
        });
        
        if (!hasAtLeastOneFile) {
            showUploadMessage('Please select at least one file to upload', 'danger');
            return;
        }
        
    } else {
        // Handle single file
        const fileInput = document.getElementById('csvFile');
        const file = fileInput.files[0];
        
        if (!file) {
            showUploadMessage('Please select a file', 'danger');
            return;
        }
        
        formData.append('file', file);
    }
    
    // Show progress
    document.getElementById('uploadProgress').style.display = 'block';
    document.getElementById('uploadMessage').innerHTML = '';
    
    fetch(`/upload/${resourceType}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('uploadProgress').style.display = 'none';
        
        if (data.success) {
            const fileCount = data.filenames ? data.filenames.length : 1;
            showUploadMessage(`${data.message} Reloading analysis...`, 'success');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showUploadMessage(data.error || 'Upload failed', 'danger');
        }
    })
    .catch(error => {
        document.getElementById('uploadProgress').style.display = 'none';
        showUploadMessage('Error uploading file(s): ' + error, 'danger');
    });
}

function showUploadMessage(message, type) {
    const messageDiv = document.getElementById('uploadMessage');
    messageDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

// Load data on page load
document.addEventListener('DOMContentLoaded', function() {
    fetchDashboardData();
});

// Switch between data sources
function switchDataSource(source) {
    currentDataSource = source;
    
    // Show appropriate UI elements
    if (source === 'csv') {
        // Show upload button for CSV mode
        const uploadBtn = document.querySelector('[data-bs-target="#uploadModal"]');
        if (uploadBtn) uploadBtn.style.display = 'inline-block';
    }
    
    // Reload data with new source
    fetchDashboardData();
}

// Fetch and populate dashboard data
async function fetchDashboardData() {
    try {
        // Add source parameter if using JSON
        const url = currentDataSource === 'json' 
            ? `/api/data/${resourceType}?source=json`
            : `/api/data/${resourceType}`;
        
        const response = await fetch(url);
        
        if (!response.ok) {
            // Handle 404 specifically for no data
            if (response.status === 404) {
                const errorData = await response.json();
                if (errorData.error === 'no_data') {
                    document.getElementById('loadingSpinner').innerHTML = `
                        <div class="alert alert-info border-0 shadow-sm">
                            <h4><i class="bi bi-cloud-upload me-2"></i>No Data Available</h4>
                            <p class="mb-3">${errorData.message}</p>
                            <button class="btn btn-primary" onclick="document.getElementById('uploadModalBtn').click()">
                                <i class="bi bi-upload me-2"></i>
                                Upload CSV Files
                            </button>
                            <a href="/" class="btn btn-outline-secondary ms-2">
                                <i class="bi bi-arrow-left me-2"></i>
                                Back to Home
                            </a>
                        </div>
                    `;
                    return;
                }
            }
            
            // Handle 400 for missing required file
            if (response.status === 400) {
                const errorData = await response.json();
                if (errorData.error === 'missing_plans_file') {
                    document.getElementById('loadingSpinner').innerHTML = `
                        <div class="alert alert-warning border-0 shadow-sm">
                            <h4><i class="bi bi-exclamation-triangle me-2"></i>Missing Required File</h4>
                            <p class="mb-3">${errorData.message}</p>
                            <p class="small text-muted mb-3">Note: File 1 (App Service Plans CSV) is required. File 2 (App Services CSV) is optional but enhances analysis.</p>
                            <button class="btn btn-warning" onclick="deleteUploadedFiles()">
                                <i class="bi bi-trash me-2"></i>
                                Clear & Upload Correct Files
                            </button>
                            <a href="/" class="btn btn-outline-secondary ms-2">
                                <i class="bi bi-arrow-left me-2"></i>
                                Back to Home
                            </a>
                        </div>
                    `;
                    return;
                }
            }
            
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        console.log('Dashboard data received:', data);
        
        // Show data source banner
        if (data.data_source === 'azure_scan') {
            const banner = document.getElementById('dataSourceBanner');
            banner.className = 'alert alert-info border-0 shadow-sm mb-4';
            banner.style.borderLeft = '4px solid #667eea';
            banner.style.display = 'block';
            banner.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="bi bi-cloud-check-fill fs-4 me-3" style="color: #667eea;"></i>
                    <div class="flex-grow-1">
                        <strong>Using Azure Scan Data</strong>
                        <p class="mb-0 small text-muted">
                            Loaded from: <code>${data.scan_file}</code> | 
                            Scanned: ${new Date(data.scan_date).toLocaleString()}
                        </p>
                    </div>
                    <a href="/overview" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-arrow-clockwise me-1"></i>
                        Refresh Scan
                    </a>
                </div>
            `;
        } else if (data.combined_insights) {
            // Show CSV mode banner (existing logic)
        }
        
        // Check if resource is not implemented yet
        if (data.status === 'not_implemented') {
            document.getElementById('loadingSpinner').innerHTML = `
                <div class="alert alert-warning">
                    <h4><i class="bi bi-exclamation-triangle me-2"></i>${data.message}</h4>
                    <p>This resource type analyzer is under development. Please check back soon!</p>
                    <a href="/" class="btn btn-primary mt-3">
                        <i class="bi bi-arrow-left me-2"></i>
                        Back to Home
                    </a>
                </div>
            `;
            return;
        }
        
        // Show analysis mode banner and adapt dashboard layout
        if (data.combined_insights) {
            showCombinedInsightsBanner(data.combined_insights);
            adaptDashboardLayout(data.combined_insights.mode || 'plans_only');
        }
        
        // Populate summary cards
        if (data.summary) populateSummary(data.summary);
        
        // Generate recommendations
        if (data.recommendations) generateRecommendations(data.recommendations, data.recommendation_definitions || {});
        
        // Create charts based on available data
        if (data.charts) {
            // For apps-only mode, use plans chart instead of tier chart
            if (data.charts.plans) {
                createPlansChart(data.charts.plans);
            } else if (data.charts.tier) {
                createTierChart(data.charts.tier);
            }
            
            if (data.charts.location) createLocationChart(data.charts.location);
            if (data.charts.os) {
                createOSChart(data.charts.os);
            } else {
                // Hide OS chart if no data
                const osCard = document.querySelector('.col-lg-4.mb-4');
                if (osCard && osCard.textContent.includes('Operating System')) {
                    osCard.style.display = 'none';
                }
            }
        }
        
        // Populate tables
        if (data.tables) {
            if (data.tables.tier_stats) {
                populateTierStatsTable(data.tables.tier_stats);
            } else {
                // Hide tier stats table if no data
                const tierTable = document.querySelector('.col-lg-6.mb-4');
                if (tierTable && tierTable.textContent.includes('Statistics by Tier')) {
                    tierTable.style.display = 'none';
                }
            }
            
            // For apps-only mode, use subscription_stats; otherwise use resource_groups
            if (data.tables.subscription_stats) {
                populateResourceGroupTable(data.tables.subscription_stats);
            } else if (data.tables.resource_groups) {
                populateResourceGroupTable(data.tables.resource_groups);
            } else {
                // Hide resource groups table if no data
                const rgTable = document.querySelectorAll('.col-lg-6.mb-4')[1];
                if (rgTable && rgTable.textContent.includes('Resource Groups')) {
                    rgTable.style.display = 'none';
                }
            }
        }
        
        // Populate density metrics
        if (data.density_metrics && data.density_metrics.length > 0) {
            populateDensityMetrics(data.density_metrics);
        } else {
            // Hide density section if no data
            const densityCard = document.querySelector('.col-lg-8.mb-4');
            if (densityCard && densityCard.textContent.includes('Density')) {
                densityCard.style.display = 'none';
            }
        }
        
        // Hide loading, show content
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
        
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        document.getElementById('loadingSpinner').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Error loading data:</strong> ${error.message}<br>
                <p class="mb-2">Current data source: <strong>${currentDataSource}</strong></p>
                <p class="mb-2">API URL: <strong>${currentDataSource === 'json' ? '/api/data/' + resourceType + '?source=json' : '/api/data/' + resourceType}</strong></p>
                <button class="btn btn-primary mt-2" onclick="location.reload()">Reload Page</button>
            </div>
        `;
        document.getElementById('loadingSpinner').style.display = 'block';
    }
}

// Show combined insights banner
function showCombinedInsightsBanner(insights) {
    const banner = document.createElement('div');
    
    // Different banner for different modes
    if (insights.mode === 'apps_only') {
        // Apps-only mode (limited analysis)
        banner.className = 'alert alert-info border-0 shadow-sm mb-4';
        banner.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-info-circle fs-4 me-3"></i>
                <div class="flex-grow-1">
                    <h6 class="mb-1"><strong>Apps-Only Analysis Mode</strong></h6>
                    <p class="mb-0 small">
                        Analyzing App Services data only (${insights.total_apps_detailed} apps found).
                        ${insights.running_apps ? `${insights.running_apps} running, ${insights.stopped_apps || 0} stopped.` : ''}
                        Upload Plans CSV (file 1) for complete cost optimization insights.
                    </p>
                </div>
                <div class="text-end">
                    <span class="badge bg-info"><i class="bi bi-file-earmark me-1"></i>Limited Analysis</span>
                </div>
            </div>
        `;
    } else if (insights.enabled) {
        // Combined mode (both files)
        banner.className = 'alert alert-success border-0 shadow-sm mb-4';
        banner.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-check2-circle fs-4 me-3"></i>
                <div class="flex-grow-1">
                    <h6 class="mb-1"><strong>Combined Analysis Mode Active</strong></h6>
                    <p class="mb-0 small">
                        Analyzing ${insights.files_count} files: Plans & Apps data combined for deeper insights.
                        ${insights.total_apps_detailed ? `Found ${insights.total_apps_detailed} apps total` : ''}
                        ${insights.running_apps ? ` (${insights.running_apps} running, ${insights.stopped_apps || 0} stopped)` : ''}
                    </p>
                </div>
                <div class="text-end">
                    <span class="badge bg-success"><i class="bi bi-file-earmark-check me-1"></i>Enhanced Analysis</span>
                </div>
            </div>
        `;
    } else {
        // Plans-only mode (standard analysis)
        banner.className = 'alert alert-primary border-0 shadow-sm mb-4';
        banner.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-graph-up fs-4 me-3"></i>
                <div class="flex-grow-1">
                    <h6 class="mb-1"><strong>Plans Analysis Mode</strong></h6>
                    <p class="mb-0 small">
                        Analyzing App Service Plans data. Upload Apps CSV (file 2) for enhanced app-level insights.
                    </p>
                </div>
                <div class="text-end">
                    <span class="badge bg-primary"><i class="bi bi-file-earmark me-1"></i>Standard Analysis</span>
                </div>
            </div>
        `;
    }
    
    // Insert at the top of main content
    const mainContent = document.getElementById('mainContent');
    mainContent.insertBefore(banner, mainContent.firstChild);
}

// Adapt dashboard layout based on analysis mode
function adaptDashboardLayout(mode) {
    // Get references to sections
    const densitySection = document.querySelector('.col-lg-8.mb-4'); // App Density Analysis card parent
    const osChartSection = document.querySelector('.col-lg-4.mb-4'); // OS Chart card parent
    
    if (mode === 'apps_only') {
        // Apps-only mode: Hide plan-specific elements
        // Hide "Total Instances" card
        const instancesCard = document.querySelector('.col-md-3:nth-child(3)');
        if (instancesCard) instancesCard.style.display = 'none';
        
        // Update card labels
        const plansLabel = document.querySelector('.col-md-3:nth-child(1) .text-muted');
        if (plansLabel) plansLabel.textContent = 'Unique Plans Referenced';
        
        // Hide density analysis (no plan data)
        if (densitySection) densitySection.style.display = 'none';
        
        // Update tier chart title
        const tierChartTitle = document.querySelector('.col-lg-6:nth-child(1) h5');
        if (tierChartTitle) {
            tierChartTitle.innerHTML = '<i class="bi bi-bar-chart text-primary"></i> Apps by Pricing Tier';
        }
        
        // Update resource group table for subscriptions
        const rgTableCard = document.querySelector('#resourceGroupTable').closest('.card');
        if (rgTableCard) {
            const rgTitle = rgTableCard.querySelector('h5');
            if (rgTitle) {
                rgTitle.innerHTML = '<i class="bi bi-folder text-success"></i> Top Subscriptions';
            }
            const rgTableHead = rgTableCard.querySelector('thead tr');
            if (rgTableHead) {
                rgTableHead.innerHTML = `
                    <th>Subscription</th>
                    <th class="text-end">Apps</th>
                `;
            }
        }
        
    } else if (mode === 'plans_only') {
        // Plans-only mode: Standard display, all elements visible
        // Update recommendation title
        const recTitle = document.querySelector('.card-header h5');
        if (recTitle && recTitle.textContent.includes('Recommendations')) {
            recTitle.innerHTML = '<i class="bi bi-lightbulb text-warning"></i> Plan Optimization Recommendations';
        }
        
        // Ensure resource group table shows standard headers
        const rgTableCard = document.querySelector('#resourceGroupTable').closest('.card');
        if (rgTableCard) {
            const rgTitle = rgTableCard.querySelector('h5');
            if (rgTitle) {
                rgTitle.innerHTML = '<i class="bi bi-folder text-success"></i> Top Resource Groups';
            }
            const rgTableHead = rgTableCard.querySelector('thead tr');
            if (rgTableHead) {
                rgTableHead.innerHTML = `
                    <th>Resource Group</th>
                    <th class="text-end">Plans</th>
                    <th class="text-end">Apps</th>
                    <th class="text-end">Instances</th>
                `;
            }
        }
        
    } else {
        // Combined mode: Show everything
        // Update recommendation title for combined analysis
        const recTitle = document.querySelector('.card-header h5');
        if (recTitle && recTitle.textContent.includes('Recommendations')) {
            recTitle.innerHTML = '<i class="bi bi-lightbulb text-warning"></i> Combined Optimization Recommendations';
        }
        
        // Ensure resource group table shows standard headers
        const rgTableCard = document.querySelector('#resourceGroupTable').closest('.card');
        if (rgTableCard) {
            const rgTitle = rgTableCard.querySelector('h5');
            if (rgTitle) {
                rgTitle.innerHTML = '<i class="bi bi-folder text-success"></i> Top Resource Groups';
            }
            const rgTableHead = rgTableCard.querySelector('thead tr');
            if (rgTableHead) {
                rgTableHead.innerHTML = `
                    <th>Resource Group</th>
                    <th class="text-end">Plans</th>
                    <th class="text-end">Apps</th>
                    <th class="text-end">Instances</th>
                `;
            }
        }
    }
}

// Populate summary cards
function populateSummary(summary) {
    document.getElementById('totalPlans').textContent = summary.total_plans;
    document.getElementById('totalApps').textContent = summary.total_apps;
    document.getElementById('totalInstances').textContent = summary.total_instances;
    document.getElementById('avgApps').textContent = summary.avg_apps_per_plan;
}

// Generate recommendation cards
function generateRecommendations(recommendations, definitions) {
    const container = document.getElementById('recommendationsList');
    document.getElementById('recommendationCount').textContent = recommendations.length;
    
    if (recommendations.length === 0) {
        container.innerHTML = `
            <div class="alert alert-success border-0" style="border: 2px solid #000 !important; border-left: 4px solid #000 !important;">
                <i class="bi bi-check-circle"></i>
                Great! No major cost optimization issues detected. Continue monitoring your resources.
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    recommendations.forEach((rec, index) => {
        const def = definitions[rec.type] || {
            title: 'Optimization Opportunity',
            description: 'Review this resource for potential improvements',
            impact: 'Medium',
            category: 'General'
        };
        
        // Gradient colors for impact badges
        const impactBadgeStyle = rec.potential_saving.toLowerCase().includes('high') 
            ? 'background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border: none;'
            : rec.potential_saving.toLowerCase().includes('medium') 
            ? 'background: linear-gradient(135deg, #FFD700, #FFA500); color: white; border: none;'
            : 'background: linear-gradient(135deg, #4ECDC4, #95E1D3); color: white; border: none;';
        
        const card = document.createElement('div');
        card.className = 'recommendation-item p-3 mb-3';
        card.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-2">
                        <h6 class="mb-0 me-2">${def.title}</h6>
                        <span class="badge" style="${impactBadgeStyle} padding: 0.5rem 1rem;">${rec.potential_saving}</span>
                        <span class="badge bg-light text-dark ms-2" style="border: 1px solid #e0e0e0;">${def.category}</span>
                    </div>
                    <p class="text-muted mb-3 small">${def.description}</p>
                    <div class="row g-3">
                        <div class="col-md-4">
                            <strong class="small d-block mb-1" style="color: #000;">Resource:</strong>
                            <p class="mb-0 small">${rec.resource}</p>
                        </div>
                        <div class="col-md-4">
                            <strong class="small d-block mb-1" style="color: #000;">Current State:</strong>
                            <p class="mb-0 small">${rec.current_state}</p>
                        </div>
                        <div class="col-md-4">
                            <strong class="small d-block mb-1" style="color: #000;">Suggestion:</strong>
                            <p class="mb-0 small" style="color: #667eea; font-weight: 500;">${rec.suggestion}</p>
                        </div>
                    </div>
                </div>
                <div class="ms-3">
                    <i class="bi bi-lightbulb-fill fs-3" style="background: linear-gradient(135deg, #FFD700, #FFA500); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;"></i>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// Create Tier Distribution Chart
function createTierChart(data) {
    const ctx = document.getElementById('tierChart').getContext('2d');
    
    tierChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Plans',
                    data: data.plans,
                    backgroundColor: chartColors.primary[0],
                    borderColor: chartColors.primary[0],
                    borderWidth: 1
                },
                {
                    label: 'Apps',
                    data: data.apps,
                    backgroundColor: chartColors.success[0],
                    borderColor: chartColors.success[0],
                    borderWidth: 1
                },
                {
                    label: 'Instances',
                    data: data.instances,
                    backgroundColor: chartColors.warm[0],
                    borderColor: chartColors.warm[0],
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                title: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Create Location Distribution Chart
function createLocationChart(data) {
    const ctx = document.getElementById('locationChart').getContext('2d');
    
    // Handle both formats: {plans, instances} for plans mode and {apps} for apps mode
    const dataValues = data.apps || data.plans || [];
    const chartLabel = data.apps ? 'Apps by Location' : 'Plans by Location';
    
    locationChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                label: chartLabel,
                data: dataValues,
                backgroundColor: chartColors.mixed,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Create OS Distribution Chart
function createOSChart(data) {
    const ctx = document.getElementById('osChart').getContext('2d');
    
    const dataValues = data.apps || data.plans || [];
    const chartLabel = data.apps ? 'Apps' : 'Plans';
    
    osChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                label: chartLabel,
                data: dataValues,
                backgroundColor: chartColors.mixed.slice(0, data.labels.length),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} ${chartLabel.toLowerCase()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Create Plans Chart for apps-only mode
function createPlansChart(data) {
    const ctx = document.getElementById('tierChart').getContext('2d');
    
    // Update the chart title
    const chartCard = ctx.canvas.closest('.card');
    const titleElem = chartCard.querySelector('h5');
    if (titleElem) {
        titleElem.innerHTML = '<i class="bi bi-bar-chart text-primary"></i> Top 10 Plans by App Count';
    }
    
    // Truncate long plan names for display
    const truncateLabel = (label) => {
        if (label.length > 25) {
            return label.substring(0, 22) + '...';
        }
        return label;
    };
    
    const truncatedLabels = data.labels.map(truncateLabel);
    
    tierChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: truncatedLabels,
            datasets: [{
                label: 'Apps',
                data: data.apps,
                backgroundColor: chartColors.primary[0],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',  // Horizontal bar chart for better label visibility
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        title: function(context) {
                            return data.labels[context[0].dataIndex];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Apps'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Populate Tier Stats Table
function populateTierStatsTable(data) {
    const tbody = document.getElementById('tierStatsTable');
    tbody.innerHTML = '';
    
    console.log('Tier stats data:', data);
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No tier statistics available</td></tr>';
        return;
    }
    
    data.forEach(row => {
        const tr = document.createElement('tr');
        
        // Check if this is apps-only data (no Plans/Instances columns)
        if (row.Plans !== undefined && row.Instances !== undefined) {
            // Full data with plans and instances
            if (row.OS !== undefined) {
                // Plans mode with OS column
                tr.innerHTML = `
                    <td><strong>${row.Tier || 'Unknown'}</strong></td>
                    <td>${row.OS || 'Unknown'}</td>
                    <td class="text-end">${row.Plans || 0}</td>
                    <td class="text-end">${row.Apps || 0}</td>
                    <td class="text-end">${row.Instances || 0}</td>
                `;
            } else {
                // Plans mode without OS column
                tr.innerHTML = `
                    <td><strong>${row.Tier || 'Unknown'}</strong></td>
                    <td class="text-end">${row.Plans || 0}</td>
                    <td class="text-end">${row.Apps || 0}</td>
                    <td class="text-end">${row.Instances || 0}</td>
                `;
            }
        } else {
            // Apps-only data
            tr.innerHTML = `
                <td><strong>${row.Tier || 'Unknown'}</strong></td>
                <td class="text-end" colspan="3">${row.Apps || 0} apps</td>
            `;
        }
        
        tbody.appendChild(tr);
    });
}

// Populate Resource Group Table
function populateResourceGroupTable(data) {
    const tbody = document.getElementById('resourceGroupTable');
    tbody.innerHTML = '';
    
    // Check if we have subscription stats (apps-only mode) or resource group stats
    const isSubscriptionData = data.length > 0 && data[0].Subscription !== undefined;
    
    // Show top 10 entries
    data.slice(0, 10).forEach(row => {
        const tr = document.createElement('tr');
        if (isSubscriptionData) {
            // Apps-only mode: show Subscription + Apps
            tr.innerHTML = `
                <td><strong>${row.Subscription}</strong></td>
                <td class="text-end">${row.Apps}</td>
            `;
        } else {
            // Plans or combined mode: show ResourceGroup + Plans + Apps + Instances
            const rgName = row.ResourceGroup || row['Resource Group'] || 'Unknown';
            tr.innerHTML = `
                <td><strong>${rgName}</strong></td>
                <td class="text-end">${row.Plans || 0}</td>
                <td class="text-end">${row.Apps || 0}</td>
                <td class="text-end">${row.Instances || 0}</td>
            `;
        }
        tbody.appendChild(tr);
    });
}

// Populate Density Metrics
function populateDensityMetrics(data) {
    const container = document.getElementById('densityTable');
    container.innerHTML = '';
    
    data.forEach(metric => {
        const card = document.createElement('div');
        card.className = 'card mb-2 border-0 shadow-sm';
        card.innerHTML = `
            <div class="card-body py-2 px-3">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <strong class="small">${metric.plan_name}</strong>
                        <br>
                        <small class="text-muted">${metric.tier}</small>
                    </div>
                    <div class="col-md-2 text-center">
                        <span class="badge bg-primary">${metric.apps} Apps</span>
                    </div>
                    <div class="col-md-2 text-center">
                        <span class="badge bg-secondary">${metric.instances} Instances</span>
                    </div>
                    <div class="col-md-2 text-center">
                        <strong class="text-${metric.color}">${metric.density}</strong>
                        <br>
                        <small class="text-muted">Apps/Instance</small>
                    </div>
                    <div class="col-md-3 text-end">
                        <span class="badge bg-${metric.color} density-status">${metric.status}</span>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// Export functionality (for future use)
function exportRecommendations() {
    fetch('/api/export/recommendations')
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cost-optimization-recommendations.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
}
