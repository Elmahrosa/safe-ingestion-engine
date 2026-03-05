import re

class PIIScrubber:

    patterns={
        "EMAIL":re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",re.I),
        "PHONE":re.compile(r"\+?\d[\d\s-]{7,}")
    }

    def scrub(self,text):

        counts={}

        for k,p in self.patterns.items():

            m=p.findall(text)

            if m:
                counts[k]=len(m)
                text=p.sub(f"[REDACTED:{k}]",text)

        return text,counts
