#
# This code is heavily inspired by original code from ScanCode Toolkit.
# The copyright header is therefore propagated. The content is primarily
# taken from following packages in the ScanCode Toolkit:
# - cluecode.plugin_copyright
# - scancode.api
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import re
import sys

import attr
from commoncode.cliutils import PluggableCommandLineOption
from commoncode.cliutils import SCAN_GROUP
from plugincode.scan import ScanPlugin
from plugincode.scan import scan_impl


@scan_impl
class AllrightsCopyrightScanner(ScanPlugin):
    """Scan a Resource for copyrights with all rights reserved. This class is an adapted version of
    scancodes cluecode.plugin_copyright.
    """

    resource_attributes = dict(
        [
            ("copyrights", attr.ib(default=attr.Factory(list))),
            ("holders", attr.ib(default=attr.Factory(list))),
            ("authors", attr.ib(default=attr.Factory(list))),
        ]
    )

    run_order = 6
    sort_order = 6

    options = [
        PluggableCommandLineOption(
            (
                "-a",
                "--allrights",
            ),
            is_flag=True,
            default=False,
            help="Scan <input> for copyrights and all rights reserved.",
            help_group=SCAN_GROUP,
            sort_order=50,
        ),
    ]

    def is_enabled(self, copyright, **kwargs):  # NOQA
        return copyright

    def get_scanner(self, **kwargs):
        return allrights_scanner


def allrights_scanner(
        location,
        deadline=sys.maxsize,
        **kwargs,
):
    """Return a mapping with a single 'copyrights' key with a value that is a list
    of mappings for copyright detected in the file at `location`.
    Adapted copy of scancodes scancode.api.get_copyrights.
    """
    from cluecode.copyrights import detect_copyrights
    from cluecode.copyrights import Detection
    import cluecode.copyrights

    cluecode.copyrights.strip_trailing_period = lambda s: s # Avoid stripping periods of detected copyrights
    cluecode.copyrights.remove_man_comment_markers = re.compile(r'^\.\\"').sub # Recognize man page comments

    detections = detect_copyrights(
        location,
        include_copyrights=True,
        include_holders=True,
        include_authors=True,
        include_copyright_years=True,
        include_copyright_allrights=True,
        deadline=deadline,
    )

    copyrights, holders, authors = Detection.split(detections, to_dict=True)

    results = dict([
        ('copyrights', copyrights),
        ('holders', holders),
        ('authors', authors),
    ])

    return results
