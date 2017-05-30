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
from unittest.mock import MagicMock, patch, ANY, call
from openwebvulndb.wordpress.vane2.release import GitHubRelease
from os.path import join
from fixtures import async_test
from aiohttp.test_utils import make_mocked_coro
from aiohttp import BasicAuth
import json


class TestGitHubRelease(TestCase):

    def setUp(self):
        self.release = GitHubRelease()
        self.release.set_repository_settings("Owner", "password", "repository_name")

        self.release.aiohttp_session = MagicMock()
        self.release.aiohttp_session.get.return_value = AsyncContextManagerMock()
        self.release.aiohttp_session.post.return_value = AsyncContextManagerMock()

        self.files_in_dir = ["file1.json", "file2.json"]
        self.dir_path = "files/to/compress"
        fake_glob = MagicMock(return_value=[join(self.dir_path, self.files_in_dir[0]),
                                                 join(self.dir_path, self.files_in_dir[1])])
        glob_patch = patch("openwebvulndb.wordpress.vane2.release.glob", fake_glob)
        glob_patch.start()
        self.addCleanup(glob_patch.stop)

    def test_set_repository_settings_merge_api_url_with_repo_owner_and_name(self):
        self.release.set_repository_settings("Owner", None, "repository_name")

        self.assertEqual(self.release.url, "https://api.github.com/repos/Owner/repository_name")

    @async_test()
    async def test_get_latest_release_request_latest_release_as_json_to_github_api(self):
        await self.release.get_latest_release()

        self.release.aiohttp_session.get.assert_called_once_with(self.release.url + "/releases/latest")

    @async_test()
    async def test_get_latest_release_return_response_as_json(self):
        response = MagicMock()
        response.json = make_mocked_coro(return_value={"tag_name": "1.0"})
        self.release.aiohttp_session.get.return_value.aenter_return = response

        release = await self.release.get_latest_release()

        response.json.assert_called_once_with()
        self.assertEqual(release, {"tag_name": "1.0"})

    def test_get_release_version_return_tag_name_of_release(self):
        release = {"tag_name": "1.0"}

        version = self.release.get_release_version(release)

        self.assertEqual(version, "1.0")

    def test_get_release_version_return_version_none_if_no_release_found(self):
        release = {"message": "Not Found"}

        version = self.release.get_release_version(release)

        self.assertIsNone(version)

    def test_get_release_id_return_id_of_release(self):
        release = {'id': "12345"}

        release_id = self.release.get_release_id(release)

        self.assertEqual(release_id, "12345")

    @async_test()
    async def test_create_release_create_release_with_new_version_from_master(self):
        self.release.get_release_version = make_mocked_coro("1.0")
        self.release.commit_data = MagicMock()

        await self.release.create_release()

        data = {'tag_name': '1.0', 'target_commitish': 'master', 'name': '1.0'}
        self.release.aiohttp_session.post.assert_called_once_with("https://api.github.com/repos/Owner/repository_name/"
                                                                  "releases", data=json.dumps(data), auth=ANY)

    @async_test()
    async def test_create_release_send_credential_with_post_request(self):
        self.release.get_release_version = make_mocked_coro("1.0")
        self.release.commit_data = MagicMock()
        self.release.set_repository_settings("Owner", "password", "repository_name")

        await self.release.create_release()

        data = {'tag_name': '1.0', 'target_commitish': 'master', 'name': '1.0'}
        self.release.aiohttp_session.post.assert_called_once_with(ANY, data=ANY, auth=BasicAuth("Owner", password="password"))

    @async_test()
    async def test_create_release_commit_data(self):
        self.release.get_release_version = make_mocked_coro("1.0")
        self.release.commit_data = MagicMock()

        await self.release.create_release()

        self.release.commit_data.assert_called_once_with()

    def test_commit_data_chdir_to_repository(self):
        fake_chdir = MagicMock()
        fake_run = MagicMock()


        with patch("openwebvulndb.wordpress.vane2.release.chdir", fake_chdir):
            with patch("openwebvulndb.wordpress.vane2.release.run", fake_run):
                self.release.commit_data()

                fake_chdir.assert_called_once_with(self.release.repository_path)

    def test_commit_data_create_commit_with_all_data_files(self):
        fake_run = MagicMock()
        fake_chdir = MagicMock()
        with patch("openwebvulndb.wordpress.vane2.release.run", fake_run):
            with patch("openwebvulndb.wordpress.vane2.release.chdir", fake_chdir):
                self.release.commit_data()

                fake_run.assert_called_once_with("./commit_data.sh")

    @async_test()
    async def test_release_vane_data_raise_value_error_if_no_wordpress_data_release_exists(self):
        self.release.get_latest_release = make_mocked_coro(return_value={})

        with self.assertRaises(ValueError):
            await self.release.release_vane_data(self.dir_path)

    @async_test()
    async def test_release_vane_data_compressed_exported_data(self):
        self.release.get_latest_release = make_mocked_coro(return_value={'tag_name': '1.0', 'id': '12345'})
        self.release.compress_exported_files = MagicMock()
        self.release.upload_compressed_data = make_mocked_coro()

        await self.release.release_vane_data(self.dir_path)

        self.release.compress_exported_files.assert_called_once_with(self.dir_path, '1.0')

    @async_test()
    async def test_release_vane_data_upload_compressed_data(self):
        self.release.get_latest_release = make_mocked_coro(return_value={'tag_name': '1.0', 'id': '12345'})
        self.release.compress_exported_files = MagicMock(return_value="filename_1.0.tar.gz")
        self.release.upload_compressed_data = make_mocked_coro()

        await self.release.release_vane_data(self.dir_path)

        self.release.upload_compressed_data.assert_called_once_with(self.dir_path, "filename_1.0.tar.gz")

    @async_test()
    async def test_upload_compressed_data_upload_exported_compressed_data_as_asset_of_latest_release(self):
        release_id = "12345"
        self.release.get_latest_release = make_mocked_coro(return_value={'tag_name': "1.0", 'id': release_id})
        asset_name = "asset.tar.gz"
        asset_raw_data = b'compressed data...'
        self.release.load_compressed_file = MagicMock(return_value=asset_raw_data)

        await self.release.upload_compressed_data(asset_name, asset_name)

        self.asset_upload_url = "https://uploads.github.com/repos/{0}/{1}/releases/{2}/assets?name={3}"\
            .format(self.release.repository_owner, self.release.repository_name, release_id, asset_name)
        headers = {'Content-Type': "application/gzip"}
        self.release.aiohttp_session.post.assert_called_once_with(self.asset_upload_url, headers=headers, auth=ANY, data=asset_raw_data)

    @async_test()
    async def test_upload_compressed_data_fetch_latest_release(self, loop):
        latest_release = {'tag_name': "1.0", 'id': "12345"}
        self.release.get_latest_release = make_mocked_coro(return_value=latest_release)
        self.release.get_assets_upload_url = MagicMock()
        asset_name = "asset.tar.gz"
        asset_raw_data = b'compressed data...'
        self.release.load_compressed_file = MagicMock(return_value=asset_raw_data)

        await self.release.upload_compressed_data(asset_name, asset_name)

        self.release.get_latest_release.assert_called_once_with()
        self.release.get_assets_upload_url.assert_called_once_with("12345", asset_name)

    def test_get_asset_upload_url(self):
        release_id = "12345"
        asset_name = "test.tar.gz"

        url = self.release.get_assets_upload_url(release_id, asset_name)

        self.assertEqual(url, "https://uploads.github.com/repos/{0}/{1}/releases/{2}/assets?name={3}".format(
            self.release.repository_owner, self.release.repository_name, release_id, asset_name))

    def test_compress_exported_files_create_tar_archives_with_all_json_files_in_directory(self):
        fake_tarfile_obj = MagicMock()
        fake_tarfile_open = MagicMock()
        fake_tarfile_open.return_value.__enter__.return_value = fake_tarfile_obj
        self.files_in_dir.append("file.txt")

        with(patch("openwebvulndb.wordpress.vane2.release.tarfile.open", fake_tarfile_open)):
            self.release.compress_exported_files(self.dir_path, "1.0")

            fake_tarfile_open.assert_called_once_with(ANY, "w:gz")
            fake_tarfile_obj.add.assert_has_calls([call(join(self.dir_path, self.files_in_dir[0]), self.files_in_dir[0]),
                                                   call(join(self.dir_path, self.files_in_dir[1]), self.files_in_dir[1])],
                                                  any_order=True)

    def test_compress_exported_files_use_version_to_release_in_archive_name(self):
        dir_path = "files/to/compress"
        fake_tarfile_open = MagicMock()

        with(patch("openwebvulndb.wordpress.vane2.release.tarfile.open", fake_tarfile_open)):
            self.release.compress_exported_files(dir_path, "1.3")

            fake_tarfile_open.assert_called_once_with(dir_path + "/vane2_data_1.3.tar.gz", ANY)

    def test_compress_exported_files_return_filename(self):
        dir_path = "files/to/compress"
        fake_tarfile_open = MagicMock()

        with(patch("openwebvulndb.wordpress.vane2.release.tarfile.open", fake_tarfile_open)):
            filename = self.release.compress_exported_files(dir_path, "1.3")

            self.assertEqual(filename, "vane2_data_1.3.tar.gz")


class AsyncContextManagerMock(MagicMock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for key in ('aenter_return', 'aexit_return'):
            setattr(self, key,  kwargs[key] if key in kwargs else MagicMock())

    async def __aenter__(self):
        return self.aenter_return

    async def __aexit__(self, *args):
        return self.aexit_return
