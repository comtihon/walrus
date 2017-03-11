import json

from walrus.packages.config import config_factory
from walrus.packages.config.stub_config import StubConfig


class Package:
    url = None  # git url
    vsn = None  # git tag / git commit hash
    config = None  # ConfigFile
    deps = None  # list of deps.

    def __init__(self, config=None, url=None, vsn=None):
        self.url = url
        self.vsn = vsn
        self.config = config
        self.__fill_deps()

    def fill_from_path(self, path):
        self.config = config_factory.upgrade_conf(path, self.config)
        self.__fill_deps()

    @classmethod
    def frompath(cls, path):
        config = config_factory.read_project(path)
        return cls(config=config)

    @classmethod
    def fromdeps(cls, name, dep):
        (url, vsn) = dep
        config = StubConfig(name)
        return cls(url=url, vsn=vsn, config=config)

    def export(self):
        return {'name': self.config.name,
                'url': self.url,
                'vsn': self.vsn,
                'deps': [dep.export() for _, dep in self.deps.items()]}

    def get_valrus_package(self):
        export = self.export()
        export_config = self.config.export()
        return json.dumps({**export, **export_config}, sort_keys=True, indent=4)

    # TODO is name enough unique?
    def get_name(self):
        return self.config.name

    def list_deps(self) -> list:
        return self.deps.values()

    def __fill_deps(self):
        deps = self.config.read_config()
        for name, dep in deps.items():
            print(name + ' ' + str(dep))
            deps[name] = Package.fromdeps(name, dep)
        self.deps = deps