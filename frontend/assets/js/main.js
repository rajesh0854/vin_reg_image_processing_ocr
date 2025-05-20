document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const emptyState = document.getElementById('empty-state');
    const selectedFilesList = document.getElementById('selected-files-list');
    const selectedCountEl = document.getElementById('selected-count');
    const resultsContainer = document.getElementById('results-container');
    const processBtn = document.getElementById('process-btn');
    const clearBtn = document.getElementById('clear-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const vehicleType = document.getElementById('vehicle-type');
    const checkType = document.getElementById('check-type');
    const saveImg = document.getElementById('save-img');
    const saveData = document.getElementById('save-data');
    const progressBar = document.getElementById('progress-bar');
    const totalImagesEl = document.getElementById('total-images');
    const passedImagesEl = document.getElementById('passed-images');
    const failedImagesEl = document.getElementById('failed-images');
    const configBar = document.querySelector('.config-bar');

    // State
    let selectedFiles = [];
    let lastScrollTop = 0;
    const MAX_FILES = CONFIG.UPLOAD.MAX_FILES;
    const API_URL = CONFIG.API.BASE_URL + CONFIG.API.CHECK_ENDPOINT;

    // Event Listeners
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelection);
    processBtn.addEventListener('click', processImages);
    clearBtn.addEventListener('click', clearAll);

    // Add animation effect to cards
    const cards = document.querySelectorAll('.card');
    animateCards(cards);

    // Sticky config bar on scroll
    window.addEventListener('scroll', () => {
        const st = window.pageYOffset || document.documentElement.scrollTop;
        
        if (st > 80) {
            configBar.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.08)';
        } else {
            configBar.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.05)';
        }
        
        lastScrollTop = st <= 0 ? 0 : st;
    });

    function animateCards(cards) {
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100 * index);
        });
    }

    // Functions
    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            handleFiles(fileInput.files);
        }
    }

    function handleFiles(files) {
        // Animate the upload button
        uploadBtn.classList.add('highlight-animation');
        setTimeout(() => {
            uploadBtn.classList.remove('highlight-animation');
        }, 800);

        // Check if adding these files would exceed the limit
        if (selectedFiles.length + files.length > MAX_FILES) {
            showNotification(`You can upload a maximum of ${MAX_FILES} images. Please remove some images first.`, 'error');
            return;
        }

        // Process each file
        Array.from(files).forEach(file => {
            // Check if file is an image
            if (!CONFIG.UPLOAD.ALLOWED_TYPES.includes(file.type)) {
                showNotification('Please upload only valid image files.', 'error');
                return;
            }

            // Store file
            const fileId = 'file_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            const fileObj = { id: fileId, file: file };
            selectedFiles.push(fileObj);
            
            // Add file to UI
            addFileToUI(fileObj);
        });
        
        // Enable process button if there are images
        processBtn.disabled = selectedFiles.length === 0;

        // Reset file input
        fileInput.value = '';

        // Update file counter
        updateFileCounter();

        // Show success notification
        if (files.length > 0) {
            showNotification(`${files.length} image${files.length > 1 ? 's' : ''} added successfully.`, 'success');
        }

        // Highlight the config bar to draw attention to the buttons
        configBar.classList.add('highlight-animation');
        setTimeout(() => {
            configBar.classList.remove('highlight-animation');
        }, 800);
        
        // Update empty state visibility
        updateEmptyState();
    }
    
    function addFileToUI(fileObj) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.dataset.id = fileObj.id;
            
            const fileSize = formatBytes(fileObj.file.size);
            
            fileItem.innerHTML = `
                <div class="file-thumb">
                    <img src="${e.target.result}" alt="${fileObj.file.name}">
                </div>
                <div class="file-info">
                    <div class="file-name">${fileObj.file.name}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
                <div class="file-remove" data-id="${fileObj.id}">
                    <i class="fas fa-times"></i>
                </div>
            `;
            
            selectedFilesList.appendChild(fileItem);
            
            // Add event listener to remove button
            const removeBtn = fileItem.querySelector('.file-remove');
            removeBtn.addEventListener('click', (e) => {
                const id = e.currentTarget.dataset.id;
                removeFile(id);
            });
            
            // Add animation effect
            fileItem.style.opacity = '0';
            fileItem.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                fileItem.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                fileItem.style.opacity = '1';
                fileItem.style.transform = 'translateY(0)';
            }, 10);
        };
        
        reader.readAsDataURL(fileObj.file);
    }
    
    function removeFile(id) {
        // Find the index of the file in the array
        const index = selectedFiles.findIndex(file => file.id === id);
        
        if (index !== -1) {
            // Remove from the array
            selectedFiles.splice(index, 1);
            
            // Remove from UI with animation
            const fileItem = document.querySelector(`.file-item[data-id="${id}"]`);
            
            fileItem.style.opacity = '0';
            fileItem.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                fileItem.remove();
                updateFileCounter();
                updateEmptyState();
                
                // Disable process button if no files
                processBtn.disabled = selectedFiles.length === 0;
            }, 300);
        }
    }
    
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    function updateEmptyState() {
        if (selectedFiles.length === 0) {
            emptyState.style.display = 'flex';
            selectedFilesList.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            selectedFilesList.style.display = 'grid';
        }
    }

    function updateFileCounter() {
        // Update the button text and selected count
        selectedCountEl.textContent = `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} selected`;
        
        if (selectedFiles.length > 0) {
            processBtn.innerHTML = `<i class="fas fa-cogs"></i> Process (${selectedFiles.length})`;
            processBtn.classList.add('highlight-animation');
            setTimeout(() => {
                processBtn.classList.remove('highlight-animation');
            }, 800);
        } else {
            processBtn.innerHTML = `<i class="fas fa-cogs"></i> Process`;
            selectedCountEl.textContent = '0 files selected';
        }
    }

    async function processImages() {
        if (selectedFiles.length === 0) {
            showNotification('Please select at least one image to process.', 'error');
            return;
        }

        // Show loading overlay with fade animation
        loadingOverlay.style.display = 'flex';
        setTimeout(() => {
            loadingOverlay.classList.add('active');
        }, 10);
        
        // Get form values
        const vehicle = vehicleType.value;
        const chkType = checkType.value;
        const saveImgValue = saveImg.checked;
        const saveDataValue = saveData.checked;

        // Clear previous results
        resultsContainer.innerHTML = '';
        
        // Reset statistics
        let passedCount = 0;
        let failedCount = 0;
        totalImagesEl.textContent = selectedFiles.length;
        passedImagesEl.textContent = '0';
        failedImagesEl.textContent = '0';
        
        // Show results section
        document.getElementById('results-section').style.display = 'block';
        
        // Process each image
        for (let i = 0; i < selectedFiles.length; i++) {
            // Update progress bar with smoother animation
            const progress = ((i + 1) / selectedFiles.length) * 100;
            progressBar.style.transition = 'width 0.5s ease';
            progressBar.style.width = `${progress}%`;
            
            try {
                const result = await processImage(selectedFiles[i].file, vehicle, chkType, saveImgValue, saveDataValue);
                
                // Display result
                displayResult(result, selectedFiles[i].file);
                
                // Update statistics
                if (result.result && result.result.includes('pass')) {
                    passedCount++;
                } else {
                    failedCount++;
                }
                
                passedImagesEl.textContent = passedCount;
                failedImagesEl.textContent = failedCount;
                
                // Add animation effect to the stats badges
                const statsBadges = document.querySelectorAll('.stats-badge');
                statsBadges.forEach(badge => {
                    badge.classList.add('highlight-stat');
                    setTimeout(() => {
                        badge.classList.remove('highlight-stat');
                    }, 500);
                });
                
            } catch (error) {
                console.error('Error processing image:', error);
                showNotification('An error occurred while processing an image.', 'error');
            }
        }
        
        // Hide loading overlay with fade animation
        loadingOverlay.classList.remove('active');
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
            progressBar.style.width = '0';
        }, 300);
        
        // Show completion notification
        showNotification('All images processed successfully!', 'success');
        
        // Smooth scroll to results section
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
        
        // Animate the result cards
        const resultCards = document.querySelectorAll('.result-card');
        resultCards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100 * index);
        });
    }

    async function processImage(file, vehicle, chkType, saveImg, saveData) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                const base64Image = e.target.result.split(',')[1]; // Remove data:image/jpeg;base64,
                
                const requestData = {
                    client: CONFIG.API.DEFAULTS.CLIENT,
                    vehicle: vehicle,
                    check_type: chkType,
                    user_id: CONFIG.API.DEFAULTS.USER_ID,
                    zone_id: CONFIG.API.DEFAULTS.ZONE_ID,
                    dealer_id: CONFIG.API.DEFAULTS.DEALER_ID,
                    image: base64Image,
                    save_img: "false", // Default false
                    save_data: "false" // Default false
                };
                
                // Override default values if checked
                if (saveImg) {
                    requestData.save_img = "true";
                }
                
                if (saveData) {
                    requestData.save_data = "true";
                }
                
                try {
                    const response = await fetch(API_URL, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestData)
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    resolve(data);
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = (error) => {
                reject(error);
            };
            
            reader.readAsDataURL(file);
        });
    }

    function displayResult(result, file) {
        // Create result card
        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';
        
        // Add result status badge
        const isPass = result.result && result.result.includes('pass');
        const statusBadge = document.createElement('span');
        statusBadge.className = `result-status ${isPass ? 'status-pass' : 'status-fail'}`;
        statusBadge.textContent = isPass ? 'PASS' : 'FAIL';
        resultCard.appendChild(statusBadge);
        
        // Add image (First, as per requirement)
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.alt = file.name;
            img.className = 'result-image';
            img.loading = 'lazy'; // Lazy load images for better performance
            resultCard.appendChild(img);
            
            // Add details container
            const detailsContainer = document.createElement('div');
            detailsContainer.className = 'result-details';
            
            // Add title with request ID
            const title = document.createElement('h3');
            title.textContent = file.name;
            title.title = result.request_id || '';
            detailsContainer.appendChild(title);
            
            // Create row for image_type and image_accuracy (as per requirement)
            const imageInfoRow = document.createElement('div');
            imageInfoRow.className = 'result-info-row';
            
            const imageTypeContainer = document.createElement('div');
            imageTypeContainer.className = 'info-item';
            
            const imageTypeLabel = document.createElement('span');
            imageTypeLabel.className = 'info-label';
            imageTypeLabel.textContent = 'Image Type:';
            
            const imageTypeValue = document.createElement('span');
            imageTypeValue.className = 'info-value';
            imageTypeValue.textContent = result.image_type || 'Unknown';
            
            imageTypeContainer.appendChild(imageTypeLabel);
            imageTypeContainer.appendChild(imageTypeValue);
            
            const imageAccuracyContainer = document.createElement('div');
            imageAccuracyContainer.className = 'info-item';
            
            const imageAccuracyLabel = document.createElement('span');
            imageAccuracyLabel.className = 'info-label';
            imageAccuracyLabel.textContent = 'Image Accuracy:';
            
            const imageAccuracyValue = document.createElement('span');
            imageAccuracyValue.className = 'info-value';
            imageAccuracyValue.textContent = result.image_accuracy ? `${(result.image_accuracy * 100).toFixed(1)}%` : 'N/A';
            
            imageAccuracyContainer.appendChild(imageAccuracyLabel);
            imageAccuracyContainer.appendChild(imageAccuracyValue);
            
            imageInfoRow.appendChild(imageTypeContainer);
            imageInfoRow.appendChild(imageAccuracyContainer);
            
            detailsContainer.appendChild(imageInfoRow);
            
            // Add read_value (as per requirement)
            const readValueContainer = document.createElement('div');
            readValueContainer.className = 'result-detail-box';
            
            const readValueLabel = document.createElement('div');
            readValueLabel.className = 'detail-box-label';
            readValueLabel.textContent = 'Read Value';
            
            const readValueContent = document.createElement('div');
            readValueContent.className = 'detail-box-content';
            readValueContent.textContent = result.read_value || 'N/A';
            
            readValueContainer.appendChild(readValueLabel);
            readValueContainer.appendChild(readValueContent);
            
            detailsContainer.appendChild(readValueContainer);
            
            // Add result (as per requirement)
            const resultValueContainer = document.createElement('div');
            resultValueContainer.className = 'result-detail-box';
            
            const resultValueLabel = document.createElement('div');
            resultValueLabel.className = 'detail-box-label';
            resultValueLabel.textContent = 'Result';
            
            const resultValueContent = document.createElement('div');
            resultValueContent.className = `detail-box-content ${isPass ? 'success-text' : 'error-text'}`;
            resultValueContent.textContent = result.result ? result.result.join(', ') : 'N/A';
            
            resultValueContainer.appendChild(resultValueLabel);
            resultValueContainer.appendChild(resultValueContent);
            
            detailsContainer.appendChild(resultValueContainer);
            
            // Add additional details in collapsible section
            const additionalDetails = document.createElement('div');
            additionalDetails.className = 'additional-details';
            
            const expandBtn = document.createElement('button');
            expandBtn.className = 'expand-btn';
            expandBtn.innerHTML = 'More Details <i class="fas fa-chevron-down"></i>';
            expandBtn.addEventListener('click', () => {
                const detailsContent = additionalDetails.querySelector('.details-content');
                if (detailsContent.style.maxHeight) {
                    detailsContent.style.maxHeight = null;
                    expandBtn.innerHTML = 'More Details <i class="fas fa-chevron-down"></i>';
                } else {
                    detailsContent.style.maxHeight = detailsContent.scrollHeight + 'px';
                    expandBtn.innerHTML = 'Less Details <i class="fas fa-chevron-up"></i>';
                }
            });
            
            const detailsContent = document.createElement('div');
            detailsContent.className = 'details-content';
            
            // Add more details to collapsible section
            addDetailRow(detailsContent, 'Check Type', result.check_type || 'N/A');
            addDetailRow(detailsContent, 'Data Accuracy', result.data_accuracy ? `${(result.data_accuracy * 100).toFixed(1)}%` : 'N/A');
            addDetailRow(detailsContent, 'Request ID', result.request_id || 'N/A');
            addDetailRow(detailsContent, 'User ID', result.user_id || 'N/A');
            addDetailRow(detailsContent, 'Dealer ID', result.dealer_id || 'N/A');
            
            additionalDetails.appendChild(expandBtn);
            additionalDetails.appendChild(detailsContent);
            
            detailsContainer.appendChild(additionalDetails);
            
            resultCard.appendChild(detailsContainer);
            resultsContainer.appendChild(resultCard);
        };
        reader.readAsDataURL(file);
    }

    function addDetailRow(container, label, value, highlight = false) {
        const detailRow = document.createElement('div');
        detailRow.className = 'result-detail';
        
        const labelEl = document.createElement('span');
        labelEl.className = 'label';
        labelEl.textContent = label + ':';
        
        const valueEl = document.createElement('span');
        valueEl.className = highlight ? 'value highlight' : 'value';
        valueEl.textContent = value;
        
        detailRow.appendChild(labelEl);
        detailRow.appendChild(valueEl);
        container.appendChild(detailRow);
    }

    function clearAll() {
        // Clear all selected files
        selectedFiles = [];
        
        // Clear UI
        selectedFilesList.innerHTML = '';
        updateEmptyState();
        
        // Hide results section
        document.getElementById('results-section').style.display = 'none';
        
        // Clear results
        resultsContainer.innerHTML = '';
        
        // Reset statistics
        totalImagesEl.textContent = '0';
        passedImagesEl.textContent = '0';
        failedImagesEl.textContent = '0';
        
        // Disable process button
        processBtn.disabled = true;
        
        // Update the selected count
        updateFileCounter();
        
        // Show notification
        showNotification('All images and results cleared.', 'info');
    }

    // Notification system
    function showNotification(message, type = 'info') {
        // Create notification element if it doesn't exist
        let notificationContainer = document.querySelector('.notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.className = 'notification-container';
            document.body.appendChild(notificationContainer);

            // Add style for notification container if not already in CSS
            const style = document.createElement('style');
            style.textContent = `
                .notification-container {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 9999;
                }
                .notification {
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                    padding: 15px 20px;
                    margin-top: 10px;
                    display: flex;
                    align-items: center;
                    transition: all 0.3s ease;
                    transform: translateX(100%);
                    opacity: 0;
                    overflow: hidden;
                    max-width: 350px;
                    border-left: 4px solid transparent;
                }
                .notification.show {
                    transform: translateX(0);
                    opacity: 1;
                }
                .notification-success {
                    border-left-color: var(--success-color);
                }
                .notification-error {
                    border-left-color: var(--danger-color);
                }
                .notification-info {
                    border-left-color: var(--primary-color);
                }
                .notification-icon {
                    margin-right: 15px;
                    font-size: 1.2rem;
                }
                .notification-success .notification-icon {
                    color: var(--success-color);
                }
                .notification-error .notification-icon {
                    color: var(--danger-color);
                }
                .notification-info .notification-icon {
                    color: var(--primary-color);
                }
                .notification-content {
                    flex: 1;
                }
                .notification-message {
                    color: var(--text-color);
                    font-size: 0.95rem;
                }
                .notification-close {
                    color: var(--text-light);
                    cursor: pointer;
                    font-size: 0.9rem;
                    padding: 5px;
                    margin-left: 10px;
                    opacity: 0.7;
                    transition: opacity 0.2s ease;
                }
                .notification-close:hover {
                    opacity: 1;
                }
                .notification-progress {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 3px;
                }
                .notification-success .notification-progress {
                    background-color: var(--success-color);
                }
                .notification-error .notification-progress {
                    background-color: var(--danger-color);
                }
                .notification-info .notification-progress {
                    background-color: var(--primary-color);
                }
                
                .highlight-stat {
                    animation: pulse 0.5s ease;
                }
                
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                
                .highlight-animation {
                    animation: highlight-pulse 0.8s cubic-bezier(0.16, 1, 0.3, 1);
                }
                
                .pulse-animation {
                    animation: pulse-effect 0.8s ease;
                }
                
                @keyframes pulse-effect {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.08); box-shadow: 0 0 20px rgba(67, 97, 238, 0.2); }
                    100% { transform: scale(1); }
                }
                
                .upload-area.cleared {
                    background-color: rgba(76, 201, 240, 0.1);
                    border-color: rgba(76, 201, 240, 0.4);
                    transition: all 0.3s ease;
                }

                .loading-overlay {
                    display: none;
                    opacity: 0;
                    visibility: visible;
                }
            `;
            document.head.appendChild(style);
        }

        // Create notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        // Icon based on type
        let iconClass = 'fa-info-circle';
        if (type === 'success') iconClass = 'fa-check-circle';
        if (type === 'error') iconClass = 'fa-exclamation-circle';
        
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="fas ${iconClass}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-message">${message}</div>
            </div>
            <div class="notification-close">
                <i class="fas fa-times"></i>
            </div>
            <div class="notification-progress"></div>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Progress animation
        const progress = notification.querySelector('.notification-progress');
        progress.style.width = '100%';
        progress.style.transition = `width ${CONFIG.UI.NOTIFICATION_TIMEOUT}ms linear`;
        
        setTimeout(() => {
            progress.style.width = '0';
        }, 100);
        
        // Close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            hideNotification(notification);
        });
        
        // Auto close after timeout
        const timeout = setTimeout(() => {
            hideNotification(notification);
        }, CONFIG.UI.NOTIFICATION_TIMEOUT);
        
        // Store timeout ID
        notification.dataset.timeoutId = timeout;
        
        // Pause timer on hover
        notification.addEventListener('mouseenter', () => {
            clearTimeout(parseInt(notification.dataset.timeoutId));
            progress.style.transition = 'none';
        });
        
        // Resume timer on leave
        notification.addEventListener('mouseleave', () => {
            const timeRemaining = parseFloat(getComputedStyle(progress).width) / parseFloat(getComputedStyle(notification).width) * CONFIG.UI.NOTIFICATION_TIMEOUT;
            progress.style.transition = `width ${timeRemaining}ms linear`;
            progress.style.width = '0';
            
            const newTimeout = setTimeout(() => {
                hideNotification(notification);
            }, timeRemaining);
            
            notification.dataset.timeoutId = newTimeout;
        });
    }
    
    function hideNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, CONFIG.UI.ANIMATION_SPEED);
    }
    
    // Initialize empty state
    updateEmptyState();
}); 