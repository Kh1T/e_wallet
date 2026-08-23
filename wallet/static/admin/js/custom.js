// Handle responsive sidebar behavior
document.addEventListener('DOMContentLoaded', function() {
    var sidebar = document.querySelector('.main-sidebar');
    var body = document.body;
    var controlSidebar = document.querySelector('.control-sidebar');
    
    // Check screen size
    function handleResize() {
        var width = window.innerWidth;
        
        if (width >= 1200) {
            // Large screen: always expanded
            body.classList.remove('sidebar-collapse', 'sidebar-mini');
        } else if (width >= 992) {
            // Medium screen: allow collapse on hover
            body.classList.add('sidebar-collapse');
        } else {
            // Small screen: hidden by default
            body.classList.remove('sidebar-open');
        }
    }
    
    // Initial check
    handleResize();
    
    // Listen for resize
    window.addEventListener('resize', handleResize);
    
    // Sidebar toggle button functionality for mobile
    var toggles = document.querySelectorAll('[data-widget="pushmenu"]');
    toggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            if (window.innerWidth < 992) {
                // Mobile: toggle sidebar open/closed
                body.classList.toggle('sidebar-open');
            }
            e.preventDefault();
        });
    });
    
    // UI Builder (Control Sidebar) toggle
    var uiBuilderToggles = document.querySelectorAll('[data-slide="true"], .control-sidebar-btn');
    uiBuilderToggles.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            if (controlSidebar) {
                controlSidebar.classList.toggle('control-sidebar-open');
                body.classList.toggle('control-sidebar-open');
            }
        });
    });
    
    // Close control sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (controlSidebar && controlSidebar.classList.contains('control-sidebar-open')) {
            if (!controlSidebar.contains(e.target) && 
                !e.target.closest('[data-slide="true"]') && 
                !e.target.closest('.control-sidebar-btn')) {
                controlSidebar.classList.remove('control-sidebar-open');
                body.classList.remove('control-sidebar-open');
            }
        }
    });
    
    // Fix filter dropdowns - add "All" option with separator
    function fixFilterDropdowns() {
        // Target ALL select elements on the page
        var allSelects = document.querySelectorAll('select');
        
        allSelects.forEach(function(select) {
            // Skip if already processed
            if (select.dataset.fixed === 'true') return;
            
            var options = Array.from(select.options);
            var labelText = select.getAttribute('name') || select.id || '';
            labelText = labelText.replace(/_/g, ' ').toLowerCase().trim();
            
            // First, remove unwanted options (labels, empty, dashes)
            options.forEach(function(option) {
                var text = option.textContent.trim();
                var value = option.value;
                var lowerText = text.toLowerCase();
                
                // Remove "--------" empty option
                if (text === "--------") {
                    option.remove();
                }
                // Remove field name labels
                else if (value === "" && (
                    lowerText === labelText || 
                    lowerText === select.getAttribute('name') ||
                    lowerText.includes('status') && labelText.includes('status') ||
                    lowerText.includes('role') && labelText.includes('role') ||
                    lowerText.includes('date') && labelText.includes('date') ||
                    option.disabled
                )) {
                    option.remove();
                }
                // Remove any empty value option
                else if (value === "" && text !== "All (default)") {
                    option.remove();
                }
            });
            
            // Add "All (default)" option at the beginning
            var allOption = document.createElement('option');
            allOption.value = "";
            allOption.textContent = "All (default)";
            allOption.selected = true;
            select.insertBefore(allOption, select.options[0]);
            
            // Add separator option
            var separator = document.createElement('option');
            separator.value = "";
            separator.textContent = "────────────────";
            separator.disabled = true;
            select.insertBefore(separator, select.options[1]);
            
            // Mark as processed
            select.dataset.fixed = 'true';
        });
    }
    
    // Run immediately
    fixFilterDropdowns();
    
    // Run multiple times to catch dynamically loaded content
    setTimeout(fixFilterDropdowns, 100);
    setTimeout(fixFilterDropdowns, 300);
    setTimeout(fixFilterDropdowns, 500);
    setTimeout(fixFilterDropdowns, 1000);
    
    // Also run when DOM changes (for SPAs or dynamic content)
    var observer = new MutationObserver(function(mutations) {
        fixFilterDropdowns();
    });
    observer.observe(document.body, { childList: true, subtree: true });
});
