const codeEl = document.getElementById("code");
const convertBtn = document.getElementById("convert");
const downloadBtn = document.getElementById("download");
const statusEl = document.getElementById("status");
const tabsEl = document.getElementById("tabs");
const previewEl = document.getElementById("preview");
const zoomLevelEl = document.getElementById("zoom-level");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const themeToggle = document.getElementById("theme-toggle");

let currentXml = null;
let currentPages = [];
let zoom = 60;

const EMPTY_STATE =
  '<div class="preview-empty">' +
  '<svg viewBox="0 0 24 24" aria-hidden="true">' +
  '<rect x="8.5" y="2" width="7" height="5" rx="1.5"/>' +
  '<rect x="2" y="17" width="7" height="5" rx="1.5"/>' +
  '<rect x="15" y="17" width="7" height="5" rx="1.5"/>' +
  '<path d="M12 7v3M5.5 17v-3.5h13V17" fill="none"/>' +
  "</svg>" +
  "<p>Здесь появится схема</p>" +
  "<span>Вставьте код и нажмите «Построить блок-схему»</span>" +
  "</div>";

function resetPreview() {
  currentPages = [];
  tabsEl.innerHTML = "";
  previewEl.innerHTML = EMPTY_STATE;
}

function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = "status" + (kind ? " " + kind : "");
}

function currentTheme() {
  return document.documentElement.getAttribute("data-theme") || "light";
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem("theme", theme);
  } catch (e) {
    /* хранилище недоступно — игнорируем */
  }
}

themeToggle.addEventListener("click", () => {
  setTheme(currentTheme() === "dark" ? "light" : "dark");
});

function applyZoom() {
  const svg = previewEl.querySelector("svg");
  if (svg) {
    svg.style.width = zoom + "%";
  }
  zoomLevelEl.textContent = zoom + "%";
}

function showPage(index) {
  if (!currentPages[index]) {
    return;
  }
  previewEl.innerHTML = currentPages[index].svg;
  [...tabsEl.children].forEach((tab, i) => {
    tab.classList.toggle("active", i === index);
  });
  applyZoom();
}

function renderPreview(pages) {
  currentPages = pages;
  tabsEl.innerHTML = "";
  if (pages.length <= 1) {
    showPage(0);
    return;
  }
  pages.forEach((page, index) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "tab";
    tab.textContent = page.name;
    tab.addEventListener("click", () => showPage(index));
    tabsEl.appendChild(tab);
  });
  showPage(0);
}

async function convert() {
  const code = codeEl.value;
  if (!code.trim()) {
    setStatus("Введите код на Python", "error");
    return;
  }

  convertBtn.disabled = true;
  downloadBtn.disabled = true;
  currentXml = null;
  setStatus("Построение…");

  try {
    const response = await fetch("/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const data = await response.json();

    if (!response.ok) {
      setStatus(data.error || "Не удалось построить схему", "error");
      resetPreview();
      return;
    }

    currentXml = data.xml;
    renderPreview(data.pages || []);
    downloadBtn.disabled = false;
    setStatus("Готово. Проверьте схему и скачайте файл.", "ok");
  } catch (error) {
    setStatus("Ошибка сети: " + error.message, "error");
  } finally {
    convertBtn.disabled = false;
  }
}

function download() {
  if (!currentXml) {
    return;
  }
  const blob = new Blob([currentXml], { type: "application/xml" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "diagram.drawio";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

convertBtn.addEventListener("click", convert);
downloadBtn.addEventListener("click", download);

zoomInBtn.addEventListener("click", () => {
  zoom = Math.min(200, zoom + 10);
  applyZoom();
});
zoomOutBtn.addEventListener("click", () => {
  zoom = Math.max(10, zoom - 10);
  applyZoom();
});

codeEl.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    convert();
  }
});

codeEl.value =
  'def main() -> None:\n' +
  '    x = float(input("x = "))\n' +
  '    if x > 0:\n' +
  '        print("positive")\n' +
  '    else:\n' +
  '        print("non-positive")\n' +
  '\n' +
  'if __name__ == "__main__":\n' +
  '    main()\n';
