<< 'ISC-License'
Copyright (c) 2019, Timothée Mazzucotelli

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
ISC-License

#!/usr/bin/env bash
set -e

PYTHON_VERSIONS="${PYTHON_VERSIONS-3.10 3.11}"

restore_previous_python_version() {
    if pdm use -f "$1" &>/dev/null; then
        echo "> Restored previous Python version: ${1##*/}"
    fi
}

if [ -n "${PYTHON_VERSIONS}" ]; then
    old_python_version="$(pdm config python.path)"
    echo "> Currently selected Python version: ${old_python_version##*/}"
    trap "restore_previous_python_version ${old_python_version}" EXIT
    for python_version in ${PYTHON_VERSIONS}; do
        if pdm use -f "python${python_version}" &>/dev/null; then
        echo "> pdm run $@ (python${python_version})"
            pdm run "$@"
        else
            echo "> pdm use -f python${python_version}: Python interpreter not available?" >&2
        fi
    done
else
    pdm run "$@"
fi
