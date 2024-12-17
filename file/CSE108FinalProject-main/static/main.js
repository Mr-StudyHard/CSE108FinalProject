function openTab(evt, tabId) {
    // Hide all tab contents
    var tabContents = document.getElementsByClassName("tab-content");
    for (var i = 0; i < tabContents.length; i++) {
        tabContents[i].style.display = "none";
    }

    // Remove "active" class from all tab links
    var tabLinks = document.getElementsByClassName("tab-link");
    for (var i = 0; i < tabLinks.length; i++) {
        tabLinks[i].classList.remove("active");
    }

    // Show the selected tab content and add "active" class to the clicked tab link
    document.getElementById(tabId).style.display = "block";
    evt.currentTarget.classList.add("active");
}

document.getElementById('signinButton').addEventListener('click',async () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        document.getElementById('message').innerText = "All fields are required!";
        return;
    }

    // Prepare the data to send
    const data = {
        username: username,
        password: password
    };

    try {
        // Send POST request to the server
        const response = await fetch('/loginpage', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        // Handle the response
        if (response.ok) {
            const redirectUrl = await response.text(); // The server sends the redirect URL as plain text
            window.location.href = redirectUrl; // Redirect to the dashboard
        } else {
            const errorText = await response.text();
            document.getElementById('message').innerText = `Error: ${errorText}`;
        }
    } catch (error) {
        document.getElementById('message').innerText = `Network error: ${error.message}`;
    }
}); 

// Back button to return to the courses page
function goBack() {
        // Get the current URL
        let currentUrl = window.location.href;
    
        // Remove the last path segment (the last '/')
        let newUrl = currentUrl.replace(/\/[^\/]+$/, '');
        
        // Redirect the browser to the new URL
        window.location.href = newUrl;
}
