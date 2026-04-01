document.addEventListener('DOMContentLoaded', async function() {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    
    if (!token) {
        window.location.href = '/';
        return;
    }
    
    // Set username in navbar
    document.getElementById('usernameDisplay').textContent = username;
    
    // Load items and transactions
    await loadItems();
    await loadTransactions();
    
    // Event listeners
    setupEventListeners();
    
    function setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                
                // Update active tab
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                e.target.classList.add('active');
                document.getElementById(tab).classList.add('active');
            });
        });
        
        // Receive form
        document.getElementById('receiveBtn').addEventListener('click', handleReceive);
        document.getElementById('receiveQty').addEventListener('input', updateReceiveBtn);
        
        // Issue form
        document.getElementById('issueBtn').addEventListener('click', handleIssue);
        document.getElementById('issueQty').addEventListener('input', updateIssueBtn);
        
        // Logout
        document.getElementById('logoutBtn').addEventListener('click', logout);
    }
    
    async function apiCall(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
        
        const response = await fetch(endpoint, {
            ...options,
            headers: { ...options.headers, ...headers }
        });
        
        if (response.status === 401) {
            logout();
            return null;
        }
        
        return response.json();
    }
    
    async function loadItems() {
        try {
            const items = await apiCall('/api/predefined_items');
            
            // Populate both dropdowns
            const receiveSelect = document.getElementById('receiveItem');
            const issueSelect = document.getElementById('issueItem');
            
            receiveSelect.innerHTML = '<option value="">Choose item...</option>';
            issueSelect.innerHTML = '<option value="">Choose item...</option>';
            
            items.forEach(item => {
                const option1 = new Option(item.name, item.id);
                const option2 = new Option(`${item.name} (Stock: ${item.quantity})`, item.id);
                
                receiveSelect.add(option1);
                issueSelect.add(option2);
            });
            
            updateIssueBtn();
        } catch (error) {
            console.error('Error loading items:', error);
        }
    }
    
    async function loadTransactions() {
        try {
            const transactions = await apiCall('/api/transactions');
            const tbody = document.querySelector('#historyTable tbody');
            tbody.innerHTML = '';
            
            transactions.forEach(t => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${new Date(t.date).toLocaleString()}</td>
                    <td>${t.item_name}</td>
                    <td>${t.quantity}</td>
                    <td>
                        <span class="status ${t.type === 'receive' ? 'receive' : 'issue'}">
                            ${t.type.toUpperCase()}
                        </span>
                    </td>
                    <td>$${t.unit_price.toFixed(2)}</td>
                    <td>$${t.total_amount.toFixed(2)}</td>
                `;
            });
        } catch (error) {
            console.error('Error loading transactions:', error);
        }
    }
    
    async function handleReceive() {
        const itemId = document.getElementById('receiveItem').value;
        const quantity = parseInt(document.getElementById('receiveQty').value);
        const unitPrice = parseFloat(document.getElementById('receivePrice').value) || 0;
        
        if (!itemId || !quantity || quantity <= 0) {
            showMessage('receiveMsg', 'Please select item and enter valid quantity', 'error');
            return;
        }
        
        try {
            const result = await apiCall('/api/receive', {
                method: 'POST',
                body: JSON.stringify({ item_id: itemId, quantity, unit_price: unitPrice })
            });
            
            if (result) {
                showMessage('receiveMsg', result.message, 'success');
                document.getElementById('receiveForm').reset();
                await loadItems();
                await loadTransactions();
            }
        } catch (error) {
            showMessage('receiveMsg', 'Failed to receive item', 'error');
        }
    }
    
    async function handleIssue() {
        const itemId = document.getElementById('issueItem').value;
        const quantity = parseInt(document.getElementById('issueQty').value);
        
        if (!itemId || !quantity || quantity <= 0) {
            showMessage('issueMsg', 'Please select item and enter valid quantity', 'error');
            return;
        }
        
        try {
            const result = await apiCall('/api/issue', {
                method: 'POST',
                body: JSON.stringify({ item_id: itemId, quantity })
            });
            
            if (result) {
                showMessage('issueMsg', result.message, 'success');
                document.getElementById('issueForm').reset();
                await loadItems();
                await loadTransactions();
            }
        } catch (error) {
            showMessage('issueMsg', error.message || 'Failed to issue item', 'error');
        }
    }
    
    function updateReceiveBtn() {
        const qty = document.getElementById('receiveQty').value;
        const btn = document.getElementById('receiveBtn');
        btn.disabled = !qty || parseInt(qty) <= 0;
    }
    
    function updateIssueBtn() {
        const itemId = document.getElementById('issueItem').value;
        const qty = document.getElementById('issueQty').value;
        const btn = document.getElementById('issueBtn');
        
        if (!itemId || !qty || parseInt(qty) <= 0) {
            btn.disabled = true;
            document.getElementById('availableQty').textContent = '';
            return;
        }
        
        // Show available quantity
        const selectedOption = document.getElementById('issueItem').selectedOptions[0];
        const available = selectedOption.text.match(/Stock:\s*(\d+)/);
        if (available) {
            document.getElementById('availableQty').textContent = `Available: ${available[1]}`;
        }
        
        btn.disabled = parseInt(qty) <= 0;
    }
    
    function showMessage(elementId, message, type) {
        const msgEl = document.getElementById(elementId);
        msgEl.textContent = message;
        msgEl.className = `message ${type}`;
        setTimeout(() => {
            msgEl.textContent = '';
            msgEl.className = 'message';
        }, 5000);
    }
    
    function logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        window.location.href = '/';
    }
});
