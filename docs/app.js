"use strict";

const state = {
  data: null,
  uthmani: null,
  nastaleeq: null,
  rukuEnds: new Map(),
  rukuAnchors: [],
  page: 1,
  script: "uthmani",
};
const elements = {
  article: document.querySelector("#mushaf-page"),
  content: document.querySelector("#page-content"),
  number: document.querySelector("#page-number"),
  status: document.querySelector("#status"),
  select: document.querySelector("#page-select"),
  juzSelect: document.querySelector("#juz-select"),
  surahSelect: document.querySelector("#surah-select"),
  previous: document.querySelector("#previous"),
  next: document.querySelector("#next"),
  juz: document.querySelector("#juz-number"),
  hizb: document.querySelector("#hizb-number"),
  script: document.querySelector("#script-select"),
  surahName: document.querySelector("#page-surah-name"),
  rukuMarkers: document.querySelector("#ruku-markers"),
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
  heading.dataset.surahId = String(surahId);
  const name = surah.nameAr.replace(/^سورة\s+/u, "");
  heading.textContent = `سورة ${name}`;
  elements.content.append(heading);
}

function surahName(surahId) {
  return surahById(surahId).nameAr.replace(/^سورة\s+/u, "");
}

function appendUthmaniText(flow, surahId, ayahNumber) {
  if (ayahNumber === 1 && surahId !== 1 && surahId !== 9) {
    const bismillah = state.uthmani["1:1"].replace(/[\s\u00a0]*١\s*$/u, "");
    flow.append(document.createTextNode(`${bismillah} `));
    const mark = document.createElement("span");
    mark.className = "bismillah-mark";
    mark.setAttribute("aria-label", "Ayah ending sign after Bismillah");
    flow.append(mark, document.createTextNode(" "));
  }
  const verseNode = document.createTextNode(
    `${state.uthmani[`${surahId}:${ayahNumber}`]} `,
  );
  flow.append(verseNode);
  return verseNode;
}

function appendNastaleeqText(flow, surahId, ayahNumber) {
  if (ayahNumber === 1 && surahId !== 1 && surahId !== 9) {
    const bismillah = state.nastaleeq["1:1"].replace(/\s+١\s*$/u, "");
    flow.append(document.createTextNode(`${bismillah} `));
    const mark = document.createElement("span");
    mark.className = "bismillah-mark nastaleeq-bismillah-mark";
    mark.setAttribute("aria-label", "Ayah ending sign after Bismillah");
    flow.append(mark, document.createTextNode(" "));
  }
  const verseNode = document.createTextNode(
    `${state.nastaleeq[`${surahId}:${ayahNumber}`]} `,
  );
  flow.append(verseNode);
  return verseNode;
}

function rememberRukuEnd(anchor, surahId, ayahNumber) {
  const ruku = state.rukuEnds.get(`${surahId}:${ayahNumber}`);
  if (!ruku) return;
  state.rukuAnchors.push({ anchor, ruku });
}

function positionRukuMarkers() {
  elements.rukuMarkers.replaceChildren();
  const pageRect = elements.article.getBoundingClientRect();
  for (const { anchor, ruku } of state.rukuAnchors) {
    const range = document.createRange();
    if (anchor.nodeType === Node.TEXT_NODE) {
      const end = Math.max(0, anchor.length - 1);
      range.setStart(anchor, end);
      range.setEnd(anchor, anchor.length);
    } else {
      range.selectNode(anchor);
    }
    const anchorRect = range.getBoundingClientRect();
    if (!anchorRect.height) continue;
  const marker = document.createElement("span");
  marker.className = "ruku-marker";
  marker.textContent = "ع";
  marker.title = `Ruku ${ruku} ends here`;
    marker.style.top = `${anchorRect.top - pageRect.top + anchorRect.height / 2}px`;
    elements.rukuMarkers.append(marker);
  }
}

function scheduleRukuMarkers() {
  requestAnimationFrame(() => {
    positionRukuMarkers();
    if (document.fonts?.ready) document.fonts.ready.then(positionRukuMarkers);
  });
}

function renderPage(number, updateHistory = true) {
  const page = state.data.pages[number - 1];
  if (!page) return;

  state.page = number;
  elements.content.replaceChildren();
  state.rukuAnchors = [];
  elements.rukuMarkers.replaceChildren();
  let currentSurah = null;
  let flow = null;
  const firstSurah = page.ayahs[0][0];
  elements.surahName.textContent = `سورة ${surahName(firstSurah)}`;
  elements.surahName.dataset.surahId = String(firstSurah);

  for (const [surahId, ayahNumber, text] of page.ayahs) {
    if (surahId !== currentSurah) {
      currentSurah = surahId;
      if (surahId !== firstSurah) appendSurahHeading(surahId);
      flow = document.createElement("p");
      flow.className = "ayah-flow";
      elements.content.append(flow);
    }

    if (state.script === "nastaleeq") {
      const verseNode = appendNastaleeqText(flow, surahId, ayahNumber);
      rememberRukuEnd(verseNode, surahId, ayahNumber);
      continue;
    }

    const verseNode = appendUthmaniText(flow, surahId, ayahNumber);
    rememberRukuEnd(verseNode, surahId, ayahNumber);
  }

  const juzs = [...new Set(page.ayahs.map(ayah => ayah[3]))];
  const rubs = [...new Set(page.ayahs.map(ayah => ayah[4]))];
  const hizbs = [...new Set(rubs.map(rub => Math.ceil(rub / 4)))];
  elements.juz.textContent = juzs.map(arabicNumber).join("–");
  elements.hizb.textContent = hizbs.map(arabicNumber).join("–");
  elements.number.textContent = String(page.number);
  elements.select.value = String(number);
  elements.juzSelect.value = String(page.ayahs[0][3]);
  elements.surahSelect.value = String(firstSurah);
  elements.previous.disabled = number === 1;
  elements.next.disabled = number === state.data.pages.length;
  elements.article.hidden = false;
  elements.article.dataset.script = state.script;
  elements.status.hidden = true;
  document.title = `Page ${number} · Quran Reader`;
  localStorage.setItem("quran-reader-page", String(number));

  if (updateHistory) history.replaceState(null, "", `#page=${number}`);
  window.scrollTo({ top: 0, behavior: "instant" });
  scheduleRukuMarkers();
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
    const [quranResponse, rukuResponse, uthmaniResponse] = await Promise.all([
      fetch("data/quran.json"),
      fetch("data/rukus.json"),
      fetch("data/uthmani.json"),
    ]);
    if (!quranResponse.ok) throw new Error(`Quran data: HTTP ${quranResponse.status}`);
    if (!rukuResponse.ok) throw new Error(`Ruku data: HTTP ${rukuResponse.status}`);
    if (!uthmaniResponse.ok) throw new Error(`Uthmani data: HTTP ${uthmaniResponse.status}`);
    state.data = await quranResponse.json();
    state.uthmani = await uthmaniResponse.json();
    const rukuData = await rukuResponse.json();
    state.rukuEnds = new Map(
      rukuData.rukus.map(ruku => [ruku.end_verse_key, ruku.id]),
    );
    for (const page of state.data.pages) {
      const option = document.createElement("option");
      option.value = page.number;
      option.textContent = String(page.number);
      elements.select.append(option);
    }
    for (let juz = 1; juz <= 30; juz += 1) {
      const option = document.createElement("option");
      option.value = juz;
      option.textContent = String(juz);
      elements.juzSelect.append(option);
    }
    for (const surah of state.data.surahs) {
      const option = document.createElement("option");
      option.value = surah.id;
      option.textContent = `${surah.id} — ${surah.nameAr.replace(/^سورة\s+/u, "")}`;
      elements.surahSelect.append(option);
    }
    state.page = requestedPage();
    const savedScript = localStorage.getItem("quran-reader-script");
    if (savedScript === "nastaleeq") {
      elements.script.value = savedScript;
      await selectScript(savedScript);
    } else {
      renderPage(state.page, false);
    }
  } catch (error) {
    elements.status.textContent = `تعذّر تحميل بيانات القرآن: ${error.message}`;
  }
}

async function selectScript(script) {
  if (script === "nastaleeq" && !state.nastaleeq) {
    elements.status.hidden = false;
    elements.status.textContent = "Loading Nastaleeq Quran script…";
    const response = await fetch("data/nastaleeq.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.nastaleeq = await response.json();
  }
  state.script = script;
  localStorage.setItem("quran-reader-script", script);
  renderPage(state.page, false);
}

elements.previous.addEventListener("click", () => renderPage(state.page - 1));
elements.next.addEventListener("click", () => renderPage(state.page + 1));
elements.select.addEventListener("change", () => renderPage(Number(elements.select.value)));
elements.juzSelect.addEventListener("change", () => {
  const juz = Number(elements.juzSelect.value);
  const page = state.data.pages.find(item => item.ayahs.some(ayah => ayah[3] === juz));
  if (page) {
    renderPage(page.number);
    elements.juzSelect.value = String(juz);
  }
});
elements.surahSelect.addEventListener("change", () => {
  const surahId = Number(elements.surahSelect.value);
  const page = state.data.pages.find(item => item.ayahs.some(ayah => ayah[0] === surahId));
  if (page) {
    renderPage(page.number);
    elements.surahSelect.value = String(surahId);
    const heading = elements.article.querySelector(`[data-surah-id="${surahId}"]`);
    if (heading) heading.scrollIntoView({ block: "start", behavior: "instant" });
  }
});
elements.script.addEventListener("change", async () => {
  try {
    await selectScript(elements.script.value);
  } catch (error) {
    elements.status.hidden = false;
    elements.status.textContent = `Unable to load script: ${error.message}`;
    elements.script.value = state.script;
  }
});
window.addEventListener("hashchange", () => state.data && renderPage(requestedPage(), false));
document.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft" && state.page < 604) renderPage(state.page + 1);
  if (event.key === "ArrowRight" && state.page > 1) renderPage(state.page - 1);
});
window.addEventListener("resize", scheduleRukuMarkers);

initialize();
