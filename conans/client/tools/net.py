import os

from conans.client.rest.uploader_downloader import FileDownloader
from conans.client.tools.files import check_md5, check_sha1, check_sha256, unzip
from conans.errors import ConanException
from conans.util.fallbacks import default_output, default_requester


def get(url, md5='', sha1='', sha256='', destination=".", filename="", keep_permissions=False,
        pattern=None, requester=None, output=None, verify=True, retry=None, retry_wait=None,
        overwrite=False, auth=None, headers=None, download_cache=None):
    """ high level downloader + unzipper + (optional hash checker) + delete temporary zip
    """
    if not filename and ("?" in url or "=" in url):
        raise ConanException("Cannot deduce file name from url. Use 'filename' parameter.")

    filename = filename or os.path.basename(url)

    in_cache = False
    if download_cache is not None and download_cache.contains(url):
        download_cache.get(url, filename)
        try:
            if md5:
                check_md5(filename, md5)
            if sha1:
                check_sha1(filename, sha1)
            if sha256:
                check_sha256(filename, sha256)
            in_cache = True
            if output:
                output.info("Using cached version of {}".format(url))
        except:
            if output:
                output.warn("Download cache contains {}, but with wrong checksum, attempting download again".format(url))
            # Attempt to unlink the file with the checksum mismatch
            try:
                os.unlink(filename)
            except:
                pass

    if not in_cache:
        download(url, filename, out=output, requester=requester, verify=verify, retry=retry,
                retry_wait=retry_wait, overwrite=overwrite, auth=auth, headers=headers)

    if md5:
        check_md5(filename, md5)
    if sha1:
        check_sha1(filename, sha1)
    if sha256:
        check_sha256(filename, sha256)

    if download_cache and not in_cache:
        try:
            download_cache.put(url, filename)
        except Exception as e:
            if output:
                output.warn("Could not add {} to download cache: {}".format(url, str(e)))

    unzip(filename, destination=destination, keep_permissions=keep_permissions, pattern=pattern,
          output=output)
    os.unlink(filename)


def ftp_download(ip, filename, login='', password=''):
    import ftplib
    try:
        ftp = ftplib.FTP(ip)
        ftp.login(login, password)
        filepath, filename = os.path.split(filename)
        if filepath:
            ftp.cwd(filepath)
        with open(filename, 'wb') as f:
            ftp.retrbinary('RETR ' + filename, f.write)
    except Exception as e:
        try:
            os.unlink(filename)
        except OSError:
            pass
        raise ConanException("Error in FTP download from %s\n%s" % (ip, str(e)))
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def download(url, filename, verify=True, out=None, retry=None, retry_wait=None, overwrite=False,
             auth=None, headers=None, requester=None):

    out = default_output(out, 'conans.client.tools.net.download')
    requester = default_requester(requester, 'conans.client.tools.net.download')
    from conans.tools import _global_config as config

    # It might be possible that users provide their own requester
    retry = retry if retry is not None else config.retry
    retry = retry if retry is not None else 1
    retry_wait = retry_wait if retry_wait is not None else config.retry_wait
    retry_wait = retry_wait if retry_wait is not None else 5

    downloader = FileDownloader(requester=requester, output=out, verify=verify, config=config)
    downloader.download(url, filename, retry=retry, retry_wait=retry_wait, overwrite=overwrite,
                        auth=auth, headers=headers)
    out.writeln("")
