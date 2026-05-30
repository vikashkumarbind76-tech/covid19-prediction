document.addEventListener('DOMContentLoaded', () => {
    // Determine which page we are on
    if (document.getElementById('screening-form')) {
        initScreeningForm();
    }
    
    if (document.getElementById('predictions-table')) {
        initAdminDashboard();
    }
});

/* ==========================================================================
   PUBLIC DIAGNOSTIC PORTAL FORM WIZARD
   ========================================================================== */
function initScreeningForm() {
    const form = document.getElementById('screening-form');
    const formSteps = document.querySelectorAll('.form-step');
    const nextButtons = document.querySelectorAll('.btn-next');
    const prevButtons = document.querySelectorAll('.btn-prev');
    const reassessButton = document.getElementById('btn-reassess');
    
    const screeningCard = document.getElementById('screening-card');
    const loadingCard = document.getElementById('loading-card');
    const resultsCard = document.getElementById('results-card');
    const loaderText = document.getElementById('loader-text');
    
    const circle = document.getElementById('probability-gauge');
    const radius = circle.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    
    // Set initial dasharray of SVG progress circle
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    circle.style.strokeDashoffset = circumference;
    
    // Step transitions
    nextButtons.forEach(button => {
        button.addEventListener('click', () => {
            const nextStepId = button.getAttribute('data-next');
            if (validateStep(nextStepId - 1)) {
                goToStep(nextStepId);
            }
        });
    });
    
    prevButtons.forEach(button => {
        button.addEventListener('click', () => {
            const prevStepId = button.getAttribute('data-prev');
            goToStep(prevStepId);
        });
    });
    
    function validateStep(currentStep) {
        if (currentStep === 1) {
            const name = document.getElementById('patient-name').value.trim();
            const age = document.getElementById('patient-age').value;
            const gender = document.getElementById('patient-gender').value;
            
            if (!name) {
                alert('Please enter your name.');
                return false;
            }
            if (!age || age < 1 || age > 120) {
                alert('Please enter a valid age between 1 and 120.');
                return false;
            }
            if (!gender) {
                alert('Please select your gender.');
                return false;
            }
        }
        return true;
    }
    
    function goToStep(stepNum) {
        // Toggle steps visibility
        formSteps.forEach(step => {
            step.classList.remove('step-active');
        });
        document.getElementById(`step-${stepNum}`).classList.add('step-active');
        
        // Update indicators
        for (let i = 1; i <= 3; i++) {
            const indicator = document.getElementById(`step-ind-${i}`);
            const line = document.getElementById(`line-${i-1}`);
            
            if (i < stepNum) {
                indicator.classList.remove('active');
                indicator.classList.add('completed');
                if (line) line.classList.add('completed');
            } else if (i == stepNum) {
                indicator.classList.add('active');
                indicator.classList.remove('completed');
                if (line) line.classList.remove('completed');
            } else {
                indicator.classList.remove('active');
                indicator.classList.remove('completed');
                if (line) line.classList.remove('completed');
            }
        }
    }
    
    // Form Submit logic
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Package inputs
        const formData = {
            name: document.getElementById('patient-name').value,
            age: document.getElementById('patient-age').value,
            gender: document.getElementById('patient-gender').value,
            fever: document.getElementById('symp-fever').checked,
            cough: document.getElementById('symp-cough').checked,
            sore_throat: document.getElementById('symp-throat').checked,
            shortness_of_breath: document.getElementById('symp-sob').checked,
            headache: document.getElementById('symp-headache').checked,
            contact: document.getElementById('exposure-contact').checked
        };
        
        // Hide form, show loader
        screeningCard.classList.add('hidden');
        loadingCard.classList.remove('hidden');
        
        // Cycle messages in loader
        const loadingMsgs = [
            "Structuring symptoms matrix...",
            "Computing clinical correlation matrices...",
            "Querying Random Forest trees...",
            "Normalizing class probability distributions..."
        ];
        let msgIndex = 0;
        const loaderInterval = setInterval(() => {
            msgIndex = (msgIndex + 1) % loadingMsgs.length;
            loaderText.textContent = loadingMsgs[msgIndex];
        }, 600);
        
        // POST to Flask
        fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server returned an error response.');
            }
            return response.json();
        })
        .then(data => {
            clearInterval(loaderInterval);
            loadingCard.classList.add('hidden');
            
            if (data.success) {
                // Populate results values
                document.getElementById('results-patient-name').textContent = `${data.name}'s Diagnosis Report`;
                document.getElementById('probability-value').textContent = `${data.probability}%`;
                
                // Animation on circle progress gauge
                const offset = circumference - (data.probability / 100) * circumference;
                circle.style.strokeDashoffset = offset;
                
                // Risk label and colors
                const riskBadge = document.getElementById('risk-badge-value');
                riskBadge.className = 'risk-badge'; // reset
                
                if (data.result === 'Positive') {
                    riskBadge.classList.add('risk-high');
                    riskBadge.textContent = 'High Risk';
                    circle.style.stroke = '#ef4444'; // Red
                } else if (data.probability >= 25.0) {
                    riskBadge.classList.add('risk-medium');
                    riskBadge.textContent = 'Moderate Risk';
                    circle.style.stroke = '#f59e0b'; // Amber
                } else {
                    riskBadge.classList.add('risk-low');
                    riskBadge.textContent = 'Low Risk';
                    circle.style.stroke = '#10b981'; // Green
                }
                
                // Set assessment text summary
                const hasSymptoms = formData.fever || formData.cough || formData.sore_throat || formData.shortness_of_breath || formData.headache;
                let summaryText = "";
                if (data.result === 'Positive') {
                    summaryText = `Based on our AI prediction model, your symptoms and exposure profile show a high probability (${data.probability}%) of COVID-19 infection. Please follow self-isolation directives and get tested immediately.`;
                } else if (data.probability >= 25.0) {
                    summaryText = `Your symptom analysis shows a moderate risk level (${data.probability}% probability). While you are below the positive diagnostics threshold, you are displaying typical symptoms or reported close contact. Monitor your health.`;
                } else {
                    summaryText = `Your risk is evaluated as low (${data.probability}% probability). The reported symptom profile does not align with active COVID-19 indicators. Keep practicing preventive care.`;
                }
                document.getElementById('assessment-summary-text').textContent = summaryText;
                
                // Populate recommendations list
                const recsList = document.getElementById('recommendations-list');
                recsList.innerHTML = '';
                data.recommendations.forEach(rec => {
                    const li = document.createElement('li');
                    li.textContent = rec;
                    recsList.appendChild(li);
                });
                
                resultsCard.classList.remove('hidden');
            } else {
                alert(`Error: ${data.error || 'Failed to analyze symptoms.'}`);
                screeningCard.classList.remove('hidden');
            }
        })
        .catch(err => {
            clearInterval(loaderInterval);
            loadingCard.classList.add('hidden');
            screeningCard.classList.remove('hidden');
            alert(`Network or Application Error: ${err.message}`);
        });
    });
    
    // Reassess event
    reassessButton.addEventListener('click', () => {
        form.reset();
        circle.style.strokeDashoffset = circumference;
        resultsCard.classList.add('hidden');
        screeningCard.classList.remove('hidden');
        goToStep(1);
    });
}

/* ==========================================================================
   ADMIN PORTAL DASHBOARD LOGIC
   ========================================================================== */
function initAdminDashboard() {
    // Render ChartJS visuals
    renderDashboardCharts();
    
    // Wire search and selection filters
    const searchInput = document.getElementById('search-input');
    const filterResult = document.getElementById('filter-result');
    const filterGender = document.getElementById('filter-gender');
    const tableRows = document.querySelectorAll('.prediction-row');
    const emptyRow = document.getElementById('no-records-row');
    
    function applyFilters() {
        const query = searchInput.value.toLowerCase().trim();
        const resultVal = filterResult.value;
        const genderVal = filterGender.value;
        let visibleCount = 0;
        
        tableRows.forEach(row => {
            const name = row.getAttribute('data-name');
            const result = row.getAttribute('data-result');
            const gender = row.getAttribute('data-gender');
            
            const matchQuery = name.includes(query);
            const matchResult = resultVal === 'All' || result === resultVal;
            const matchGender = genderVal === 'All' || gender === genderVal;
            
            if (matchQuery && matchResult && matchGender) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });
        
        if (emptyRow) {
            emptyRow.style.display = visibleCount === 0 ? '' : 'none';
        }
    }
    
    if (searchInput) searchInput.addEventListener('input', applyFilters);
    if (filterResult) filterResult.addEventListener('change', applyFilters);
    if (filterGender) filterGender.addEventListener('change', applyFilters);
    
    // Record deletion action
    const deleteButtons = document.querySelectorAll('.btn-delete-record');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const recordId = btn.getAttribute('data-id');
            if (confirm(`Confirm permanent deletion of assessment record #${recordId}? This operation is irreversible.`)) {
                fetch(`/admin/delete/${recordId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Reload dashboard to update graphics and metrics in real-time
                        window.location.reload();
                    } else {
                        alert(`Error: ${data.error || 'Failed to delete record.'}`);
                    }
                })
                .catch(err => {
                    alert(`Network Error: ${err.message}`);
                });
            }
        });
    });
}

function renderDashboardCharts() {
    if (typeof chartData === 'undefined') return;
    
    const splitCtx = document.getElementById('splitChart').getContext('2d');
    const symptomsCtx = document.getElementById('symptomsChart').getContext('2d');
    
    // Chart 1: Pie chart for Diagnostic Split (Positive vs Negative)
    new Chart(splitCtx, {
        type: 'pie',
        data: {
            labels: ['Positive', 'Negative'],
            datasets: [{
                data: [chartData.positive, chartData.negative],
                backgroundColor: [
                    '#ef4444', // Danger Red
                    '#10b981'  // Success Green
                ],
                borderColor: '#1e293b',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: "'Inter', sans-serif", size: 12 }
                    }
                }
            }
        }
    });
    
    // Chart 2: Column bar chart for Symptoms Distribution
    new Chart(symptomsCtx, {
        type: 'bar',
        data: {
            labels: ['Fever', 'Dry Cough', 'Sore Throat', 'Shortness of Breath', 'Headache', 'Contact Exposure'],
            datasets: [{
                label: 'Logged Frequency',
                data: [
                    chartData.fever,
                    chartData.cough,
                    chartData.sore_throat,
                    chartData.shortness_of_breath,
                    chartData.headache,
                    chartData.contact
                ],
                backgroundColor: '#06b6d4', // Cyan
                borderColor: '#0891b2',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        precision: 0
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}
