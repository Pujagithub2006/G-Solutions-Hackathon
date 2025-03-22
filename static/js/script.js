

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
        if (data.success) {
            alert('Login successful!');
            window.location.href = 'index.html'; // Redirect to home page
        } else {
            alert('Invalid username or password');
        }
    })
    .catch(error => console.error("Error:", error));  // FIX: Corrected syntax for error handling
});

