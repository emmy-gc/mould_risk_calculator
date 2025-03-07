document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileNameDisplay = document.getElementById('file-name');
    const form = document.getElementById('upload-form');
    const uploadMessage = document.getElementById('upload-message');
    const dropZone = document.getElementById('drop-zone');
    const submitBtn = document.getElementById('submit-btn');

    browseBtn.addEventListener('click', () => {
        fileInput.click();
    });

   
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            handleFileSelection(file);
        }
    });

   
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length) {
            const file = e.dataTransfer.files[0];
            fileInput.files = e.dataTransfer.files;
            handleFileSelection(file);
        }
    });

    
    function handleFileSelection(file) {
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showMessage('Please upload a CSV file.', 'error');
            fileInput.value = '';
            submitBtn.disabled = true;
            return;
        }

        fileNameDisplay.textContent = `Selected file: ${file.name}`;
        submitBtn.disabled = false;
        uploadMessage.style.display = 'none';
    }

   
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        uploadMessage.style.display = 'none';

        try {
            const formData = new FormData(this);
            const url = this.dataset.url;
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';

            const response = await fetch(url, {
                method: "POST",
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();
            
            if (data.error) {
                showMessage(data.error, 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Calculate Mold Risk';
            } else if (data.redirect_url) {
                window.location.href = data.redirect_url;
            }
        } catch (error) {
            showMessage('An error occurred while processing your request.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Calculate Mold Risk';
        }
    });


    function showMessage(message, type) {
        uploadMessage.textContent = message;
        uploadMessage.className = `upload-message ${type}`;
        uploadMessage.style.display = 'block';
    }
});