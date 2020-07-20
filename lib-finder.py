#!/usr/bin/env python3
#
# Script to get Gradle dependency declaration for a set
# of jar files using Maven Central REST API
#

import os
import sys
import requests
import re
import configparser
from tabulate import tabulate


def load_custom_equivalences():
    config = configparser.ConfigParser()
    config.read("custom-equivalences.properties")
    return config


def get_configured_equivalence(properties, library_name):
    if properties['main']:
        return properties['main'].get(library_name)
    return None


def get_components(name):
    match_obj = re.search(r'(.*)-(\d.*?)\.jar', name, re.M | re.I)
    if match_obj is None or len(match_obj.groups()) != 2:
        return ()
    return match_obj.groups()


def usage():
    print("Usage: lib-finder lib-folder")
    print()
    print("       lib-folder: path of the folder that contains he libraries to search in Maven ")


if len(sys.argv) < 2:
    usage()
    exit(1)

libFolder = sys.argv[1]
libraries = next(os.fwalk(libFolder))[2]
libraries = list(filter(lambda x: not x.startswith(".") and not x.startswith("biospace"), libraries))
equivalences = []
customEquivalences = load_custom_equivalences()

for library in libraries:
    if not library.endswith(".jar"):
        print(f"! {library} does not look like a jar, ignoring...")
        equivalences.append((library, "?"))
        continue

    manualEquivalence = get_configured_equivalence(customEquivalences, library)
    if manualEquivalence is not None:
        equivalences.append((library, manualEquivalence))
        continue

    libraryComponents = get_components(library)

    if not len(libraryComponents) == 2:
        print(f"! {library} does not conform with the expected format name...")
        equivalences.append((library, "?"))
        continue

    query = f"a:{libraryComponents[0]} AND v:{libraryComponents[1]}"
    resp = requests.get(f"https://search.maven.org/solrsearch/select?q={query}")
    if not resp.status_code == 200:
        equivalences.append((library, "?"))
        continue

    searchResult = resp.json()['response']
    if searchResult is None or searchResult['numFound'] == 0:
        equivalences.append((library, "?"))
        continue

    mavenMatch = searchResult['docs'][0]['id']  # Get the first match, ignore the rest
    equivalences.append((library, mavenMatch))

equivalences.sort(key=lambda x: x[0])
print()
print(tabulate(equivalences, headers=['Jar', 'Gradle import'], tablefmt='orgtbl'))
print()
for equivalence in equivalences:
    if equivalence[1] == "?":
        print(f"// MISSING {equivalence[0]}")
    else:
        print(f"implementation '{equivalence[1]}' // {equivalence[0]}")


