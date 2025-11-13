// ------------------------------
// Конструктор inline-кнопок
// ------------------------------

const buttons = []; // структура: [{text: "...", url: "..."}]

// Добавить новую кнопку
function addButton() {
    const text = document.getElementById("btn_text").value.trim();
    const url = document.getElementById("btn_url").value.trim();

    if (!text || !url) {
        alert("Заполните текст и URL кнопки!");
        return;
    }

    buttons.push({ text, url });

    document.getElementById("btn_text").value = "";
    document.getElementById("btn_url").value = "";

    renderButtonsPreview();
}

// Удалить кнопку по индексу
function removeButton(index) {
    buttons.splice(index, 1);
    renderButtonsPreview();
}

// Обновить визуальный список кнопок
function renderButtonsPreview() {
    const container = document.getElementById("buttons_preview");
    container.innerHTML = "";

    if (buttons.length === 0) {
        container.innerHTML = `<div class="empty">Кнопок пока нет</div>`;
        return;
    }

    buttons.forEach((btn, index) => {
        const el = document.createElement("div");
        el.className = "btn-item";
        el.innerHTML = `
            <div>
                <strong>${btn.text}</strong><br>
                <small>${btn.url}</small>
            </div>
            <button class="delete-btn" onclick="removeButton(${index})">✖</button>
        `;
        container.appendChild(el);
    });
}

// Получить итоговый JSON кнопок (вызывается при отправке шаблона)
function getButtonsJson() {
    if (buttons.length === 0) return null;

    return {
        inline_keyboard: buttons.map(b => [{ text: b.text, url: b.url }])
    };
}

// Подключение JSON конструктора к форме
document.getElementById("save_post_template").addEventListener("click", async () => {
    const title = document.getElementById("title").value;
    const text = document.getElementById("text").value;
    const image_url = document.getElementById("image_url").value;
    const schedule_time = document.getElementById("schedule_time").value;
    const group_id = document.getElementById("group_id").value;

    const body = {
        title,
        text,
        image_url: image_url || null,
        schedule_time: schedule_time || null,
        tg_group_id: parseInt(group_id),
        buttons_json: getButtonsJson()
    };

    console.log("FINAL JSON:", body);

    const res = await fetch("/api/posts-templates/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });

    if (res.ok) {
        alert("Шаблон успешно сохранён!");
    } else {
        alert("Ошибка при сохранении шаблона.");
    }
});
