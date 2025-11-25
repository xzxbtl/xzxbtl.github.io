// ===============================
// ГЛОБАЛЬНОЕ СОСТОЯНИЕ
// ===============================

let templates = [];
let editIndex = null;
let deleteIndex = null;

// rows: массив строк, каждая строка — массив кнопок [{ text, url? , callback_data? }]
let buttonRows = [[]];

// DOM
const templatesList = document.getElementById("templatesList");
const emptyState = document.getElementById("emptyState");
const totalCount = document.getElementById("totalCount");

const postModalBackdrop = document.getElementById("postModalBackdrop");
const modalTitle = document.getElementById("modalTitle");
const modalSubtitle = document.getElementById("modalSubtitle");

const f_title = document.getElementById("title");
const f_text = document.getElementById("text");
const f_image = document.getElementById("image_url");
const f_schedule = document.getElementById("schedule_time");

const btn_text = document.getElementById("btn_text");
const btn_type = document.getElementById("btn_type");
const btn_value = document.getElementById("btn_value");
const buttonsPreview = document.getElementById("buttonsPreview");

const modalDelete = document.getElementById("modalDelete");

// ===============================
// УТИЛИТЫ: API
// ===============================

async function handleApiResponse(response) {
  if (!response.ok) {
    let msg = "Неизвестная ошибка";
    try {
      const data = await response.json();
      msg = data.detail || data.error || JSON.stringify(data);
    } catch (e) {}
    window.location.href = `/error?msg=${encodeURIComponent(msg)}`;
    return null;
  }
  return response.json();
}

// ===============================
// ОТРИСОВКА СПИСКА
// ===============================

function renderTemplates() {
  templatesList.innerHTML = "";
  totalCount.textContent = templates.length;

  if (templates.length === 0) {
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  templates.forEach((t, i) => {
    const card = document.createElement("div");
    card.className = "template-item";

    card.innerHTML = `
      <button class="delete-btn" onclick="openDeleteModal(${i}, event)">Удалить</button>
      <div class="template-title-line">
        <div class="template-title-text">${t.title || "Без названия"}</div>
        <div class="template-type">Пост</div>
      </div>
      <div class="template-desc">${t.text || ""}</div>
    `;

    card.onclick = () => openPostModalEdit(i);
    templatesList.appendChild(card);
  });
}

// ===============================
// РАБОТА С МОДАЛКОЙ ПОСТА
// ===============================

function resetForm() {
  f_title.value = "";
  f_text.value = "";
  f_image.value = "";
  f_schedule.value = "";

  buttonRows = [[]];
  btn_text.value = "";
  btn_value.value = "";
  btn_type.value = "url";
  renderButtonsPreview();
}

function openPostModalNew() {
  editIndex = null;
  modalTitle.textContent = "Создание шаблона поста";
  modalSubtitle.textContent = "Заполните поля и при необходимости добавьте inline-кнопки.";
  resetForm();
  postModalBackdrop.style.display = "flex";
}

function openPostModalEdit(index) {
  editIndex = index;
  const t = templates[index];

  modalTitle.textContent = "Редактирование шаблона поста";
  modalSubtitle.textContent = "Измените нужные поля и сохраните изменения.";

  f_title.value = t.title || "";
  f_text.value = t.text || "";
  f_image.value = t.media_url || t.image_url || "";
  if (t.schedule_time) {
    try {
      f_schedule.value = t.schedule_time.substring(0, 16);
    } catch (e) {
      f_schedule.value = "";
    }
  } else {
    f_schedule.value = "";
  }

  // восстановление кнопок из buttons_json
  buttonRows = [[]];
  if (t.buttons_json && Array.isArray(t.buttons_json.inline_keyboard)) {
    buttonRows = t.buttons_json.inline_keyboard.map(row => row.map(btn => ({ ...btn })));
  }
  if (buttonRows.length === 0) buttonRows = [[]];

  renderButtonsPreview();
  postModalBackdrop.style.display = "flex";
}

function closePostModal() {
  postModalBackdrop.style.display = "none";
}

// закрытие по клику на фон
postModalBackdrop.addEventListener("click", (e) => {
  if (e.target === postModalBackdrop) {
    closePostModal();
  }
});

// ===============================
// КОНСТРУКТОР КНОПОК
// ===============================

function addButton() {
  const text = btn_text.value.trim();
  const type = btn_type.value;
  const value = btn_value.value.trim();

  if (!text || !value) {
    alert("Заполните текст и значение кнопки!");
    return;
  }

  const btn = { text };
  if (type === "url") {
    btn.url = value;
  } else {
    btn.callback_data = value;
  }

  // добавляем в последнюю строку
  let lastRow = buttonRows[buttonRows.length - 1];
  if (!lastRow) {
    lastRow = [];
    buttonRows.push(lastRow);
  }
  lastRow.push(btn);

  btn_text.value = "";
  btn_value.value = "";
  renderButtonsPreview();
}

function newRow() {
  // новая пустая строка
  buttonRows.push([]);
  renderButtonsPreview();
}

function removeButton(rowIndex, btnIndex) {
  if (!buttonRows[rowIndex]) return;
  buttonRows[rowIndex].splice(btnIndex, 1);
  // чистим пустые строки в конце
  while (buttonRows.length > 1 && buttonRows[buttonRows.length - 1].length === 0) {
    buttonRows.pop();
  }
  renderButtonsPreview();
}

function renderButtonsPreview() {
  buttonsPreview.innerHTML = "";
  const hasButtons = buttonRows.some(row => row.length > 0);

  if (!hasButtons) {
    buttonsPreview.innerHTML = `<div class="empty">Кнопок пока нет</div>`;
    return;
  }

  buttonRows.forEach((row, rowIndex) => {
    if (row.length === 0) return;
    const rowDiv = document.createElement("div");
    rowDiv.className = "btn-row-preview";

    row.forEach((btn, btnIndex) => {
      const el = document.createElement("div");
      el.className = "preview-btn";
      const typeLabel = btn.url ? "URL" : "CB";
      const val = btn.url || btn.callback_data || "";

      el.innerHTML = `
        <span>${btn.text}</span>
        <span class="type">(${typeLabel})</span>
        <span title="${val}">🔗</span>
      `;
      el.onclick = (e) => {
        e.stopPropagation();
        removeButton(rowIndex, btnIndex);
      };
      rowDiv.appendChild(el);
    });

    buttonsPreview.appendChild(rowDiv);
  });
}

function getButtonsJson() {
  const filteredRows = buttonRows
    .map(row => row.filter(btn => btn && btn.text && (btn.url || btn.callback_data)))
    .filter(row => row.length > 0);

  if (filteredRows.length === 0) return null;
  return { inline_keyboard: filteredRows };
}

// ===============================
// СОХРАНЕНИЕ ШАБЛОНА (CREATE / UPDATE)
// ===============================

async function submitTemplate() {
  let title = f_title.value.trim();
  const text = f_text.value.trim();
  const imageUrl = f_image.value.trim();
  const scheduleRaw = f_schedule.value;

  if (!title && !text && !imageUrl) {
    alert("Заполните хотя бы название, текст или картинку.");
    return;
  }
  if (!title) title = "Шаблон поста";

  const payload = {
    id: editIndex !== null ? templates[editIndex].id : null,
    user_id: USER_ID,                     // 👈 ОБЯЗАТЕЛЬНО
    title,
    text,
    image_url: imageUrl || null,
    schedule_time: scheduleRaw ? new Date(scheduleRaw).toISOString() : null,
    buttons_json: getButtonsJson()
  };

  const url =
    editIndex !== null
      ? `/api/posts/${templates[editIndex].id}?user_id=${USER_ID}`
      : `/api/posts?user_id=${USER_ID}`;

  const method = editIndex !== null ? "PUT" : "POST";

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await handleApiResponse(res);
  if (!data) return;

  if (editIndex !== null) {
    templates[editIndex] = data;
  } else {
    templates.unshift(data);
  }
  renderTemplates();
  closePostModal();
}

// ===============================
// УДАЛЕНИЕ
// ===============================

function openDeleteModal(index, event) {
  event.stopPropagation();
  deleteIndex = index;
  modalDelete.style.display = "flex";
}

function closeDeleteModal() {
  deleteIndex = null;
  modalDelete.style.display = "none";
}

async function confirmDelete() {
  if (deleteIndex === null) return;
  const tpl = templates[deleteIndex];

  const res = await fetch(`/api/posts/${templates[deleteIndex].id}?user_id=${USER_ID}`, {
    method: "DELETE",
  });

  const data = await handleApiResponse(res);
  if (!data) return;

  templates.splice(deleteIndex, 1);
  deleteIndex = null;
  renderTemplates();
  closeDeleteModal();
}

// ===============================
// ЗАГРУЗКА С СЕРВЕРА
// ===============================

async function loadTemplates() {
  const res = await fetch(`/api/posts?user_id=${USER_ID}`);
  const data = await handleApiResponse(res);
  if (!data) return;
  templates = data;
  renderTemplates();
}

document.addEventListener("DOMContentLoaded", loadTemplates);
