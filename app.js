// app.js
// Main application file for initialization and state management.

import { sendRequest } from './api.js';
import * as ui from './ui.js';
import * as handlers from './handlers.js';
import { escapeHTML } from './utils.js';

// --- Global State and DOM References ---
window.currentUser = null;
window.sessionToken = null;
window.currentWeeklyReports = [];
window.allArchivedReports = {};

// DOM Elements
window.appContainer = null;
window.messageArea = null;
window.welcomeMessage = null;
window.logoutBtn = null;
window.tabs = null;
window.panes = null;
window.statusSubmissionListArea = null;
window.submitStatusTitle = null;
window.submissionFormSection = null;
window.reviewReportSection = null;
window.reviewListArea = null;
window.backToFormBtn = null;
window.confirmSubmitBtn = null;
window.reviewStatusBtn = null;
window.reportContainer = null;
window.exportArchiveBtn = null;
window.archiveContainer = null;
window.archiveYearSelect = null;
window.archiveMonthSelect = null;
window.showArchiveBtn = null;
window.archiveConfirmModal = null;
window.cancelArchiveBtn = null;
window.confirmArchiveBtn = null;
window.personnelListArea = null;
window.addPersonnelBtn = null;
window.personnelModal = null;
window.personnelForm = null;
window.cancelPersonnelBtn = null;
window.importExcelBtn = null;
window.excelImportInput = null;
window.userListArea = null;
window.addUserBtn = null;
window.userModal = null;
window.userForm = null;
window.cancelUserBtn = null;
window.userModalTitle = null;
window.personnelSearchInput = null;
window.personnelSearchBtn = null;
window.userSearchInput = null;
window.userSearchBtn = null;
window.exportMonthlySummaryBtn = null;
window.historyContainer = null;

// --- Main Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    assignDomElements();
    
    try {
        window.currentUser = JSON.parse(localStorage.getItem('currentUser'));
        window.sessionToken = localStorage.getItem('sessionToken');
    } catch (e) {
        window.currentUser = null;
        window.sessionToken = null;
    }

    if (!window.currentUser || !window.sessionToken) {
        localStorage.removeItem('currentUser');
        localStorage.removeItem('sessionToken');
        window.location.href = '/login.html';
        return;
    }
    
    ui.populateRankDropdowns();
    initializePage();
});

function assignDomElements() {
    window.appContainer = document.getElementById('app-container');
    window.messageArea = document.getElementById('message-area');
    window.welcomeMessage = document.getElementById('welcome-message');
    window.logoutBtn = document.getElementById('logout-btn');
    window.tabs = document.querySelectorAll('.tab-button');
    window.panes = document.querySelectorAll('.tab-pane');
    window.statusSubmissionListArea = document.getElementById('status-submission-list-area');
    window.submitStatusTitle = document.getElementById('submit-status-title');
    window.submissionFormSection = document.getElementById('submission-form-section');
    window.reviewReportSection = document.getElementById('review-report-section');
    window.reviewListArea = document.getElementById('review-list-area');
    window.backToFormBtn = document.getElementById('back-to-form-btn');
    window.confirmSubmitBtn = document.getElementById('confirm-submit-btn');
    window.reviewStatusBtn = document.getElementById('review-status-btn');
    window.reportContainer = document.getElementById('report-container');
    window.exportArchiveBtn = document.getElementById('export-archive-btn');
    window.archiveContainer = document.getElementById('archive-container');
    window.archiveYearSelect = document.getElementById('archive-year-select');
    window.archiveMonthSelect = document.getElementById('archive-month-select');
    window.showArchiveBtn = document.getElementById('show-archive-btn');
    window.archiveConfirmModal = document.getElementById('archive-confirm-modal');
    window.cancelArchiveBtn = document.getElementById('cancel-archive-btn');
    window.confirmArchiveBtn = document.getElementById('confirm-archive-btn');
    window.personnelListArea = document.getElementById('personnel-list-area');
    window.addPersonnelBtn = document.getElementById('add-personnel-btn');
    window.personnelModal = document.getElementById('personnel-modal');
    window.personnelForm = document.getElementById('personnel-form');
    window.cancelPersonnelBtn = document.getElementById('cancel-personnel-btn');
    window.importExcelBtn = document.getElementById('import-excel-btn');
    window.excelImportInput = document.getElementById('excel-import-input');
    window.userListArea = document.getElementById('user-list-area');
    window.addUserBtn = document.getElementById('add-user-btn');
    window.userModal = document.getElementById('user-modal');
    window.userForm = document.getElementById('user-form');
    window.cancelUserBtn = document.getElementById('cancel-user-btn');
    window.userModalTitle = document.getElementById('user-modal-title');
    window.personnelSearchInput = document.getElementById('personnel-search-input');
    window.personnelSearchBtn = document.getElementById('personnel-search-btn');
    window.userSearchInput = document.getElementById('user-search-input');
    window.userSearchBtn = document.getElementById('user-search-btn');
    window.exportMonthlySummaryBtn = document.getElementById('export-monthly-summary-btn');
    window.historyContainer = document.getElementById('history-container');
}

function initializePage() {
    appContainer.classList.remove('hidden');
    const userRole = currentUser.role;
    welcomeMessage.textContent = `ล็อกอินในฐานะ: ${escapeHTML(currentUser.username)} (${escapeHTML(userRole)})`;

    const is_admin = (userRole === 'admin');
    document.getElementById('tab-dashboard').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-submit-status').classList.remove('hidden');
    document.getElementById('tab-history').classList.remove('hidden');
    document.getElementById('tab-report').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-archive').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-personnel').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-admin').classList.toggle('hidden', !is_admin);

    if (is_admin) {
        switchTab('tab-dashboard');
    } else {
        switchTab('tab-submit-status');
    }

    logoutBtn.addEventListener('click', async () => {
        try {
            await sendRequest('logout', { token: sessionToken });
        } catch (error) {
            console.error("Logout failed:", error);
        }
        localStorage.removeItem('currentUser');
        localStorage.removeItem('sessionToken');
        window.location.href = '/login.html';
    });

    // Event Listeners
    tabs.forEach(tab => tab.addEventListener('click', () => switchTab(tab.id)));
    if(addPersonnelBtn) addPersonnelBtn.addEventListener('click', () => ui.openPersonnelModal());
    if(cancelPersonnelBtn) cancelPersonnelBtn.addEventListener('click', () => personnelModal.classList.remove('active'));
    if(personnelForm) personnelForm.addEventListener('submit', handlers.handlePersonnelFormSubmit);
    if(personnelListArea) personnelListArea.addEventListener('click', handlers.handlePersonnelListClick);
    if(addUserBtn) addUserBtn.addEventListener('click', () => ui.openUserModal());
    if(cancelUserBtn) cancelUserBtn.addEventListener('click', () => userModal.classList.remove('active'));
    if(userForm) userForm.addEventListener('submit', handlers.handleUserFormSubmit);
    if(userListArea) userListArea.addEventListener('click', handlers.handleUserListClick);
    if(importExcelBtn) importExcelBtn.addEventListener('click', () => excelImportInput.click());
    if(excelImportInput) excelImportInput.addEventListener('change', handlers.handleExcelImport);
    if (reviewStatusBtn) reviewStatusBtn.addEventListener('click', handlers.handleReviewStatus);
    if (backToFormBtn) backToFormBtn.addEventListener('click', () => {
        reviewReportSection.classList.add('hidden');
        submissionFormSection.classList.remove('hidden');
    });
    if (confirmSubmitBtn) confirmSubmitBtn.addEventListener('click', handlers.handleSubmitStatusReport);
    if (exportArchiveBtn) exportArchiveBtn.addEventListener('click', () => {
        if (!currentWeeklyReports || currentWeeklyReports.length === 0) {
            ui.showMessage('ไม่มีข้อมูลรายงานที่จะส่งออก', false);
            return;
        }
        archiveConfirmModal.classList.add('active');
    });
    if (cancelArchiveBtn) cancelArchiveBtn.addEventListener('click', () => archiveConfirmModal.classList.remove('active'));
    if (confirmArchiveBtn) confirmArchiveBtn.addEventListener('click', handlers.handleExportAndArchive);
    if (showArchiveBtn) showArchiveBtn.addEventListener('click', handlers.handleShowArchive);
    if (archiveContainer) archiveContainer.addEventListener('click', handlers.handleArchiveDownloadClick);
    
    if (personnelSearchBtn) {
        personnelSearchBtn.addEventListener('click', () => loadDataForPane('pane-personnel'));
        personnelSearchInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') loadDataForPane('pane-personnel'); });
    }
    if (userSearchBtn) {
        userSearchBtn.addEventListener('click', () => loadDataForPane('pane-admin'));
        userSearchInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') loadDataForPane('pane-admin'); });
    }
    
    if (archiveYearSelect) {
        archiveYearSelect.addEventListener('change', () => {
            const selectedYear = archiveYearSelect.value;
            archiveMonthSelect.innerHTML = '<option value="">เลือกเดือน</option>';
            if (selectedYear && allArchivedReports[selectedYear]) {
                const sortedMonths = Object.keys(allArchivedReports[selectedYear]).sort((a, b) => b - a);
                sortedMonths.forEach(month => {
                    const option = document.createElement('option');
                    option.value = month;
                    option.textContent = new Date(2000, parseInt(month) - 1, 1).toLocaleString('th-TH', { month: 'long' });
                    archiveMonthSelect.appendChild(option);
                });
            }
        });
    }
    if(exportMonthlySummaryBtn) exportMonthlySummaryBtn.addEventListener('click', handlers.handleExportMonthlySummary);
    if(historyContainer) historyContainer.addEventListener('click', handlers.handleHistoryEditClick);
}

// --- Data Loading and Tab Switching ---
window.loadDataForPane = async function(paneId) {
    let searchTerm = '';
    const actions = {
        'pane-dashboard': { action: 'get_dashboard_summary', renderer: ui.renderDashboard, key: 'summary' },
        'pane-personnel': { action: 'list_personnel', renderer: ui.renderPersonnel, key: 'personnel', searchInput: personnelSearchInput },
        'pane-admin': { action: 'list_users', renderer: ui.renderUsers, key: 'users', searchInput: userSearchInput },
        // --- START: การเปลี่ยนแปลง ---
        'pane-submit-status': { action: 'list_personnel', renderer: ui.renderStatusSubmissionForm, key: 'personnel' },
        // --- END: การเปลี่ยนแปลง ---
        'pane-history': { action: 'get_submission_history', renderer: ui.renderSubmissionHistory, key: 'history' },
        'pane-report': { action: 'get_status_reports', renderer: ui.renderWeeklyReport, key: 'reports' },
        'pane-archive': { action: 'get_archived_reports', renderer: (data) => {
            window.allArchivedReports = data || {};
            ui.populateArchiveSelectors(allArchivedReports);
            if(archiveContainer) archiveContainer.innerHTML = '';
        }, key: 'archives' }
    };

    const paneConfig = actions[paneId];
    if (!paneConfig) return;

    if (paneConfig.searchInput) {
        searchTerm = paneConfig.searchInput.value;
    }

    try {
        const res = await sendRequest(paneConfig.action, { searchTerm });
        if (res && res.status === 'success') {
            const dataToRender = res[paneConfig.key];
            if (dataToRender !== undefined) {
                // --- START: การเปลี่ยนแปลง ---
                // ส่ง response object ทั้งหมดไปให้ renderer
                paneConfig.renderer(dataToRender, res);
                // --- END: การเปลี่ยนแปลง ---
            } else {
                ui.showMessage(`เกิดข้อผิดพลาด: ไม่พบข้อมูล '${paneConfig.key}'`, false);
            }
        } else if (res && res.message) {
            ui.showMessage(res.message, false);
        }
    } catch (error) {
        ui.showMessage(error.message, false);
    }
}

window.switchTab = function(tabId) {
    tabs.forEach(tab => {
        const paneId = tab.id.replace('tab-', 'pane-');
        const pane = document.getElementById(paneId);
        if(!pane) return;
        if (tab.id === tabId) {
            tab.classList.add('active');
            pane.classList.remove('hidden');
            loadDataForPane(paneId);
        } else {
            tab.classList.remove('active');
            pane.classList.add('hidden');
        }
    });
}
