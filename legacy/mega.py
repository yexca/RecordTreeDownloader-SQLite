import subprocess, sys, shlex

class Mega:
    def __init__(self):
        pass

    def run(self, cmd):
        print(">>", cmd)
        args = cmd if isinstance(cmd, (list, tuple)) else shlex.split(cmd)
        proc = subprocess.Popen(
            args,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1
        )
        try:
            for line in iter(proc.stdout.readline, ""):
                sys.stdout.write(line)
                sys.stdout.flush()
        finally:
            proc.stdout.close()
            ret=proc.wait()
        if ret != 0:
            raise RuntimeError(f"command failed: {cmd}")

    def is_logged_in(self):
        # cmd = "mega-whoami"
        result = subprocess.run(
            ["mega-whoami"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            encoding="utf-8",
            text=True
        )
        return result.returncode == 0
    
    def login_if_needed(self, acc, pwd):
        if self.is_logged_in():
            print("Already logged in.")
        else:
            print("logging in...")
            self.run(["mega-login", acc, pwd])
        
    def download(self, link, save_dir):
        self.run(["mega-get", link, save_dir])