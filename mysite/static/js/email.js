export function setupEmail(){
    const usernameInput = document.getElementById('username');
    const domainSelect = document.getElementById('domain');
    const emailInput = document.getElementById('email');
    const form = document.querySelector('form');
    const fileTypeSelect = document.getElementById('fileType');

    form.addEventListener('submit', (event) => {
        emailInput.value = `${usernameInput.value}@${domainSelect.value}`;

        const fileTypeInput = document.createElement('input');
        fileTypeInput.type = 'hidden';
        fileTypeInput.name = 'fileType';
        fileTypeInput.value = fileTypeSelect.value;

        form.appendChild(fileTypeInput);
    });
}
