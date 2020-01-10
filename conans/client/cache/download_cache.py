import os
import shutil

from hashlib import sha256
from six import text_type
from tempfile import NamedTemporaryFile

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

class DownloadCache(object):
    def __init__(self, cache_folder):
        self.cache_folder = cache_folder
        if not os.path.isdir(self.cache_folder):
            os.makedirs(self.cache_folder)

    def contains(self, url):
        return os.path.exists(self.file_of(url))

    def get(self, url, filename):
        src = self.file_of(url)
        if not os.path.exists(src):
            raise KeyError(url)
        shutil.copyfile(src, filename)

    def put(self, url, filename):
        target_dir = self.dir_of(url)
        dest = self.file_of(url)
        os.makedirs(target_dir, exist_ok=True)

        # Create a temporary file in the target directory and
        # atomically replace the cache file with the new file
        # so that we don't need any file locking. This only
        # works in Python 3.3 or higher (where os.replace was
        # introduced), so fall back to non-atomic renaming on
        # older versions. (But even in the non-atomic case
        # the temporary file ensures that in the worst case the
        # cache doesn't contain the entry, but not that an
        # incomplete file is found there.)
        temp_file = NamedTemporaryFile(dir=target_dir, delete=False)
        temp_file.close()
        try:
            shutil.copyfile(filename, temp_file.name)
            if 'replace' in dir(os):
                os.replace(temp_file.name, dest)
            else:
                try:
                    os.unlink(dest)
                except FileNotFoundError:
                    pass
                os.rename(temp_file.name, dest)
        except:
            # Try to remove the temporary file on a best-effort
            # basis, but forward the original error more than
            # any error that might occur during the removal of
            # the file.
            try:
                os.unlink(temp_file)
            except:
                pass
            raise

    def remove(self, url):
        try:
            os.unlink(self.file_of(url))
        except FileNotFoundError:
            pass

    @staticmethod
    def encode(url):
        if isinstance(url, text_type):
            url = url.encode('utf-8', errors='replace')
        return sha256(url).hexdigest()

    def dir_of(self, url):
        encoded = self.encode(url)
        parts = [encoded[i:i+2] for i in range(0, 4, 2)]
        return os.path.join(self.cache_folder, *parts)

    def file_of(self, url):
        encoded = self.encode(url)
        parts = [encoded[i:i+2] for i in range(0, 4, 2)]
        return os.path.join(self.cache_folder, *parts, encoded)
