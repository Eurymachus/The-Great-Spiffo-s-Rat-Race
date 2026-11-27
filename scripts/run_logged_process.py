"""Run a foreground child with bounded, private, closed-log archives."""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import uuid

from host_artifacts import FORMAT, MANIFEST, checked, inventory, protect, utcnow


class Segments:
    def __init__(self, root, label, limit=10 * 1024 * 1024):
        self.root = checked(root)
        if not self.root.is_dir():
            raise ValueError('Log root must already exist.')
        self.label, self.limit = label, limit
        self.path, self.streams, self.size, self.day = None, {}, 0, None
        self.started_at = None
        self.closed_paths = []

    def close(self):
        if self.path is None:
            return
        for stream in self.streams.values():
            stream.close()
        data = dict(format=FORMAT, kind='closed-routine-log',
                    completed_at=utcnow().isoformat(), retention_started_at=self.started_at,
                    files=inventory(self.path))
        (self.path / MANIFEST).write_text(json.dumps(data, indent=2), encoding='utf-8')
        self.closed_paths.append(self.path.name)
        self.path, self.streams = None, {}

    def write(self, stream, block):
        while block:
            today = utcnow().date()
            if self.path is not None and (self.size >= self.limit or today != self.day):
                self.close()
            if self.path is None:
                self.path = self.root / ('routine-' + self.label + '-' + utcnow().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
                self.path.mkdir()
                protect(self.path)
                self.streams = {name: (self.path / (name + '.log')).open('wb') for name in ('stdout', 'stderr')}
                self.size, self.day = 0, today
                self.started_at = utcnow().isoformat()
            portion, block = block[:self.limit - self.size], block[self.limit - self.size:]
            self.streams[stream].write(portion)
            self.streams[stream].flush()
            self.size += len(portion)


def run(command, root, label, limit=10 * 1024 * 1024, control_root=None):
    logs = Segments(root, label, limit)
    events = queue.Queue(maxsize=128)
    control = None
    child_env = os.environ.copy()
    if control_root is not None:
        control_root = checked(control_root)
        control_root.mkdir(exist_ok=True)
        protect(control_root)
        token = uuid.uuid4().hex
        control = dict(token=token, pid=os.getpid(), started_at=utcnow().isoformat(), state='running')
        child_env.update(RR_PROCESS_STOP_FILE=str(control_root / (token + '.stop')),
                         RR_PROCESS_STOP_TOKEN=token)

    def write_control(state, result=None):
        if control is not None:
            control.update(state=state, exit_code=result, closed_segments=logs.closed_paths)
            temporary = control_root / (label + '.json.tmp')
            temporary.write_text(json.dumps(control), encoding='utf-8')
            temporary.replace(control_root / (label + '.json'))

    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child_env)

    def pump(name, stream):
        try:
            while block := stream.read1(65536):
                events.put((name, block))
        except OSError:
            events.put(('error', None))
        finally:
            stream.close()
            events.put((name, None))

    threads = [threading.Thread(target=pump, args=(name, stream), daemon=True)
               for name, stream in [('stdout', child.stdout), ('stderr', child.stderr)]]
    for thread in threads:
        thread.start()
    remaining = 2
    try:
        write_control('running')
        while remaining:
            try:
                name, block = events.get(timeout=1)
            except queue.Empty:
                if logs.path is not None and logs.day != utcnow().date():
                    logs.close()
                continue
            if name == 'error':
                raise OSError('Child log stream failed.')
            if block is None:
                remaining -= 1
            else:
                logs.write(name, block)
        result = child.wait()
        logs.close()
        write_control('exited', result)
        return result
    except BaseException:
        # A logging failure must fail the wrapper, not leave an unmonitored child.
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for stream in logs.streams.values():
            stream.close()
        write_control('failed')
        # Do not mark a failed/incomplete segment safe for automatic expiry.
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--label', choices=['web', 'worker'], required=True)
    parser.add_argument('--control-root')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    command = options.command[1:] if options.command[:1] == ['--'] else options.command
    if not command:
        parser.error('A child command is required.')
    raise SystemExit(run(command, Path(options.root), options.label, control_root=options.control_root))
