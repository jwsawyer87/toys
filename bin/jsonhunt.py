#! /usr/bin/python -u

import re
import sys
import json
import getopt

def syntax(msg=None):
    if msg:
        sys.stderr.write(msg + "\n")
    sys.stderr.write("Syntax: %s [--verbose] [--file FILENAME] [--not] REGEXP[=REGEXP]\n")
    exit(1)

def regexpCompile(pattern, optional=False):
    ret = None
    if pattern or (not optional):
        if not pattern:
            syntax("Pattern must be present")
        try:
            ret = re.compile(pattern)
        except Exception as e:
            syntax("Could not compile %s: %s" % (repr(pattern), str(e)))

    return ret

class Jsonhunt(object):
    def __init__(self, key, value, negate=False):
        self.key = key
        self.value = value
        self.negate = negate

    def hunt(self, root, path=[]):
        ret = []

        if type(root) == dict:
            matched = False
            for curr in root.keys():
                currValue = root[curr]

                keyMatch = True if self.key.search(curr) else False
                valueMatch = True if not self.value else ((type(currValue) in [str, unicode]) and self.value.search(currValue))

                if self.negate:
                    if self.value:
                        matched = keyMatch and (not valueMatch)
                else:
                    matched = keyMatch and valueMatch

                ret += self.hunt(root[curr], path + [str(curr)])

            if self.negate and (not matched) and (not self.value):
                matched = all([not self.key.match(curr) for curr in root.keys()])

            if matched:
                ret += [{"path": "/" + "/".join(path), "tree": root}]

        elif type(root) == list:
            for curr in range(len(root)):
                ret += self.hunt(root[curr], path + [str(curr)])

        if not path:
            """
              Before the top-level method returns its result, it simplifies the lists and dictionaries
              in the results so we only see the elements that matched the search and nothing below them. 
              We turn the values of lists and dictionaries into strings that simply describe the
              lists/dictionaries.
            """
            for tree in [hit["tree"] for hit in ret]:
                for item in tree.keys() if type(tree) == dict else []:
                    if type(tree[item]) == list:
                        tree[item] = "<%d element list>" % len(tree[item])
                    elif type(tree[item]) == dict:
                        tree[item] = "<%d element dictionary>" % len(tree[item].keys())

        return ret

if __name__ == "__main":
    negate = False
    filename = None

    (opts, args) = ([], [])
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "vf:", ["negate", "file="])
    except Exception as e:
        syntax(str(e))

    for (opt,arg) in opts:
        if opt in ["-v", "--negate"]:
            negate = not negate
        if opt in ["-F", "--file"]:
            filename = arg
        else:
            syntax("Don't know how to handle %s" % repr(opt))

    if len(args) != 1:
        syntax("Exactly one argument is expected")

    match = re.search("^([^=]+)(=(.+))?$", args[0])
    if not match:
        syntax("%s is not a valid key-value pair" % repr(args[0]))

    key = regexpCompile(match.group(1))
    value = regexpCompile(match.group(3), optional=True)

    root = None
    if filename:
        with open(filename) as stream:
            root = json.load(stream)
    else:
        if sys.stdin.isatty():
            syntax("stdin must be redirected")
        root = json.load(sys.stdin)

    root = Jsonhunt(key, value, negate).hunt(root)

    print json.dumps(root, indent=2, sort_keys=True)