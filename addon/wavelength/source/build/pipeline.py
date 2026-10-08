"""Polled subprocess pipeline; no Blender API and no shell command strings."""
import os
from pathlib import Path
import signal
import subprocess
import time

class Pipeline:
    def __init__(self,commands,directory,timeout=120,environment=None):
        self.commands=list(commands);self.directory=Path(directory);self.timeout=timeout
        self.environment=environment;self.process=None;self.index=0;self.state='READY';self.log=None
        self.message='';self.started=0
    def poll(self):
        if self.state in {'DONE','FAILED','CANCELLED'}: return self.state
        if self.process:
            code=self.process.poll()
            if code is None:
                if time.monotonic()-self.started>self.timeout:
                    self.cancel();self.state='FAILED';self.message='Compiler timed out'
                return self.state
            self.log.close();self.log=None;self.process=None
            if code:
                self.state='FAILED';self.message=f'Stage {self.index} exited with {code}';return self.state
        if self.index==len(self.commands): self.state='DONE';return self.state
        command=self.commands[self.index]
        self.log=(self.directory/f'stage-{self.index+1}.log').open('w')
        try:
            self.process=subprocess.Popen(command,cwd=self.directory,stdout=self.log,stderr=subprocess.STDOUT,
                                          env=self.environment,start_new_session=True)
        except OSError as exc:
            self.log.close();self.log=None;self.state='FAILED';self.message=str(exc);return self.state
        self.index+=1;self.started=time.monotonic();self.state='RUNNING';return self.state
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
