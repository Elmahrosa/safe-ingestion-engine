import fnmatch
import urllib.robotparser
from urllib.parse import urlparse

class ComplianceGuard:

    def __init__(self, patterns):
        self.patterns = patterns
        self.rp = urllib.robotparser.RobotFileParser()

    def is_permitted(self,url):

        if not any(fnmatch.fnmatch(url.lower(),p.lower()) for p in self.patterns):
            return False,"BLOCKED_SCOPE","URL not allowed"

        parsed=urlparse(url)
        robots=f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            self.rp.set_url(robots)
            self.rp.read()
        except:
            return False,"BLOCKED_ROBOTS","robots unreachable"

        if not self.rp.can_fetch("*",url):
            return False,"BLOCKED_ROBOTS","Denied by robots"

        return True,"ALLOWED","Passed checks"
