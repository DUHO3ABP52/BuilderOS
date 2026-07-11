const API = "/api/v1";
const state = {
  token: localStorage.getItem("builderos_token") || "",
  user: null,
  view: "dashboard",
  data: {},
  error: "",
};

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
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
        text: "Я координатор BuilderOS. Напишите «сделай договор», «найди ГОСТ», «добавь платёж…», «добавь встречу завтра» или «помощь».",
      },
    ];
    try {
      state.data.llm = await api("/ai/llm-status");
    } catch (_) {
      state.data.llm = null;
    }
  } else if (state.view === "tasks") {
    state.data.tasks = await api("/tasks");
  } else if (state.view === "finance") {
    state.data.payments = await api("/finance/payments");
    state.data.financeSummary = await api("/finance/summary");
  } else if (state.view === "calendar") {
    state.data.calendar = await api("/calendar/upcoming?days=30");
  } else if (state.view === "graph") {
    state.data.projects = await api("/projects");
    state.data.companies = await api("/companies");
    const projectId = state.data.graphProjectId || (state.data.projects[0] && state.data.projects[0].id);
    state.data.graphProjectId = projectId || "";
    state.data.graph = projectId ? await api(`/graph/projects/${projectId}`) : null;
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
          ${navButton("finance", "Финансы")}
          ${navButton("calendar", "Календарь")}
          ${navButton("graph", "Граф объекта")}
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
  const data = state.data.dashboard || { counts: {}, recent_events: [], finance: {}, upcoming_events: [] };
  const finance = data.finance || {};
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
          ["payments_open", "Платежи"],
          ["events_week", "События"],
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
        <h2>Финансы (оплаченные)</h2>
        <p class="muted">Приход: ${finance.income_paid ?? 0} · Расход: ${finance.expense_paid ?? 0} · Баланс: ${finance.balance_paid ?? 0}</p>
      </div>
      <div class="panel">
        <h2>Ближайшие события</h2>
        <table class="table">
          <thead><tr><th>Когда</th><th>Событие</th><th>Тип</th></tr></thead>
          <tbody>
            ${(data.upcoming_events || [])
              .map(
                (item) => `
              <tr>
                <td>${formatDate(item.starts_at)}</td>
                <td>${item.title}</td>
                <td>${item.event_type}</td>
              </tr>`
              )
              .join("") || `<tr><td colspan="3" class="muted">Нет событий на неделю</td></tr>`}
          </tbody>
        </table>
      </div>
      <div class="panel">
        <h2>Последние события журнала</h2>
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
                <td>
                  <button class="secondary" data-graph="${item.id}">Граф</button>
                  <button class="secondary" data-archive="${item.id}">Архив</button>
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
  content.querySelectorAll("[data-graph]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.data.graphProjectId = button.dataset.graph;
      state.view = "graph";
      await safeLoad();
    });
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
  const preview = state.data.templatePreview || null;
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Загрузить образец → шаблон</h2>
        <p class="muted">DOCX, PDF, TXT или фото договора. Система разберёт текст, найдёт переменные и создаст шаблон.</p>
        <form id="sample-form" class="form-grid">
          <input class="full" type="file" name="file" accept=".docx,.pdf,.txt,.md,.png,.jpg,.jpeg,.webp,.tif,.tiff" required />
          <input name="name" placeholder="Название шаблона (необязательно)" />
          <select name="category">
            <option value="">Авто</option>
            <option value="contract">Договор</option>
            <option value="act">Акт</option>
            <option value="estimate">Смета</option>
            <option value="letter">Письмо</option>
            <option value="other">Другое</option>
          </select>
          <div class="full actions">
            <button type="button" class="secondary" id="preview-sample-btn">Предпросмотр</button>
            <button type="submit">Создать шаблон</button>
          </div>
        </form>
        ${
          preview
            ? `<div class="muted" style="margin-top:1rem">
                Формат: ${preview.source_format} · тип: ${preview.doc_type} · переменных: ${(preview.variables || []).length}
                ${(preview.warnings || []).length ? `<div>Предупреждения: ${preview.warnings.join("; ")}</div>` : ""}
                <pre style="white-space:pre-wrap;max-height:180px;overflow:auto;background:rgba(0,0,0,.2);padding:0.8rem;border-radius:12px">${preview.excerpt || ""}</pre>
              </div>`
            : ""
        }
      </div>
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
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Шаблоны";
  const form = content.querySelector("#sample-form");
  content.querySelector("#preview-sample-btn").addEventListener("click", async () => {
    const fileInput = form.querySelector('input[name="file"]');
    if (!fileInput.files.length) throw new Error("Выберите файл");
    const body = new FormData();
    body.append("file", fileInput.files[0]);
    state.data.templatePreview = await api("/templates/import/preview", { method: "POST", body });
    renderTemplates();
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    if (!data.get("file") || !data.get("file").size) throw new Error("Выберите файл");
    if (!data.get("name")) data.delete("name");
    if (!data.get("category")) data.delete("category");
    await api("/templates/import/sample", { method: "POST", body: data });
    state.data.templatePreview = null;
    await safeLoad();
  });
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
  const searchHits = state.data.knowledgeSearch || [];
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>RAG-поиск</h2>
        <form id="knowledge-search-form" class="form-grid">
          <input class="full" name="q" placeholder="Например: гарантийный срок" required />
          <div class="full actions">
            <button type="submit">Найти</button>
            <button type="button" class="secondary" id="reindex-btn">Переиндексировать</button>
          </div>
        </form>
        <table class="table">
          <thead><tr><th>Результат</th><th>Источник</th><th>Score</th></tr></thead>
          <tbody>
            ${searchHits.length
              ? searchHits
                  .map(
                    (item) => `
              <tr>
                <td>${item.title}<div class="muted">${item.excerpt || ""}</div></td>
                <td>${item.source}</td>
                <td>${item.score == null ? "—" : Number(item.score).toFixed(2)}</td>
              </tr>`
                  )
                  .join("")
              : `<tr><td colspan="3" class="muted">Введите запрос для семантического поиска</td></tr>`}
          </tbody>
        </table>
      </div>
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
  content.querySelector("#knowledge-search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const result = await api(`/knowledge/search?q=${encodeURIComponent(String(form.get("q")))}`);
    state.data.knowledgeSearch = result.items || [];
    renderKnowledge();
  });
  content.querySelector("#reindex-btn").addEventListener("click", async () => {
    await api("/knowledge/reindex", { method: "POST" });
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
  const llm = state.data.llm;
  let llmLine = "LLM: статус неизвестен";
  if (llm) {
    if (!llm.enabled) llmLine = "LLM: выключена (работают только правила)";
    else if (llm.model_ready || llm.provider_status === "ok") {
      const ep = (llm.endpoints || []).find((item) => item.status === "ok");
      llmLine = `LLM: готова · ${llm.provider} · ${ep ? ep.model : llm.model}`;
    } else {
      const warm = (llm.warmup && llm.warmup.detail) || llm.provider_status;
      llmLine = `LLM: загружается… (${warm})`;
    }
    if (llm.vision) {
      if (!llm.vision.enabled) llmLine += " · Vision OCR: выкл";
      else if (llm.vision.model_ready) llmLine += ` · Vision OCR: ${llm.vision.model}`;
      else llmLine += ` · Vision OCR: ${llm.vision.status || "ожидание"} (${llm.vision.model})`;
    }
  }
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Координатор</h2>
        <p class="muted">Локальные агенты + LLM. Документы только из шаблонов, без выдуманных данных.</p>
        <p class="muted">${llmLine}</p>
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
    try {
      state.data.llm = await api("/ai/llm-status");
    } catch (_) {}
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

function renderFinance() {
  const items = state.data.payments || [];
  const summary = state.data.financeSummary || {};
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Сводка</h2>
        <p class="muted">Приход: ${summary.income_paid ?? 0} · Расход: ${summary.expense_paid ?? 0} · Баланс: ${summary.balance_paid ?? 0} · Открытых: ${summary.open_payments ?? 0}</p>
        <h2>Новый платёж</h2>
        <form id="payment-form" class="form-grid">
          <input class="full" name="title" placeholder="Название" required />
          <select name="direction">
            <option value="income">Приход</option>
            <option value="expense">Расход</option>
          </select>
          <select name="kind">
            <option value="advance">Аванс</option>
            <option value="act">Акт</option>
            <option value="invoice">Счёт</option>
            <option value="material">Материалы</option>
            <option value="salary">Зарплата</option>
            <option value="other">Прочее</option>
          </select>
          <input name="amount" type="number" min="0.01" step="0.01" placeholder="Сумма" required />
          <input name="due_on" type="date" />
          <textarea class="full" name="description" rows="2" placeholder="Комментарий"></textarea>
          <div class="full actions"><button type="submit">Создать</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Платёж</th><th>Сумма</th><th>Статус</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (item) => `
              <tr>
                <td>${item.title}<div class="muted">${item.direction} · ${item.kind}</div></td>
                <td>${item.amount} ${item.currency}</td>
                <td>${item.status}</td>
                <td>
                  ${item.status !== "paid" ? `<button class="secondary" data-paid="${item.id}">Оплачен</button>` : ""}
                  <button class="secondary" data-archive="${item.id}">Архив</button>
                </td>
              </tr>`
              )
              .join("") || `<tr><td colspan="4" class="muted">Платежей пока нет</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Финансы";
  content.querySelector("#payment-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await api("/finance/payments", {
      method: "POST",
      body: JSON.stringify({
        title: form.get("title"),
        direction: form.get("direction"),
        kind: form.get("kind"),
        amount: Number(form.get("amount")),
        due_on: form.get("due_on") || null,
        description: form.get("description") || null,
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-paid]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/finance/payments/${button.dataset.paid}/paid`, { method: "POST" });
      await safeLoad();
    });
  });
  content.querySelectorAll("[data-archive]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/finance/payments/${button.dataset.archive}/archive`, { method: "POST" });
      await safeLoad();
    });
  });
}

function renderCalendar() {
  const items = state.data.calendar || [];
  const defaultStart = new Date();
  defaultStart.setDate(defaultStart.getDate() + 1);
  defaultStart.setMinutes(0, 0, 0);
  const localValue = new Date(defaultStart.getTime() - defaultStart.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Новое событие</h2>
        <form id="event-form" class="form-grid">
          <input class="full" name="title" placeholder="Название" required />
          <select name="event_type">
            <option value="meeting">Встреча</option>
            <option value="site_visit">Выезд</option>
            <option value="deadline">Срок</option>
            <option value="payment">Оплата</option>
            <option value="document">Документ</option>
            <option value="other">Прочее</option>
          </select>
          <input name="starts_at" type="datetime-local" value="${localValue}" required />
          <input class="full" name="location" placeholder="Место" />
          <textarea class="full" name="description" rows="2" placeholder="Описание"></textarea>
          <div class="full actions"><button type="submit">Добавить</button></div>
        </form>
      </div>
      <div class="panel">
        <table class="table">
          <thead><tr><th>Когда</th><th>Событие</th><th>Тип</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (item) => `
              <tr>
                <td>${formatDate(item.starts_at)}</td>
                <td>${item.title}<div class="muted">${item.location || ""}</div></td>
                <td>${item.event_type}</td>
                <td><button class="secondary" data-archive="${item.id}">Архив</button></td>
              </tr>`
              )
              .join("") || `<tr><td colspan="4" class="muted">Ближайших событий нет</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Календарь";
  content.querySelector("#event-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const startsAt = new Date(String(form.get("starts_at")));
    await api("/calendar/events", {
      method: "POST",
      body: JSON.stringify({
        title: form.get("title"),
        event_type: form.get("event_type"),
        starts_at: startsAt.toISOString(),
        ends_at: new Date(startsAt.getTime() + 60 * 60 * 1000).toISOString(),
        location: form.get("location") || null,
        description: form.get("description") || null,
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-archive]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/calendar/events/${button.dataset.archive}/archive`, { method: "POST" });
      await safeLoad();
    });
  });
}

function renderGraph() {
  const projects = state.data.projects || [];
  const companies = state.data.companies || [];
  const graph = state.data.graph;
  const projectOptions = projects
    .map(
      (item) =>
        `<option value="${item.id}" ${item.id === state.data.graphProjectId ? "selected" : ""}>${item.name}</option>`
    )
    .join("");
  const companyOptions = companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
  const stats = (graph && graph.stats) || {};
  const content = el(`
    <div class="grid">
      <div class="panel">
        <h2>Объект</h2>
        <p class="muted">Автосвязи из заказчика, документов, платежей, задач, памяти + ручные рёбра.</p>
        <form id="graph-select" class="form-grid">
          <select class="full" name="project_id" required>
            <option value="">Выберите объект</option>
            ${projectOptions}
          </select>
          <div class="full actions"><button type="submit">Показать граф</button></div>
        </form>
        ${
          graph
            ? `<p class="muted">Узлов: ${stats.nodes ?? 0} · связей: ${stats.edges ?? 0} · документов: ${stats.documents ?? 0} · платежей: ${stats.payments ?? 0}</p>`
            : ""
        }
        <h2>Ручная связь</h2>
        <form id="graph-edge-form" class="form-grid">
          <select class="full" name="company_id" required>
            <option value="">Связать с компанией</option>
            ${companyOptions}
          </select>
          <select name="relation">
            <option value="related_to">related_to</option>
            <option value="mentions">mentions</option>
            <option value="depends_on">depends_on</option>
          </select>
          <input name="label" placeholder="Подпись связи" />
          <div class="full actions"><button type="submit" ${graph ? "" : "disabled"}>Добавить</button></div>
        </form>
      </div>
      <div class="panel">
        <h2>Узлы</h2>
        <table class="table">
          <thead><tr><th>Тип</th><th>Название</th></tr></thead>
          <tbody>
            ${((graph && graph.nodes) || [])
              .map((node) => `<tr><td>${node.entity_type}</td><td>${node.label}</td></tr>`)
              .join("") || `<tr><td colspan="2" class="muted">Выберите объект</td></tr>`}
          </tbody>
        </table>
        <h2 style="margin-top:1rem">Связи</h2>
        <table class="table">
          <thead><tr><th>От</th><th>Связь</th><th>К</th><th>Источник</th><th></th></tr></thead>
          <tbody>
            ${((graph && graph.edges) || [])
              .map((edge) => {
                const from = ((graph && graph.nodes) || []).find((n) => n.id === edge.from_id);
                const to = ((graph && graph.nodes) || []).find((n) => n.id === edge.to_id);
                return `<tr>
                  <td>${from ? from.label : edge.from_id}</td>
                  <td>${edge.label || edge.relation}</td>
                  <td>${to ? to.label : edge.to_id}</td>
                  <td>${edge.source}</td>
                  <td>${
                    edge.edge_id
                      ? `<button class="secondary" data-archive-edge="${edge.edge_id}">Архив</button>`
                      : ""
                  }</td>
                </tr>`;
              })
              .join("") || `<tr><td colspan="5" class="muted">Нет связей</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `);
  renderShell(content);
  document.getElementById("page-title").textContent = "Граф объекта";
  content.querySelector("#graph-select").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    state.data.graphProjectId = String(form.get("project_id") || "");
    await safeLoad();
  });
  content.querySelector("#graph-edge-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.data.graphProjectId) return;
    const form = new FormData(event.target);
    await api("/graph/edges", {
      method: "POST",
      body: JSON.stringify({
        project_id: state.data.graphProjectId,
        from_type: "project",
        from_id: state.data.graphProjectId,
        to_type: "company",
        to_id: form.get("company_id"),
        relation: form.get("relation"),
        label: form.get("label") || null,
        source: "manual",
      }),
    });
    await safeLoad();
  });
  content.querySelectorAll("[data-archive-edge]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/graph/edges/${button.dataset.archiveEdge}/archive`, { method: "POST" });
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
    finance: renderFinance,
    calendar: renderCalendar,
    graph: renderGraph,
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
