"""Polled subprocess pipeline; no Blender API and no shell command strings."""
import os
from pathlib import Path
import signal
import subprocess
import time

class Pipeline:
    def __init__(self,commands,directory,timeout=120,environment=None,*,stage_names=None):
        self.commands=list(commands);self.directory=Path(directory);self.timeout=timeout
        self.environment=environment;self.process=None;self.index=0;self.state='READY';self.log=None
        self.message='';self.started=0
        self.stage_names = stage_names
    def stage_name(self, index):
        if self.stage_names:
            return self.stage_names[index]
        command=self.commands[index]
        return f'Stage {index+1}' if callable(command) else Path(command[0]).name

    def recent_output(self):
        """Read a bounded tail, including the compiler's current partial line."""
        if self.process is None:
            return ()
        try:
            with (self.directory/f'stage-{self.index}.log').open('rb') as stream:
                size=stream.seek(0,os.SEEK_END)
                offset=max(0,size-4096)
                stream.seek(offset)
                lines=stream.read(4096).decode('utf-8',errors='replace').splitlines()
        except OSError:
            return ()
        if offset and len(lines)>1:
            lines=lines[1:]
        return tuple(line.strip()[-240:] for line in lines if line.strip())[-4:]

    def progress(self):
        """Report completed stages and label the active stage without estimating its progress."""
        total=len(self.commands)
        if self.state=='READY':
            return 0.0, 'Preparing build'
        completed=self.index-int(self.process is not None)
        fraction=completed/max(1,total)
        if self.process is None:
            return fraction, f'Completed {completed}/{total} stages'
        stage=self.stage_name(self.index-1)
        elapsed=int(time.monotonic()-self.started)
        return fraction, f'{stage} ({self.index}/{total}) · {elapsed//60}:{elapsed%60:02d}'

    # docs:begin pipeline-poll
    def poll(self):
        """Advance at most one queued stage and return its nonblocking state.

        Called repeatedly by the owner. Terminal states are stable; a timeout
        cancels the active process and records FAILED rather than restarting it.
        """
        if self.state in {'DONE','FAILED','CANCELLED'}: return self.state
        if self.process:
            # poll() never waits for a compiler; Blender must keep handling input.
            code=self.process.poll()
            if code is None:
                if time.monotonic()-self.started>self.timeout:
                    stage = self.stage_name(self.index-1)
                    self.cancel()
                    self.state = 'FAILED'
                    self.message = f'{stage} timed out after {self.timeout:g} seconds (stage-{self.index}.log)'
                return self.state
            self.log.close();self.log=None;self.process=None
            if code:
                self.state='FAILED'
                self.message=f'{self.stage_name(self.index-1)} exited with code {code} (stage-{self.index}.log)'
                return self.state
        if self.index==len(self.commands): self.state='DONE';return self.state
        command=self.commands[self.index]
        # Callable stages and subprocess stages share the same ordered queue.
        if callable(command):
            try:command()
            except Exception as exc:self.state='FAILED';self.message=str(exc);return self.state
            self.index+=1;self.state='RUNNING';return self.state
        log_name=f'stage-{self.index+1}.log'
        try:
            self.log=(self.directory/log_name).open('w')
            self.process=subprocess.Popen(command,cwd=self.directory,stdout=self.log,stderr=subprocess.STDOUT,
                                          env=self.environment,start_new_session=True)
        except OSError as exc:
            if self.log:self.log.close();self.log=None
            self.state='FAILED'
            self.message=f'Could not start {self.stage_name(self.index)} ({log_name}): {exc}'
            return self.state
        self.index+=1;self.started=time.monotonic();self.state='RUNNING';return self.state
    # docs:end pipeline-poll
    def cancel(self):
        if self.process and self.process.poll() is None:
            if os.name=='posix': os.killpg(self.process.pid,signal.SIGKILL)
            else: self.process.kill()
            self.process.wait(timeout=5)
        if self.log:self.log.close();self.log=None
        self.process=None;self.state='CANCELLED';self.message='Build cancelled'


def publish_bsp(source, destination):
    """Replace the selected output atomically after compilation has succeeded."""
    import shutil
    import tempfile
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.' + destination.name + '.', suffix='.tmp',
                                         dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            with source.open('rb') as incoming:
                shutil.copyfileobj(incoming, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
