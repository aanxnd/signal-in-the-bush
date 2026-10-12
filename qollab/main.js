import * as experiment from 'runner';

const status = document.getElementById('status');
const button = document.getElementById('measure');
const map = document.getElementById('map');
let downloadUrl;
try {
  const saved = JSON.parse(await experiment.prepare.callPromising());
  map.srcdoc = saved.map_html;
  document.getElementById('classical').textContent = `${saved.exact_covered.toLocaleString()} covered fixes`;
  document.getElementById('classical-sites').textContent = `Sites ${saved.exact_sites.join(', ')} · greedy matches this coverage`;
  status.textContent = 'Verified inputs loaded. Classical coverage recomputed. Explore the saved map or take a fresh measurement.';
  button.disabled = false;
} catch (error) {
  status.textContent = `Could not initialize the experiment: ${error.message || error}`;
  console.error(String(error));
}
button.addEventListener('click', async () => {
  const depth = Number(document.getElementById('depth').value);
  const shots = Number(document.getElementById('shots').value);
  if (!Number.isInteger(shots) || shots < 128 || shots > 8192) {
    status.textContent = 'Enter an integer measurement count from 128 to 8192.';
    return;
  }
  button.disabled = true;
  status.textContent = `Measuring depth ${depth} on your selected backend…`;
  try {
    const result = JSON.parse(await experiment.measure.callPromising(backend, depth, shots));
    const report = result.report;
    map.srcdoc = result.map_html;
    document.getElementById('live').textContent = report.repaired ? `${report.repaired.covered_fixes.toLocaleString()} covered fixes` : 'No feasible sample';
    document.getElementById('live-details').textContent = report.repaired ? `Raw sites ${report.raw.sites.join(', ')} → repaired ${report.repaired.sites.join(', ')} · ${report.backend} · p=${depth}` : `No selected answer substituted. Backend: ${report.backend}`;
    status.textContent = `Fresh measurement finished: ${report.backend}, ${shots} shots. Green map markers show the live repaired selection. Stop and Run again for another job.`;
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type:'application/json'}));
    const download = document.getElementById('download');
    download.href = downloadUrl;
    download.download = 'signal-in-the-bush-live-result.json';
    download.hidden = false;
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    status.textContent = `Measurement failed: ${error.message || error}. Stop and Run again to retry; no saved result is presented as live.`;
    console.error(String(error));
  }
});
