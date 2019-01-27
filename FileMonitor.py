"""
argument is directory to watch and filetypes
if file of correct type is added or changed
we call upon PhotonSlicerGUI to ask user how to slice
"""

import os, sys,time

class FileMonitor:
    def __init__(self,path_to_watch=".", extensions_to_watch=(".stl",".svg")):
        if getattr(sys, 'frozen', False):# frozen
            self.installpath = os.path.dirname(sys.executable)
        else: # unfrozen
            self.installpath = os.path.dirname(os.path.realpath(__file__))


        self.path_to_watch = path_to_watch.strip()
        self.ends=extensions_to_watch
        self.before = dict ([(f, None) for f in os.listdir (self.path_to_watch)])

        # Wait for changed/added files
        self.added=[]
        while not self.added:
            time.sleep(1)
            self.added=list(self.monitor())


    def monitor(self):
          after = dict ([(f, None) for f in os.listdir (self.path_to_watch)])
          added = [f for f in after if not f in self.before]
          added = (a for a in added if any(a.lower().endswith(end) for end in self.ends))
          self.before = after
          return (added)

if __name__=='__main__':
    m=FileMonitor()
