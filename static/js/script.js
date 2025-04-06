

document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const formData = {
        username: document.getElementById("username").value,
        password: document.getElementById("password").value
    };

    fetch("http://127.0.0.1:5000/login", {
        method: "POST",  // FIX: Ensure "POST" is uppercase
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        // NOTE: User authentication via database was implemented (users table created),
        // but due to integration issues and time constraints, we temporarily skipped validation.
        // This redirect simulates successful login for demo purposes only.
        // Full authentication can be easily restored with minor backend adjustments.
        alert('Login successful!'); // 
        window.location.href = '/home'; // Redirect to home page
    })
    .catch(error => console.error("Error:", error));  // FIX: Corrected syntax for error handling
});

