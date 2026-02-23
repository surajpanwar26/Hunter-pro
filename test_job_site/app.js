/* ========================================
   TechJobs Pro — Application Form Logic
   Multi-page navigation, validation, review
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const pages   = ['page1', 'page2', 'page3', 'successPage'];
    const steps   = document.querySelectorAll('.step');
    const lines   = document.querySelectorAll('.step-line');
    let currentPage = 0;

    /* ---- helpers ---- */
    const show = id => document.getElementById(id).style.display = 'block';
    const hide = id => document.getElementById(id).style.display = 'none';

    function goTo(idx) {
        pages.forEach(p => hide(p));
        show(pages[idx]);
        currentPage = idx;
        updateSteps(idx);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function updateSteps(idx) {
        steps.forEach((s, i) => {
            s.classList.remove('active', 'completed');
            if (i < idx) s.classList.add('completed');
            if (i === idx) s.classList.add('active');
        });
        lines.forEach((l, i) => {
            l.classList.remove('active', 'completed');
            if (i < idx) l.classList.add('completed');
            if (i === idx) l.classList.add('active');
        });
    }

    /* ---- navigation buttons ---- */
    document.getElementById('btnNext1').addEventListener('click', () => {
        if (!validatePage1()) return;
        goTo(1);
    });

    document.getElementById('btnBack2').addEventListener('click', () => goTo(0));
    document.getElementById('btnNext2').addEventListener('click', () => {
        buildReview();
        goTo(2);
    });

    document.getElementById('btnBack3').addEventListener('click', () => goTo(1));
    document.getElementById('btnSubmit').addEventListener('click', () => submitApplication());

    /* ---- page-1 validation (light) ---- */
    function validatePage1() {
        const fields = ['firstName', 'lastName', 'email', 'phone'];
        let ok = true;
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (!el.value.trim()) {
                el.style.borderColor = '#dc2626';
                ok = false;
            } else {
                el.style.borderColor = '';
            }
        });
        // check required checkbox
        const terms = document.getElementById('agreeTerms') || document.querySelector('input[name="agreeTerms"]');
        if (terms && !terms.checked) {
            const wrapper = terms.closest('.highlight-checkbox') || terms.closest('.checkbox-option');
            if (wrapper) wrapper.style.outline = '2px solid #dc2626';
            ok = false;
        } else if (terms) {
            const wrapper = terms.closest('.highlight-checkbox') || terms.closest('.checkbox-option');
            if (wrapper) wrapper.style.outline = '';
        }
        if (!ok) alert('Please fill all required fields (First Name, Last Name, Email, Phone) and accept Terms.');
        return ok;
    }

    /* ---- file upload UX ---- */
    const zone = document.querySelector('.file-upload-zone');
    const fileInput = document.getElementById('resume');
    const filenameEl = document.getElementById('uploadedFilename');

    if (zone && fileInput) {
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                showFilename(fileInput.files[0]);
            }
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) showFilename(fileInput.files[0]);
        });
    }

    function showFilename(file) {
        if (!filenameEl) return;
        filenameEl.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        filenameEl.style.display = 'block';
    }

    /* ---- build review ---- */
    function buildReview() {
        const rc = document.getElementById('reviewContent');
        if (!rc) return;

        const personalFields = [
            ['First Name',  val('firstName')],
            ['Last Name',   val('lastName')],
            ['Email',       val('email')],
            ['Phone',       val('phone')],
            ['City',        val('city')],
            ['State',       val('state')],
            ['Zip Code',    val('zipCode')],
            ['Country',     selText('country')],
            ['LinkedIn',    val('linkedIn')],
            ['Portfolio',   val('portfolio')],
            ['Gender',      selText('gender')],
            ['Work Auth',   radio('workAuth')],
            ['Visa Sponsor',radio('visaSponsorship')],
            ['Commute OK',  radio('commuteOk')],
            ['Resume',      fileInput.files.length ? fileInput.files[0].name : '—'],
        ];

        const expFields = [
            ['Years Exp',            val('yearsExperience')],
            ['Years Python',         val('yearsExperiencePython')],
            ['Years React',          val('yearsExperienceReact')],
            ['Current Company',      val('currentCompany')],
            ['Current Salary',       val('currentSalary')],
            ['Expected Salary',      val('expectedSalary')],
            ['Notice Period',        val('noticePeriod')],
            ['Earliest Start',       val('earliestStartDate')],
            ['Education',            selText('educationLevel')],
            ['Field of Study',       selText('fieldOfStudy')],
            ['University',           val('university')],
            ['GPA',                  val('gpa')],
            ['Work Preference',      radio('workPreference')],
            ['Leadership Exp',       radio('leadershipExp')],
            ['Disability',           radio('disability')],
            ['Cover Letter',         val('coverLetter') ? val('coverLetter').substring(0, 60) + '…' : '—'],
            ['Skills',               checkedBoxes('skills')],
            ['Referral',             selText('referralSource')],
            ['Confidence',           val('confidenceLevel')],
        ];

        rc.innerHTML = `
            ${reviewSection('Personal Information', personalFields, 0)}
            ${reviewSection('Experience & Qualifications', expFields, 1)}
        `;

        // wire edit buttons
        rc.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', () => goTo(parseInt(btn.dataset.page)));
        });
    }

    function reviewSection(title, fields, pageIdx) {
        return `
        <div class="review-section">
            <div class="review-section-header">
                <span>${title}</span>
                <button class="btn-edit" data-page="${pageIdx}">✏️ Edit</button>
            </div>
            <div class="review-grid">
                ${fields.map(([l, v]) => `
                    <div class="review-item">
                        <span class="review-label">${l}</span>
                        <span class="review-value ${v ? '' : 'empty'}">${v || '—'}</span>
                    </div>`).join('')}
            </div>
        </div>`;
    }

    /* ---- value helpers ---- */
    function val(id) {
        const el = document.getElementById(id);
        return el ? el.value.trim() : '';
    }

    function selText(id) {
        const el = document.getElementById(id);
        return el ? el.options[el.selectedIndex]?.text || '' : '';
    }

    function radio(name) {
        const checked = document.querySelector(`input[name="${name}"]:checked`);
        return checked ? checked.parentElement.textContent.trim() : '';
    }

    function checkedBoxes(name) {
        return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
            .map(cb => cb.parentElement.textContent.trim())
            .join(', ') || '—';
    }

    /* ---- submit ---- */
    function submitApplication() {
        const confirm = document.getElementById('confirmAccuracy');
        if (confirm && !confirm.checked) {
            alert('Please confirm the accuracy of your information.');
            return;
        }
        const appId = 'APP-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).substring(2, 6).toUpperCase();
        const now = new Date().toLocaleString();

        hide('page3');
        show('successPage');
        updateSteps(3);

        document.querySelector('.progress-bar-container').style.display = 'none';

        const sc = document.querySelector('.success-content');
        if (sc) {
            sc.querySelector('h2').textContent = 'Application Submitted!';
            sc.querySelector('.success-details').innerHTML = `
                <div class="success-item"><span>Application ID</span><strong>${appId}</strong></div>
                <div class="success-item"><span>Submitted</span><strong>${now}</strong></div>
                <div class="success-item"><span>Position</span><strong>Senior Software Engineer</strong></div>
                <div class="success-item"><span>Status</span><strong style="color:#059669">Under Review</strong></div>
            `;
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    /* ---- init ---- */
    goTo(0);
});
