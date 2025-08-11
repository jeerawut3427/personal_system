// ui.js
// Contains all functions related to updating and rendering the user interface.

import { escapeHTML, formatThaiDate } from './utils.js';

// การแก้ไข: ทุกฟังก์ชันจะเข้าถึงตัวแปร DOM ผ่าน window object

export function showMessage(message, isSuccess = true) {
    if (!window.messageArea) return;
    window.messageArea.textContent = message;
    window.messageArea.className = `mb-4 text-center p-3 rounded-lg ${isSuccess ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`;
    setTimeout(() => { if(window.messageArea) { window.messageArea.innerHTML = ''; window.messageArea.className = 'mb-4 text-center'; } }, 5000);
}

export function populateRankDropdowns() {
    const ranks = {
        'นายทหารสัญญาบัตร (ชาย)': ['น.อ.(พ)', 'น.อ.หม่อมหลวง', 'น.อ.', 'น.ท.', 'น.ต.', 'ร.อ.', 'ร.ท.', 'ร.ต.'],
        'นายทหารสัญญาบัตร (หญิง)': ['น.อ.(พ).หญิง', 'น.อ.หญิง', 'น.ท.หญิง', 'น.ต.หญิง', 'ร.อ.หญิง', 'ร.ท.หญิง', 'ร.ต.หญิง'],
        'นายทหารประทวน (ชาย)': ['พ.อ.อ.(พ)', 'พ.อ.อ.', 'พ.อ.ท.', 'พ.อ.ต.', 'จ.อ.', 'จ.ท.', 'จ.ต.'],
        'นายทหารประทวน (หญิง)': ['พ.อ.อ.หญิง', 'พ.อ.ท.หญิง', 'พ.อ.ต.หญิง', 'จ.อ.หญิง', 'จ.ท.หญิง', 'จ.ต.หญิง'],
        'พลเรือน': ['นาย', 'นาง', 'นางสาว']
    };
    const rankSelects = [document.getElementById('person-rank'), document.getElementById('user-rank')];
    rankSelects.forEach(select => {
        if (!select) return;
        select.innerHTML = '<option value="">-- กรุณาเลือก --</option>';
        for (const groupName in ranks) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = groupName;
            ranks[groupName].forEach(rank => {
                const option = document.createElement('option');
                option.value = rank;
                option.textContent = rank;
                optgroup.appendChild(option);
            });
            select.appendChild(optgroup);
        }
    });
}

export function renderDashboard(summary) {
    if (!summary) return;
    const totalPersonnelEl = document.getElementById('dashboard-total-personnel');
    const onDutyEl = document.getElementById('dashboard-on-duty');
    const statusSummaryArea = document.getElementById('dashboard-status-summary');
    const deptStatusArea = document.getElementById('dashboard-department-status');

    if(totalPersonnelEl) totalPersonnelEl.textContent = summary.total_personnel || '0';
    if(onDutyEl) onDutyEl.textContent = summary.total_on_duty || '0';
    
    if(statusSummaryArea) {
        statusSummaryArea.innerHTML = '';
        if (summary.status_summary && Object.keys(summary.status_summary).length > 0) {
            for (const [status, count] of Object.entries(summary.status_summary)) {
                const p = document.createElement('p');
                p.textContent = `${escapeHTML(status)}: ${count} นาย`;
                statusSummaryArea.appendChild(p);
            }
        } else {
            statusSummaryArea.textContent = 'ยังไม่มีรายงาน';
        }
    }

    if(deptStatusArea) {
        deptStatusArea.innerHTML = '';
        if (summary.all_departments && summary.all_departments.length > 0) {
            summary.all_departments.forEach(dept => {
                const isSubmitted = summary.submitted_departments.includes(dept);
                const card = document.createElement('div');
                card.className = `p-3 rounded-lg border ${isSubmitted ? 'bg-green-100 border-green-300' : 'bg-red-100 border-red-300'}`;
                card.innerHTML = `
                    <p class="font-semibold text-sm ${isSubmitted ? 'text-green-800' : 'text-red-800'}">${escapeHTML(dept)}</p>
                    <p class="text-xs ${isSubmitted ? 'text-green-600' : 'text-red-600'}">${isSubmitted ? 'ส่งแล้ว' : 'ยังไม่ส่ง'}</p>
                `;
                deptStatusArea.appendChild(card);
            });
        } else {
            deptStatusArea.innerHTML = '<p class="text-gray-500 col-span-full">ไม่พบข้อมูลแผนก</p>';
        }
    }
}

export function renderPersonnel(personnel) {
    if(!window.personnelListArea) return;
    window.personnelListArea.innerHTML = '';
    if (!personnel || personnel.length === 0) {
        window.personnelListArea.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-gray-500">ไม่พบข้อมูลกำลังพล</td></tr>';
        return;
    }
    personnel.forEach((p, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `<td class="px-4 py-2">${index + 1}</td>
                         <td class="px-4 py-2">${escapeHTML(p.rank)}</td>
                         <td class="px-4 py-2">${escapeHTML(p.first_name)}</td>
                         <td class="px-4 py-2">${escapeHTML(p.last_name)}</td>
                         <td class="px-4 py-2">${escapeHTML(p.position)}</td>
                         <td class="px-4 py-2">${escapeHTML(p.specialty)}</td>
                         <td class="px-4 py-2">${escapeHTML(p.department)}</td>
                         <td class="px-4 py-2 whitespace-nowrap">
                            <button data-id='${escapeHTML(p.id)}' class="edit-person-btn text-blue-600 hover:text-blue-900 mr-2">แก้ไข</button>
                            <button data-id='${escapeHTML(p.id)}' class="delete-person-btn text-red-600 hover:text-red-900">ลบ</button>
                         </td>`;
        window.personnelListArea.appendChild(row);
    });
}

export function renderUsers(users) {
    if(!window.userListArea) return;
    window.userListArea.innerHTML = '';
     if (!users || users.length === 0) {
        window.userListArea.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">ไม่พบข้อมูลผู้ใช้</td></tr>';
        return;
    }
    users.forEach(u => {
        const row = document.createElement('tr');
        const roleText = u.role === 'admin' ? 'Admin' : 'User';
        const roleClass = u.role === 'admin' ? 'text-red-600 font-semibold' : 'text-gray-600';
        row.innerHTML = `<td class="px-4 py-2 font-mono">${escapeHTML(u.username)}</td>
                         <td class="px-4 py-2">${escapeHTML(u.rank)} ${escapeHTML(u.first_name)} ${escapeHTML(u.last_name)}</td>
                         <td class="px-4 py-2">${escapeHTML(u.position)}</td>
                         <td class="px-4 py-2">${escapeHTML(u.department)}</td>
                         <td class="px-4 py-2 ${roleClass}">${escapeHTML(roleText)}</td>
                         <td class="px-4 py-2 whitespace-nowrap">
                            <button data-username='${escapeHTML(u.username)}' class="edit-user-btn text-blue-600 hover:text-blue-900 mr-2">แก้ไข</button>
                            <button data-username='${escapeHTML(u.username)}' class="delete-user-btn text-red-600 hover:text-red-900">ลบ</button>
                         </td>`;
        window.userListArea.appendChild(row);
    });
}

export function renderStatusSubmissionForm(personnel) {
    if(!window.statusSubmissionListArea || !window.submitStatusTitle) return;
    window.statusSubmissionListArea.innerHTML = '';
    window.submitStatusTitle.textContent = `ส่งยอดกำลังพล แผนก ${escapeHTML(window.currentUser.department)}`;
    if (!personnel || personnel.length === 0) {
        window.statusSubmissionListArea.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">ไม่พบข้อมูลกำลังพลในแผนกของคุณ</td></tr>';
        return;
    }
    personnel.forEach((p, index) => {
        const row = document.createElement('tr');
        const personnelName = `${escapeHTML(p.rank)} ${escapeHTML(p.first_name)} ${escapeHTML(p.last_name)}`;
        row.dataset.personnelId = escapeHTML(p.id);
        row.dataset.personnelName = personnelName;
        row.innerHTML = `
            <td class="px-4 py-2">${index + 1}</td><td class="px-4 py-2">${personnelName}</td>
            <td class="px-4 py-2">
                <select class="status-select w-full border rounded px-2 py-1 bg-white">
                    <option value="ไม่มี">ไม่มี</option><option value="ราชการ">ราชการ</option><option value="คุมงาน">คุมงาน</option>
                    <option value="ศึกษา">ศึกษา</option><option value="ลากิจ">ลากิจ</option><option value="ลาพักผ่อน">ลาพักผ่อน</option>
                </select>
            </td>
            <td class="px-4 py-2"><input type="text" class="details-input w-full border rounded px-2 py-1" placeholder="รายละเอียด/สถานที่..."></td>
            <td class="px-4 py-2"><input type="date" class="start-date-input w-full border rounded px-2 py-1"></td>
            <td class="px-4 py-2"><input type="date" class="end-date-input w-full border rounded px-2 py-1"></td>
        `;
        window.statusSubmissionListArea.appendChild(row);
    });
}

export function renderWeeklyReport(reports) {
    if(!window.reportContainer) return;
    window.reportContainer.innerHTML = '';
    window.currentWeeklyReports = reports;
    if (!reports || reports.length === 0) {
        window.reportContainer.innerHTML = '<p class="text-center text-gray-500">ยังไม่มีรายงานในระบบ</p>';
        return;
    }

    const reportsByDept = reports.reduce((acc, report) => {
        const dept = report.department || 'ไม่ระบุแผนก';
        if (!acc[dept]) {
            acc[dept] = [];
        }
        acc[dept].push(report);
        return acc;
    }, {});

    window.reportContainer.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6';

    for (const department in reportsByDept) {
        const deptReports = reportsByDept[department];
        
        const card = document.createElement('div');
        card.className = 'bg-white p-4 rounded-lg shadow border border-gray-200 flex flex-col';

        const cardHeader = document.createElement('h3');
        cardHeader.className = 'text-lg font-semibold mb-3 text-gray-800 border-b pb-2';
        cardHeader.textContent = `แผนก: ${escapeHTML(department)}`;
        card.appendChild(cardHeader);

        const cardBody = document.createElement('div');
        cardBody.className = 'space-y-4 mt-2';
        
        deptReports.forEach(report => {
            const reportContent = document.createElement('div');
            
            let itemsHtml = report.items.map(item => `
                <tr class="border-t">
                    <td class="py-2 pr-2 text-sm text-gray-700">${escapeHTML(item.personnel_name)}</td>
                    <td class="py-2 px-2 text-sm text-blue-600 font-medium">${escapeHTML(item.status)}</td>
                    <td class="py-2 pl-2 text-sm text-gray-500">${escapeHTML(item.details) || '-'}</td>
                </tr>
            `).join('');

            reportContent.innerHTML = `
                <div class="flex justify-between items-center text-sm text-gray-500 mb-2">
                    <span>ส่งโดย: ${escapeHTML(report.submitted_by)}</span>
                    <span>${new Date(report.timestamp).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })} น.</span>
                </div>
                <table class="w-full text-left">
                    <thead>
                        <tr>
                            <th class="text-left text-xs font-medium text-gray-500 uppercase pb-1 w-2/5">ชื่อ-สกุล</th>
                            <th class="text-left text-xs font-medium text-gray-500 uppercase pb-1 w-1/5">สถานะ</th>
                            <th class="text-left text-xs font-medium text-gray-500 uppercase pb-1 w-2/5">รายละเอียด</th>
                        </tr>
                    </thead>
                    <tbody>${itemsHtml}</tbody>
                </table>
            `;
            cardBody.appendChild(reportContent);
        });
        
        card.appendChild(cardBody);
        window.reportContainer.appendChild(card);
    }
}

export function renderSubmissionHistory(history) {
    const historyContainer = document.getElementById('history-container');
    if (!historyContainer) return;
    historyContainer.innerHTML = '';

    if (!history || history.length === 0) {
        historyContainer.innerHTML = '<p class="text-center text-gray-500">ไม่พบประวัติการส่งรายงาน</p>';
        return;
    }

    history.forEach(report => {
        const reportWrapper = document.createElement('div');
        reportWrapper.className = 'p-4 border rounded-lg bg-gray-50';
        
        const itemsHtml = report.items.map(item => `
            <tr class="border-t">
                <td class="py-2 pr-2">${escapeHTML(item.personnel_name)}</td>
                <td class="py-2 px-2 text-blue-600">${escapeHTML(item.status)}</td>
                <td class="py-2 pl-2 text-gray-600">${escapeHTML(item.details) || '-'}</td>
            </tr>
        `).join('');

        reportWrapper.innerHTML = `
            <div class="flex justify-between items-center mb-3">
                <h3 class="text-lg font-semibold text-gray-700">รายงานวันที่ ${formatThaiDate(report.date)}</h3>
                <span class="text-sm text-gray-500">ส่งเมื่อ: ${new Date(report.timestamp).toLocaleString('th-TH')}</span>
            </div>
            <table class="min-w-full bg-white text-sm">
                 <thead>
                    <tr>
                        <th class="text-left font-medium text-gray-500 uppercase pb-1 w-2/5">ชื่อ-สกุล</th>
                        <th class="text-left font-medium text-gray-500 uppercase pb-1 w-1/5">สถานะ</th>
                        <th class="text-left font-medium text-gray-500 uppercase pb-1 w-2/5">รายละเอียด</th>
                    </tr>
                </thead>
                <tbody>
                    ${itemsHtml}
                </tbody>
            </table>
        `;
        historyContainer.appendChild(reportWrapper);
    });
}

export function populateArchiveSelectors(archives) {
    if(!window.archiveYearSelect || !window.archiveMonthSelect) return;
    window.archiveYearSelect.innerHTML = '<option value="">เลือกปี</option>';
    window.archiveMonthSelect.innerHTML = '<option value="">เลือกเดือน</option>';
    if (archives && Object.keys(archives).length > 0) {
        const sortedYears = Object.keys(archives).sort((a, b) => b - a);
        sortedYears.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = parseInt(year) + 543;
            window.archiveYearSelect.appendChild(option);
        });
    }
}

export function renderArchivedReports(reports) {
    if(!window.archiveContainer) return;
    window.archiveContainer.innerHTML = '';
    if (!reports || reports.length === 0) {
        window.archiveContainer.innerHTML = '<p class="text-center text-gray-500">ไม่พบรายงานในเดือนที่เลือก</p>';
        return;
    }
    
    const reportsByDate = reports.reduce((acc, report) => {
        const date = report.date;
        if (!acc[date]) {
            acc[date] = [];
        }
        acc[date].push(report);
        return acc;
    }, {});

    const sortedDates = Object.keys(reportsByDate).sort((a, b) => new Date(b) - new Date(a));

    sortedDates.forEach(date => {
        const dailyReports = reportsByDate[date];
        const dateCard = document.createElement('div');
        dateCard.className = 'mb-6 p-4 border rounded-lg bg-gray-50';

        let reportsHtml = '';
        dailyReports.forEach(report => {
            const itemsHtml = report.items.map(item => `
                <tr class="border-t">
                    <td class="py-2 pr-2">${escapeHTML(item.personnel_name)}</td>
                    <td class="py-2 px-2 text-blue-600">${escapeHTML(item.status)}</td>
                    <td class="py-2 pl-2 text-gray-600">${escapeHTML(item.details) || '-'}</td>
                </tr>
            `).join('');

            reportsHtml += `
                <div class="mt-4">
                    <div class="flex justify-between items-center text-sm text-gray-500 mb-2">
                        <span>แผนก: ${escapeHTML(report.department)}</span>
                        <span>ส่งโดย: ${escapeHTML(report.submitted_by)}</span>
                    </div>
                    <table class="min-w-full bg-white text-sm">
                        <thead>
                            <tr>
                                <th class="text-left font-medium text-gray-500 uppercase pb-1 w-2/5">ชื่อ-สกุล</th>
                                <th class="text-left font-medium text-gray-500 uppercase pb-1 w-1/5">สถานะ</th>
                                <th class="text-left font-medium text-gray-500 uppercase pb-1 w-2/5">รายละเอียด</th>
                            </tr>
                        </thead>
                        <tbody>${itemsHtml}</tbody>
                    </table>
                </div>
            `;
        });

        dateCard.innerHTML = `
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-semibold text-gray-800">ประวัติการเก็บรายงาน วันที่ ${formatThaiDate(date)}</h3>
                <button class="download-daily-archive-btn bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded" data-date="${escapeHTML(date)}">ดาวน์โหลดของวันนี้</button>
            </div>
            ${reportsHtml}
        `;
        window.archiveContainer.appendChild(dateCard);
    });
}

export function openPersonnelModal(person = null) {
    window.personnelForm.reset();
    const title = window.personnelForm.querySelector('#personnel-modal-title');
    if (person) {
        title.textContent = 'แก้ไขข้อมูลกำลังพล';
        window.personnelForm.querySelector('#person-id').value = person.id;
        window.personnelForm.querySelector('#person-rank').value = person.rank;
        window.personnelForm.querySelector('#person-first-name').value = person.first_name;
        window.personnelForm.querySelector('#person-last-name').value = person.last_name;
        window.personnelForm.querySelector('#person-position').value = person.position;
        window.personnelForm.querySelector('#person-specialty').value = person.specialty;
        window.personnelForm.querySelector('#person-department').value = person.department;
    } else {
        title.textContent = 'เพิ่มข้อมูลกำลังพล';
        window.personnelForm.querySelector('#person-id').value = '';
    }
    window.personnelModal.classList.add('active');
}

export function openUserModal(user = null) {
    window.userForm.reset();
    const usernameInput = window.userForm.querySelector('#user-username');
    if (user) {
        window.userModalTitle.textContent = 'แก้ไขข้อมูลผู้ใช้';
        usernameInput.value = user.username;
        usernameInput.readOnly = true;
        usernameInput.classList.add('bg-gray-200');
        window.userForm.querySelector('#user-rank').value = user.rank;
        window.userForm.querySelector('#user-first-name').value = user.first_name;
        window.userForm.querySelector('#user-last-name').value = user.last_name;
        window.userForm.querySelector('#user-position').value = user.position;
        window.userForm.querySelector('#user-department').value = user.department;
        window.userForm.querySelector('#user-role').value = user.role;
    } else {
        window.userModalTitle.textContent = 'เพิ่มผู้ใช้ใหม่';
        usernameInput.readOnly = false;
        usernameInput.classList.remove('bg-gray-200');
    }
    window.userModal.classList.add('active');
}
