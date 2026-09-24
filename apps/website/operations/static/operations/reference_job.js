(() => {
  const root = document.getElementById('reference-job');
  if (!root) return;
  const element = id => document.getElementById(id);
  let job;
  function elapsed() {
    if (!job || !job.started_at) return;
    const end = job.finished_at ? Date.parse(job.finished_at) : Date.now();
    const seconds = Math.max(0, Math.floor((end - Date.parse(job.started_at)) / 1000));
    element('job-elapsed').textContent = `${Math.floor(seconds / 3600)}h ${Math.floor(seconds / 60) % 60}m ${seconds % 60}s`;
  }
  const clock = setInterval(elapsed, 1000);
  async function refresh() {
    let again = true;
    try {
      const response = await fetch(root.dataset.url, {cache: 'no-store', headers: {'Accept': 'application/json'}});
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Unavailable');
      job = await response.json();
      const heading = document.querySelector('#content h1');
      if (heading) heading.textContent = job.title;
      for (const field of ['status', 'previous_build_id', 'installed_build_id', 'summary', 'started_at', 'finished_at']) {
        const value = document.querySelector(`.field-${field} .readonly`);
        if (value) value.textContent = field.endsWith('_at') && job[field] ? new Date(job[field]).toLocaleString() : (job[field] || '-');
      }
      element('job-connection').textContent = job.active ? 'Live updates connected. Refreshing every 2 seconds.' : `Finished: ${job.status}`;
      element('job-stage').textContent = job.active ? (job.message || 'Waiting for worker output.') : (job.summary || job.status);
      const progress = element('job-progress');
      progress.hidden = !job.active;
      if (job.percent === null) progress.removeAttribute('value');
      else progress.value = job.percent;
      element('job-progress-label').textContent = !job.active ? '' : job.percent === null ? 'The tool has not reported a percentage for this stage.' : `${job.percent.toFixed(1)}% of current stage`;
      const log = element('job-log');
      const output = job.log || 'No captured output yet. Jobs started before live logging was enabled cannot provide a running log.';
      if (log.textContent !== output) {
        log.textContent = output;
        if (element('job-follow').checked) log.scrollTop = log.scrollHeight;
      }
      elapsed();
      again = job.active;
      if (!again) clearInterval(clock);
    } catch {
      element('job-connection').textContent = 'Connection lost. Retrying automatically; if this continues, refresh and sign in again.';
    }
    if (again) setTimeout(refresh, 2000);
  }
  refresh();
})();
