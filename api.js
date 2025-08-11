// api.js
// Handles all communication with the backend server.

const API_URL = '/api';

export async function sendRequest(action, payload = {}) {
    if (!sessionToken) {
        window.location.href = '/login.html';
        throw new Error('No session token found.');
    }

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            cache: 'no-cache',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify({ action, payload })
        });

        if (response.status === 401) {
            localStorage.removeItem('currentUser');
            localStorage.removeItem('sessionToken');
            window.location.href = '/login.html';
            throw new Error('Unauthorized');
        }

        if (!response.ok) throw new Error(`Network response was not ok. Status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error("API request failed:", error);
        throw new Error('การเชื่อมต่อกับเซิร์ฟเวอร์ล้มเหลว');
    }
}
