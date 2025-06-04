from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(ManifestStaticFilesStorage):
  def hashed_name(self, name, content=None, filename=None):
    try:
      result = super().hashed_name(name, content, filename)
    except ValueError:
      # When a map file is missing, let's forgive and ignore that.
      result = name
      if not name.endswith(".map"):
        print("Cannot find file " + name + " for hashing extension. Check NPM_FILE_PATTERNS.")
    return result
