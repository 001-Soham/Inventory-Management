document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                if (response.ok) {
                    localStorage.setItem('token', data.access_token);
                    localStorage.setItem('userId', data.user_id);
                    localStorage.setItem('username', data.username);
                    window.location.href = '/dashboard';
                } else {
                    document.getElementById('loginError').textContent = data.error;
                }
            } catch (error) {
                document.getElementById('loginError').textContent = 'Login failed';
            }
        });
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('regUsername').value;
            const password = document.getElementById('regPassword').value;
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                if (response.ok) {
                    alert('Registration successful! Please login.');
                    window.location.href = '/';
                } else {
                    document.getElementById('registerError').textContent = data.error;
                }
            } catch (error) {
                document.getElementById('registerError').textContent = 'Registration failed';
            }
        });
    }
});
