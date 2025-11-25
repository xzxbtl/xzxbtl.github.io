let templates = [];
let editIndex = null;
let deleteIndex = null;
let currentMode = "common";

/* DOM элементы */
const listElement = document.getElementById("templateList");
const emptyState = document.getElementById("emptyState");
const totalCount = document.getElementById("totalCount");
const modalBackdrop = document.getElementById("modalBackdrop");

/* Поля общей части */
const m_title = document.getElementById("m_title");
const m_desc = document.getElementById("m_desc");
const m_tags = document.getElementById("m_tags");
const m_language = document.getElementById("m_language");
const m_schedule = document.getElementById("m_schedule");
const m_visibility = document.getElementById("m_visibility");
const m_allow_comments = document.getElementById("m_allow_comments");
const m_allow_duet = document.getElementById("m_allow_duet");

/* TikTok */
const tt_sound = document.getElementById("tt_sound");
const tt_cover = document.getElementById("tt_cover");
const tt_captions = document.getElementById("tt_captions");
const tt_category = document.getElementById("tt_category");

/* YouTube */
const yt_category = document.getElementById("yt_category");
const yt_privacy = document.getElementById("yt_privacy");
const yt_kids = document.getElementById("yt_kids");
const yt_license = document.getElementById("yt_license");
const yt_embed = document.getElementById("yt_embed");
const yt_short = document.getElementById("yt_short");

/* Extra blocks */
const tiktokExtra = document.getElementById("tiktokExtra");
const youtubeExtra = document.getElementById("youtubeExtra");
const modalTitle = document.getElementById("modalTitle");
const modalSubtitle = document.getElementById("modalSubtitle");

async function handleApiResponse(response) {
    if (!response.ok) {
        let msg = "Неизвестная ошибка";

        try {
            const data = await response.json();
            msg = data.detail || data.error || JSON.stringify(data);
        } catch (_) {}

        // редирект на HTML-страницу ошибки
        window.location.href = `/error?msg=${encodeURIComponent(msg)}`;
        return null;
    }

    return response.json();
}

/* ========== ОТКРЫТИЕ МОДАЛКИ СОЗДАНИЯ/РЕДАКТИРОВАНИЯ ========== */
function openModal(platform) {
  currentMode = platform;
  editIndex = null;

  modalTitle.textContent =
    platform === "tiktok" ? "Добавление TikTok шаблона" :
    platform === "youtube" ? "Добавление YouTube шаблона" :
    "Добавление общего шаблона";

  modalSubtitle.textContent =
    platform === "tiktok" ? "Специальные поля для TikTok Template" :
    platform === "youtube" ? "Специальные поля YouTube Template" :
    "Поля, доступные для любой платформы";

  /* Показ корректных секций */
  tiktokExtra.style.display = platform === "tiktok" ? "block" : "none";
  youtubeExtra.style.display = platform === "youtube" ? "block" : "none";

  clearFields();
  modalBackdrop.style.display = "flex";
}

/* очистка полей */
function clearFields() {
  m_title.value = "";
  m_desc.value = "";
  m_tags.value = "";
  m_language.value = "ru";
  m_schedule.value = "";
  m_visibility.value = "public";
  m_allow_comments.checked = true;
  m_allow_duet.checked = true;

  tt_sound.value = "";
  tt_cover.value = "";
  tt_captions.checked = true;
  tt_category.value = "";

  yt_category.value = "22";
  yt_privacy.value = "public";
  yt_kids.checked = false;
  yt_license.value = "youtube";
  yt_embed.checked = true;
  yt_short.checked = true;
}

function closeModal() {
  modalBackdrop.style.display = "none";
}

/* закрытие по фону */
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});

/* ========== РЕНДЕР СПИСКА ========== */
function renderTemplates() {
  listElement.innerHTML = "";
  totalCount.textContent = templates.length;

  if (templates.length === 0) {
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  templates.forEach((t, i) => {
    const el = document.createElement("div");
    el.className = "template-item";

  const typeClass =
      t.platform === "tiktok" ? "tiktok" :
      t.platform === "youtube" ? "youtube" : "common";

    el.innerHTML = `
      <button class="delete-btn" onclick="openConfirmDelete(${i}, event)">🗑</button>

      <div class="template-title">
        <span>${t.title || "Без названия"}</span>
        <span class="template-type ${typeClass}">
          ${t.platform === "tiktok" ? "TikTok" :
            t.platform === "youtube" ? "YouTube" : "Общий"}
        </span>
      </div>

      <div class="template-desc">${t.description || ""}</div>
    `;

    el.onclick = () => editTemplate(i);
    listElement.appendChild(el);
  });
}

/* ========== РЕДАКТИРОВАНИЕ ========== */
function editTemplate(i) {
  editIndex = i;
  const t = templates[i];
  currentMode = t.platform;

  modalBackdrop.style.display = "flex";

  modalTitle.textContent =
    t.platform === "tiktok" ? "Редактирование TikTok шаблона" :
    t.platform === "youtube" ? "Редактирование YouTube шаблона" :
    "Редактирование общего шаблона";

  tiktokExtra.style.display = t.platform === "tiktok" ? "block" : "none";
  youtubeExtra.style.display = t.platform === "youtube" ? "block" : "none";

  m_title.value = t.title;
  m_desc.value = t.description;
  m_tags.value = (t.tags || []).join(", ");
  m_language.value = t.language;
  m_visibility.value = t.visibility;
  m_allow_comments.checked = t.allow_comments;
  m_allow_duet.checked = t.allow_duet;
  m_schedule.value = t.schedule_time ? t.schedule_time.substring(0,16) : "";

  if (t.platform === "tiktok") {
     const extra = t.extra || {};

    tt_sound.value = extra.sound_id || "";
    tt_cover.value = extra.cover_time || "";
    tt_captions.checked = extra.enable_auto_captions ?? true;
    tt_category.value = extra.category || "";
  }

  if (t.platform === "youtube") {
    const extra = t.extra || {};

    yt_category.value = extra.category_id ?? 22;
    yt_privacy.value = extra.privacy_status || "public";
    yt_kids.checked = extra.made_for_kids ?? false;
    yt_license.value = extra.license || "youtube";
    yt_embed.checked = extra.allow_embedding ?? true;
    yt_short.checked = extra.publish_as_short ?? true;
  }
}

/* ========== СОХРАНЕНИЕ / FECTH НА FASTAPI ========== */
function saveTemplate() {
  let title = m_title.value.trim();
  if (!title) title = "Шаблон";

  const base = {
    id: editIndex !== null ? templates[editIndex].id : null,
    user_id: USER_ID,
    title,
    description: m_desc.value.trim(),
    tags: m_tags.value.split(",").map(t => t.trim()).filter(Boolean),
    language: m_language.value,
    schedule_time: m_schedule.value ? new Date(m_schedule.value).toISOString() : null,
    visibility: m_visibility.value,
    allow_comments: m_allow_comments.checked,
    allow_duet: m_allow_duet.checked
  };

  let payload;

  if (currentMode === "common") {
    payload = {
      ...base,
      platform: "common",
      extra: {}
    };
  }

  if (currentMode === "tiktok") {
    payload = {
      ...base,
      platform: "tiktok",
      extra: {
        sound_id: tt_sound.value || null,
        cover_time: tt_cover.value ? parseFloat(tt_cover.value) : null,
        enable_auto_captions: tt_captions.checked,
        category: tt_category.value || null
      }
    };
  }

  if (currentMode === "youtube") {
    payload = {
      ...base,
      platform: "youtube",
      extra: {
        category_id: parseInt(yt_category.value),
        privacy_status: yt_privacy.value,
        made_for_kids: yt_kids.checked,
        license: yt_license.value,
        allow_embedding: yt_embed.checked,
        publish_as_short: yt_short.checked
      }
    };
  }

  const url = editIndex !== null
    ? `/api/video/${templates[editIndex].id}?user_id=${USER_ID}`
    : `/api/video`;

  const method = editIndex !== null ? "PUT" : "POST";

  fetch(url, {
    method: method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(handleApiResponse)
  .then(data => {
    if (!data) return;

    if (editIndex !== null) templates[editIndex] = data;
    else templates.push(data);

    renderTemplates();
    closeModal();
  });
}

/* ========== МОДАЛКА УДАЛЕНИЯ ========== */
function openConfirmDelete(i, event) {
  event.stopPropagation();
  deleteIndex = i;
  document.getElementById("confirmDeleteModal").style.display = "flex";
}

function closeConfirmDelete() {
  deleteIndex = null;
  document.getElementById("confirmDeleteModal").style.display = "none";
}

function confirmDelete() {
  if (deleteIndex === null) return;

  const template = templates[deleteIndex];

  fetch(`/api/video/${template.id}?user_id=${USER_ID}`, { method: "DELETE" })
    .then(handleApiResponse)
    .then(() => {
      templates.splice(deleteIndex, 1);
      renderTemplates();
      closeConfirmDelete();
    });
}

/* ========== ЗАГРУЗКА ШАБЛОНОВ ИЗ FASTAPI ========== */
function loadTemplates() {
  fetch(`/api/video?user_id=${USER_ID}`)
    .then(handleApiResponse)
    .then(data => {
      if (!data) return;
      templates = data;
      renderTemplates();
    });
}

loadTemplates();