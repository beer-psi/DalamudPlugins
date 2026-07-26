# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests>=2.34.2",
# ]
# ///
import json
import os
from time import time

import requests

DOWNLOAD_URL = '{}/releases/download/v{}/latest.zip'
GITHUB_RELEASES_API_URL = 'https://api.github.com/repos/{}/{}/releases/tags/v{}'

DEFAULTS = {
    'IsHide': False,
    'IsTestingExclusive': False,
    'ApplicableVersion': 'any',
}

DUPLICATES = {
    'DownloadLinkInstall': ['DownloadLinkTesting', 'DownloadLinkUpdate'],
}

TRIMMED_KEYS = [
    'Author',
    'Name',
    'Punchline',
    'Description',
    'Changelog',
    'InternalName',
    'AssemblyVersion',
    'RepoUrl',
    'ApplicableVersion',
    'Tags',
    'CategoryTags',
    'DalamudApiLevel',
    'IconUrl',
    'ImageUrls',
]

def main():
    # extract the manifests from the repository
    master = extract_manifests()

    # trim the manifests
    master = [trim_manifest(manifest) for manifest in master]

    # convert the list of manifests into a master list
    add_extra_fields(master)

    # update LastUpdate fields
    try:
        get_last_updated_times(master)
    except FileNotFoundError:
        pass

    # write the master
    write_master(master)

def extract_manifests():
    manifests = []

    for dirpath, dirnames, filenames in os.walk('./plugins'):
        plugin_name = dirpath.split('/')[-1]
        if len(filenames) == 0 or f'{plugin_name}.json' not in filenames:
            continue
        with open(f'{dirpath}/{plugin_name}.json', 'r') as f:
            manifest = json.load(f)
            manifests.append(manifest)

    return manifests

def add_extra_fields(manifests):
    for manifest in manifests:
        owner, repo = manifest["RepoUrl"].split("/")[-2:]

        # generate the download link
        manifest['DownloadLinkInstall'] = DOWNLOAD_URL.format(manifest['RepoUrl'], manifest['AssemblyVersion'])

        # add default values if missing
        for k, v in DEFAULTS.items():
            if k not in manifest:
                manifest[k] = v

        # duplicate keys as specified in DUPLICATES
        for source, keys in DUPLICATES.items():
            for k in keys:
                if k not in manifest:
                    manifest[k] = manifest[source]

        manifest['DownloadCount'] = get_release_download_count(owner, repo, manifest['AssemblyVersion'])

def get_release_download_count(username, repo, id):
    r = requests.get(GITHUB_RELEASES_API_URL.format(username, repo, id))
    if r.status_code == 200:
        data = r.json()
        total = 0
        for asset in data['assets']:
            total += asset['download_count']
        return total
    else:
        return 0

def get_last_updated_times(manifests):
    with open('pluginmaster.json', 'r') as f:
        previous_manifests = json.load(f)

        for manifest in manifests:
            manifest['LastUpdate'] = str(int(time()))

            for previous_manifest in previous_manifests:
                if manifest['InternalName'] != previous_manifest['InternalName']:
                    continue

                if (
                    manifest['AssemblyVersion'] == previous_manifest['AssemblyVersion']
                    and (last_update := previous_manifest.get("LastUpdate")) is not None
                ):
                    manifest['LastUpdate'] = last_update

                break

def write_master(master):
    # write as pretty json
    with open('pluginmaster.json', 'w') as f:
        json.dump(master, f, indent=4)

def trim_manifest(plugin):
    return {k: plugin[k] for k in TRIMMED_KEYS if k in plugin}

if __name__ == '__main__':
    main()
