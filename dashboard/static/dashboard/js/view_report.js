function showDeleteModal() {
    document.getElementById('delete-modal').style.display = 'flex';
}

function hideDeleteModal() {
    document.getElementById('delete-modal').style.display = 'none';
}

function startRename() {
    const reportName = document.getElementById('report-name');
    const renameForm = document.getElementById('rename-form');
    const newNameInput = document.getElementById('new-name');
    
    reportName.style.display = 'none';
    renameForm.style.display = 'flex';
    newNameInput.focus();
    newNameInput.select();
}

function cancelRename() {
    const reportName = document.getElementById('report-name');
    const renameForm = document.getElementById('rename-form');
    
    reportName.style.display = 'block';
    renameForm.style.display = 'none';
}

function saveNewName() {
    const newName = document.getElementById('new-name').value.trim();
    if (!newName) return;

    fetch(renameReportUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: 'name=' + encodeURIComponent(newName)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('report-name').textContent = data.new_name;
            cancelRename();
            // Update sidebar item if it exists
            const sidebarItem = document.querySelector(`a[href="${viewReportUrl}"]`);
            if (sidebarItem) {
                sidebarItem.textContent = data.new_name;
            }
        }
    });
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('delete-modal');
    if (event.target == modal) {
        hideDeleteModal();
    }
}

// Add toggle functionality for full analysis
document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('toggle-full-analysis');
    const previewDiv = document.querySelector('.analysis-preview');
    const fullDiv = document.querySelector('.analysis-full');

    if (toggleButton && previewDiv && fullDiv) {
        toggleButton.addEventListener('click', function() {
            const isShowingPreview = previewDiv.style.display !== 'none';
            if (isShowingPreview) {
                previewDiv.style.display = 'none';
                fullDiv.style.display = 'block';
                toggleButton.textContent = 'Show Less';
            } else {
                previewDiv.style.display = 'block';
                fullDiv.style.display = 'none';
                toggleButton.textContent = 'View Full Analysis';
            }
        });
    }
});

// Update the stock analysis form handler
document.getElementById('text-submission-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const form = this;
    const formData = new FormData(form);
    const statusDiv = document.getElementById('analysis-status');
    const resultDiv = document.getElementById('analysis-result');
    const resultSymbol = document.getElementById('result-symbol');
    const analysisPreview = document.createElement('div');
    const analysisFull = document.createElement('div');
    const analysisContent = document.querySelector('.analysis-content');
    
    // Show loading status
    statusDiv.style.display = 'block';
    
    // Use the form's action URL for the fetch request
    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading status
        statusDiv.style.display = 'none';
        
        if (data.success) {
            // Display the analysis result
            resultSymbol.textContent = data.stock_symbol;
            
            // Create preview and full divs
            analysisPreview.className = 'analysis-preview';
            analysisFull.className = 'analysis-full';
            analysisPreview.innerHTML = data.analysis_result;
            analysisFull.innerHTML = data.analysis_result;
            analysisFull.style.display = 'none';
            
            // Clear existing content and add new divs
            analysisContent.innerHTML = '';
            analysisContent.appendChild(analysisPreview);
            analysisContent.appendChild(analysisFull);
            
            resultDiv.style.display = 'block';
            
            // Reset toggle button and set up its click handler
            const toggleButton = document.getElementById('toggle-full-analysis');
            if (toggleButton) {
                toggleButton.textContent = 'View Full Analysis';
                
                // Remove any existing click handlers
                toggleButton.replaceWith(toggleButton.cloneNode(true));
                
                // Add new click handler
                document.getElementById('toggle-full-analysis').addEventListener('click', function() {
                    const isShowingPreview = analysisPreview.style.display !== 'none';
                    if (isShowingPreview) {
                        analysisPreview.style.display = 'none';
                        analysisFull.style.display = 'block';
                        this.textContent = 'Show Less';
                    } else {
                        analysisPreview.style.display = 'block';
                        analysisFull.style.display = 'none';
                        this.textContent = 'View Full Analysis';
                    }
                });
            }
            
            // Scroll to the result
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        // Hide loading status
        statusDiv.style.display = 'none';
        alert('Error analyzing stock. Please try again.');
        console.error('Error:', error);
    });
});

// Add delay utility function
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Stock Information Functions
async function getStockInfo(retryCount = 0) {
    const stockSymbol = document.getElementById('stock-symbol').value.trim();
    if (!stockSymbol) {
        alert('Please enter a stock symbol');
        return;
    }

    const statusDiv = document.getElementById('analysis-status');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="spinner"></div><p>Fetching stock information...</p>';

    try {
        const response = await fetch(`/dashboard/report/${reportId}/stock-info/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `stock_symbol=${encodeURIComponent(stockSymbol)}`
        });

        const result = await response.json();
        
        if (response.status === 429 || (result.error && result.error.includes('Too Many Requests'))) {
            if (retryCount < 3) {
                statusDiv.innerHTML = '<div class="spinner"></div><p>Rate limited. Retrying in ' + (5 + retryCount * 5) + ' seconds...</p>';
                await delay((5 + retryCount * 5) * 1000); // Wait 5, 10, or 15 seconds based on retry count
                return getStockInfo(retryCount + 1);
            } else {
                throw new Error('Rate limit exceeded. Please try again in a few minutes.');
            }
        }

        statusDiv.style.display = 'none';
        
        if (result.success) {
            displayStockInfo(result.data, stockSymbol);
        } else {
            throw new Error(result.error || 'Failed to get stock information');
        }
    } catch (error) {
        statusDiv.style.display = 'none';
        let errorMessage = error.message;
        if (error.message.includes('Rate limit')) {
            errorMessage = 'We are currently experiencing high traffic. Please try again in a few minutes.';
        }
        alert(errorMessage);
        console.error('Error:', error);
    }
}

function displayStockInfo(stockInfo, stockSymbol) {
    const stockInfoDiv = document.getElementById('stock-info-result');
    const infoSymbol = document.getElementById('info-symbol');
    const stockInfoContent = document.querySelector('.stock-info-content');
    
    // Update the symbol
    infoSymbol.textContent = stockSymbol;
    
    // Format the stock information
    let formattedInfo = '';
    
    // Group the information into sections
    const sections = {
        'Basic Information': ['Symbol', 'Company Name', 'Sector', 'Industry', 'Country', 'Website'],
        'Market Data': ['Current Price', 'Previous Close', 'Open', 'Day High', 'Day Low', 'Volume'],
        'Technical Indicators': ['20-day SMA', '50-day SMA', 'RSI'],
        'Market Information': ['Primary Exchange', 'List Date', 'Shares Outstanding', 'Market Cap'],
        'Company Size': ['Full Time Employees']
    };

    for (const [section, fields] of Object.entries(sections)) {
        formattedInfo += `<div class="info-section"><h4>${section}</h4>`;
        for (const field of fields) {
            if (stockInfo[field]) {
                formattedInfo += `<div class="info-row"><span class="info-label">${field}:</span> <span class="info-value">${stockInfo[field]}</span></div>`;
            }
        }
        formattedInfo += '</div>';
    }
    
    // Add last updated timestamp
    formattedInfo += `<div class="info-section"><h4>Additional Information</h4>`;
    formattedInfo += `<div class="info-row"><span class="info-label">Last Updated:</span> <span class="info-value">${stockInfo['Last Updated']}</span></div>`;
    formattedInfo += '</div>';
    
    // Update the content and show the div
    stockInfoContent.innerHTML = formattedInfo;
    stockInfoDiv.style.display = 'block';
    
    // Scroll to the stock info
    stockInfoDiv.scrollIntoView({ behavior: 'smooth' });
} 