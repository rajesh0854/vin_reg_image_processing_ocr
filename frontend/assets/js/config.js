/**
 * Configuration file for Image Analysis System
 * Modify these settings according to your requirements
 */

const CONFIG = {
    // API Configuration
    API: {
        // Base URL for the API endpoint
        BASE_URL: 'http://127.0.0.1:5001',
        
        // API endpoint path for VIN/registration check
        CHECK_ENDPOINT: '/vin_reg_check',
        
        // Default values for API requests
        DEFAULTS: {
            CLIENT: 'hero',
            USER_ID: 'user101',
            ZONE_ID: 'zone202',
            DEALER_ID: 'dealer103'
        }
    },
    
    // Upload Configuration
    UPLOAD: {
        // Maximum number of images allowed to upload at once
        MAX_FILES: 50,
        
        // Allowed image types (mime types)
        ALLOWED_TYPES: ['image/jpeg', 'image/png', 'image/jpg']
    },
    
    // UI Configuration
    UI: {
        // Animation speed for transitions (in milliseconds)
        ANIMATION_SPEED: 300,
        
        // Auto-close notifications after this time (in milliseconds)
        NOTIFICATION_TIMEOUT: 5000
    }
};

// Apply configuration values to UI elements when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Set maximum files limit in the UI
    const maxFilesEl = document.getElementById('max-files-limit');
    if (maxFilesEl) {
        maxFilesEl.textContent = CONFIG.UPLOAD.MAX_FILES;
    }
}); 