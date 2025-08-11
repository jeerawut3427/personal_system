const API_URL = '/api';

const loginForm = document.getElementById('login-form');
const messageArea = document.getElementById('message-area');

function showMessage(message, isSuccess = true) {
    messageArea.textContent = message;
    messageArea.className = `mb-4 text-center p-3 rounded-lg ${isSuccess ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`;
}

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitButton = loginForm.querySelector('button[type="submit"]');
    const username = loginForm.querySelector('#login-username').value;
    const password = loginForm.querySelector('#login-password').value;

    submitButton.disabled = true;
    submitButton.textContent = 'กำลังเข้าสู่ระบบ...';

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'login', payload: { username, password } })
        });
        
        const result = await response.json();

        if (result.status === 'success' && result.user && result.token) {
            // --- การเปลี่ยนแปลง ---
            // 1. เก็บแค่ข้อมูล user ที่ไม่สำคัญและ token
            // 2. ใช้ localStorage แทน sessionStorage เพื่อให้ token อยู่นานกว่า (แต่ยังไม่ปลอดภัยเท่า HttpOnly Cookie)
            localStorage.setItem('currentUser', JSON.stringify(result.user));
            localStorage.setItem('sessionToken', result.token);
            
            window.location.href = '/main.html';
        } else {
            showMessage(result.message || 'เกิดข้อผิดพลาดในการล็อกอิน', false);
            // Re-enable button on failure
            submitButton.disabled = false;
            submitButton.textContent = 'เข้าสู่ระบบ';
        }
    } catch (error) {
        showMessage('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้', false);
        submitButton.disabled = false;
        submitButton.textContent = 'เข้าสู่ระบบ';
    }
});
