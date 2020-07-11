from constants import GITHUB_URL


def file_url(repo_name, rev, path):
    """
    Forges Github URL to a blob in a repo (through branch or commit rev).

    :param str repo_name: Github repository name such as 'Author/Repo'
    :param str rev: branch, commit or tag
    :param str path: the path to the file
    :return: URL
    :rtype: str
    """
    return "{}/{}/blob/{}/{}".format(GITHUB_URL, repo_name, rev, path)


def raw_file_url(repo_name, rev, path):
    """
    Forges Github URL to a blob raw content in a repo (through branch or commit rev).

    :param str repo_name: Github repository name such as 'Author/Repo'
    :param str rev: branch, commit or tag
    :param str path: the path to the file
    :return: URL
    :rtype: str
    """
    return "{}/{}/raw/{}/{}".format(GITHUB_URL, repo_name, rev, path)


def compare_url(repo_name, rev_a, rev_b):
    """
    Forges Github URL to compare rev_a to rev_b with link to files comparison.

    :param str repo_name: Github repository name such as 'Author/Repo'
    :param str rev_a: branch, commit or tag
    :param str rev_b: branch, commit or tag
    :return: URL
    :rtype: str
    """
    return "{}/{}/compare/{}...{}#files_bucket".format(GITHUB_URL, repo_name, rev_a, rev_b)
