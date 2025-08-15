// app.js
// Main application file for initialization and state management.

import { sendRequest } from './api.js';
import * as ui from './ui.js';
import * as handlers from './handlers.js';
import { escapeHTML } from './utils.js';

// --- Global State and DOM References ---
window.currentUser = null;
window.currentWeeklyReports = [];
window.allArchivedReports = {};
window.personnelCurrentPage = 1;
window.userCurrentPage = 1;

// --- Auto Logout Feature ---
let inactivityTimer;
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

function performLogout() {
    clearTimeout(inactivityTimer);
    sendRequest('logout', {}).finally(() => {
        localStorage.removeItem('currentUser');
        window.location.href = '/login.html';
    });
}

function autoLogoutUser() {
    ui.showMessage("คุณไม่มีการใช้งานเป็นเวลานาน ระบบจะทำการออกจากระบบเพื่อความปลอดภัย", false);
    setTimeout(performLogout, 3000);
}

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(autoLogoutUser, INACTIVITY_TIMEOUT_MS);
}

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
window.historyContainer = null;

// --- Main Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    assignDomElements();
    
    try {
        window.currentUser = JSON.parse(localStorage.getItem('currentUser'));
    } catch (e) {
        window.currentUser = null;
    }

    if (!window.currentUser) {
        localStorage.removeItem('currentUser');
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
    window.historyContainer = document.getElementById('history-container');
}

function initializePage() {
    appContainer.classList.remove('hidden');
    const userRole = currentUser.role;
    welcomeMessage.textContent = `ล็อกอินในฐานะ: ${escapeHTML(currentUser.username)} (${escapeHTML(userRole)})`;

    const is_admin = (userRole === 'admin');
    
    // Show/hide tabs based on role
    document.getElementById('tab-user-dashboard').classList.toggle('hidden', is_admin);
    document.getElementById('tab-dashboard').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-submit-status').classList.remove('hidden');
    document.getElementById('tab-history').classList.remove('hidden');
    document.getElementById('tab-report').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-archive').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-personnel').classList.toggle('hidden', !is_admin);
    document.getElementById('tab-admin').classList.toggle('hidden', !is_admin);

    // Determine default tab
    const urlParams = new URLSearchParams(window.location.search);
    let activeTabId = urlParams.get('tab');

    if (!activeTabId || !document.getElementById(`tab-${activeTabId}`)) {
        activeTabId = is_admin ? 'dashboard' : 'user-dashboard';
    }
    
    displayTabContent(`tab-${activeTabId}`);

    logoutBtn.addEventListener('click', () => {
        ui.showCustomConfirm("ยืนยันการออกจากระบบ", "คุณต้องการออกจากระบบใช่หรือไม่?", () => {
            performLogout();
        });
    });

    // --- Setup Inactivity & Back-to-Top Listeners ---
    window.addEventListener('mousemove', resetInactivityTimer);
    window.addEventListener('keydown', resetInactivityTimer);
    window.addEventListener('click', resetInactivityTimer);
    resetInactivityTimer();

    const backToTopBtn = document.getElementById('back-to-top-btn');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTopBtn.classList.remove('hidden');
        } else {
            backToTopBtn.classList.add('hidden');
        }
    });
    backToTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Event Listeners
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.id.replace('tab-', '');
            window.location.href = `main.html?tab=${tabId}`;
        });
    });
    
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
        const searchPersonnel = () => {
            window.personnelCurrentPage = 1;
            loadDataForPane('pane-personnel');
        };
        personnelSearchBtn.addEventListener('click', searchPersonnel);
        personnelSearchInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') searchPersonnel(); });
    }
    if (userSearchBtn) {
        const searchUser = () => {
            window.userCurrentPage = 1;
            loadDataForPane('pane-admin');
        };
        userSearchBtn.addEventListener('click', searchUser);
        userSearchInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') searchUser(); });
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
    if(historyContainer) historyContainer.addEventListener('click', handlers.handleHistoryEditClick);
}

// --- Data Loading and Tab Switching ---
window.loadDataForPane = async function(paneId) {
    let payload = {};
    const actions = {
        'pane-user-dashboard': { action: 'get_user_dashboard_summary', renderer: ui.renderUserDashboard },
        'pane-dashboard': { action: 'get_dashboard_summary', renderer: ui.renderDashboard },
        'pane-personnel': { action: 'list_personnel', renderer: ui.renderPersonnel, searchInput: personnelSearchInput, pageState: 'personnelCurrentPage' },
        'pane-admin': { action: 'list_users', renderer: ui.renderUsers, searchInput: userSearchInput, pageState: 'userCurrentPage' },
        'pane-submit-status': { action: 'list_personnel', renderer: ui.renderStatusSubmissionForm, fetchAll: true },
        'pane-history': { action: 'get_submission_history', renderer: ui.renderSubmissionHistory },
        'pane-report': { action: 'get_status_reports', renderer: ui.renderWeeklyReport },
        'pane-archive': { action: 'get_archived_reports', renderer: (res) => {
            const archives = res.archives;
            window.allArchivedReports = archives || {};
            ui.populateArchiveSelectors(window.allArchivedReports);
            if(window.archiveContainer) window.archiveContainer.innerHTML = '';
        }}
    };

    const paneConfig = actions[paneId];
    if (!paneConfig) return;

    if (paneConfig.searchInput) {
        payload.searchTerm = paneConfig.searchInput.value;
    }
    if (paneConfig.pageState) {
        payload.page = window[paneConfig.pageState];
    }
    if (paneConfig.fetchAll) {
        payload.fetchAll = true;
    }

    try {
        const res = await sendRequest(paneConfig.action, payload);
        if (res && res.status === 'success') {
            if (paneConfig.renderer) {
                paneConfig.renderer(res);
            }
        } else if (res && res.message) {
            ui.showMessage(res.message, false);
        }
    } catch (error) {
        ui.showMessage(error.message, false);
    }
}

function displayTabContent(tabId) {
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
