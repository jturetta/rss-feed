const $ = (sel) => document.querySelector(sel);

const urlInput = $("#url");
const btnPreview = $("#btn-preview");
const btnGenerate = $("#btn-generate");
const btnCopy = $("#btn-copy");
const loading = $("#loading");
const errorEl = $("#error");
const previewSection = $("#preview-section");
const resultSection = $("#result-section");
const previewList = $("#preview-list");
const itemsCount = $("#items-count");
const sourceUrl = $("#source-url");
const nativeNotice = $("#native-notice");
const feedTitle = $("#feed-title");
const feedUrlInput = $("#feed-url");
const feedLink = $("#feed-link");

let lastPreview = null;

function getPayload() {
  const payload = { url: urlInput.value.trim() };
  const ts = $("#title-selector").value.trim();
  const ls = $("#link-selector").value.trim();
  const ds = $("#desc-selector").value.trim();
  const is = $("#img-selector").value.trim();
  if (ts) payload.title_selector = ts;
  if (ls) payload.link_selector = ls;
  if (ds) payload.description_selector = ds;
  if (is) payload.image_selector = is;
  return payload;
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.remove("hidden");
}

function hideError() {
  errorEl.classList.add("hidden");
}

function renderPreview(data) {
  lastPreview = data;
  previewSection.classList.remove("hidden");
  resultSection.classList.add("hidden");
  $("#github-section").classList.add("hidden");
  sourceUrl.textContent = data.source_url;
  itemsCount.textContent = data.items_count;

  if (data.type === "native") {
    nativeNotice.classList.remove("hidden");
    previewList.innerHTML = "";
    btnGenerate.textContent = "Salvar referência ao feed nativo";
    return;
  }

  nativeNotice.classList.add("hidden");
  btnGenerate.textContent = "Gerar Feed RSS";

  previewList.innerHTML = data.items.slice(0, 10).map((item) => `
    <div class="preview-item">
      ${item.image ? `<img src="${item.image}" alt="" onerror="this.style.display='none'">` : ""}
      <div class="preview-item-content">
        <h3>${escapeHtml(item.title)}</h3>
        ${item.description ? `<p>${escapeHtml(item.description)}</p>` : ""}
        <a href="${item.link}" target="_blank">${item.link}</a>
      </div>
    </div>
  `).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function apiPost(endpoint, payload) {
  const resp = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "Erro na requisição");
  return data;
}

btnPreview.addEventListener("click", async () => {
  hideError();
  previewSection.classList.add("hidden");

  const url = urlInput.value.trim();
  if (!url) {
    showError("Informe uma URL válida.");
    return;
  }

  loading.classList.remove("hidden");
  btnPreview.disabled = true;

  try {
    const data = await apiPost("/api/preview", getPayload());
    renderPreview(data);
  } catch (err) {
    showError(err.message);
  } finally {
    loading.classList.add("hidden");
    btnPreview.disabled = false;
  }
});

btnGenerate.addEventListener("click", async () => {
  if (!lastPreview) return;
  hideError();
  loading.classList.remove("hidden");
  btnGenerate.disabled = true;

  try {
    const payload = getPayload();
    if (feedTitle.value.trim()) payload.title = feedTitle.value.trim();

    const data = await apiPost("/api/feeds", payload);
    const fullUrl = data.type === "native"
      ? data.native_rss_url
      : `${window.location.origin}${data.feed_url}`;

    feedUrlInput.value = fullUrl;
    feedLink.href = fullUrl;
    resultSection.classList.remove("hidden");
    await showLocalhostNotice(data.feed_url);
    showGithubExport(payload, data);
  } catch (err) {
    showError(err.message);
  } finally {
    loading.classList.add("hidden");
    btnGenerate.disabled = false;
  }
});

btnCopy.addEventListener("click", () => {
  feedUrlInput.select();
  navigator.clipboard.writeText(feedUrlInput.value);
  btnCopy.textContent = "Copiado!";
  setTimeout(() => { btnCopy.textContent = "Copiar"; }, 2000);
});

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnPreview.click();
});

async function showLocalhostNotice(feedPath) {
  const notice = $("#localhost-notice");
  const lanRow = $("#lan-url-row");
  const lanUrlEl = $("#lan-feed-url");
  const isLocal = /localhost|127\.0\.0\.1/.test(window.location.hostname);

  if (!isLocal || !feedPath) {
    notice.classList.add("hidden");
    return;
  }

  notice.classList.remove("hidden");
  lanRow.classList.add("hidden");

  try {
    const resp = await fetch("/api/server-info");
    const info = await resp.json();
    if (info.lan_ip) {
      lanUrlEl.textContent = `http://${info.lan_ip}:${info.port}${feedPath}`;
      lanRow.classList.remove("hidden");
    }
  } catch (_) {}
}

function slugFromUrl(url) {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/\./g, "-");
    const path = u.pathname.replace(/\//g, "-").replace(/^-|-$/g, "") || "feed";
    return `${host}-${path}`.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/-+/g, "-").slice(0, 60);
  } catch {
    return "meu-feed";
  }
}

function showGithubExport(payload, data) {
  const section = $("#github-section");
  const repo = $("#github-repo").value.trim() || "SEU-USUARIO/rss-feed";
  const [owner, name] = repo.includes("/") ? repo.split("/") : ["SEU-USUARIO", "rss-feed"];
  const feedId = slugFromUrl(payload.url);

  const config = {
    id: feedId,
    title: payload.title || data.source_url,
    source_url: payload.url,
  };
  if (payload.title_selector) config.title_selector = payload.title_selector;
  if (payload.link_selector) config.link_selector = payload.link_selector;
  if (payload.description_selector) config.description_selector = payload.description_selector;
  if (payload.image_selector) config.image_selector = payload.image_selector;

  const publicUrl = `https://${owner}.github.io/${name}/feeds/${feedId}.xml`;
  $("#github-feed-url").value = publicUrl;
  $("#github-config").textContent = JSON.stringify(config, null, 2);
  section.classList.remove("hidden");
}

$("#btn-copy-github").addEventListener("click", () => {
  navigator.clipboard.writeText($("#github-feed-url").value);
  $("#btn-copy-github").textContent = "Copiado!";
  setTimeout(() => { $("#btn-copy-github").textContent = "Copiar"; }, 2000);
});

$("#btn-copy-config").addEventListener("click", () => {
  navigator.clipboard.writeText($("#github-config").textContent);
  $("#btn-copy-config").textContent = "Copiado!";
  setTimeout(() => { $("#btn-copy-config").textContent = "Copiar config"; }, 2000);
});
