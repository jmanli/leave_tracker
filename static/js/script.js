// This file can contain general JavaScript for your application
// For example, if you need a common date picker init for all date fields
// Or any generic AJAX handling.

// Example: Initialize Bootstrap tooltips everywhere
document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});