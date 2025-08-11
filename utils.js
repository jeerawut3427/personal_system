// utils.js
// Contains helper and utility functions for data formatting and export.

// --- Helper Functions ---

function toThaiNumerals(n) {
    const thaiDigits = ['๐', '๑', '๒', '๓', '๔', '๕', '๖', '๗', '๘', '๙'];
    return n.toString().replace(/[0-9]/g, d => thaiDigits[parseInt(d)]);
}

function getThaiHeaderDate(date) {
    const thaiMonthsAbbr = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
    const d = new Date(date);
    const day = toThaiNumerals(d.getDate());
    const month = thaiMonthsAbbr[d.getMonth()];
    const year = toThaiNumerals((d.getFullYear() + 543).toString().slice(-2));
    return `${day} ${month} ${year}`;
}

export function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return str.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export function formatThaiDate(isoDate) {
    if (!isoDate) return '';
    const date = new Date(isoDate);
    const year = date.getFullYear() + 543;
    const month = date.toLocaleString('th-TH', { month: 'long' });
    const day = date.getDate();
    return `${day} ${month} ${year}`;
}

export function exportSingleReportToExcel(reports, fileName) {
    const dataForExport = [];
    let allItems = [];
    reports.forEach(report => {
        allItems = allItems.concat(report.items);
    });

    let seq = 1;
    allItems.forEach(item => {
        const nameParts = item.personnel_name.split(' ');
        const rank = nameParts.length > 0 ? nameParts[0] : '';
        const firstName = nameParts.length > 1 ? nameParts[1] : '';
        const lastName = nameParts.length > 2 ? nameParts.slice(2).join(' ') : '';
        
        dataForExport.push({
            'ลำดับ': toThaiNumerals(seq++),
            'ชื่อและนามสกุล': `${firstName}  ${lastName}`,
            'ยศ-คำนำหน้า': rank,
            'สถานะ': item.status,
            'รายละเอียด': item.details,
            'ช่วงวันที่': item.start_date === item.end_date 
                        ? formatThaiDate(item.start_date) 
                        : `${formatThaiDate(item.start_date)} - ${formatThaiDate(item.end_date)}`
        });
    });

    const allDates = reports.map(r => new Date(r.date));
    const minDate = new Date(Math.min.apply(null, allDates));
    const maxDate = new Date(Math.max.apply(null, allDates));
    const dateRangeString = `ระหว่างวันที่ ${getThaiHeaderDate(minDate)} - ${getThaiHeaderDate(maxDate)}`;

    const header1 = ["บัญชีรายชื่อ น.สัญญาบัตรที่ไปราชการ, คุมงาน, ศึกษา, ลากิจ และลาพักผ่อน ประจำสัปดาห์ของ กวก.ชย.ทอ."];
    const header2 = [dateRangeString];
    
    const ws = XLSX.utils.aoa_to_sheet([header1]);
    XLSX.utils.sheet_add_aoa(ws, [header2], { origin: 'A2' });
    
    if (!ws['!merges']) ws['!merges'] = [];
    ws['!merges'].push({ s: { r: 0, c: 0 }, e: { r: 0, c: 5 } }); 
    ws['!merges'].push({ s: { r: 1, c: 0 }, e: { r: 1, c: 5 } });

    const orderedData = dataForExport.map(row => ({
        'ลำดับ': row['ลำดับ'],
        'ชื่อและนามสกุล': row['ชื่อและนามสกุล'],
        'ยศ-คำนำหน้า': row['ยศ-คำนำหน้า'],
        'สถานะ': row['สถานะ'],
        'รายละเอียด': row['รายละเอียด'],
        'ช่วงวันที่': row['ช่วงวันที่']
    }));

    XLSX.utils.sheet_add_json(ws, orderedData, { origin: 'A3', skipHeader: false });

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "รายงาน");
    XLSX.writeFile(wb, fileName || "รายงาน.xlsx");
}
