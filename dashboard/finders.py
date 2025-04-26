from django_npm.finders import NpmFinder


class NpmStringFinder(NpmFinder):
  def _make_list_generator(self, ignore_patterns=None):
    # Original NpmFinder returns a PosixPath, which is incompatible with ManifestStaticFilesStorage
    for path, storage in super()._make_list_generator(ignore_patterns):
      yield str(path), storage
