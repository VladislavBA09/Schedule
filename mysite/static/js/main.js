export function Clean() {
    window.addEventListener('DOMContentLoaded', () => {
        fetch('/cleanup_session', {
            method: 'POST',
            credentials: 'same-origin',
        })
        .then(response => {
            if (response.ok) {
                console.log('Session cleaned successfully');
            } else {
                console.error('Error cleaning session');
            }
        })
        .catch(error => {
            console.error('Error during session cleanup:', error);
        });
    });
}