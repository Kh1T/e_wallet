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
});
