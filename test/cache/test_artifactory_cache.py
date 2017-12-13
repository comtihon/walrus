import os
import unittest
from os.path import join

import requests
from artifactory import ArtifactoryPath
from mock import patch

import test
from coon.__main__ import create, package
from coon.pac_cache.cache import Cache
from coon.pac_cache.cache_man import CacheMan
from coon.pac_cache.local_cache import LocalCache
from coon.packages.dep import Dep
from coon.packages.package import Package
from coon.packages.package_builder import Builder
from coon.packages.package_controller import Controller
from test.abs_test_class import TestClass, set_git_url, set_git_tag, set_deps, modify_config


def mock_fetch_package(dep: Package):
    test_dir = test.get_test_dir('artifactory_tests')
    tmp_path = join(os.getcwd(), test_dir, 'tmp')
    dep.update_from_cache(join(tmp_path, dep.name))


# Artifactory should be available locally on path
class ArtifactoryTests(TestClass):
    def __init__(self, method_name):
        super().__init__('artifactory_tests', method_name)

    @property
    def path(self):
        return 'http://localhost:8081/artifactory/example-repo-local'

    @property
    def username(self):
        return 'admin'

    @property
    def password(self):
        return 'password'

    @property
    def global_config(self):
        return {'temp_dir': self.tmp_dir,
                'compiler': self.compiler,
                'cache': [
                    {
                        'name': 'local_cache',
                        'type': 'local',
                        'url': 'file://' + self.cache_dir
                    },
                    {
                        'name': 'artifactory-local',
                        'type': 'artifactory',
                        'url': self.path,
                        'username': self.username,
                        'password': self.password
                    }]}

    def setUp(self):
        super().setUp()
        create(self.test_dir, {'<name>': 'test_project'})

    # Test package uploading to artifactory
    @patch('coon.global_properties.ensure_conf_file')
    def test_simple_uploading(self, mock_conf):
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'http://github/comtihon/test_project')
        set_git_tag(pack_path, '1.0.0')
        pack = Package.from_path(pack_path)
        package(pack_path, {})
        builder = Builder.init_from_path(pack_path)
        builder.system_config.cache.add_package(pack, 'artifactory-local', False, False)
        exists = self.check_exists(pack)
        self.assertEqual(True, exists)

    # Test package branch uploading to artifactory
    @patch('coon.global_properties.ensure_conf_file')
    def test_branch_uploading(self, mock_conf):
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'http://github/comtihon/test_project')
        pack = Package.from_path(pack_path)
        package(pack_path, {})
        builder = Builder.init_from_path(pack_path)
        builder.system_config.cache.add_package(pack, 'artifactory-local', False, False)
        exists = self.check_exists(pack)
        self.assertEqual(True, exists)

    # check if not exists, add package, check if exists
    @patch('coon.global_properties.ensure_conf_file')
    def test_exists(self, mock_conf):
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'http://github/comtihon/test_project')
        set_git_tag(pack_path, '1.0.0')
        pack = Package.from_path(pack_path)
        builder = Builder.init_from_path(pack_path)
        exists = self.check_exists(pack)
        self.assertEqual(False, exists)
        package(pack_path, {})
        self.assertEqual(True, os.path.isfile(join(pack_path, 'test_project.cp')))
        builder.system_config.cache.add_package(pack, 'artifactory-local', False, False)
        exists = self.check_exists(pack)
        self.assertEqual(True, exists)

    # download package from remote cache, add to local
    @patch('coon.global_properties.ensure_conf_file')
    def test_simple_downloading(self, mock_conf):
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        pack = Package.from_dep('test_project', Dep('git://github.com/comtihon/test_project', 'master', tag='0.0.1'))
        pack.update_from_cache(pack_path)
        package(pack_path, {})
        builder = Builder.init_from_path(pack_path)
        self.add_with_namespace(pack_path, pack)
        self.assertEqual(False, builder.system_config.cache.local_cache.exists(pack))
        artifactory_cache = builder.system_config.cache.remote_caches['artifactory-local']
        artifactory_cache.fetch_package(pack)
        self.assertEqual(True, os.path.isfile(join(self.tmp_dir, 'test_project.cp')))
        builder.system_config.cache.add_fetched(artifactory_cache, pack)
        self.assertEqual(True, builder.system_config.cache.local_cache.exists(pack))

    # upload package and all it's deps to remote
    @patch.object(LocalCache, 'fetch_package', side_effect=mock_fetch_package)
    @patch('coon.global_properties.ensure_conf_file')
    def test_uploading_with_deps(self, mock_conf, _):
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'https://github/comtihon/test_project')
        set_git_tag(pack_path, '1.0.0')
        set_deps(pack_path,
                 [
                     {'name': 'dep',
                      'url': 'https://github.com/comtihon/dep',
                      'tag': '1.0.0'}
                 ])
        # Create dep with dep.
        create(self.tmp_dir, {'<name>': 'dep'})
        dep_path = join(self.tmp_dir, 'dep')
        set_git_url(dep_path, 'https://github/comtihon/dep')
        set_git_tag(dep_path, '1.0.0')
        set_deps(dep_path,
                 [
                     {'name': 'dep_dep',
                      'url': 'https://github.com/comtihon/dep_dep',
                      'tag': '1.0.0'}
                 ])
        create(self.tmp_dir, {'<name>': 'dep_dep'})
        dep_dep_path = join(self.tmp_dir, 'dep_dep')
        set_git_url(dep_dep_path, 'https://github/comtihon/dep_dep')
        set_git_tag(dep_dep_path, '1.0.0')
        builder = Builder.init_from_path(pack_path)
        builder.populate()
        self.assertEqual(True, package(pack_path, {}))
        self.assertEqual(True, builder.add_package('artifactory-local', True, True))
        # All two deps are in cache now
        dep_pack = Package.from_path(dep_path)
        dep_dep_pack = Package.from_path(dep_dep_path)
        self.assertEqual(True, self.check_exists(dep_pack))
        self.assertEqual(True, self.check_exists(dep_dep_pack))

    # download package and all it's deps from remote
    @patch.object(LocalCache, 'fetch_package', side_effect=mock_fetch_package)
    @patch('coon.global_properties.ensure_conf_file')
    def test_downloading_with_deps(self, mock_conf, _):
        mock_conf.return_value = self.conf_file
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'https://github/comtihon/test_project')
        set_git_tag(pack_path, '1.0.0')
        set_deps(pack_path,
                 [
                     {'name': 'dep',
                      'url': 'https://github.com/comtihon/dep',
                      'tag': '1.0.0'}
                 ])
        # Create dep with dep.
        create(self.tmp_dir, {'<name>': 'dep'})
        dep_path = join(self.tmp_dir, 'dep')
        set_git_url(dep_path, 'https://github/comtihon/dep')
        set_git_tag(dep_path, '1.0.0')
        set_deps(dep_path,
                 [
                     {'name': 'dep_dep',
                      'url': 'https://github.com/comtihon/dep_dep',
                      'tag': '1.0.0'}
                 ])
        create(self.tmp_dir, {'<name>': 'dep_dep'})
        dep_dep_path = join(self.tmp_dir, 'dep_dep')
        set_git_url(dep_dep_path, 'https://github/comtihon/dep_dep')
        set_git_tag(dep_dep_path, '1.0.0')
        builder = Builder.init_from_path(pack_path)
        builder.populate()
        self.assertEqual(True, package(pack_path, {}))
        # adding package and deps by hand, to load with correct namespaces
        self.add_with_namespace(pack_path, builder.project)
        self.add_with_namespace(dep_path, Package.from_path(dep_path))
        self.add_with_namespace(dep_dep_path, Package.from_path(dep_dep_path))
        self.clear_local_cache()
        # clear local cache to be sure we don't have this packages locally
        dep = Package.from_path(dep_path)
        dep_dep = Package.from_path(dep_dep_path)
        self.assertEqual(False, builder.system_config.cache.local_cache.exists(dep))
        self.assertEqual(False, builder.system_config.cache.local_cache.exists(dep_dep))
        artifactory_cache = builder.system_config.cache.remote_caches['artifactory-local']
        # download package and all its deps from remote
        exists = builder.system_config.cache.exists_remote(artifactory_cache, builder.project)
        self.assertEqual(True, exists)
        self.assertEqual(True, builder.system_config.cache.local_cache.exists(dep))
        self.assertEqual(True, builder.system_config.cache.local_cache.exists(dep_dep))

    # download package and all it's deps from remote, if some deps are not in remote
    @patch.object(LocalCache, 'fetch_package', side_effect=mock_fetch_package)
    @patch('coon.global_properties.ensure_conf_file')
    def test_downloading_with_deps_some_missing(self, mock_conf, _):
        mock_conf.return_value = self.conf_file
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'https://github/comtihon/test_project')
        set_git_tag(pack_path, '1.0.0')
        set_deps(pack_path,
                 [
                     {'name': 'dep',
                      'url': 'https://github.com/comtihon/dep',
                      'tag': '1.0.0'}
                 ])
        # Create dep with dep.
        create(self.tmp_dir, {'<name>': 'dep'})
        dep_path = join(self.tmp_dir, 'dep')
        set_git_url(dep_path, 'https://github/comtihon/dep')
        set_git_tag(dep_path, '1.0.0')
        builder = Builder.init_from_path(pack_path)
        builder.populate()
        self.assertEqual(True, package(pack_path, {}))
        # Load project without dep to artifactory
        self.add_with_namespace(pack_path, builder.project)
        self.clear_local_cache()
        # clear local cache to be sure we don't have this packages locally
        dep = Package.from_path(dep_path)
        self.assertEqual(False, builder.system_config.cache.local_cache.exists(dep))
        artifactory_cache = builder.system_config.cache.remote_caches['artifactory-local']
        # download package from remote
        exists = builder.system_config.cache.exists_remote(artifactory_cache, builder.project)
        self.assertEqual(True, exists)
        # package's dep was fetched, built and added by local cache
        self.assertEqual(True, builder.system_config.cache.local_cache.exists(dep))

    # Cache man should not crash if repo is unavailable
    # Test if this cache is unavailable
    def test_cache_unavailable(self):
        caches = {'temp_dir': self.tmp_dir,
                  'compiler': self.compiler,
                  'cache': [
                      {
                          'name': 'local_cache',
                          'type': 'local',
                          'url': 'file://' + self.cache_dir
                      },
                      {
                          'name': 'artifactory-local',
                          'type': 'artifactory',
                          'url': 'http://some_unavailable_url',
                          'username': self.username,
                          'password': self.password
                      }]}
        cache_man = CacheMan(caches)
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'http://github/comtihon/test_project')
        set_git_tag(pack_path, '1.0.0')
        pack = Package.from_path(pack_path)
        package(pack_path, {})
        res = cache_man.add_package(pack, 'artifactory-local', False, False)
        self.assertEqual(False, res)

    # Package from artifactory cache can be fetched to local
    @patch('coon.global_properties.ensure_conf_file')
    def test_fetch_package(self, mock_conf):
        mock_conf.return_value = self.conf_file
        erl = Cache.get_erlang_version()
        pack_path = join(self.test_dir, 'test_project')
        set_git_url(pack_path, 'http://github/comtihon/test_project')
        # package and load
        modify_config(pack_path, {'tag': '1.0.0'})
        package(pack_path, {})
        path = ArtifactoryPath(join(self.path, 'comtihon/test_project/1.0.0', erl),
                               auth=(self.username, self.password))
        if not path.exists():
            path.mkdir()
        path.deploy_file(join(pack_path, 'test_project' + '.cp'))
        # load another version
        modify_config(pack_path, {'tag': '1.1.0'})
        package(pack_path, {})
        path = ArtifactoryPath(join(self.path, 'comtihon/test_project/1.1.0', erl),
                               auth=(self.username, self.password))
        if not path.exists():
            path.mkdir()
        path.deploy_file(join(pack_path, 'test_project' + '.cp'))
        # check local cache doesn't contain this package
        pack1 = Package.from_dep('test_project', Dep('git://github.com/comtihon/test_project', 'master', tag='1.0.0'))
        pack2 = Package.from_dep('test_project', Dep('git://github.com/comtihon/test_project', 'master', tag='1.1.0'))
        controller = Controller()
        self.assertEqual(False, controller.system_config.cache.local_cache.exists(pack1))
        self.assertEqual(False, controller.system_config.cache.local_cache.exists(pack2))
        artifactory_cache = controller.system_config.cache.remote_caches['artifactory-local']
        # check versions available
        self.assertEqual(['1.0.0', '1.1.0'], artifactory_cache.get_versions('comtihon/test_project'))
        # check fetched version exists
        self.assertEqual(True, controller.fetch('comtihon/test_project', '1.0.0'))
        self.assertEqual(True, controller.system_config.cache.local_cache.exists(pack1))
        self.assertEqual(False, controller.system_config.cache.local_cache.exists(pack2))
        # fetch newer version
        self.assertEqual(True, controller.fetch('comtihon/test_project', '1.1.0'))
        self.assertEqual(True, controller.system_config.cache.local_cache.exists(pack1))
        self.assertEqual(True, controller.system_config.cache.local_cache.exists(pack2))

    def tearDown(self):
        super().tearDown()
        try:
            path = ArtifactoryPath(self.path, auth=(self.username, self.password))
            if path.exists():
                path.rmdir()
        except requests.exceptions.ConnectionError:
            return

    # check exist with username as a namespace (as ArtifactoryCache::add_package adds package with username namespace)
    def check_exists(self, pack: Package):
        check_path = join(self.username, pack.name, pack.git_vsn, Cache.get_erlang_version())
        path = ArtifactoryPath(join(self.path, check_path), auth=(self.username, self.password))
        return path.exists()

    # ArtifactoryCache::add_package adds package with username namespace. This test function avoids it
    def add_with_namespace(self, pack_path: str, pack: Package):
        package_path = join(pack.fullname, pack.git_vsn, Cache.get_erlang_version())
        path = ArtifactoryPath(join(self.path, package_path),
                               auth=(self.username, self.password))
        if not path.exists():
            path.mkdir()  # exist_ok doesn't work there on python3.2-3.5
        path_to_package = join(pack_path, pack.name + '.cp')
        path.deploy_file(path_to_package)


if __name__ == '__main__':
    unittest.main()