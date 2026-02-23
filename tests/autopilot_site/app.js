function saveStepData(stepKey, formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  const payload = {};
  const fields = form.querySelectorAll('input, select, textarea');
  fields.forEach((field) => {
    if (!field.name) return;

    if (field.type === 'radio') {
      if (field.checked) payload[field.name] = field.value;
      return;
    }

    if (field.type === 'checkbox') {
      payload[field.name] = field.checked;
      return;
    }

    payload[field.name] = field.value;
  });

  try {
    localStorage.setItem(`autopilot:${stepKey}`, JSON.stringify(payload));
  } catch (err) {
    console.error('Failed to persist form step', err);
  }
}

function loadStepData(stepKey, formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  let payload = {};
  try {
    payload = JSON.parse(localStorage.getItem(`autopilot:${stepKey}`) || '{}');
  } catch {
    payload = {};
  }

  const fields = form.querySelectorAll('input, select, textarea');
  fields.forEach((field) => {
    if (!field.name) return;
    if (!(field.name in payload)) return;

    if (field.type === 'radio') {
      field.checked = String(field.value) === String(payload[field.name]);
      return;
    }

    if (field.type === 'checkbox') {
      field.checked = !!payload[field.name];
      return;
    }

    field.value = payload[field.name];
  });
}

function mergeStoredData() {
  const keys = ['step1', 'step2'];
  const merged = {};
  keys.forEach((key) => {
    try {
      const payload = JSON.parse(localStorage.getItem(`autopilot:${key}`) || '{}');
      Object.assign(merged, payload);
    } catch {
      // ignore malformed payloads
    }
  });
  return merged;
}

function clearAllData() {
  ['step1', 'step2'].forEach((key) => localStorage.removeItem(`autopilot:${key}`));
}
