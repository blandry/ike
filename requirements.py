import os

f = open("requirements.txt")
reqs = f.read().split("\n")

for req in reqs:
    # ignore comments or pip options
    if req.startswith('--') or req.startswith('#'):
        continue
    # ignore blank lines
    if len(req) > 0:
        os.system("easy_install-2.7 %s" % req)
