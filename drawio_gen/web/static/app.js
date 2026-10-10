const codeEl = document.getElementById("code");
const modeDiagramBtn = document.getElementById("mode-diagram");
const modeWordBtn = document.getElementById("mode-word");
const convertBtn = document.getElementById("convert");
const formatBtn = document.getElementById("format");
const copyBtn = document.getElementById("copy-word");
const downloadDiagramBtn = document.getElementById("download-diagram");
const downloadDocxBtn = document.getElementById("download-docx");
const statusEl = document.getElementById("status");
const tabsEl = document.getElementById("tabs");
const previewEl = document.getElementById("preview");
const zoomLevelEl = document.getElementById("zoom-level");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const themeToggle = document.getElementById("theme-toggle");
const languageEl = document.getElementById("language");
const langLabelEl = document.getElementById("lang-label");
const appTitle = document.getElementById("app-title");
const appHint = document.getElementById("app-hint");
const paneHint = document.getElementById("pane-hint");

const SAMPLES = {
  python:
    'def main() -> None:\n' +
    '    x = float(input("x = "))\n' +
    '    if x > 0:\n' +
    '        print("positive")\n' +
    '    else:\n' +
    '        print("non-positive")\n' +
    '\n' +
    'if __name__ == "__main__":\n' +
    '    main()\n',
  csharp:
    "using System;\n" +
    "\n" +
    "class Program\n" +
    "{\n" +
    "    static void Main(string[] args)\n" +
    "    {\n" +
    '        int x = int.Parse(Console.ReadLine());\n' +
    "        if (x > 0)\n" +
    "        {\n" +
    '            Console.WriteLine("positive");\n' +
    "        }\n" +
    "        else\n" +
    "        {\n" +
    '            Console.WriteLine("non-positive");\n' +
    "        }\n" +
    "    }\n" +
    "}\n",
};

let mode = "diagram";
let currentXml = null;
let currentPages = [];
let currentCode = "";
let currentLanguage = "auto";
let hasFormatted = false;
let zoom = 60;
let pristine = true;

function sampleFor(language) {
  return SAMPLES[language] || SAMPLES.python;
}

function storeLanguage(language) {
  try {
    localStorage.setItem("language", language);
  } catch (e) {}
}

function storeMode(m) {
  try {
    localStorage.setItem("mode", m);
  } catch (e) {}
}

const EMPTY_DIAGRAM =
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

const EMPTY_WORD =
  '<div class="preview-empty">' +
  '<svg viewBox="0 0 24 24" aria-hidden="true">' +
  '<rect x="8.5" y="2" width="7" height="5" rx="1.5"/>' +
  '<rect x="2" y="17" width="7" height="5" rx="1.5"/>' +
  '<rect x="15" y="17" width="7" height="5" rx="1.5"/>' +
  '<path d="M12 7v3M5.5 17v-3.5h13V17" fill="none"/>' +
  "</svg>" +
  "<p>Здесь появится форматированный код</p>" +
  "<span>Вставьте код и нажмите «Форматировать»</span>" +
  "</div>";

function setMode(m) {
  mode = m;
  if (m === "diagram") {
    modeDiagramBtn.classList.add("mode-tab--active");
    modeDiagramBtn.setAttribute("aria-selected", "true");
    modeWordBtn.classList.remove("mode-tab--active");
    modeWordBtn.setAttribute("aria-selected", "false");
    document.body.setAttribute("data-mode", "diagram");
    appTitle.textContent = "Генератор блок-схем";
    appHint.innerHTML = 'Код <b>Python</b> или <b>C#</b> → файл <code>.drawio</code> с одной страницей на функцию';
    paneHint.textContent = "Ctrl / ⌘ + Enter — построить";
    if (!currentPages.length) {
      previewEl.innerHTML = EMPTY_DIAGRAM;
    } else {
      renderPreview(currentPages);
    }
  } else {
    modeWordBtn.classList.add("mode-tab--active");
    modeWordBtn.setAttribute("aria-selected", "true");
    modeDiagramBtn.classList.remove("mode-tab--active");
    modeDiagramBtn.setAttribute("aria-selected", "false");
    document.body.setAttribute("data-mode", "word");
    appTitle.textContent = "Код в Word";
    appHint.innerHTML = 'Форматирование кода для вставки в <b>Microsoft Word</b>';
    paneHint.textContent = "Ctrl / ⌘ + Enter — форматировать";
    if (!hasFormatted) {
      previewEl.innerHTML = EMPTY_WORD;
    } else {
      previewEl.innerHTML = "<pre>" + currentFormattedHtml + "</pre>";
      langLabelEl.textContent = currentFormattedLang || "—";
    }
  }
  storeMode(m);
}

function resetPreview() {
  currentXml = null;
  currentPages = [];
  tabsEl.innerHTML = "";
  previewEl.innerHTML = mode === "diagram" ? EMPTY_DIAGRAM : EMPTY_WORD;
  langLabelEl.textContent = "";
  copyBtn.disabled = true;
  downloadDocxBtn.disabled = true;
  downloadDiagramBtn.disabled = true;
  hasFormatted = false;
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
  } catch (e) {}
}

themeToggle.addEventListener("click", () => {
  setTheme(currentTheme() === "dark" ? "light" : "dark");
});

modeDiagramBtn.addEventListener("click", () => setMode("diagram"));
modeWordBtn.addEventListener("click", () => setMode("word"));

function applyZoom() {
  const svg = previewEl.querySelector("svg");
  if (svg) {
    svg.style.width = zoom + "%";
  }
  zoomLevelEl.textContent = zoom + "%";
}

function showPage(index) {
  if (!currentPages[index]) return;
  previewEl.innerHTML = currentPages[index].svg;
  [...tabsEl.children].forEach((tab, i) => {
    tab.classList.toggle("active", i === index);
  });
  applyZoom();
  previewEl.querySelectorAll(".linkable").forEach((node) => {
    node.addEventListener("click", () => {
      const target = node.getAttribute("data-page");
      const next = currentPages.findIndex((page) => page.name === target);
      if (next >= 0) showPage(next);
    });
  });
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
    setStatus("Введите код программы", "error");
    return;
  }

  convertBtn.disabled = true;
  downloadDiagramBtn.disabled = true;
  currentXml = null;
  setStatus("Построение…");

  try {
    const response = await fetch("/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language: languageEl.value }),
    });
    const data = await response.json();

    if (!response.ok) {
      setStatus(data.error || "Не удалось построить схему", "error");
      resetPreview();
      return;
    }

    currentXml = data.xml;
    renderPreview(data.pages || []);
    downloadDiagramBtn.disabled = false;
    setStatus(`Готово (${data.language_name || "код"}). Проверьте схему и скачайте файл.`, "ok");
  } catch (error) {
    setStatus("Ошибка сети: " + error.message, "error");
  } finally {
    convertBtn.disabled = false;
  }
}

function downloadDiagram() {
  if (!currentXml) return;
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

let currentFormattedHtml = "";
let currentFormattedLang = "";

async function format() {
  const code = codeEl.value;
  if (!code.trim()) {
    setStatus("Введите код", "error");
    return;
  }

  formatBtn.disabled = true;
  copyBtn.disabled = true;
  downloadDocxBtn.disabled = true;
  setStatus("Форматирование…");

  try {
    const response = await fetch("/format", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language: languageEl.value }),
    });
    const data = await response.json();

    if (!response.ok) {
      setStatus(data.error || "Не удалось отформатировать код", "error");
      resetPreview();
      return;
    }

    currentCode = code;
    currentFormattedLang = data.language || languageEl.value;
    currentFormattedHtml = data.html;
    hasFormatted = true;

    previewEl.innerHTML = "<pre>" + data.html + "</pre>";
    langLabelEl.textContent = data.language || "—";

    copyBtn.disabled = false;
    downloadDocxBtn.disabled = false;
    setStatus(`Готово — ${data.language}.`, "ok");
  } catch (error) {
    setStatus("Ошибка сети: " + error.message, "error");
  } finally {
    formatBtn.disabled = false;
  }
}

async function copyToWord() {
  if (!hasFormatted || !currentCode) return;

  copyBtn.disabled = true;
  setStatus("Копирование…");

  try {
    const response = await fetch("/clipboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: currentCode, language: currentFormattedLang }),
    });
    const data = await response.json();

    if (!response.ok) {
      setStatus(data.error || "Ошибка копирования", "error");
      copyBtn.disabled = false;
      return;
    }

    const rtf = data.rtf;

    try {
      await navigator.clipboard.write({
        "text/rtf": rtf,
        "text/plain": currentCode,
      });
      setStatus("Скопировано! Вставьте в Word (Ctrl+V)", "ok");
    } catch (clipErr) {
      setStatus("Буфер обмена недоступен. Скачайте .docx.", "error");
    }
  } catch (error) {
    setStatus("Ошибка сети: " + error.message, "error");
  } finally {
    copyBtn.disabled = false;
  }
}

async function downloadDocx() {
  if (!hasFormatted || !currentCode) return;

  downloadDocxBtn.disabled = true;
  setStatus("Формирование файла…");

  try {
    const response = await fetch("/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: currentCode, language: currentFormattedLang }),
    });

    if (!response.ok) {
      const data = await response.json();
      setStatus(data.error || "Ошибка скачивания", "error");
      downloadDocxBtn.disabled = false;
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "code.docx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setStatus("Файл code.docx скачан", "ok");
  } catch (error) {
    setStatus("Ошибка сети: " + error.message, "error");
  } finally {
    downloadDocxBtn.disabled = false;
  }
}

convertBtn.addEventListener("click", convert);
formatBtn.addEventListener("click", format);
copyBtn.addEventListener("click", copyToWord);
downloadDiagramBtn.addEventListener("click", downloadDiagram);
downloadDocxBtn.addEventListener("click", downloadDocx);

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
    if (mode === "diagram") convert();
    else format();
  }
});

codeEl.addEventListener("input", () => {
  pristine = false;
});

languageEl.addEventListener("change", () => {
  storeLanguage(languageEl.value);
  if (pristine) {
    codeEl.value = sampleFor(languageEl.value === "csharp" ? "csharp" : "python");
    pristine = true;
  }
});

(function init() {
  let saved = "auto";
  try {
    saved = localStorage.getItem("language") || "auto";
  } catch (e) {}
  if ([...languageEl.options].some((option) => option.value === saved)) {
    languageEl.value = saved;
  }
  codeEl.value = sampleFor(saved === "csharp" ? "csharp" : "python");

  let savedMode = "diagram";
  try {
    savedMode = localStorage.getItem("mode") || "diagram";
  } catch (e) {}
  setMode(savedMode === "word" ? "word" : "diagram");
})();