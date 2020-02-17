# Copyright 2018 The Fuego Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""

Test collect_args

"""
from pathlib import Path

import pytest

from lib import collect_args


def test_required_string_arg():
    requiredArgs = [
        ["n", "name", "some string"],
    ]
    args = collect_args.collectArgsInt(['-n', 'abc'], requiredArgs, [], None, False)
    assert args.name == 'abc'


def test_optional_string_arg():
    optionalArgs = [
        ["o", "name", "some string"],
    ]
    args = collect_args.collectArgsInt(['-o', 'bcd'], [], optionalArgs, None, False)
    assert args.name == 'bcd'


def test_required_integer_arg():
    requiredArgs = [
        ["v", "value", "some integer", int],
    ]
    args = collect_args.collectArgsInt(['-v', '121'], requiredArgs, [], None, False)
    assert args.value == 121


def test_missing_required_arg():
    requiredArgs = [
        ["n", "name", "some string"],
    ]
    # expecting OSError: reading from stdin while output is captured
    with pytest.raises(OSError):
        args = collect_args.collectArgsInt([], requiredArgs, [], None, False)


def test_args_from_yaml():
    required_args = [
        ["o", "outputDir", "local directory to save images segments"],
        ["i", "inputCsv", "csvfile with contents of Fuego Cropped Images"],
        ["x", "compulsoryInt", "an integer argument that is compulsory", int],
    ]
    opt_args = [
        ["s", "startRow", "starting row", int],
        ["e", "endRow", "ending row", int],
    ]
    test_yaml = str(Path(__file__).parent / 'test_args.txt')
    test_args = [f"@{test_yaml}"]
    args = collect_args.collectArgsInt(test_args, required_args, opt_args, None, True, '@')
    # test_args = ["--outputDir", "tmpimages", "--inputCsv", "file.csv", "--compulsoryInt", "10", "--endRow", "2"]
    # args = collect_args.collectArgsInt(test_args, required_args, opt_args, None, True)
    assert args.outputDir == "tmpimages"
    assert args.endRow == 2
