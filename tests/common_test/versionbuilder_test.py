# openwebvulndb-tools: A collection of tools to maintain vulnerability databases
# Copyright (C) 2016-  Delve Labs inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from unittest import TestCase
from unittest.mock import MagicMock
from openwebvulndb.common.versionbuilder import VersionBuilder
from openwebvulndb.common.models import Signature, VersionDefinition, VersionList, FileSignature, File, FileList


class TestVersionBuilder(TestCase):

    def setUp(self):
        def exclude_useless_files_for_identification(file_paths, version_list):
            return file_paths
        self.version_builder = VersionBuilder()
        self.version_builder.exclude_useless_files_for_identification = exclude_useless_files_for_identification

    def test_create_file_list_from_version_list_return_all_hash_regroup_by_files(self):

        signature0 = Signature(path="file", hash="12345")
        signature1 = Signature(path="readme", hash="54321")
        signature2 = Signature(path="readme", hash="56789")
        version0 = VersionDefinition(version="1.0", signatures=[signature0, signature1])
        version1 = VersionDefinition(version="1.1", signatures=[signature0, signature1])
        version2 = VersionDefinition(version="1.2", signatures=[signature0, signature2])
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        file_list = self.version_builder.create_file_list_from_version_list(version_list)

        file = [file for file in file_list.files if file.path == "file"][0]
        self.assertEqual(file.path, "file")
        self.assertEqual(len(file.signatures), 1)
        self.assertEqual(file.signatures[0].hash, "12345")
        self.assertEqual(len(file.signatures[0].versions), 3)

        readme = [file for file in file_list.files if file.path == "readme"][0]
        self.assertEqual(readme.path, "readme")
        self.assertEqual(len(readme.signatures), 2)
        self.assertEqual(readme.signatures[0].hash, "54321")
        self.assertEqual(len(readme.signatures[0].versions), 2)
        self.assertIn("1.0", readme.signatures[0].versions)
        self.assertIn("1.1", readme.signatures[0].versions)
        self.assertEqual(readme.signatures[1].hash, "56789")
        self.assertEqual(readme.signatures[1].versions, ["1.2"])

    def test_create_file_list_from_version_list_return_none_if_no_signature_in_version_definitions(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        version2 = VersionDefinition(version="1.2")
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])
        self.version_builder.is_version_list_empty = MagicMock(return_value=False)

        file_list = self.version_builder.create_file_list_from_version_list(version_list)

        self.assertIsNone(file_list)

    def test_create_file_list_from_version_list_recreate_version_list(self):
        self.version_builder.recreate_version_list = MagicMock()
        self.version_builder.is_version_list_empty = MagicMock(return_value=False)
        version_list = VersionList(key="key", producer="producer")

        self.version_builder.create_file_list_from_version_list(version_list, files_to_keep_per_version=50)

        self.version_builder.recreate_version_list.assert_called_once_with(version_list, 50)

    def test_create_file_from_version_list_file_create_file_with_all_file_signatures_for_file_path(self):
        version_list = VersionList(producer="producer", key="key", versions=[])
        self.version_builder.get_file_signatures = MagicMock(return_value=["signatures"])

        file = self.version_builder.create_file_from_version_list("file", version_list)

        self.assertEqual(file.path, "file")
        self.version_builder.get_file_signatures.assert_called_once_with("file", version_list)
        self.assertEqual(file.signatures, ["signatures"])

    def test_get_file_signatures_regroup_all_versions_with_identical_hash_for_file_in_same_file_signature_model(self):
        signature0 = Signature(path="file", hash="12345")
        signature1 = Signature(path="readme", hash="54321")
        version0 = VersionDefinition(version="1.0", signatures=[signature0, signature1])
        version1 = VersionDefinition(version="1.1", signatures=[signature0, signature1])
        version2 = VersionDefinition(version="1.2", signatures=[signature0, signature1])
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        file_signatures0 = self.version_builder.get_file_signatures("file", version_list)
        file_signatures1 = self.version_builder.get_file_signatures("readme", version_list)

        file_signature0 = file_signatures0[0]
        file_signature1 = file_signatures1[0]
        self.assertEqual(len(file_signatures0), 1)
        self.assertEqual(len(file_signatures1), 1)
        self.assertEqual(file_signature0.hash, signature0.hash)
        self.assertEqual(file_signature1.hash, signature1.hash)
        versions = [version.version for version in version_list.versions]
        self.assertTrue(all(version in versions for version in file_signature0.versions))
        self.assertTrue(all(version in versions for version in file_signature1.versions))

    def test_get_signature_return_signature_with_specified_file_path_in_version_definition(self):
        signature0 = Signature(path="file0", hash="1")
        signature1 = Signature(path="file1", hash="2")
        signature2 = Signature(path="file2", hash="3")
        version = VersionDefinition(version="1.0", signatures=[signature0, signature1, signature2])

        sign0 = self.version_builder.get_signature("file0", version)
        sign1 = self.version_builder.get_signature("file1", version)
        sign2 = self.version_builder.get_signature("file2", version)

        self.assertEqual(sign0, signature0)
        self.assertEqual(sign1, signature1)
        self.assertEqual(sign2, signature2)

    def test_get_file_paths_from_version_list(self):
        signature0 = Signature(path="file0", hash="1")
        signature1 = Signature(path="file1", hash="2")
        signature2 = Signature(path="file2", hash="3")
        signature3 = Signature(path="file3", hash="4")
        signature4 = Signature(path="file0", hash="5")
        version0 = VersionDefinition(version="1.0", signatures=[signature0, signature1, signature2])
        version1 = VersionDefinition(version="1.1", signatures=[signature0, signature1, signature3])
        version2 = VersionDefinition(version="1.2", signatures=[signature4, signature2])
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        file_paths = self.version_builder.get_file_paths_from_version_list(version_list)

        self.assertEqual(len(file_paths), 4)
        self.assertIn("file0", file_paths)
        self.assertIn("file1", file_paths)
        self.assertIn("file2", file_paths)
        self.assertIn("file3", file_paths)

    def test_create_file_list_from_version_list_exclude_files_beginning_with_trunk(self):
        signature0 = Signature(path="wp-content/plugins/my-plugin/trunk/file0", hash="1")
        signature1 = Signature(path="wp-content/plugins/my-plugin/file1", hash="2")
        signature2 = Signature(path="wp-content/plugins/my-plugin/file2", hash="3")
        signature3 = Signature(path="wp-content/plugins/my-plugin/trunk/file3", hash="4")
        version = VersionDefinition(version="1.2", signatures=[signature0, signature1, signature2, signature3])
        version_list = VersionList(producer="producer", key="plugins/my-plugin", versions=[version])

        file_list = self.version_builder.create_file_list_from_version_list(version_list)

        self.assertEqual(len(file_list.files), 2)
        self.assertIn(signature1.path, [file.path for file in file_list.files])
        self.assertIn(signature2.path, [file.path for file in file_list.files])

    def test_create_file_list_from_version_list_exclude_files_beginning_with_tags(self):
        signature0 = Signature(path="wp-content/plugins/my-plugin/tags/1.0/file0", hash="1")
        signature1 = Signature(path="wp-content/plugins/my-plugin/file1", hash="2")
        signature2 = Signature(path="wp-content/plugins/my-plugin/file2", hash="3")
        signature3 = Signature(path="wp-content/plugins/my-plugin/tags/1.0/file3", hash="4")
        version = VersionDefinition(version="1.2", signatures=[signature0, signature1, signature2, signature3])
        version_list = VersionList(producer="producer", key="plugins/my-plugin", versions=[version])

        file_list = self.version_builder.create_file_list_from_version_list(version_list)

        self.assertEqual(len(file_list.files), 2)
        self.assertIn(signature1.path, [file.path for file in file_list.files])
        self.assertIn(signature2.path, [file.path for file in file_list.files])

    def test_create_file_list_from_version_list_exclude_files_beginning_with_branches(self):
        signature0 = Signature(path="wp-content/plugins/my-plugin/branches/file0", hash="1")
        signature1 = Signature(path="wp-content/plugins/my-plugin/file1", hash="2")
        signature2 = Signature(path="wp-content/plugins/my-plugin/file2", hash="3")
        signature3 = Signature(path="wp-content/plugins/my-plugin/branches/file3", hash="4")
        version = VersionDefinition(version="1.2", signatures=[signature0, signature1, signature2, signature3])
        version_list = VersionList(producer="producer", key="plugins/my-plugin", versions=[version])

        file_list = self.version_builder.create_file_list_from_version_list(version_list)

        self.assertEqual(len(file_list.files), 2)
        self.assertIn(signature1.path, [file.path for file in file_list.files])
        self.assertIn(signature2.path, [file.path for file in file_list.files])

    def test_recreate_version_list_do_nothing_if_total_amount_of_files_is_lower_than_max(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        version2 = VersionDefinition(version="1.2")
        for i in range(0, 5):
            version0.signatures.append(Signature(path="file%d" % i, hash=str(i)))
            version1.signatures.append(Signature(path="file%d" % i, hash="A%d" % i))
            version2.signatures.append(Signature(path="file%d" % i, hash="B%d" % i))
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        self.version_builder.recreate_version_list(version_list, files_to_keep_per_diff=10)

        self.assertEqual(version_list.versions[0], version0)
        self.assertEqual(version_list.versions[1], version1)
        self.assertEqual(version_list.versions[2], version2)

    def test_recreate_version_list_choose_files_arbitrarily_if_only_one_version_and_more_files_than_max(self):
        version = VersionDefinition(version="1.0")
        for i in range(0, 15):
            version.signatures.append(Signature(path="file%d" % i, hash=str(i)))
        version_list = VersionList(producer="producer", key="key", versions=[version])

        self.version_builder.recreate_version_list(version_list, files_to_keep_per_diff=10)

        self.assertEqual(len(version_list.versions[0].signatures), 10)

    def test_recreate_version_list_add_files_to_diff_to_have_max_files_per_version_if_less_diff_than_max(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        version2 = VersionDefinition(version="1.2")
        for i in range(0, 15):
            version0.signatures.append(Signature(path="file%d" % i, hash=str(i)))
            version1.signatures.append(Signature(path="file%d" % i, hash=str(i)))
        for i in range(0, 4):
            version2.signatures.append(Signature(path="file%d" % (i + 15), hash=str(i * 2)))
            version2.signatures.append(Signature(path="file%d" % i, hash="hash"))
        for i in range(4, 6):
            version2.signatures.append(Signature(path="file%d" % i, hash=str(i)))
        # only one difference between the two versions
        version1.signatures.append(Signature(path="fileA", hash="unique_hash"))
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        self.version_builder.recreate_version_list(version_list, files_to_keep_per_diff=10)

        self.assertEqual(len(version0.signatures), 10)
        self.assertEqual(len(version1.signatures), 10)
        self.assertEqual(len(version2.signatures), 10)
        self.assertIn("fileA", [signature.path for signature in version1.signatures])
        for i in range(0, 4):
            self.assertIn("file%d" % i, [signature.path for signature in version2.signatures])
            self.assertIn("file%d" % (i + 15), [signature.path for signature in version2.signatures])
        for i in range(4, 6):
            self.assertIn("file%d" % i, [signature.path for signature in version2.signatures])

    def test_get_diff_between_versions_set_all_files_as_diff_for_first_version(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        for i in range(0, 5):
            version0.signatures.append(Signature(path="file%d" % i, hash=str(i)))
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1])

        diff_list = self.version_builder._get_diff_between_versions(version_list, 14)

        self.assertEqual(len(diff_list["1.0"]), 5)

    def test_recreate_version_list_keep_max_files_from_most_common_files_if_no_changes_between_version(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        for i in range(0, 10):  # All versions are equal
            same_signature = Signature(path="file%d" % i, hash=str(i))
            version0.signatures.append(same_signature)
            version1.signatures.append(same_signature)
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1])

        self.version_builder.recreate_version_list(version_list, 10)

        self.assertEqual(len(version0.signatures), 10)
        for i in range(0, 10):
            self.assertIn("file%d" % i, [signature.path for signature in version0.signatures])

    def test_get_diff_between_versions_return_all_files_that_differ_or_are_added_between_versions(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        version2 = VersionDefinition(version="1.2")
        for i in range(0, 5):  # All versions are equal
            same_signature = Signature(path="file%d" % i, hash=str(i))
            version0.signatures.append(same_signature)
            version1.signatures.append(same_signature)
            version2.signatures.append(same_signature)
        for i in range(5, 10):  # 5 diff between each version
            version0.signatures.append(Signature(path="file%d" % i, hash=str(i)))
            version1.signatures.append(Signature(path="file%d" % i, hash="A%d" % i))
            version2.signatures.append(Signature(path="file%d" % i, hash="B%d" % i))
        for i in range(10, 15):  # 10 diff between 1.0 and 1.1
            version0.signatures.append(Signature(path="file%d" % i, hash=str(i)))
            version1.signatures.append(Signature(path="file%d" % i, hash="A%d" % i))
            version2.signatures.append(Signature(path="file%d" % i, hash="A%d" % i))
        for i in range(15, 20):  # 10 diff between 1.1 and 1.2
            version0.signatures.append(Signature(path="file%d" % i, hash=str(i)))
            version1.signatures.append(Signature(path="file%d" % i, hash=str(i)))
            version2.signatures.append(Signature(path="file%d" % i, hash="A%d" % i))
        for i in range(20, 25):  # 15 diff between 1.1 and 1.2
            version2.signatures.append(Signature(path="file%d" % i, hash=str(i)))

        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        diff_list = self.version_builder._get_diff_between_versions(version_list, 10)

        self.assertEqual(len(diff_list["1.1"]), 10)
        self.assertEqual(len(diff_list["1.2"]), 10)

    def test_keep_most_common_file_in_all_diff_for_each_diff(self):
        diff_1_0 = ["file0", "file1", "file2", "file3", "file4"]
        diff_1_1 = ["file2", "file3"]
        diff_1_2 = ["file3", "file5", "file6"]
        differences_between_versions = {"1.0": diff_1_0, "1.1": diff_1_1, "1.2": diff_1_2}

        self.version_builder._keep_most_common_file_in_all_diff_for_each_diff(differences_between_versions, 2)

        self.assertEqual(len(differences_between_versions["1.0"]), 2)
        self.assertIn("file2", differences_between_versions["1.0"])
        self.assertIn("file3", differences_between_versions["1.0"])
        self.assertEqual(len(differences_between_versions["1.1"]), 2)
        self.assertIn("file2", differences_between_versions["1.1"])
        self.assertIn("file3", differences_between_versions["1.1"])
        self.assertEqual(len(differences_between_versions["1.2"]), 2)
        self.assertIn("file3", differences_between_versions["1.2"])

    def test_get_most_common_files(self):
        version0 = VersionDefinition(version="1.0")
        version1 = VersionDefinition(version="1.1")
        version2 = VersionDefinition(version="1.2")
        # most common files
        signature0 = Signature(path="file0", hash="1")
        signature1 = Signature(path="file1", hash="2")
        version0.signatures.append(signature0)
        version1.signatures.append(signature0)
        version2.signatures.append(signature0)
        version0.signatures.append(signature1)
        version1.signatures.append(signature1)
        version2.signatures.append(signature1)
        # Only in 1.1 and 1.2
        version1.signatures.append(Signature(path="file2", hash="3"))
        version2.signatures.append(Signature(path="file2", hash="4"))
        # only in 1.0
        version0.signatures.append(Signature(path="file3", hash="5"))
        version_list = VersionList(producer="producer", key="key", versions=[version0, version1, version2])

        three_most_common_files = self.version_builder._get_most_common_files(version_list, 3)
        two_most_common_files = self.version_builder._get_most_common_files(version_list, 2)

        self.assertIn("file0", three_most_common_files)
        self.assertIn("file1", three_most_common_files)
        self.assertIn("file2", three_most_common_files)
        self.assertNotIn("file3", three_most_common_files)
        self.assertIn("file0", two_most_common_files)
        self.assertIn("file1", two_most_common_files)
        self.assertNotIn("file2", two_most_common_files)
        self.assertNotIn("file3", two_most_common_files)

    def test_get_most_common_files_present_in_version_return_files_in_given_version_and_common_to_most_versions(self):
        version = VersionDefinition(version="1.0")
        version.signatures.append(Signature(path="file0", hash="1"))
        version.signatures.append(Signature(path="file1", hash="2"))
        version.signatures.append(Signature(path="file2", hash="3"))
        self.version_builder._get_most_common_files = MagicMock(return_value=["file0", "file1", "file3", "file4",
                                                                              "file2"])

        files = self.version_builder._get_most_common_files_present_in_version("version_list", version, 2)

        self.assertIn("file0", files)
        self.assertIn("file1", files)
        self.assertNotIn("file2", files)  # won't be returned because only two files are required and it's the least common file.
        self.assertNotIn("file3", files)
        self.assertNotIn("file4", files)

    def test_compare_signature_dont_return_files_that_are_removed_in_current_version(self):
        file0 = Signature(path="file0", hash="0")
        file1 = Signature(path="file1", hash="1")
        previous_version = VersionDefinition(version="1.0", signatures=[file0, file1])
        current_version = VersionDefinition(version="1.1", signatures=[file1])

        diff = self.version_builder._compare_versions_signatures(previous_version, current_version)

        self.assertEqual(len(diff), 0)
