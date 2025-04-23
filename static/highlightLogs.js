// static/highlightLogs.js

function highlightLogLines(iframe) {
  const doc = iframe.contentDocument || iframe.contentWindow.document;
  if (!doc) return;

  const lines = doc.body.querySelectorAll(".log-line");
  lines.forEach(line => {
    const text = line.textContent;
    if (/ERROR|CRITICAL|FATAL/i.test(text)) {
      line.classList.add("log-error");
    } else if (/WARNING/i.test(text)) {
      line.classList.add("log-warning");
    } else if (/INFO|NOTICE/i.test(text)) {
      line.classList.add("log-info");
    }
  });
}

function loadLog() {
  const logName = document.getElementById('logSelect').value;
  const lines = document.getElementById('linesInput').value || 300;
  const level = document.getElementById('levelSelect').value;
  const filter = document.getElementById('filterInput').value.trim();

  const url = `/api/logs/view?filename=${logName}&lines=${lines}&level=${level}&filter=${encodeURIComponent(filter)}`;
  document.getElementById('logIframe').src = url;
}

function manualRefresh() {
  loadLog();
}

document.addEventListener("DOMContentLoaded", function () {
  fetch("/api/logs/files")
    .then(res => res.json())
    .then(files => {
      const select = document.getElementById("logSelect");
      files.forEach(file => {
        const opt = document.createElement("option");
        opt.value = file;
        opt.textContent = file;
        select.appendChild(opt);
      });
      if (files.length) {
        select.value = files[0];
        loadLog();
      }
    });

  const refreshSelect = document.getElementById("refreshSelect");
  let refreshInterval;

  function setRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    const seconds = parseInt(refreshSelect.value);
    if (seconds > 0) {
      refreshInterval = setInterval(loadLog, seconds * 1000);
    }
  }

  refreshSelect.addEventListener("change", setRefresh);
  document.getElementById("logSelect").addEventListener("change", loadLog);
  document.getElementById("linesInput").addEventListener("change", loadLog);
  document.getElementById("filterInput").addEventListener("input", loadLog);
  document.getElementById("levelSelect").addEventListener("change", loadLog);

  document.getElementById("downloadFiltered").addEventListener("click", () => {
    const logName = document.getElementById('logSelect').value;
    const lines = document.getElementById('linesInput').value || 300;
    const level = document.getElementById('levelSelect').value;
    const filter = document.getElementById('filterInput').value.trim();
    const url = `/api/logs/download?filename=${logName}&lines=${lines}&level=${level}&filter=${encodeURIComponent(filter)}`;
    window.open(url, '_blank');
  });

  setRefresh();
});