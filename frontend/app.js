const API = "/api/v1";
const state = {
  token: localStorage.getItem("builderos_token") || "",
  user: null,
  view: "dashboard",
  data: {},
  error: "",
};

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 401) {
    logout(false);
    throw new Error("Требуется вход");
  }
  if (!response.ok) {
    let detail = "Ошибка запроса";
    try {
      const body = await response.json();
      detail = body.detail || detail;
      if (Array.isArray(detail)) detail = detail.map((item) => item.msg || item).join("; ");
    } catch (_) {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  return response.blob();
}

function logout(renderNow = true) {
  state.token = "";
  state.user = null;
  localStorage.removeItem("builderos_token");
  if (renderNow) render();
}

function el(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

async function loadView() {
  state.error = "";
  if (state.view === "dashboard") {
    state.data.dashboard = await api("/dashboard");
  } else if (state.view === "companies") {
    state.data.companies = await api("/companies");
  } else if (state.view === "projects") {
    state.data.projects = await api("/projects");
    state.data.companies = await api("/companies");
  } else if (state.view === "templates") {
    state.data.templates = await api("/templates");
  } else if (state.view === "documents") {
    state.data.documents = await api("/documents");
    state.data.templates = await api("/templates");
    state.data.projects = await api("/projects");
  } else if (state.view === "knowledge") {
    state.data.knowledge = await api("/knowledge");
  } else if (state.view === "events") {
    state.data.events = await api("/events");
  } else if (state.view === "assistant") {
    state.data.chat = state.data.chat || [
      {
        role: "assistant",
        text: "Я координатор BuilderOS. Напишите «сделай договор», «найди ГОСТ», «добавь задачу…» или «помощь».",
      },
    ];
  } else if (state.view === "tasks") {
    state.data.tasks = await api("/tasks");
  }
}

function renderLogin() {
  const root = document.getElementById("app");
  root.innerHTML = "";
  const card = el(`
    <div class="login-page">
      <div class="login-card">
        <div class="brand">Builder<span>OS</span></div>
        <h1>Вход в систему</h1>
        <p class="muted">Локальный цифровой сотрудник строительной компании</p>
        <form id="login-form">
          <input name="email" type="email" placeholder="Email" value="admin@example.com" required />
          <input name="password" type="password" placeholder="Пароль" value="change-me" required />
          <button type="submit">Войти</button>
        </form>
        <div id="login-error"></div>
      </div>
    </div>
  `);
  root.appendChild(card);
  card.querySelector("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      const token = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      state.token = token.access_token;
      localStorage.setItem("builderos_token", state.token);
      state.user = await api("/auth/me");
      await loadView();
      render();
    } catch (error) {
      card.querySelector("#login-error").innerHTML = `<div class="error">${error.message}</div>`;
    }
  });
}

function navButton(id, label) {
  return `<button class="${state.view === id ? "active" : ""}" data-view="${id}">${label}</button>`;
}

function renderShell(content) {
  const root = document.getElementById("app");
  root.innerHTML = "";
  const shell = el(`
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">Builder<span>OS</span></div>
        <p>Операционная система строительного ИП</p>
        <nav class="nav">
          ${navButton("dashboard", "Сегодня")}
          ${navButton("assistant", "ИИ-помощник")}
          ${navButton("companies", "Компании")}
          ${navButton("projects", "Объекты")}
          ${navButton("documents", "Документы")}
          ${navButton("templates", "Шаблоны")}
          ${navButton("tasks", "Задачи")}
          ${navButton("knowledge", "База знаний")}
          ${navButton("events", "Журнал")}
        </nav>
      </aside>
      <main class="main">
        <div class="topbar">
          <div>
            <h1 id="page-title"></h1>
            <div class="muted">${state.user?.full_name || ""} · ${state.user?.email || ""}</div>
          </div>
          <button class="secondary" id="logout-btn">Выйти</button>
        </div>
        <div id="content"></div>
      </main>
    </div>
  `);
  root.appendChild(shell);
  shell.querySelector("#content").appendChild(content);
  shell.querySelector("#logout-btn").addEventListener("click", () => logout());
  shell.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.view = button.dataset.view;
      await safeLoad();
    });
  });
}

async function safeLoad() {
  try {
    await loadView();
    render();
  } catch (error) {
    state.error = error.message;
    render();
  }
}

function renderDashboard() {
  const data = state.data.dashboard || { counts: {}, recent_events: [] };
  const content = el(`
    <div class="grid">
      <div class="grid stats">
        ${[
          ["companies", "Компании"],
          ["projects", "Объекты"],
          ["documents", "Документы"],
          ["templates", "Шаблоны"],
          ["knowledge", "Знания"],
          ["tasks", "Задачи"],
        ]
          .map(
            ([key, label]) => `
          <div class="panel">
            <div class="muted">${label}</div>
            <div class="stat-value">${data.counts[key] ?? 0}</div>
          </div>`
          )
          .join("")}
      </div>
      <div class="panel">
        <h2>Последние события</h2>
        <table class="table">
          <thead><tr><th>Когда</th><th>Событие</th><th>Тип</th></tr></thead>
          <tbody>
            ${(data.recent_events || [])
              .map(
                (item) => `
              <tr>
                <td>${formatDate(item.created_at)}</td>
                <td>${item.summary}</td>
                <td>${item.entity_type}</td>
              </tr>`
              )
              .join("") || `<tr><td colspan="3" class="muted">Пока нет событий</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Сегодня";
}

function renderCompanies() {
  const items = state.data.companies || [];
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Новая компания</h2>
        <form id="company-form" class="form-grid">
          <input name="name" placeholder="Название" required />
          <select name="kind">
            <option value="customer">Заказчик</option>
            <option value="contractor">Подрядчик</option>
            <option value="supplier">Поставщик</option>
          </select>
          <input name="inn" placeholder="ИНН" />
          <input name="contact_name" placeholder="Контакт" />
          <input class="full" name="legal_address" placeholder="Юридический адрес" />
          <div class="full actions"><button type="submit">Создать</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Название</th><th>Тип</th><th>ИНН</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (item) => `
              <tr>
                <td>${item.name}</td>
                <td>${item.kind}</td>
                <td>${item.inn || "—"}</td>
                <td><button class="secondary" data-archive="${item.id}">Архив</button></td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Компании";
  content.querySelector("#company-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await api("/companies", {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        kind: form.get("kind"),
        inn: form.get("inn") || null,
        contact_name: form.get("contact_name") || null,
        legal_address: form.get("legal_address") || null,
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-archive]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/companies/${button.dataset.archive}/archive`, { method: "POST" });
      await safeLoad();
    });
  });
}

function renderProjects() {
  const items = state.data.projects || [];
  const companies = state.data.companies || [];
  const options = companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Новый объект</h2>
        <form id="project-form" class="form-grid">
          <input name="name" placeholder="Название объекта" required />
          <input name="address" placeholder="Адрес" />
          <select name="customer_id"><option value="">Заказчик</option>${options}</select>
          <select name="contractor_id"><option value="">Подрядчик</option>${options}</select>
          <input name="contract_value" type="number" step="0.01" placeholder="Сумма договора" />
          <div class="full actions"><button type="submit">Создать</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Объект</th><th>Статус</th><th>Сумма</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (item) => `
              <tr>
                <td>${item.name}<div class="muted">${item.address || ""}</div></td>
                <td>${item.status}</td>
                <td>${item.contract_value ?? "—"}</td>
                <td><button class="secondary" data-archive="${item.id}">Архив</button></td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Объекты";
  content.querySelector("#project-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await api("/projects", {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        address: form.get("address") || null,
        customer_id: form.get("customer_id") || null,
        contractor_id: form.get("contractor_id") || null,
        contract_value: form.get("contract_value") ? Number(form.get("contract_value")) : null,
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-archive]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/projects/${button.dataset.archive}/archive`, { method: "POST" });
      await safeLoad();
    });
  });
}

function renderTemplates() {
  const items = state.data.templates || [];
  const content = el(`
    <div class="panel">
      <h2>Реестр шаблонов</h2>
      <table class="table">
        <thead><tr><th>Название</th><th>Категория</th><th>Версия</th><th>Slug</th></tr></thead>
        <tbody>
          ${items
            .map(
              (item) => `
            <tr>
              <td>${item.name}</td>
              <td>${item.category}</td>
              <td>v${item.version}</td>
              <td>${item.slug}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Шаблоны";
}

function renderDocuments() {
  const items = state.data.documents || [];
  const templates = state.data.templates || [];
  const projects = state.data.projects || [];
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Создать из шаблона</h2>
        <form id="document-form" class="form-grid">
          <select name="template_id" required>
            <option value="">Шаблон</option>
            ${templates.map((item) => `<option value="${item.id}">${item.name} v${item.version}</option>`).join("")}
          </select>
          <select name="project_id">
            <option value="">Объект</option>
            ${projects.map((item) => `<option value="${item.id}">${item.name}</option>`).join("")}
          </select>
          <input class="full" name="title" placeholder="Название документа" />
          <textarea class="full" name="variables" rows="8" placeholder='Переменные JSON, например {"customer":{"name":"ООО","inn":"7707083893"},"contract":{"price":100000}}'></textarea>
          <div class="full actions"><button type="submit">Создать черновик</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Документ</th><th>Версия</th><th>Статус</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (item) => `
              <tr>
                <td>${item.title}<div class="muted">${item.doc_type}</div></td>
                <td>v${item.current_version}</td>
                <td>${item.status}</td>
                <td class="actions">
                  <button class="secondary" data-export-docx="${item.id}">DOCX</button>
                  <button class="secondary" data-export-pdf="${item.id}">PDF</button>
                </td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Документы";
  content.querySelector("#document-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    let variables = {};
    const raw = String(form.get("variables") || "").trim();
    if (raw) variables = JSON.parse(raw);
    await api(`/documents/from-template/${form.get("template_id")}`, {
      method: "POST",
      body: JSON.stringify({
        project_id: form.get("project_id") || null,
        title: form.get("title") || null,
        variables,
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-export-docx]").forEach((button) => {
    button.addEventListener("click", async () => {
      const blob = await api(`/documents/${button.dataset.exportDocx}/export/docx`);
      downloadBlob(blob, "document.docx");
    });
  });
  content.querySelectorAll("[data-export-pdf]").forEach((button) => {
    button.addEventListener("click", async () => {
      const blob = await api(`/documents/${button.dataset.exportPdf}/export/pdf`);
      downloadBlob(blob, "document.pdf");
    });
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function renderKnowledge() {
  const items = state.data.knowledge || [];
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Добавить запись</h2>
        <form id="knowledge-form" class="form-grid">
          <input name="title" placeholder="Название" required />
          <select name="category">
            <option value="sp">СП</option>
            <option value="snip">СНиП</option>
            <option value="gost">ГОСТ</option>
            <option value="internal">Внутреннее</option>
            <option value="template">Шаблон</option>
            <option value="other">Другое</option>
          </select>
          <textarea class="full" name="content" rows="6" placeholder="Текст" required></textarea>
          <div class="full actions"><button type="submit">Сохранить</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Название</th><th>Категория</th></tr></thead>
          <tbody>
            ${items
              .map((item) => `<tr><td>${item.title}</td><td>${item.category}</td></tr>`)
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "База знаний";
  content.querySelector("#knowledge-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await api("/knowledge", {
      method: "POST",
      body: JSON.stringify({
        title: form.get("title"),
        category: form.get("category"),
        content: form.get("content"),
      }),
    });
    await safeLoad();
  });
}

function renderEvents() {
  const items = state.data.events || [];
  const content = el(`
    <div class="panel">
      <table class="table">
        <thead><tr><th>Когда</th><th>Действие</th><th>Событие</th></tr></thead>
        <tbody>
          ${items
            .map(
              (item) => `
            <tr>
              <td>${formatDate(item.created_at)}</td>
              <td>${item.action}</td>
              <td>${item.summary}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Журнал";
}

function renderAssistant() {
  const chat = state.data.chat || [];
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Координатор</h2>
        <p class="muted">Локальные агенты: Document, Knowledge, Memory, Task. Без выдуманных данных.</p>
        <div class="chat" id="chat-box">
          ${chat
            .map(
              (item) => `
            <div class="bubble ${item.role}">
              ${item.text}
              ${item.meta ? `<div class="meta-tag">${item.meta}</div>` : ""}
            </div>`
            )
            .join("")}
        </div>
        <form id="chat-form" class="form-grid" style="margin-top:1rem">
          <textarea class="full" name="message" rows="3" placeholder="Например: сделай договор" required></textarea>
          <textarea class="full" name="variables" rows="5" placeholder='Переменные JSON (для договора)'></textarea>
          <label class="full muted"><input type="checkbox" name="confirm" /> Создать черновик даже без всех полей</label>
          <div class="full actions"><button type="submit">Отправить</button></div>
        </form>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "ИИ-помощник";
  const box = content.querySelector("#chat-box");
  box.scrollTop = box.scrollHeight;
  content.querySelector("#chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const message = String(form.get("message") || "").trim();
    let variables = {};
    const raw = String(form.get("variables") || "").trim();
    if (raw) variables = JSON.parse(raw);
    state.data.chat.push({ role: "user", text: message });
    renderAssistant();
    const answer = await api("/ai/ask", {
      method: "POST",
      body: JSON.stringify({
        message,
        variables,
        confirm: Boolean(form.get("confirm")),
      }),
    });
    state.data.chat.push({
      role: "assistant",
      text: answer.reply,
      meta: `${answer.agent} · ${answer.intent} · ${answer.status}`,
    });
    renderAssistant();
  });
}

function renderTasks() {
  const items = state.data.tasks || [];
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Новая задача</h2>
        <form id="task-form" class="form-grid">
          <input class="full" name="title" placeholder="Название" required />
          <textarea class="full" name="description" rows="3" placeholder="Описание"></textarea>
          <div class="full actions"><button type="submit">Создать</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Задача</th><th>Статус</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (item) => `
              <tr>
                <td>${item.title}<div class="muted">${item.description || ""}</div></td>
                <td>${item.status}</td>
                <td><button class="secondary" data-done="${item.id}">Готово</button></td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Задачи";
  content.querySelector("#task-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await api("/tasks", {
      method: "POST",
      body: JSON.stringify({
        title: form.get("title"),
        description: form.get("description") || null,
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-done]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/tasks/${button.dataset.done}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "done" }),
      });
      await safeLoad();
    });
  });
}

function render() {
  if (!state.token) {
    renderLogin();
    return;
  }
  if (state.error) {
    const content = el(`<div class="error">${state.error}</div>`);
    renderShell(content);
    document.getElementById("page-title").textContent = "Ошибка";
    return;
  }
  const views = {
    dashboard: renderDashboard,
    assistant: renderAssistant,
    companies: renderCompanies,
    projects: renderProjects,
    templates: renderTemplates,
    documents: renderDocuments,
    tasks: renderTasks,
    knowledge: renderKnowledge,
    events: renderEvents,
  };
  views[state.view]();
}

async function boot() {
  if (!state.token) {
    renderLogin();
    return;
  }
  try {
    state.user = await api("/auth/me");
    await loadView();
    render();
  } catch (_) {
    logout();
  }
}

boot();
