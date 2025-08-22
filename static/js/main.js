// Main JavaScript for Timetable & Attendance System

// Global error handler for datepicker/timepicker issues
window.addEventListener('error', function(e) {
    if (e.message && e.message.includes('datepicker is not a function')) {
        console.warn('Datepicker error detected, initializing fallback...');
        initializePickers();
    } else if (e.message && e.message.includes('timepicker is not a function')) {
        console.warn('Timepicker error detected, initializing fallback...');
        initializePickers();
    }
});

$(document).ready(function() {
    // Initialize tooltips
    try {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    } catch (e) {
        console.warn('Tooltip initialization failed:', e);
    }

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Search functionality
    $('#searchInput').on('keyup', function() {
        var value = $(this).val().toLowerCase();
        $('table tbody tr').filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
        });
    });

    // Attendance marking functionality
    $('.attendance-btn').on('click', function() {
        var studentId = $(this).data('student-id');
        var timetableId = $(this).data('timetable-id');
        var status = $(this).data('status');
        var date = $('#attendance-date').val();

        markAttendance(studentId, timetableId, status, date);
    });

    // Bulk attendance marking
    $('#bulk-attendance-form').on('submit', function(e) {
        e.preventDefault();
        var formData = $(this).serialize();
        
        $.ajax({
            url: '/api/bulk-mark-attendance',
            method: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    showAlert('Attendance marked successfully!', 'success');
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    showAlert('Error marking attendance', 'danger');
                }
            },
            error: function() {
                showAlert('Error marking attendance', 'danger');
            }
        });
    });

    // Timetable generation
    $('#generate-timetable').on('click', function() {
        var loadingBtn = $(this);
        var originalText = loadingBtn.text();
        
        loadingBtn.html('<span class="spinner-border spinner-border-sm me-2"></span>Generating...');
        loadingBtn.prop('disabled', true);

        $.ajax({
            url: '/api/generate-timetable',
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    showAlert('Timetable generated successfully!', 'success');
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    showAlert('Error generating timetable: ' + response.message, 'danger');
                }
            },
            error: function() {
                showAlert('Error generating timetable', 'danger');
            },
            complete: function() {
                loadingBtn.text(originalText);
                loadingBtn.prop('disabled', false);
            }
        });
    });

    // Export functionality
    $('.export-btn').on('click', function() {
        var format = $(this).data('format');
        var type = $(this).data('type');
        
        window.open('/api/export/' + type + '/' + format, '_blank');
    });

    // Real-time notifications
    checkNotifications();
    setInterval(checkNotifications, 30000); // Check every 30 seconds

    // Auto-refresh attendance data
    if ($('#attendance-table').length) {
        setInterval(refreshAttendanceData, 60000); // Refresh every minute
    }

    // Date picker initialization
    if ($.fn.datepicker) {
        $('.date-picker').datepicker({
            format: 'yyyy-mm-dd',
            autoclose: true,
            todayHighlight: true
        });
    } else {
        // Fallback: convert date-picker inputs to HTML5 date inputs
        $('.date-picker').each(function() {
            var $input = $(this);
            if (!$input.attr('type')) {
                $input.attr('type', 'date');
            }
        });
        console.log('jQuery UI datepicker not available, using HTML5 date inputs as fallback');
    }

    // Time picker initialization
    if ($.fn.timepicker) {
        $('.time-picker').timepicker({
            minuteStep: 15,
            showMeridian: false,
            defaultTime: false
        });
    } else {
        // Fallback: convert time-picker inputs to HTML5 time inputs
        $('.time-picker').each(function() {
            var $input = $(this);
            if (!$input.attr('type')) {
                $input.attr('type', 'time');
                $input.attr('step', '900'); // 15 minutes in seconds
            }
        });
        console.log('Bootstrap timepicker not available, using HTML5 time inputs as fallback');
    }

    // Form validation
    $('.needs-validation').on('submit', function(e) {
        if (!this.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        $(this).addClass('was-validated');
    });

    // Modal events
    $('.modal').on('shown.bs.modal', function() {
        $(this).find('input:first').focus();
    });

    // Sidebar toggle for mobile
    $('#sidebarToggle').on('click', function() {
        $('body').toggleClass('sidebar-toggled');
        $('.sidebar').toggleClass('toggled');
    });

    // Print functionality
    $('.print-btn').on('click', function() {
        window.print();
    });

    // Copy to clipboard
    $('.copy-btn').on('click', function() {
        var text = $(this).data('text');
        navigator.clipboard.writeText(text).then(function() {
            showAlert('Copied to clipboard!', 'success');
        });
    });
});

// Function to mark attendance
function markAttendance(studentId, timetableId, status, date) {
    $.ajax({
        url: '/api/mark-attendance',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            student_id: studentId,
            timetable_id: timetableId,
            status: status,
            date: date
        }),
        success: function(response) {
            if (response.success) {
                showAlert('Attendance marked successfully!', 'success');
                updateAttendanceButton(studentId, status);
            } else {
                showAlert('Error marking attendance', 'danger');
            }
        },
        error: function() {
            showAlert('Error marking attendance', 'danger');
        }
    });
}

// Function to update attendance button
function updateAttendanceButton(studentId, status) {
    var btn = $('[data-student-id="' + studentId + '"]');
    var statusClass = '';
    var statusText = '';
    
    switch(status) {
        case 'present':
            statusClass = 'btn-success';
            statusText = 'Present';
            break;
        case 'absent':
            statusClass = 'btn-danger';
            statusText = 'Absent';
            break;
        case 'late':
            statusClass = 'btn-warning';
            statusText = 'Late';
            break;
    }
    
    btn.removeClass('btn-primary btn-success btn-danger btn-warning')
       .addClass(statusClass)
       .text(statusText);
}

// Function to show alerts
function showAlert(message, type) {
    var alertHtml = '<div class="alert alert-' + type + ' alert-dismissible fade show" role="alert">' +
                    message +
                    '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                    '</div>';
    
    $('.container').first().prepend(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
}

// Function to check notifications
function checkNotifications() {
    $.ajax({
        url: '/api/notifications',
        method: 'GET',
        success: function(response) {
            if (response.notifications && response.notifications.length > 0) {
                updateNotificationBadge(response.notifications.length);
                showNotificationToast(response.notifications[0]);
            }
        }
    });
}

// Function to update notification badge
function updateNotificationBadge(count) {
    var badge = $('#notification-badge');
    if (badge.length) {
        badge.text(count);
        badge.show();
    } else {
        $('.navbar-nav .dropdown-toggle').append('<span id="notification-badge" class="badge bg-danger ms-1">' + count + '</span>');
    }
}

// Function to show notification toast
function showNotificationToast(notification) {
    var toastHtml = '<div class="toast" role="alert">' +
                    '<div class="toast-header">' +
                    '<strong class="me-auto">' + notification.title + '</strong>' +
                    '<small>' + notification.created_at + '</small>' +
                    '<button type="button" class="btn-close" data-bs-dismiss="toast"></button>' +
                    '</div>' +
                    '<div class="toast-body">' + notification.message + '</div>' +
                    '</div>';
    
    $('#toast-container').append(toastHtml);
    $('.toast').toast('show');
}

// Function to refresh attendance data
function refreshAttendanceData() {
    $.ajax({
        url: '/api/attendance-data',
        method: 'GET',
        success: function(response) {
            if (response.data) {
                updateAttendanceTable(response.data);
            }
        }
    });
}

// Function to update attendance table
function updateAttendanceTable(data) {
    // Update table with new data
    // This would depend on your specific table structure
    console.log('Attendance data updated:', data);
}

// Function to generate timetable
function generateTimetable() {
    var constraints = {
        courses: $('#courses').val(),
        teachers: $('#teachers').val(),
        classrooms: $('#classrooms').val(),
        timeSlots: $('#time-slots').val()
    };
    
    $.ajax({
        url: '/api/generate-timetable',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(constraints),
        success: function(response) {
            if (response.success) {
                showAlert('Timetable generated successfully!', 'success');
                displayTimetable(response.timetable);
            } else {
                showAlert('Error generating timetable: ' + response.message, 'danger');
            }
        },
        error: function() {
            showAlert('Error generating timetable', 'danger');
        }
    });
}

// Function to display timetable
function displayTimetable(timetableData) {
    var table = $('#timetable-table tbody');
    table.empty();
    
    timetableData.forEach(function(slot) {
        var row = '<tr>' +
                  '<td>' + slot.day + '</td>' +
                  '<td>' + slot.start_time + ' - ' + slot.end_time + '</td>' +
                  '<td>' + slot.course + '</td>' +
                  '<td>' + slot.teacher + '</td>' +
                  '<td>' + slot.classroom + '</td>' +
                  '<td><button class="btn btn-sm btn-outline-primary edit-slot" data-id="' + slot.id + '">Edit</button></td>' +
                  '</tr>';
        table.append(row);
    });
}

// Function to export data
function exportData(type, format) {
    var params = new URLSearchParams();
    params.append('type', type);
    params.append('format', format);
    
    window.open('/api/export?' + params.toString(), '_blank');
}

// Function to validate form
function validateForm(formId) {
    var form = $('#' + formId);
    var isValid = true;
    
    form.find('[required]').each(function() {
        if (!$(this).val()) {
            $(this).addClass('is-invalid');
            isValid = false;
        } else {
            $(this).removeClass('is-invalid');
        }
    });
    
    return isValid;
}

// Function to clear form
function clearForm(formId) {
    $('#' + formId)[0].reset();
    $('#' + formId + ' .is-invalid').removeClass('is-invalid');
}

// Function to confirm action
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Function to format date
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString();
}

// Function to format time
function formatTime(timeString) {
    return timeString.substring(0, 5);
}

// Function to calculate attendance percentage
function calculateAttendancePercentage(present, total) {
    if (total === 0) return 0;
    return Math.round((present / total) * 100);
}

// Function to update progress circle
function updateProgressCircle(percentage) {
    $('.progress-circle').css('background', 
        'conic-gradient(#28a745 0deg ' + (percentage * 3.6) + 'deg, #e9ecef ' + (percentage * 3.6) + 'deg 360deg)'
    );
    $('.percentage').text(percentage + '%');
}

// Enhanced attendance marking functions
function markAllPresent() {
    $('.attendance-radio[value="present"]').prop('checked', true).trigger('change');
    showAlert('All students marked as present', 'success');
}

function markAllAbsent() {
    $('.attendance-radio[value="absent"]').prop('checked', true).trigger('change');
    showAlert('All students marked as absent', 'warning');
}

function clearAllAttendance() {
    $('.attendance-radio').prop('checked', false).trigger('change');
    showAlert('All attendance cleared', 'info');
}

// Filter table rows
function filterTable(status) {
    const rows = document.querySelectorAll('#attendanceTable tbody tr');
    
    rows.forEach(row => {
        if (status === 'all' || row.dataset.status === status) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Update button states
    $('.filter-buttons .btn').removeClass('active');
    $('.filter-buttons .btn[onclick*="' + status + '"]').addClass('active');
}

// Bulk actions for admin
function bulkDeleteUsers() {
    const selectedUsers = $('.user-checkbox:checked');
    if (selectedUsers.length === 0) {
        showAlert('Please select users to delete', 'warning');
        return;
    }
    
    if (confirm('Are you sure you want to delete ' + selectedUsers.length + ' users?')) {
        const userIds = [];
        selectedUsers.each(function() {
            userIds.push($(this).val());
        });
        
        $.ajax({
            url: '/admin/bulk_delete_users',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({user_ids: userIds}),
            success: function(response) {
                if (response.success) {
                    showAlert('Users deleted successfully', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showAlert('Error deleting users', 'danger');
                }
            }
        });
    }
}

// Auto-save functionality
function enableAutoSave(formId) {
    $('#' + formId + ' input, #' + formId + ' select, #' + formId + ' textarea').on('change', function() {
        const formData = $('#' + formId).serialize();
        
        $.ajax({
            url: '/api/autosave',
            method: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    $('.autosave-indicator').text('✓ Saved').removeClass('text-warning').addClass('text-success');
                }
            },
            error: function() {
                $('.autosave-indicator').text('⚠ Error saving').removeClass('text-success').addClass('text-warning');
            }
        });
    });
}

// Dashboard real-time updates
function initializeDashboard() {
    // Update statistics cards with animation
    function animateNumber(element, targetNumber) {
        const startNumber = parseInt(element.text()) || 0;
        const increment = (targetNumber - startNumber) / 20;
        
        let currentNumber = startNumber;
        const timer = setInterval(function() {
            currentNumber += increment;
            if ((increment > 0 && currentNumber >= targetNumber) || 
                (increment < 0 && currentNumber <= targetNumber)) {
                currentNumber = targetNumber;
                clearInterval(timer);
            }
            element.text(Math.floor(currentNumber));
        }, 50);
    }
    
    // Refresh dashboard data
    function refreshDashboardData() {
        $.ajax({
            url: '/api/dashboard-stats',
            method: 'GET',
            success: function(response) {
                if (response.stats) {
                    Object.keys(response.stats).forEach(key => {
                        const element = $('[data-stat="' + key + '"]');
                        if (element.length) {
                            animateNumber(element, response.stats[key]);
                        }
                    });
                }
            }
        });
    }
    
    // Refresh every 5 minutes
    setInterval(refreshDashboardData, 300000);
}

// Enhanced form validation
function setupFormValidation() {
    // Real-time validation
    $('form input[required], form select[required]').on('blur', function() {
        validateField($(this));
    });
    
    // Password strength indicator
    $('input[type="password"]').on('input', function() {
        const password = $(this).val();
        const strength = calculatePasswordStrength(password);
        updatePasswordStrength($(this), strength);
    });
}

function validateField(field) {
    const value = field.val().trim();
    const fieldType = field.attr('type');
    let isValid = true;
    let message = '';
    
    if (field.prop('required') && !value) {
        isValid = false;
        message = 'This field is required';
    } else if (fieldType === 'email' && value && !isValidEmail(value)) {
        isValid = false;
        message = 'Please enter a valid email address';
    } else if (fieldType === 'password' && value && value.length < 6) {
        isValid = false;
        message = 'Password must be at least 6 characters long';
    }
    
    if (isValid) {
        field.removeClass('is-invalid').addClass('is-valid');
        field.siblings('.invalid-feedback').hide();
    } else {
        field.removeClass('is-valid').addClass('is-invalid');
        field.siblings('.invalid-feedback').text(message).show();
    }
    
    return isValid;
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function calculatePasswordStrength(password) {
    let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 10) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    return strength;
}

function updatePasswordStrength(field, strength) {
    const indicator = field.siblings('.password-strength');
    const strengthText = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColors = ['danger', 'warning', 'info', 'success', 'success'];
    
    if (indicator.length) {
        indicator.removeClass('text-danger text-warning text-info text-success')
                .addClass('text-' + strengthColors[strength])
                .text(strengthText[strength]);
    }
}

// Utility function to safely initialize date and time pickers
function initializePickers() {
    // Initialize date pickers
    if ($.fn.datepicker) {
        $('.date-picker').datepicker({
            format: 'yyyy-mm-dd',
            autoclose: true,
            todayHighlight: true
        });
    } else {
        // Fallback: convert date-picker inputs to HTML5 date inputs
        $('.date-picker').each(function() {
            var $input = $(this);
            if (!$input.attr('type')) {
                $input.attr('type', 'date');
            }
        });
        console.log('jQuery UI datepicker not available, using HTML5 date inputs as fallback');
    }

    // Initialize time pickers
    if ($.fn.timepicker) {
        $('.time-picker').timepicker({
            minuteStep: 15,
            showMeridian: false,
            defaultTime: false
        });
    } else {
        // Fallback: convert time-picker inputs to HTML5 time inputs
        $('.time-picker').each(function() {
            var $input = $(this);
            if (!$input.attr('type')) {
                $input.attr('type', 'time');
                $input.attr('step', '900'); // 15 minutes in seconds
            }
        });
        console.log('Bootstrap timepicker not available, using HTML5 time inputs as fallback');
    }
}

// Call the utility function when DOM is ready
$(document).ready(function() {
    initializePickers();
});

// Also call it when new content is loaded (for dynamic content)
$(document).on('shown.bs.modal', function() {
    initializePickers();
});

// Initialize everything when document is ready
$(document).ready(function() {
    initializeDashboard();
    setupFormValidation();
    
    // Add smooth scrolling
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $($(this).attr('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 70
            }, 500);
        }
    });
    
    // Add loading states to forms
    $('form').on('submit', function() {
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.text();
        submitBtn.html('<span class="spinner-border spinner-border-sm me-2"></span>Processing...')
                .prop('disabled', true);
        
        // Re-enable after 10 seconds as fallback
        setTimeout(function() {
            submitBtn.text(originalText).prop('disabled', false);
        }, 10000);
    });
}); 