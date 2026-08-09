"use strict";

const state = { data: null, page: 1 };
const BISMILLAH_END = "ٱلرَّحِيمِ";
const elements = {
  article: document.querySelector("#mushaf-page"),
  content: document.querySelector("#page-content"),
  number: document.querySelector("#page-number"),
  status: document.querySelector("#status"),
  select: document.querySelector("#page-select"),
  previous: document.querySelector("#previous"),
  next: document.querySelector("#next"),
  juz: document.querySelector("#juz-number"),
  rub: document.querySelector("#rub-number"),
};

function arabicNumber(value) {
  return value.toLocaleString("ar-EG", { useGrouping: false });
}

function surahById(id) {
  return state.data.surahs[id - 1];
}

function appendSurahHeading(surahId) {
  const surah = surahById(surahId);
  const heading = document.createElement("h2");
  heading.className = "surah-heading";
  const name = surah.nameAr.replace(/^سورة\s+/u, "");
  heading.textContent = `سورة ${name}`;
  elements.content.append(heading);
}

function appendAyahText(flow, surahId, ayahNumber, text) {
  const endIndex = text.indexOf(BISMILLAH_END);
  const hasEmbeddedBismillah =
    surahId !== 1 && ayahNumber === 1 && endIndex >= 0 && endIndex < 50;
  if (!hasEmbeddedBismillah) {
    flow.append(document.createTextNode(`${text} `));
    return;
  }

  const splitIndex = endIndex + BISMILLAH_END.length;
  flow.append(document.createTextNode(`${text.slice(0, splitIndex)} `));
  const bismillahMark = document.createElement("span");
  bismillahMark.className = "bismillah-mark";
  bismillahMark.textContent = "۝";
  bismillahMark.setAttribute("aria-label", "Ayah ending sign after Bismillah");
  flow.append(bismillahMark, document.createTextNode(`${text.slice(splitIndex)} `));
}

function renderPage(number, updateHistory = true) {
  const page = state.data.pages[number - 1];
  if (!page) return;

  state.page = number;
  elements.content.replaceChildren();
  let currentSurah = null;
  let flow = null;

  for (const [surahId, ayahNumber, text] of page.ayahs) {
    if (surahId !== currentSurah) {
      currentSurah = surahId;
      appendSurahHeading(surahId);
      flow = document.createElement("p");
      flow.className = "ayah-flow";
      elements.content.append(flow);
    }

    appendAyahText(flow, surahId, ayahNumber, text);
    const marker = document.createElement("span");
    marker.className = "ayah-number";
    marker.setAttribute("aria-label", `الآية ${ayahNumber}`);
    marker.textContent = `۝${arabicNumber(ayahNumber)}`;
    flow.append(marker, document.createTextNode(" "));
  }

  const juzs = [...new Set(page.ayahs.map(ayah => ayah[3]))];
  const rubs = [...new Set(page.ayahs.map(ayah => ayah[4]))];
  elements.juz.textContent = juzs.map(arabicNumber).join("–");
  elements.rub.textContent = rubs.map(arabicNumber).join("–");
  elements.number.textContent = String(page.number);
  elements.select.value = String(number);
  elements.previous.disabled = number === 1;
  elements.next.disabled = number === state.data.pages.length;
  elements.article.hidden = false;
  elements.status.hidden = true;
  document.title = `Page ${number} · Quran Reader`;
  localStorage.setItem("quran-reader-page", String(number));

  if (updateHistory) history.replaceState(null, "", `#page=${number}`);
  window.scrollTo({ top: 0, behavior: "instant" });
}

function requestedPage() {
  const hashMatch = location.hash.match(/^#page=(\d+)$/);
  const stored = localStorage.getItem("quran-reader-page");
  const candidate = Number(hashMatch?.[1] || stored || 1);
  return Number.isInteger(candidate) && candidate >= 1 && candidate <= 604
    ? candidate
    : 1;
}

async function initialize() {
  try {
    const response = await fetch("data/quran.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    for (const page of state.data.pages) {
      const option = document.createElement("option");
      option.value = page.number;
      option.textContent = String(page.number);
      elements.select.append(option);
    }
    renderPage(requestedPage(), false);
  } catch (error) {
    elements.status.textContent = `تعذّر تحميل بيانات القرآن: ${error.message}`;
  }
}

elements.previous.addEventListener("click", () => renderPage(state.page - 1));
elements.next.addEventListener("click", () => renderPage(state.page + 1));
elements.select.addEventListener("change", () => renderPage(Number(elements.select.value)));
window.addEventListener("hashchange", () => state.data && renderPage(requestedPage(), false));
document.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft" && state.page < 604) renderPage(state.page + 1);
  if (event.key === "ArrowRight" && state.page > 1) renderPage(state.page - 1);
});

initialize();
